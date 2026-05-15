"""
管理画面向け LLM 設定・ゴールデンケース（Neon）
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _db():
    from src.services.database import get_database
    return get_database()


def ensure_llm_tables() -> bool:
    db = _db()
    conn = db.get_connection() if db else None
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS golden_test_cases (
                id SERIAL PRIMARY KEY,
                input_text TEXT NOT NULL,
                expected_category VARCHAR(32) NOT NULL,
                expected_subcategory VARCHAR(64),
                expected_medicines JSONB,
                source VARCHAR(32) DEFAULT 'pharmacist',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS medicine_compare_logs (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255),
                rule_medicines JSONB,
                gpt_medicines JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_golden_created ON golden_test_cases(created_at DESC);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_compare_logs_created ON medicine_compare_logs(created_at DESC);"
        )
        conn.commit()
        cur.close()
        db.put_connection(conn)
        try:
            from src.services.budget_guard import ensure_llm_admin_defaults
            ensure_llm_admin_defaults()
        except Exception as e:
            logger.debug("ensure_llm_admin_defaults: %s", e)
        return True
    except Exception as e:
        logger.error("ensure_llm_tables failed: %s", e)
        if conn:
            conn.rollback()
            db.put_connection(conn)
        return False


def list_golden_cases(limit: int = 500) -> List[Dict[str, Any]]:
    db = _db()
    conn = db.get_connection() if db else None
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, input_text, expected_category, expected_subcategory,
                   expected_medicines, source, notes, created_at
            FROM golden_test_cases
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        db.put_connection(conn)
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "input_text": row[1],
                "expected_category": row[2],
                "expected_subcategory": row[3],
                "expected_medicines": row[4],
                "source": row[5],
                "notes": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
            })
        return result
    except Exception as e:
        logger.error("list_golden_cases: %s", e)
        if conn:
            db.put_connection(conn)
        return []


def insert_golden_case(data: Dict[str, Any]) -> Optional[int]:
    db = _db()
    conn = db.get_connection() if db else None
    if not conn:
        return None
    try:
        cur = conn.cursor()
        meds = data.get("expected_medicines")
        if meds is not None and not isinstance(meds, str):
            meds = json.dumps(meds, ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO golden_test_cases
            (input_text, expected_category, expected_subcategory, expected_medicines, source, notes)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (
                data["input_text"],
                data["expected_category"],
                data.get("expected_subcategory"),
                meds,
                data.get("source", "pharmacist"),
                data.get("notes"),
            ),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        db.put_connection(conn)
        return new_id
    except Exception as e:
        logger.error("insert_golden_case: %s", e)
        if conn:
            conn.rollback()
            db.put_connection(conn)
        return None


def export_golden_jsonl() -> str:
    lines = []
    for case in list_golden_cases():
        lines.append(json.dumps(case, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")


def log_medicine_compare(session_id: str, rule_meds: List[str], gpt_meds: List[str]) -> bool:
    db = _db()
    conn = db.get_connection() if db else None
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO medicine_compare_logs (session_id, rule_medicines, gpt_medicines)
            VALUES (%s, %s::jsonb, %s::jsonb)
            """,
            (
                session_id,
                json.dumps(rule_meds, ensure_ascii=False),
                json.dumps(gpt_meds, ensure_ascii=False),
            ),
        )
        cutoff = datetime.now() - timedelta(days=90)
        cur.execute("DELETE FROM medicine_compare_logs WHERE created_at < %s", (cutoff,))
        conn.commit()
        cur.close()
        db.put_connection(conn)
        return True
    except Exception as e:
        logger.error("log_medicine_compare: %s", e)
        if conn:
            conn.rollback()
            db.put_connection(conn)
        return False
