あなたは Agent C（Phase1 shadow 差し込み設計）。実装はせず設計ドキュメントのみ。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。その制約に従え。

## やること
1. 現行フローを追う: chat_post_pipeline → SafetyGate → SessionOps → triage → IntentRouter(resolve_route) → unified/legacy → dispatcher
2. shadow を入れる最短経路を提案:
   - `src/services/jev_client.py`
   - `src/services/jev_decisions.py`
   - `src/services/jev_metrics.py`
   - `src/dialogue/routing/jev_router.py`
3. Feature flags の読み場所（既存 `llm_flags` / `routing_config` パターンに合わせる）。
4. RouteDecision 変換: Choice/Noul → primary/sub。emergency/security override の疑似コード。
5. state builder: §8.3 通り。どの session フィールドからメタを取るかファイル参照付きで。
6. shadow log スキーマ（legacy_decision / jev_decision / executed / matched / latency / usage）。
7. 本線を変えない保証（PRIMARY=false 時は必ず legacy 実行）。
8. 既存テスト: `tests/routing/*`, `tests/emergency/*`, `tests/security/*` で回帰対象一覧。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/JEV_PHASE1_INSERTION_DESIGN_20260921.md`

内容: シーケンス、変更ファイル一覧、非目標、リスク、疑似コード、他エージェントへの依頼メモ。

完了したら短い要約を最後のメッセージに出す。

