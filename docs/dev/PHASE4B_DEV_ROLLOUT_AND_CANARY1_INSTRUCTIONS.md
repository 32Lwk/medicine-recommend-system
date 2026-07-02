# Phase 4b — dev 一括展開 & 本番カナリア 1 指示書

作成日: 2026-07-02

対象計画: [ux品質改善計画v2](../../.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md)

設計正本: [PHASE4B_ROUTER_PRIMARY_MIGRATION.md](PHASE4B_ROUTER_PRIMARY_MIGRATION.md)

---

## 方針（ユーザー承認済み）

| 項目 | 決定 |
|------|------|
| **カナリア用 LINE sid** | `U20a3beee49563dcd07bb3dd0fc1ca32c`（ログ上は `line:U20a3beee49563dcd07bb3dd0fc1ca32c`） |
| **登録者** | 本人のみ（dev / 本番カナリアとも実害リスクは低い） |
| **直近デプロイ先** | `medicine-recommend-dev`（`asia-northeast1`） |
| **監視期間** | **24h**（既定） |
| **dev での展開形態** | **カナリアではなく一括実装** — `CHAT_PIPELINE_V2_*_ALLOWLIST` / `PRIMARY_ALLOWLIST` は **設定しない** |
| **本番カナリア** | `medicine-recommend` へ移行する段階で ALLOWLIST を使う（本書 §5） |

### dev と本番の違い

```
medicine-recommend-dev（APP_ENV=development）
  → v2 / dispatch / LLM / PRIMARY / TRIM / Phase 2–3 UX 十二種は
    config/llm_flags.py により env 未設定でも自動 ON（ALLOWLIST 不要）
  → 明示 false のみ個別 OFF。ロールバックは env=false または旧リビジョン
  → **コードデプロイ必須**（env だけでは Phase 4b 実装は載らない）

medicine-recommend（APP_ENV=production）
  → v2 / PRIMARY / TRIM / UX 十二種は env で明示 ON + ALLOWLIST 限定
  → カナリア sid: line:U20a3beee49563dcd07bb3dd0fc1ca32c
```

**意図的に dev 自動 ON にしないもの**: Phase 1 / 1b の `LATENCY_*`（A/B 計測用・既定 OFF のまま）

---

## 参照スクリプト・検証

| ファイル | 用途 |
|----------|------|
| [scripts/verify_v2_canary_flags.py](../../scripts/verify_v2_canary_flags.py) | フラグ組み合わせの FLAGS_OK 検証 |
| [scripts/canary_sim_smoke.py](../../scripts/canary_sim_smoke.py) | 固定 sid 手動スモーク |
| [scripts/cloudrun_v2_env.example](../../scripts/cloudrun_v2_env.example) | env 変数一覧（**本番カナリア用**。dev 一括では ALLOWLIST 行は使わない） |
| [docs/ops/CLOUD_RUN_LLM_ENV.md](../ops/CLOUD_RUN_LLM_ENV.md) | サービス名・基本 LLM 変数 |
| [docs/ops/GITLAB_TEMPORARY_MIGRATION.md](../ops/GITLAB_TEMPORARY_MIGRATION.md) §3.5 | `--update-env-vars` 上書き事故防止 |

---

## §1 — dev 一括展開（medicine-recommend-dev）— 今回の主作業

### 1.1 目的

ローカルで検証済みの Phase 4b 構成（PRIMARY + LEGACY_FALLBACK_TRIM + Phase 3 八種）を **dev Cloud Run に一括反映**し、24h 監視する。

### 1.2 dev で必要な env（コード反映後）

**必須**: `APP_ENV=development`（タイポ `developmen` 等は修正すること）

**不要**（`config/llm_flags.py` の開発ランタイム自動 ON により省略可）:

- `CHAT_PIPELINE_V2` および v2 サブフラグ（DISPATCH / LLM）
- `CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY` / `CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM`
- Phase 3 八種（`RECO_LOW_RISK_HEADACHE` 等）
- Phase 2 四種（`SAFETY_VIOLENCE_CONTEXT_GUARD` 等）

検証:

```powershell
$env:APP_ENV="development"
# PRIMARY / TRIM / Phase3 等は unset のまま
python scripts/verify_v2_canary_flags.py
# → FLAGS_OK (dev auto-on)
```

**設定しないもの（dev 一括）**

- `CHAT_PIPELINE_V2_ALLOWLIST`
- `CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST`
- `CHAT_PIPELINE_V2_*_DENYLIST`（ロールバック時のみ）

既に手動投入済みの PRIMARY / Phase3 等は **削除してよい**（重複設定）。`APP_ENV` タイポ修正と **GitLab push → Cloud Build** によるコード反映が先決。

