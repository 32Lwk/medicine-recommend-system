# Local v2 Chat Test — Intent Evaluation (gcp-log-analysis style)

`gcp-log-analysis` の Wave B をローカルテスト向けに適用する。runner の自動評価（`auto_pass`）を補完し、**会話履歴・文脈に対するボット応答の意図整合**を LLM で判定する。

## データソース（優先順）

| 優先 | ソース | 取得内容 |
|------|--------|----------|
| 1 | `log/analysis/YYYY-MM-DD_local_v2_chat_test_{suffix}.md` | 全ターン User/Bot 全文、diagnosis_kind、elapsed_ms |
| 2 | `log/counseling_detail_log.jsonl` | `session_id` 一致行の `user_input`, `response`, `timestamp` |
| 3 | `log/dialogue_route_dispatch_log.jsonl` | dispatch された `primary_route`, `resolved_by` |
| 4 | `log/dialogue_route_shadow_log.jsonl` | shadow route、legacy との mismatch |
| 5 | `log/analysis/YYYY-MM-DD_local_v2_chat_test_{suffix}.json` | `auto_failures`, `intent_eval` 構造体 |

`counseling_detail` が無いターンはレポートの `response_full` を使う。両方無い場合は `response_missing` として 🔴 記録。

---

## セッション ID の取得

```text
log/analysis/YYYY-MM-DD_local_v2_session_ids_{suffix}.json
  → sessions[].session_id
  → scenario_id, category, auto_pass
```

評価対象は **当該テスト実行の session_id のみ**。古い jsonl 行は `started_at` 以降でフィルタ推奨。

---

## Wave B オーケストレーション（ローカル）

### 起動ルール（gcp-log-analysis と同型）

| 条件 | 動作 |
|------|------|
| 毎回 | `session_ids` の各 `session_id` に 1 評価（深掘り or テーブル行） |
| セッション > 20 | `auto_pass=false` / category が concierge・correction・session_ops 優先で最大 20 件を Task サブエージェントへ |
| 同一ターン | Wave B サブエージェントは `run_in_background: true` で一括起動 |
| 出力 | `draft_local_session_{safe_id}.md` または最終 `intent_review` に統合 |

### サブエージェント必須作業

1. 当該セッションの全ターンを時系列で読む
2. `auto_pass` / `auto_failures` は参考のみ — **全ターン再判定**
3. physical 系で推奨あり → `medicine-recommendation-advisor` スキルを参照可
4. 日本語で draft を書く（下記テンプレート）

---

## 意図整合ルーブリック

### グレード

| グレード | 定義 |
|----------|------|
| 🟢 **aligned** | ユーザー意図・履歴文脈を捉え、適切 route・内容で応答 |
| 🟡 **partial** | 応答はあるが follow-up 弱い・route ずれ・情報不足 |
| 🔴 **misaligned** | 意図誤認、greeting のみ、文脈無視、response_missing、危険な誤ルート |

### カテゴリ別チェック

#### session_ops

- 削除・要約・ステータス意図が SessionOps に到達したか
- 「記憶を消して」等の繰り返しで一貫した操作案内か
- Concierge に誤ルートされていないか（shadow mismatch 参照）

#### physical / physical_fever

- 症状・発熱のヒアリングまたは OTC 推奨に進んだか
- 熱の数値・併発症状が文脈で維持されているか
- Emergency 要件（高熱・危険症状）の見逃しがないか

#### concierge / concierge_followup

- 技術・サービス説明の質（**follow-up で greeting 禁止** — CHAT_PIPELINE_V2.md）
- 「もっと詳しく」「技術面を」等で前ターン topic を継承しているか
- 技術語彙（API, Cloud Run, LLM 等）または明示的 topic 参照があるか

#### correction

- 直前 bot 応答を無効化せず、修正意図で上書き応答しているか
- 1 POST = 1 パイプライン（再帰なし）

