設計ドキュメントを作成しました。

[JEV_PHASE1_INSERTION_DESIGN_20260921.md](D:/Programing/medicine-recommend/docs/planning/codex-parallel-jev-20260921/JEV_PHASE1_INSERTION_DESIGN_20260921.md)

主な設計方針:

- `resolve_route()` で legacy を先に確定してから Jev shadow を非同期実行
- `PRIMARY=false` では必ず同一の legacy decision を返却
- Jev は既存 dispatcher 用 session key を更新しない
- §8.3準拠の state builder、Choice/Noul変換、安全系overrideを定義
- shadowログスキーマ、変更ファイル、回帰テスト一覧、リスク、非目標、他エージェントへの依頼を記載

実装・テスト実行・設定変更は行っていません。

