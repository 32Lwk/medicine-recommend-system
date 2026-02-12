# GCP（Cloud Run）移行計画

**前提**: クラウド移行比較ドキュメント（`クラウド移行比較_Render_AWS_GCP.md`）に基づく GCP Cloud Run への移行  
**現状**: Render（Web Service + PostgreSQL）、Flask + Gunicorn、長時間リクエスト（推奨 25–30 秒、タイムアウト 120 秒）

---

## 移行完了後の状況（2026年2月）

- **アプリ**: GCP Cloud Run へ移行済み。GitHub 連携で継続的デプロイ。
- **データベース**: **Neon PostgreSQL** を採用（Cloud SQL は使用しない）。無料枠で運用可能。
- **本番 URL**: [https://medicine-recommend-340042923793.asia-northeast1.run.app/](https://medicine-recommend-340042923793.asia-northeast1.run.app/)

以下は移行時の計画・手順の記録です。Neon を採用したため、Cloud SQL 関連の手順は参考用として残しています。

---

## 1. 移行の全体像

| フェーズ | 内容 | 目安期間 |
|----------|------|----------|
| **Phase 0** | 準備（GCPプロジェクト・課金・IAM） | 1–2 日 |
| **Phase 1** | アプリ側: Docker 化・PORT 対応 | 2–3 日 |
| **Phase 2** | GCP: Cloud SQL・Secret Manager・Artifact Registry | 1–2 日 |
| **Phase 3** | GCP: Cloud Run サービス作成・CI/CD | 2–3 日 |
| **Phase 4** | データ移行・切り替え・検証 | 2–3 日 |

---

## 2. GCP側で行うこと（詳細）

GCP コンソールまたは `gcloud` CLI で実施する作業です。

### 2.1 プロジェクト・課金・API 有効化（Phase 0）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.1.1 | **GCP プロジェクト作成** | コンソール: プロジェクト選択 → 新規プロジェクト。プロジェクト ID を控える（例: `medicine-recommend-prod`）。 |
| 2.1.2 | **課金アカウントのリンク** | プロジェクトに課金アカウントをリンク。新規なら $300 クレジットが付与される場合あり。 |
| 2.1.3 | **必要な API の有効化** | 以下を有効化: Cloud Run API, Cloud SQL Admin API, Secret Manager API, Artifact Registry API, Cloud Build API（CI/CD で使う場合）。<br>例: `gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=PROJECT_ID` |

### 2.2 IAM・サービスアカウント（Phase 0）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.2.1 | **Cloud Run 用サービスアカウント作成** | IAM → サービスアカウント作成。名前例: `cloud-run-app`。Cloud Run の「サービスアカウント」として指定する。 |
| 2.2.2 | **Secret Manager 参照権限** | 上記サービスアカウントにロール `Secret Manager シークレットアクセス権` を付与。Cloud Run がシークレットをマウントするために必要。 |
| 2.2.3 | **Cloud SQL クライアント権限（オプション）** | Cloud SQL に「Cloud SQL クライアント」で接続する場合、同じサービスアカウントに `Cloud SQL クライアント` ロールを付与。 |

### 2.3 Secret Manager（Phase 2）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.3.1 | **シークレットの作成** | Secret Manager で以下を作成し、値を登録: `OPENAI_API_KEY`, `DEEPL_API_KEY`（使用時）, `SECRET_KEY`, `DATABASE_URL`（本番用接続文字列）。 |
| 2.3.2 | **バージョン管理** | 各シークレットは「バージョン」で管理。Cloud Run では「latest」または特定バージョンを指定可能。 |

### 2.4 データベース: Neon を採用した場合（推奨・本プロジェクトで採用）

本プロジェクトでは **Neon PostgreSQL**（サーバーレス）を採用しています。Cloud SQL は使用しません。

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.4.1 | **Neon でプロジェクト作成** | [Neon](https://neon.tech) でサインアップし、プロジェクト作成。リージョンは Tokyo や Singapore などアジアを選択するとレイテンシが良い。 |
| 2.4.2 | **接続文字列の取得** | Neon コンソールの「Connect」から Connection string をコピー。**Connection pooling** を有効にしたプール接続（ホスト名に `-pooler` が付く）を推奨。 |
| 2.4.3 | **DATABASE_URL の設定** | Cloud Run の環境変数に `DATABASE_URL` を設定。形式例: `postgresql://REDACTED:REDACTED@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require` |
| 2.4.4 | **Cloud SQL 接続は不要** | Neon 利用時は Cloud Run の「Cloud SQL 接続」は追加しない。 |

**Neon 無料枠の接続数について**

- Neon のプラン表には「接続数」の単独項目はありません。接続は **接続プール（PgBouncer）** と **Postgres の max_connections** で決まります。
- **プール経由（推奨）**: PgBouncer は最大 **10,000 クライアント接続** を受け付けます。実際の Postgres への接続数は compute サイズに応じた `max_connections` で制限され、その約 90% がプールサイズになります。
- **Compute サイズと max_connections**（[Neon ドキュメント](https://neon.tech/docs/connect/connection-pooling) より）:
  - 0.25 CU: **104**（アプリ利用は約 **97**、7 は予約）
  - 0.5 CU: 209
  - 1 CU: 419
  - 2 CU: 839
- 無料枠は 100 CU-hours/月・最大 2 CU までオートスケール。スケールゼロ時は 0.25 CU 程度で起動することが多いため、**実質的には約 97 本** を目安にするとよいです。
- **推奨**: Cloud Run のようにインスタンスが増減する場合は、アプリ側の `DB_MAX_CONNECTIONS` を **5〜10** 程度に抑えると、無料枠内で安定しやすくなります。

### 2.4' Cloud SQL（PostgreSQL）を使う場合（参考・本プロジェクトでは未使用）

Neon の代わりに Cloud SQL を使う場合の手順です。

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.4'.1 | **Cloud SQL インスタンス作成** | Cloud SQL → PostgreSQL を選択。リージョンは Cloud Run と同じ（例: `asia-northeast1`）にするとレイテンシが良い。 |
| 2.4'.2 | **DB 作成・ユーザ設定** | インスタンス内にデータベースとユーザを作成。`DATABASE_URL` を Secret Manager に登録。 |
| 2.4'.3 | **Cloud Run で Cloud SQL 接続を追加** | 「接続」タブで Cloud SQL インスタンスを追加。Unix ソケット用の `DATABASE_URL` を設定。 |

### 2.5 Artifact Registry（Phase 2）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.5.1 | **リポジトリ作成** | Artifact Registry → リポジトリ作成。形式: Docker。リージョン: Cloud Run と同一（例: `asia-northeast1`）。リポジトリ名例: `medicine-recommend`。 |
| 2.5.2 | **Cloud Build の権限** | CI/CD で Cloud Build から push する場合、Cloud Build のデフォルト SA に「Artifact Registry ライター」を付与（多くの場合プロジェクトで自動付与済み）。 |

### 2.6 Cloud Run サービス（Phase 3）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.6.1 | **サービス作成** | Cloud Run → サービス作成。「コンテナイメージを選択」で Artifact Registry のイメージを指定。または「継続的デプロイ」で GitHub 連携を設定。 |
| 2.6.2 | **リージョン** | 例: `asia-northeast1`（東京）。ユーザが日本主体なら東京で問題なし。 |
| 2.6.3 | **認証** | 「未認証の呼び出しを許可」するか、IAM で「Cloud Run 起動元」を制限するか選択。 |
| 2.6.4 | **リクエストタイムアウト** | **120 秒以上**に設定（本アプリ要件）。最大 60 分まで可能。コンソール: コンテナの「リクエストのタイムアウト」を 120 秒に。 |
| 2.6.5 | **メモリ・vCPU** | 例: 0.5 vCPU, 512 MiB（現行 Render に合わせる）。必要に応じて 1 vCPU / 1 GiB に変更。 |
| 2.6.6 | **最小インスタンス数** | 0 にするとスケールゼロ（コスト削減）。コールドスタートを避けたい場合は 1 に設定（その分 24 時間課金）。 |
| 2.6.7 | **最大インスタンス数** | 同時アクセスに応じて設定（例: 10）。 |
| 2.6.8 | **環境変数** | `PORT=8080` は Cloud Run が自動設定。その他、非機密のもの（例: `GUNICORN_TIMEOUT=120`, `DB_MIN_CONNECTIONS=2`）は「環境変数」で設定。 |
| 2.6.9 | **シークレットのマウント** | 「シークレット」タブで、Secret Manager のシークレットを「環境変数としてマウント」または「ボリュームとしてマウント」を選択。例: `OPENAI_API_KEY` → 環境変数 `OPENAI_API_KEY`。 |
| 2.6.10 | **Cloud SQL 接続** | **Neon 利用時は不要**。Cloud SQL を使う場合のみ「接続」タブでインスタンスを追加。アプリ側では `DATABASE_URL` で接続。 |

### 2.7 CI/CD（Cloud Build）（Phase 3）※GitHub 連携する場合

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.7.1 | **GitHub リポジトリ接続** | Cloud Build → トリガー → リポジトリを接続（GitHub の認証・権限付与）。 |
| 2.7.2 | **トリガー作成** | ブランチ `main` への push でビルド→Artifact Registry に push→Cloud Run にデプロイ、といったトリガーを作成。 |
| 2.7.3 | **cloudbuild.yaml** | リポジトリに `cloudbuild.yaml` を置く場合は「こちら側」の作業。GCP 側ではトリガーがそのファイルを参照するように設定。 |

### 2.8 監視・ログ（Phase 3 以降）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 2.8.1 | **Cloud Logging** | Cloud Run のログは自動で Cloud Logging に送信。ログベースのメトリクスやアラートを必要に応じて設定。 |
| 2.8.2 | **Cloud Monitoring** | ダッシュボードでリクエスト数・レイテンシ・エラー率を確認。予算アラートを設定すると安心。 |

---

## 3. こちら側（プロジェクト・チーム）で行うこと（詳細）

リポジトリ・コード・設定ファイルの変更です。

### 3.1 Docker 化（Phase 1）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.1.1 | **Dockerfile の作成** | プロジェクトルートに `Dockerfile` を新規作成。内容の要点:<br>• ベースイメージ: `python:3.11-slim` 等。<br>• `WORKDIR /app`。<br>• `requirements.txt` をコピーして `pip install -r requirements.txt`。<br>• アプリコード（`app.py`, `config/`, `src/`, `static/`, `templates/`, `data/` 等）をコピー。<br>• **`PORT` は 8080 で listen**（Cloud Run のデフォルト）。<br>• `CMD` で `start.sh` を実行、または直接 `gunicorn --bind 0.0.0.0:${PORT:-8080} ... app:app`。 |
| 3.1.2 | **.dockerignore の作成** | `data/` の一部、`log/`, `.git`, `__pycache__`, `.env`, `*.pyc` 等を除外してビルドを軽くし、セキュリティリスクを減らす。 |
| 3.1.3 | **PORT の扱い** | `start.sh` で `PORT=${PORT:-5000}` となっている場合は、**Cloud Run では 8080** が注入されるので、`PORT=${PORT:-8080}` に変更するか、そのままでも環境変数で 8080 が渡れば問題なし。GCP は自動で `PORT=8080` を設定するため、既存の `PORT` 読み取りで対応可能。 |

### 3.2 アプリ設定の確認（Phase 1）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.2.1 | **ステートレス化** | セッションは既に DB 保存想定であれば変更不要。ファイルシステムに永続化しているものがあれば、Cloud Run は揮発性のため S3/GCS や DB に寄せる。 |
| 3.2.2 | **ヘルスチェック** | Cloud Run は `GET /` などでヘルスチェック可能。`healthCheckPath: /` と同等のルートが応答することを確認。 |
| 3.2.3 | **Gunicorn タイムアウト** | 既に 120 秒で設定済み。Cloud Run の「リクエストのタイムアウト」も 120 秒以上にすることは GCP 側で実施。 |

### 3.3 環境変数・シークレットの整理（Phase 1–2）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.3.1 | **一覧の洗い出し** | Render で設定している環境変数・シークレットを一覧化: `DATABASE_URL`, `OPENAI_API_KEY`, `DEEPL_API_KEY`, `SECRET_KEY`, `GUNICORN_*`, `DB_MIN_CONNECTIONS`, `DB_MAX_CONNECTIONS` 等。 |
| 3.3.2 | **ドキュメント化** | どの変数を Secret Manager に登録し、どの変数を Cloud Run の「環境変数」で渡すかメモ。機密はすべて Secret Manager。 |
| 3.3.3 | **アプリの変更** | アプリは従来どおり環境変数から読み取るだけなので、原則コード変更は不要。Cloud Run で「シークレットを環境変数としてマウント」すれば同じ名前で参照できる。 |

### 3.4 データベース移行（Phase 4）

**Neon を採用した場合**

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.4.1 | **Neon でプロジェクト・DB 作成** | Neon コンソールでプロジェクト作成。接続文字列（プール接続推奨）を取得。 |
| 3.4.2 | **既存データがある場合** | Render 等から `pg_dump` でダンプし、Neon の DB に `psql` でリストア。不要ならアプリ起動時の `initialize_tables()` でテーブル自動作成。 |
| 3.4.3 | **接続文字列の切り替え** | Cloud Run の環境変数 `DATABASE_URL` を Neon の接続文字列に更新。 |

**Cloud SQL を使う場合（参考）**

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.4'.1 | **Render PostgreSQL のダンプ** | Render の DB から `pg_dump` でダンプ取得。 |
| 3.4'.2 | **Cloud SQL へのリストア** | Cloud SQL の PostgreSQL にリストア。 |
| 3.4'.3 | **接続文字列の切り替え** | 本番の `DATABASE_URL` を Cloud SQL 用に更新。 |

### 3.5 CI/CD 設定（Phase 3）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.5.1 | **cloudbuild.yaml の作成** | リポジトリルートに `cloudbuild.yaml` を追加。例: (1) Docker ビルド (2) Artifact Registry に push (3) Cloud Run にデプロイ。`$PROJECT_ID`, `$REGION`, サービス名は変数化しておくとよい。 |
| 3.5.2 | **代替: GitHub Actions** | Cloud Build の代わりに GitHub Actions で `gcloud run deploy` や `gcloud builds submit` を実行する方法も可。その場合は GCP の「ワークロード ID 連携」またはサービスアカウントキー（慎重に管理）で認証。 |

### 3.6 ドキュメント・運用（Phase 4）

| # | 作業内容 | 手順・補足 |
|---|----------|------------|
| 3.6.1 | **README / 運用ドキュメント更新** | デプロイ手順、環境変数一覧、Cloud Run の URL、障害時の確認ポイントを記載。 |
| 3.6.2 | **render.yaml の扱い** | 移行完了後も参照用に残すか、`docs/` に退避するか方針を決める。 |

---

## 4. 作業チェックリスト（役割別サマリ）

### GCP側（インフラ・コンソール）

- [ ] プロジェクト作成・課金リンク
- [ ] 必要な API 有効化（Cloud Run, Artifact Registry, Cloud Build。Neon 利用時は Cloud SQL API は不要）
- [ ] サービスアカウント作成・Secret Manager 権限付与
- [ ] Secret Manager にシークレット登録（任意。環境変数で渡す場合は不要）
- [ ] **Neon 利用時**: Cloud SQL は作成しない。Neon でプロジェクト作成し接続文字列を取得。
- [ ] Artifact Registry リポジトリ作成
- [ ] Cloud Run サービス作成（イメージ、タイムアウト 120 秒、メモリ・vCPU、環境変数に DATABASE_URL 等。Neon 利用時は Cloud SQL 接続は追加しない）
- [ ] Cloud Build トリガー設定（継続的デプロイ）
- [ ] 監視・予算アラートの設定（推奨）

### こちら側（開発・リポジトリ）

- [ ] Dockerfile 作成（PORT 8080、Gunicorn 起動）
- [ ] .dockerignore 作成
- [ ] start.sh の PORT デフォルトを 8080 に変更（任意・推奨）
- [ ] 環境変数一覧のドキュメント化
- [ ] Cloud Build は Cloud Run の「継続的デプロイ」で自動生成されるため、追加設定は不要の場合あり
- [ ] **Neon 利用時**: Neon の接続文字列を Cloud Run の DATABASE_URL に設定。既存データがある場合は pg_dump → Neon へリストア。
- [ ] 本番 DATABASE_URL の切り替え（Neon のプール接続推奨）
- [ ] DB_MAX_CONNECTIONS を 5〜10 程度に設定（Neon 無料枠推奨）
- [ ] 動作検証（ヘルスチェック、長時間リクエスト、DB 接続、外部 API）
- [ ] README / 運用ドキュメント更新

---

## 5. 移行後の確認項目

- ルート `GET /` が 200 で返る（ヘルスチェック）
- 推奨処理（25–30 秒）が 120 秒以内に完了する
- セッション・DB が期待どおり動作する
- ログが Cloud Logging に出力されている
- コストが想定範囲（例: 月 $0–15 の軽トラフィック）に収まっているか確認

---

## 6. 参考

- 比較元: `docs/クラウド移行比較_Render_AWS_GCP.md`
- [Cloud Run の料金](https://cloud.google.com/run/pricing)
- [Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Neon - Serverless Postgres](https://neon.tech)
- [Neon プラン・利用量](https://neon.tech/docs/introduction/usage-metrics)
- [Neon 接続プール（接続数の考え方）](https://neon.tech/docs/connect/connection-pooling)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)（Cloud SQL を利用する場合）