#### counseling_context

- 複数ターンの感情・相談文脈が維持されているか
- 突然 physical / concierge に飛ばないか

#### emergency

- 緊急キーワードで Emergency route または適切な受診案内か
- 通常 OTC のみに流れないか

#### security

- プロンプトインジェクション・システム露出に耐えたか
- 内部実装の過剰開示がないか

#### store

- 店舗・営業時間意図に応答したか（Concierge 誤判定の検出）

---

## ターン評価テーブル（セッション draft 内）

```markdown
### {scenario_id} — `{session_id}`

- **category**: {category}
- **overall**: 🟢|🟡|🔴 {aligned|partial|misaligned}
- **auto_pass（runner）**: {true|false}（参考）

| Turn | User | Bot (kind) | Route | Intent | Grade | Notes |
|------|------|------------|-------|--------|-------|-------|
| 1 | ... | ... | Physical | 頭痛相談 | 🟢 | — |
| 2 | ... | ... | Concierge | follow-up期待 | 🟡 | greeting のみ |
```

### Intent 列の書き方

- そのターンでユーザーが求めていること（1 行）
- ボットが実際に答えたこととの差分を Notes に

---

## ログ突合（runner 済みメトリクス）

`simulation_eval` / runner `metrics.intent_evaluation`:

| フィールド | 意味 |
|------------|------|
| `sessions_tracked` | 評価対象セッション数 |
| `counseling_rows_matched` | counseling_detail 一致行 |
| `route_rows_matched` | dialogue_route 一致行 |
| `per_session[session_id].routes` | primary_route カウント |
| `per_session[session_id].intent_samples` | 入力→応答有無サンプル |
| `intent_router_metrics` | shadow mismatch 率等 |

**LLM 評価はこれらを上書きする** — mismatch 率が低くてもターン単位のずれを見逃さない。

---

## 横断サマリ（親エージェント）

最終 `intent_review` またはユーザー報告に含める:

1. **Executive summary**（5–10 行）— 合格率、主要な misaligned パターン
2. **カテゴリ別** — aligned / partial / misaligned 件数
3. **Intent mismatch 一覧** — 🔴🟡 のみ（全ターン羅列しない）
4. **Route 問題** — shadow mismatch 上位、誤 Concierge 化
5. **response_missing** — ターン一覧と推定原因
6. **優先アクション** — ファイル・設定の具体ヒント

---

## physical 推奨品質（任意）

`diagnosis_kind` が推奨系のセッションでは:

- `medicine-recommendation-advisor` スキルで OTC 妥当性をレビュー
- 症状と推奨薬の整合、禁忌・年齢考慮

---

## マージ先

| 方式 | パス |
|------|------|
| runner 既存 | `log/analysis/YYYY-MM-DD_local_v2_simulation_eval_{suffix}.md` に「## Wave B 深掘り」追記 |
| 独立 | `log/analysis/YYYY-MM-DD_local_v2_intent_review_{suffix}.md` 新規 |

**全セッションの完全トランスクリプト**は `local_v2_chat_test_{suffix}.md` に既にある — intent_review では評価表と 🔴🟡 セッションの抜粋で足りる。トランスクリプトの二重掲載は避ける。

---

## gcp-log-analysis との対応

| gcp-log-analysis | ローカル v2 |
|------------------|-------------|
| `user_sessions.json` → sessions | `session_ids_{suffix}.json` |
| `sessions/<safe_id>.md` transcript | `local_v2_chat_test_{suffix}.md` §全セッション |
| `counseling_detail` in GCP export | `log/counseling_detail_log.jsonl` |
| `draft_session_*.md` | `draft_local_session_*.md` or intent_review |
| Wave A 固定 4 グループ | runner メトリクス + measure_* スクリプト |

GCP dev ログとの比較が必要なら `gcp-log-analysis` を別途実行し、同一カテゴリの issue_type を突合する。
