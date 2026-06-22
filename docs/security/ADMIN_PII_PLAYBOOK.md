# 管理画面 PII 運用プレイブック

## 方針

- LINE 公式アカウント経由のセッション ID は `line:Uxxxxxxxx` 形式。表示・エスカレーション手順は Web セッションと同じ
- ユーザー原文は **自動マスクしない**（トリアージ・緊急判断のため）
- 一覧は **120 文字**、詳細パネルは **800 文字** まで表示（`ADMIN_LIST_SNIPPET_MAX_CHARS` / `ADMIN_DETAIL_USER_MESSAGE_MAX_CHARS`）
- 画面共有・ログ転記時は担当者がマスク判断する

## 表示時の注意

1. 氏名・電話・住所・メールが含まれる場合は必要最小限のみ共有
2. 緊急キュー（`critical_crisis` / `critical_medical`）は即時エスカレーション手順に従う
3. スクショ・外部チャットへの貼り付けは社内規程に従う

## エスカレーション優先度

`critical_crisis` > `critical_medical` > `store_high` > `store_low`

## LINE 長期記憶（2026-06-22〜）

| データ | 保存場所 | PII 例 |
|--------|---------|--------|
| 永続プロファイル | `line_user_profile` | 年齢・性別・アレルギー・服薬・既往 |
| 相談要約 | `consultation_summaries` | 症状・推奨薬名・key_facts |
| 会話アーカイブ | `message_archive` | ユーザー原文（フル履歴） |

### 表示・削除時の注意

1. 管理画面「長期記憶」タブは **自動マスクなし**。画面共有・エクスポート時はプロファイル・要約・アーカイブを個別に判断する
2. ユーザー削除依頼（チャット内）または管理者削除 API 実行時は、ライフサイクル `line_memory_deleted` が記録される
3. `scope=all` 削除はプロファイル・要約・**アーカイブ**まで消去する（現行 `messages` は保持）。完全消去が必要な場合はセッション削除手順も確認する
4. 削除・開示請求の窓口は [プライバシーポリシー第7条](../public/プライバシーポリシー.md) および不具合報告フォーム

詳細: [LINE_LONG_TERM_MEMORY.md](../ops/LINE_LONG_TERM_MEMORY.md)
