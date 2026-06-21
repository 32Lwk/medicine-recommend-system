# Sage UI 手動 QA チェックリスト

Big Bang 移行後、Web チャット（`?ui=sage` またはデフォルト Sage）で確認する項目。

## 推奨フロー（sage_reco）

- [ ] 症状入力 → SSE 順序: cards → advice → done → reco_detail
- [ ] カルーセルに医薬品カードが表示される
- [ ] 個別アドバイス・成分重複警告・医師相談が表示される
- [ ] usage_sections（用法・禁忌）が reco_detail 後に表示される
- [ ] 0件・エスカレーション時に error ブロックが表示される
- [ ] 👍/👎 フィードバックが送信できる（plain summary）

## ステータス（sage_status）

- [ ] 診断名通知・属性更新・ユーザー情報登録
- [ ] 店舗案内（在庫・施設・遺失物）
- [ ] 緊急・危機対応
- [ ] Concierge（capabilities / about / greeting）

## Q&A（sage_qa）

- [ ] 医薬品相談回答が sage_qa で表示される
- [ ] qa_delta SSE で追記される（該当ルート）

## i18n

- [ ] 言語切替（en/ko/zh）で diagnosis フィールドが翻訳表示される
- [ ] HTML 一括翻訳に依存しない（マーカー + diagnosis のみ）

## 管理画面

- [ ] sage_reco メッセージが Sage バブル + スコアパネルで表示
- [ ] detailed_diagnosis / スコアモーダルが動作

## API / ログ

- [ ] GET `/api/sessions` の diagnosis から admin フィールドが除去されている
- [ ] 推奨ログに diagnosis_snapshot + app_output（plain summary）が記録される

## TTS

- [ ] 推奨結果の音声読み上げ（toggleVoiceRead）が diagnosis から生成される

## Legacy フォールバック

- [ ] `?ui=legacy` で従来 HTML が表示される（LEGACY_UI_FALLBACK 未設定時）
