# 管理画面 PII 運用プレイブック

## 方針

- ユーザー原文は **自動マスクしない**（トリアージ・緊急判断のため）
- 一覧は **120 文字**、詳細パネルは **800 文字** まで表示（`ADMIN_LIST_SNIPPET_MAX_CHARS` / `ADMIN_DETAIL_USER_MESSAGE_MAX_CHARS`）
- 画面共有・ログ転記時は担当者がマスク判断する

## 表示時の注意

1. 氏名・電話・住所・メールが含まれる場合は必要最小限のみ共有
2. 緊急キュー（`critical_crisis` / `critical_medical`）は即時エスカレーション手順に従う
3. スクショ・外部チャットへの貼り付けは社内規程に従う

## エスカレーション優先度

`critical_crisis` > `critical_medical` > `store_high` > `store_low`