<details>
<summary>旧手順: env 手動投入リスト（コード未反映時の暫定）</summary>

```bash
CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY=true
CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM=true
RECO_LOW_RISK_HEADACHE=true
ROUTING_STORE_PROCUREMENT=true
ROUTING_CONCIERGE_INTENT=true
ROUTING_CONCIERGE_FOLLOWUP=true
UX_CORRECTION_DELETE_CANCEL=true
UX_SESSION_OPS_REAL_DATA=true
UX_PROGRESSIVE_CLARIFICATION=true
UX_RECO_DEDUP=true
```

</details>

### 1.3 デプロイ前チェックリスト

- [x] 現行 `medicine-recommend-dev` の env をエクスポート・バックアップ（`gcloud run services describe`）
- [x] `--update-env-vars` 使用（`--set-env-vars` は禁止 — 既存キー消失）
- [x] `OPENAI_API_KEY` / `DATABASE_URL` 等が消えていないことをデプロイ後に確認
- [x] ベースライン保存: `log/analysis/2026-07-02_dev_baseline_pre-p4b-rollout_service.json` / `_env.json`

### 1.4 デプロイ後スモーク（LINE sid）

カナリア sid で実機確認（dev 一括でもこの sid でよい）:

```powershell
$env:CANARY_SID="line:U20a3beee49563dcd07bb3dd0fc1ca32c"
python scripts/canary_sim_smoke.py --base-url https://<medicine-recommend-dev-url>/
```

期待:

- physical / store（または concierge / session_ops）で **dispatch handled**
- `/health` 200、`/admin/system_status` で DB available

### 1.5 24h 監視 KPI

| KPI | 閾値 |
|-----|------|
| dispatch_success_rate | ≥ 92% |
| handler None | 0 |
| legacy_fallback_trimmed 急増 | なし |
| shadow_regression | ≤ 0.5% または既知 exempt のみ |
| 重大安全事故（緊急誤検知・チャネル不整合） | 0 |

### 1.6 ロールバック（dev）

フラグのみ（コード revert 不要）:

1. `CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY=false`
2. `CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM=false`
3. または Cloud Run 直前リビジョンへトラフィック 100%

---

## §2 — `/admin` からの設定（将来実装・別タスク）

**現状**: Phase 4b フラグは **環境変数のみ**。`/admin` からの変更 UI は未実装。

**要件（ユーザー依頼）**: 運用者が `/admin` から次を確認・設定できるようにする（**本ドキュメント作成時点ではコード変更なし。実装は別 Agent タスク**）。

| 項目 | 想定 UI |
|------|---------|
| 現在の v2 / PRIMARY / TRIM / Phase3 フラグ状態 | 読み取り専用表示（`system_status` 拡張または専用 API） |
| 本番カナリア sid 一覧 | `CHAT_PIPELINE_V2_ALLOWLIST` / `PRIMARY_ALLOWLIST` の表示（マスク可） |
| カナリア sid 追加・削除 | **本番のみ** — Cloud Run env 更新をトリガーするか、運用手順リンクを表示 |
| dev 一括モード | 「ALLOWLIST 不要（development 全セッション）」の説明を固定表示 |
| ロールバック | PRIMARY OFF / 直前リビジョンへのリンクまたは Runbook 表示 |

実装時の参照: `templates/admin_chat.html`, `static/js/admin_chat.js`, `config/llm_flags.py`

**Agent 向け実装プロンプト（別セッション）** は本書末尾 §7 を使用。

---

## §3 — dev 展開完了後の判定

| 結果 | 次アクション |
|------|----------------|
| 24h KPI Go | 本番カナリア 1（§5）の承認・実施 |
| No-Go | PRIMARY/TRIM を OFF にロールバック、原因調査 |
| 既知揺れのみ（followup keyword） | ルーティング退行でなければ Go 可 |

---

## §4 — Agent 用指示文（dev 一括展開・コピペ用）

