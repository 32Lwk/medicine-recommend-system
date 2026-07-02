"""Migrate non-v2 data from source Postgres to Neon dev (Cloud Run)."""
from __future__ import annotations

import os
import sys

import psycopg2
import psycopg2.extras

SOURCE_URL = os.environ["SOURCE_DATABASE_URL"]
DEV_URL = os.environ["DEV_DATABASE_URL"]

# session_manager.is_v2_local_test_session と同等
KEEP_SESSION_WHERE = """
NOT (
    COALESCE(username, '') LIKE 'v2-test-%'
    OR COALESCE(user_agent, '') LIKE '%local-v2-chat-test%'
    OR COALESCE(session_metadata->>'v2_local_test', '') IN ('true', 't', '1')
    OR (
        session_metadata IS NOT NULL
        AND session_metadata ? 'v2_test_scenario'
    )
)
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS feedback_reports (
    id SERIAL PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(255),
    username VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    security_score FLOAT,
    feedback_text TEXT,
    is_google_form BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    negative_reason VARCHAR(64),
    metadata JSONB
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255),
    messages JSONB,
    user_attributes JSONB,
    last_activity TIMESTAMP NOT NULL,
    client_ip VARCHAR(255),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_active BOOLEAN DEFAULT TRUE,
    processing_status JSONB,
    line_feedback_pending JSONB,
    session_metadata JSONB
);
CREATE TABLE IF NOT EXISTS global_state (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS line_webhook_dedup (
    dedup_key VARCHAR(220) PRIMARY KEY,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS golden_test_cases (
    id SERIAL PRIMARY KEY,
    case_key VARCHAR(255) UNIQUE,
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS medicine_compare_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_feedback_reports_created_at ON feedback_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_reports_resolved ON feedback_reports(resolved);
CREATE INDEX IF NOT EXISTS idx_global_state_updated_at ON global_state(updated_at);
CREATE INDEX IF NOT EXISTS idx_line_webhook_dedup_seen_at ON line_webhook_dedup(seen_at);
"""


def _adapt_value(v):
    if isinstance(v, (dict, list, bool)):
        return psycopg2.extras.Json(v)
    return v


def _upsert_rows(dev_cur, table: str, rows: list[dict], conflict_col: str | None) -> int:
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    if conflict_col:
        update_set = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != conflict_col)
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_col}) DO UPDATE SET {update_set}"
        )
    else:
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    for row in rows:
        dev_cur.execute(sql, [_adapt_value(row[c]) for c in cols])
    return len(rows)


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s)",
        (table,),
    )
    return bool(cur.fetchone()["exists"])


def _fetch_all(cur, table: str, order_by: str) -> list[dict]:
    cur.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
    return cur.fetchall()


def main() -> int:
    if not SOURCE_URL or not DEV_URL:
        print("SOURCE_DATABASE_URL and DEV_DATABASE_URL required", file=sys.stderr)
        return 1

    src = psycopg2.connect(SOURCE_URL)
    dev = psycopg2.connect(DEV_URL)
    try:
        with dev.cursor() as dc:
            dc.execute(SCHEMA_SQL)
            for table in (
                "medicine_compare_logs",
                "golden_test_cases",
                "line_webhook_dedup",
                "global_state",
                "feedback_reports",
                "sessions",
            ):
                dc.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        dev.commit()

        with src.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sc:
            sc.execute(f"SELECT COUNT(*) AS n FROM sessions WHERE {KEEP_SESSION_WHERE}")
            keep_n = sc.fetchone()["n"]
            sc.execute(f"SELECT COUNT(*) AS n FROM sessions WHERE NOT ({KEEP_SESSION_WHERE})")
            skip_n = sc.fetchone()["n"]
            print(f"source sessions: keep={keep_n} skip_v2={skip_n}")

            sc.execute(f"SELECT * FROM sessions WHERE {KEEP_SESSION_WHERE} ORDER BY session_id")
            sessions = sc.fetchall()
            feedback = _fetch_all(sc, "feedback_reports", "id")
            global_state = _fetch_all(sc, "global_state", "key")
            dedup = _fetch_all(sc, "line_webhook_dedup", "dedup_key")
            golden = (
                _fetch_all(sc, "golden_test_cases", "id")
                if _table_exists(sc, "golden_test_cases")
                else []
            )
            compare = (
                _fetch_all(sc, "medicine_compare_logs", "id")
                if _table_exists(sc, "medicine_compare_logs")
                else []
            )

        with dev.cursor() as dc:
            n_sessions = _upsert_rows(dc, "sessions", sessions, "session_id")
            n_feedback = _upsert_rows(dc, "feedback_reports", feedback, "id")
            n_global = _upsert_rows(dc, "global_state", global_state, "key")
            n_dedup = _upsert_rows(dc, "line_webhook_dedup", dedup, "dedup_key")
            n_golden = _upsert_rows(dc, "golden_test_cases", golden, "id")
            n_compare = _upsert_rows(dc, "medicine_compare_logs", compare, "id")
            if feedback:
                dc.execute(
                    "SELECT setval(pg_get_serial_sequence('feedback_reports','id'), "
                    "(SELECT COALESCE(MAX(id), 1) FROM feedback_reports))"
                )
            if golden:
                dc.execute(
                    "SELECT setval(pg_get_serial_sequence('golden_test_cases','id'), "
                    "(SELECT COALESCE(MAX(id), 1) FROM golden_test_cases))"
                )
            if compare:
                dc.execute(
                    "SELECT setval(pg_get_serial_sequence('medicine_compare_logs','id'), "
                    "(SELECT COALESCE(MAX(id), 1) FROM medicine_compare_logs))"
                )
        dev.commit()

        print(
            "dev migrated:",
            f"sessions={n_sessions}",
            f"feedback={n_feedback}",
            f"global_state={n_global}",
            f"line_webhook_dedup={n_dedup}",
            f"golden_test_cases={n_golden}",
            f"medicine_compare_logs={n_compare}",
        )
    finally:
        src.close()
        dev.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
