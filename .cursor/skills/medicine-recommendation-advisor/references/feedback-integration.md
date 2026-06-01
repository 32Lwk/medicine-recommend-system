# Feedback UI 連携（評価レポート ↔ 既存 UI）

## 既存の仕組み

| 要素 | 場所 |
|------|------|
| DB テーブル | `feedback_reports`（`src/services/database.py`） |
| 挿入 | `insert_feedback()` |
| チャット UI | `format_feedback_buttons()` — `handlePositiveFeedback` / `handleNegativeFeedback` |
| 診断時 | `chat_diagnosis_handler` が `error_type: "diagnosis_detected"` で feedback_data を付与 |

## 評価レポート（`log/reviews/`）との対応

評価 Markdown に以下を必ず書く（admin エクスポート・UI 連携の鍵）:

```yaml
session_id: "<sid>"
feedback_report_id: null   # 既存行があれば ID
error_type: null           # 例: diagnosis_detected
case_id: GC-COLD-PROD-001
verdict: 要改善
```

## オーナー決定（admin 連携設計）

| 項目 | 決定 |
|------|------|
| 再評価トリガー | **ネガティブ feedback**（推奨が出すぎた・不適切） |
| 過剰ブロック再評価 | **ネガティブ**または admin が「推奨が出ない」を選んだ行 — **手動**で advisor 起動（分類: *over_block*）。golden: **GC-SAFE-OVER-001** |
| 自動評価 | **手動**（admin がエージェント依頼） |
| UI 表示 | **要約 1 行 + MD パス**（全文は `log/reviews/`） |
| 紐付け | **session_id + feedback_report_id** |
| PMDA≠CureBell | feedback 一覧に **「データ要確認」** フラグ |
| 多言語 | **日本語化後**の症状で評価 |
| admin 要約言語 | **日本語固定** |
| `log/reviews/` 保持 | **無期限**（手動削除） |
| 評価優先 | **PMDA > golden**（golden 更新提案） |

## Feedback DB 拡張（実装は別 PR）

| カラム / 値 | 用途 |
|-------------|------|
| `negative_reason` | ネガティブ時の理由コード |
| `no_recommendation` | **推奨が出ない** — 過剰ブロック再評価のトリガー（オーナー T5） |
| （既存） | 不適切・副作用・その他 |

admin UI: ネガティブ送信時に理由選択。`no_recommendation` 行は **over_block** 分類で advisor 手動再評価。

## 将来の admin 連携（実装は別 PR）

1. ネガティブ `feedback_reports` 行を一覧（`negative_reason` フィルタ可）
2. admin が「再評価」→ `@medicine-recommendation-advisor`
3. `log/reviews/{date}_{session_id}_{feedback_id}.md` 保存
4. UI に要約行: 判定 / Case ID / 不一致数 / 分類 / `review_path`

### UI 要約フィールド

| フィールド | ソース |
|------------|--------|
| 判定 | 評価レポート |
| Case ID | golden |
| PMDA/CureBell 不一致 | 照合表 ❌ 件数 → **データ要確認** フラグ |
| 分類 | algorithm / data / clinical / **over_block**（過剰ブロック） |
| review_path | `log/reviews/...` |

## エージェントの参照順（session_id あり）

1. `get_session_from_db(session_id)` — メッセージ・推奨カード
2. `get_feedback_reports()` — 同一 session の未解決 feedback
3. `data/otc_medicine_data.csv` + PMDA + CureBell
4. golden case
5. `log/reviews/` に新規保存
