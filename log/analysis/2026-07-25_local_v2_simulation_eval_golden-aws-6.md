# Chat Pipeline v2 シミュレーション意図評価 (2026-07-25)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-25T01:27:28.494441+00:00
- セッション数: 8 / 総ターン: 16
- 自動合格: 5 / 要確認: 3
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 8
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1784942848500395855394` | golden-session-8283-about | 2 | PASS | 0/0 | 0 | — | — |
| `1784942893352850464867` | golden-session-8283-architecture | 3 | REVIEW | 0/0 | 0 | — | — |
| `1784942961867330980821` | golden-session-8283-aws-gcp | 4 | PASS | 0/0 | 0 | — | — |
| `1784943047536811837728` | golden-session-3443-side-effect | 1 | REVIEW | 0/0 | 0 | — | — |
| `1784943062904074991870` | golden-session-2059-side-effect | 1 | REVIEW | 0/0 | 0 | — | — |
| `1784943078075632357138` | golden-session-6483-regression | 2 | PASS | 0/0 | 0 | — | — |
| `1784943208045279385686` | golden-session-2070-regression | 2 | PASS | 0/0 | 0 | — | — |
| `1784943248976612882415` | golden-session-1951-regression | 1 | PASS | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### golden-session-8283-architecture (`1784942893352850464867`)
- failures: missing_context_kw:アーキテクチャ
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 16498ms):

最近の更新では、OTC 上位50の画像まわりが整い、より見やすく確認しやすくなりました。あわせて、推奨の見直しや画面表示、読み上げ、静的アセットの扱いも改善され、全体的により使いやすくなっています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 17244ms):

このチャットは、症状に合わせて市販薬の候補を案内するための相談ツールです。

診断や処方は行わず、病院や診療所のように診察をする場ではありません。

薬の候補はルールに基づいて選び、必要に応じて薬剤師や登録販売者などへの相談をおすすめします。

気になる症状があれば、年齢、性別、症状がいつからか、アレルギー、現在飲んでいる薬、持病の有無を教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 23336ms):

公開されている構成としては、GCP 本番は Cloud Run、AWS ステージングは ECS Express Gateway と ALB、WAF で動いています。

翻訳や読み上げは環境ごとに使い分けられていて、AWS ステージングでは Amazon Translate と Amazon Polly、GCP 本番では DeepL と Web Speech API が使われています。

詳しく知りたい場合は、会話の流れ、デプロイ、または AWS と GCP の違いのどれを深掘りするか指定してください。

会話の保存先は PostgreSQL、実行ログはクラウドログに残り、AWS 側では静的ファイル配信に CloudFront も使われます。

公開されているデプロイ確認としては、`/health` で反映状況の確認ができ、ソースも GitHub で公開されています。

画像は Cloudflare R2 の共通 CDN から配信されます。

### golden-session-3443-side-effect (`1784943047536811837728`)
- failures: missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンって眠い？
- **Bot** (`system_error`, 11261ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### golden-session-2059-side-effect (`1784943062904074991870`)
- failures: missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンって眠くなる？
- **Bot** (`system_error`, 11116ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| golden-session-8283-about | `1784942848500395855394` |
| golden-session-8283-architecture | `1784942893352850464867` |
| golden-session-8283-aws-gcp | `1784942961867330980821` |
| golden-session-3443-side-effect | `1784943047536811837728` |
| golden-session-2059-side-effect | `1784943062904074991870` |
| golden-session-6483-regression | `1784943078075632357138` |
| golden-session-2070-regression | `1784943208045279385686` |
| golden-session-1951-regression | `1784943248976612882415` |
