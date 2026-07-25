# Chat Pipeline v2 シミュレーション意図評価 (2026-07-25)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-25T01:37:43.779194+00:00
- セッション数: 8 / 総ターン: 16
- 自動合格: 7 / 要確認: 1
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 8
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1784943463783199183941` | golden-session-8283-about | 2 | PASS | 0/0 | 0 | — | — |
| `1784943506323241211047` | golden-session-8283-architecture | 3 | PASS | 0/0 | 0 | — | — |
| `1784943581026453769773` | golden-session-8283-aws-gcp | 4 | PASS | 0/0 | 0 | — | — |
| `1784943667510584810182` | golden-session-3443-side-effect | 1 | PASS | 0/0 | 0 | — | — |
| `1784943695353212909658` | golden-session-2059-side-effect | 1 | PASS | 0/0 | 0 | — | — |
| `1784943718877188315813` | golden-session-6483-regression | 2 | PASS | 0/0 | 0 | — | — |
| `1784943852250001605278` | golden-session-2070-regression | 2 | PASS | 0/0 | 0 | — | — |
| `1784943894655769197666` | golden-session-1951-regression | 1 | REVIEW | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### golden-session-1951-regression (`1784943894655769197666`)
- failures: missing_context_kw:更新
#### Turn 1
- **User**: 最近の更新内容を教えてください。
- **Bot** (`concierge_doc_changelog`, 20956ms):

最近は、OTC 上位50画像の整備や推奨候補の見直し、TTS と画面表示の改善が進み、より使いやすくなりました。あわせて、端末の場所に応じた静的アセットの切り替えも整い、表示まわりがなめらかになっています。


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| golden-session-8283-about | `1784943463783199183941` |
| golden-session-8283-architecture | `1784943506323241211047` |
| golden-session-8283-aws-gcp | `1784943581026453769773` |
| golden-session-3443-side-effect | `1784943667510584810182` |
| golden-session-2059-side-effect | `1784943695353212909658` |
| golden-session-6483-regression | `1784943718877188315813` |
| golden-session-2070-regression | `1784943852250001605278` |
| golden-session-1951-regression | `1784943894655769197666` |
