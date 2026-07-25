# Chat Pipeline v2 シミュレーション意図評価 (2026-07-25)

gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と
`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。

- 実行時刻: 2026-07-25T01:35:22.044518+00:00
- セッション数: 3 / 総ターン: 5
- 自動合格: 0 / 要確認: 3
- GPT シミュレーション: False

## ログ突合サマリ

- 追跡セッション: 3
- counseling_detail マッチ行: 0
- route ログマッチ行: 0

## セッション別評価

| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |
|------------|----------|-------|------|----------------|--------------|------------|----------------|
| `1784943322048275844867` | golden-session-8283-architecture | 3 | REVIEW | 0/0 | 0 | — | — |
| `1784943390661055303729` | golden-session-3443-side-effect | 1 | REVIEW | 0/0 | 0 | — | — |
| `1784943405661208549013` | golden-session-2059-side-effect | 1 | REVIEW | 0/0 | 0 | — | — |

## 要確認 — ターン別トランスクリプト

### golden-session-8283-architecture (`1784943322048275844867`)
- failures: missing_context_kw:Cloud Run
#### Turn 1
- **User**: 最近の更新内容は？
- **Bot** (`concierge_doc_changelog`, 17629ms):

最近は、医薬品の画像やおすすめの見せ方がよりわかりやすくなり、探しやすさが向上しました。あわせて、画面の更新情報や音声案内、ローカル環境での表示まわりも整い、全体としてより使いやすくなっています。

#### Turn 2
- **User**: あなたについて詳しく教えて
- **Bot** (`concierge_app_about`, 17182ms):

私は、症状にあわせて市販薬の候補をチャットで案内する相談ツールです。

病院や診療所のような診察・処方は行わず、診断も行いません。

薬の候補選びはルールに基づいて行い、必要に応じて医師・薬剤師・登録販売者への相談をおすすめします。

この会話では、私が案内役としてお答えします。

薬について確認したいことがあれば、症状や年齢などを教えてください。

#### Turn 3
- **User**: あなたのシステムアーキテクチャについて詳しく教えて
- **Bot** (`concierge_architecture`, 22934ms):

会話の処理はまずトリアージで分類し、その後に用途ごとの担当へ振り分けます。

市販薬の候補選定はルールベースのスコアリングで行われ、薬名を LLM が自由に作る方式ではありません。

応答では推奨カードや状態表示を返し、ストリーミング表示も行います。

データは会話セッションやメッセージ履歴を PostgreSQL に、実行ログを各クラウドのログ基盤に保存します。

### golden-session-3443-side-effect (`1784943390661055303729`)
- failures: response_missing_or_too_short, missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンって眠い？
- **Bot** (`unknown`, 11035ms):

(empty)

### golden-session-2059-side-effect (`1784943405661208549013`)
- failures: response_missing_or_too_short, missing_context_kw:ロキソニン
#### Turn 1
- **User**: ロキソニンって眠くなる？
- **Bot** (`unknown`, 10835ms):

(empty)


## Admin 確認

- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON
- 検索: `v2-test` または `session_id`（下表）

| scenario_id | session_id |
|-------------|------------|
| golden-session-8283-architecture | `1784943322048275844867` |
| golden-session-3443-side-effect | `1784943390661055303729` |
| golden-session-2059-side-effect | `1784943405661208549013` |