```
Agent モード。Build は使わない。git commit は依頼時のみ。

指示書: @docs/dev/PHASE4B_DEV_ROLLOUT_AND_CANARY1_INSTRUCTIONS.md
設計: @docs/dev/PHASE4B_ROUTER_PRIMARY_MIGRATION.md
運用: @docs/ops/CLOUD_RUN_LLM_ENV.md

## タスク: medicine-recommend-dev への Phase 4b 一括展開

### 承認済みパラメータ
- デプロイ先: medicine-recommend-dev (asia-northeast1)
- LINE sid（実機スモーク用）: line:U20a3beee49563dcd07bb3dd0fc1ca32c
- 展開形態: dev 一括（ALLOWLIST 系 env は設定しない）
- 監視: 24h

### 実施手順
1. 現行 env をバックアップ（gcloud describe）
2. §1.2 の env のみ update-env-vars でマージ（ALLOWLIST 禁止）
3. GitLab/Cloud Build 経由でデプロイ（既存パイプラインに従う）
4. /health, /admin/system_status 確認
5. canary_sim_smoke.py で line:U20a3beee49563dcd07bb3dd0fc1ca32c スモーク
6. 24h 監視 KPI を §1.5 に従い記録
7. plan v2 と PHASE4B_ROUTER_PRIMARY_MIGRATION.md に結果追記

### やらないこと
- medicine-recommend（本番）へのデプロイ（別承認）
- ALLOWLIST / PRIMARY_ALLOWLIST の dev 設定
- sync_legacy / Orchestrator 削除
- /admin UI 実装（§7 は別タスク）
- 新規 regex/probe

### 完了報告
- env 差分、リビジョン、スモーク結果
- dispatch % / shadow_regression %（累積 + 直近150）
- 24h KPI または監視開始時点の中間値
- 本番カナリア 1 着手 Go/No-Go
```

---

## §5 — 本番カナリア 1（medicine-recommend）— dev Go 後

dev 24h Go のあと、本番は **ALLOWLIST カナリア** で実施する。

### 5.1 env（本番のみ）

```bash
APP_ENV=production
CHAT_PIPELINE_V2=true
CHAT_PIPELINE_V2_ALLOWLIST=line:U20a3beee49563dcd07bb3dd0fc1ca32c
CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY=true
CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST=line:U20a3beee49563dcd07bb3dd0fc1ca32c
CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM=true
# Phase 3 八種（§1.2 と同一）
```

### 5.2 手順・KPI・ロールバック

[PHASE4B_ROUTER_PRIMARY_MIGRATION.md §4b-5b](PHASE4B_ROUTER_PRIMARY_MIGRATION.md) の「Cloud Run 設定手順」「カナリア 1 監視 KPI」「ロールバック Runbook」に従う。

### 5.3 Agent 用指示文（本番カナリア 1・dev Go 後に使用）

```
Agent モード。Build は使わない。

指示書: @docs/dev/PHASE4B_DEV_ROLLOUT_AND_CANARY1_INSTRUCTIONS.md §5
前提: medicine-recommend-dev 24h KPI Go

## タスク: 本番カナリア 1
- サービス: medicine-recommend (asia-northeast1)
- ALLOWLIST: line:U20a3beee49563dcd07bb3dd0fc1ca32c のみ
- 監視: 24h
- デプロイ前ベースライン: log/analysis/YYYY-MM-DD_prod_baseline_pre-canary1.json

§5.1 env をマージ → デプロイ → スモーク → 24h 監視 → plan 追記
ロールバック: PRIMARY_ALLOWLIST 空 or 直前リビジョン
```

---

## §6 — カナリア 2 & p4-unify 完了

| 段階 | 条件 |
|------|------|
| **カナリア 2** | カナリア 1 の 24h Go 後、ALLOWLIST を約 10% 相当まで拡大 |
| **p4-unify completed** | カナリア 2 Go + legacy 物理削除（4b-5c）完了後、plan frontmatter を `completed` に |

---

## §7 — Agent 用指示文（/admin 設定 UI・別タスク）

コード変更が許可された別セッションで実施。

```
Agent モード。

要件: @docs/dev/PHASE4B_DEV_ROLLOUT_AND_CANARY1_INSTRUCTIONS.md §2

## 目的
/admin から Phase 4b フラグ状態の確認と、本番カナリア sid の運用支援 UI を追加。

## スコープ
- 読み取り: CHAT_PIPELINE_V2 / PRIMARY / TRIM / Phase3 八種の effective 状態
- 表示: 本番 ALLOWLIST / PRIMARY_ALLOWLIST（env 由来・マスク可）
- dev 一括: 「development 全セッション・ALLOWLIST 不要」の説明
- 書き込み: Cloud Run env を直接変えず、Runbook リンク + コピー用 gcloud 例で可（安全優先）
- ロールバック手順へのリンク

## やらないこと
- 本番 env の無承認自動変更
- フラグの永続化を DB に移す（初版は env 正本のまま）

## 検証
- /admin で表示確認
- verify_v2_canary_flags.py と表示内容の整合
```

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-07-02 | 初版。dev 一括 / 本番カナリア分離、sid 承認、Agent 指示文、/admin 将来タスク |
| 2026-07-02 | **§1 実施** — `medicine-recommend-dev` へ Phase 4b 一括展開（rev `00142-ln2`）。監視: [2026-07-02_dev_p4b-rollout_monitoring.json](../../log/analysis/2026-07-02_dev_p4b-rollout_monitoring.json) |
