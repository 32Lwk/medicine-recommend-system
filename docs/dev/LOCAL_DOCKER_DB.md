# ローカル Docker Postgres / Neon dev 分離

## 構成

| 環境 | DB | 接続文字列の置き場所 |
|------|-----|---------------------|
| **ローカル** | Docker Postgres (`docker compose up -d`) | `.env` の `DATABASE_URL` |
| **Cloud Run dev** | Neon dev インスタンス | `gcloud run services update` / Secret Manager |

ローカル `.env` 例:

```env
DATABASE_URL=postgresql://medicine:medicine@localhost:5432/medicine_recommend
```

## 初回起動

```powershell
python app.py
```

`DATABASE_URL` が `localhost` / `127.0.0.1` のとき、`app.py` は自動で:

1. `docker compose up -d`
2. Postgres 接続可能になるまで待機（既定 60 秒）
3. `sslmode=disable` を自動付与（ローカル Docker は SSL 非対応のため）

を行ってから uvicorn を起動します。手動で Docker を上げる必要はありません。

無効化: `.env` に `LOCAL_DOCKER_DB_AUTO=0`

`database.py` の `initialize_tables()` がスキーマを作成する。初回移行済みならデータも入っている。

## 旧 Neon → 分離移行（再実行用）

1. **全データ → ローカル Docker**

```powershell
$src = "<旧 Neon DATABASE_URL>"
docker run --rm -v "${PWD}/tmp_db_migration:/backup" postgres:17 `
  pg_dump $src -Fc --no-owner --no-acl -f /backup/full.dump
docker run --rm --network medicine-recommend_default `
  -v "${PWD}/tmp_db_migration:/backup" -e PGPASSWORD=medicine postgres:17 `
  pg_restore -h postgres -U medicine -d medicine_recommend `
  --clean --if-exists --no-owner --no-acl /backup/full.dump
```

2. **dev 用のみ → Neon dev**（`line:%` セッション + feedback + global_state + dedup）

```powershell
$env:LOCAL_DATABASE_URL = "postgresql://medicine:medicine@localhost:5432/medicine_recommend"
$env:DEV_DATABASE_URL = "<Neon dev pooler URL>?sslmode=require"
docker run --rm --network medicine-recommend_default `
  -e DEV_DATABASE_URL -e LOCAL_DATABASE_URL `
  -v "${PWD}:/app" -w /app python:3.11-slim `
  bash -c "pip install -q psycopg2-binary && python scripts/migrate_dev_neon_selective.py"
```

## Cloud Run dev の DATABASE_URL 切替

`GITLAB_TEMPORARY_MIGRATION.md` §3.5 を読み、**既存 env を消さない**ようマージして更新する。

```powershell
gcloud run services update medicine-recommend-dev `
  --region=asia-northeast1 `
  --project=<GCP_PROJECT_ID> `
  --update-env-vars="DATABASE_URL=<Neon dev URL>"
```

## dev Neon に含めるデータ（選別基準）

`session_manager.is_v2_local_test_session` と同等:

- **除外（v2 テスト）**: `username` が `v2-test-` 始まり / `User-Agent` に `local-v2-chat-test` / `session_metadata.v2_local_test` / `session_metadata.v2_test_scenario`
- **移行対象**: 上記以外の `sessions` 全件 + `feedback_reports` / `global_state` / `line_webhook_dedup` 等

旧 Neon では数値 `session_id` の Web セッション **1,044 件はすべて v2 テスト**（ローカル `local_v2_chat_test_runner` が旧 DB に書き込んだもの）。実データは主に `line:*`（12 件）と feedback 等。

再移行: `scripts/migrate_dev_neon_selective.py`（`SOURCE_DATABASE_URL` + `DEV_DATABASE_URL`）

## 注意

- `tmp_db_migration/` はダンプに PII が含まれるため Git 追跡しない（`.gitignore` 済み）
- Neon Free の egress 上限に達すると dump 元が読めなくなる。移行は上限前に実施する
