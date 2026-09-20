分析成果物を作成しました。

[JEV_HYPOTHESIS_ROUTING_20260921.md](D:\Programing\medicine-recommend\docs\planning\codex-parallel-jev-20260921\JEV_HYPOTHESIS_ROUTING_20260921.md)

要点:

- H2・H3・H4を採用、H1・H5・H6を追加検証待ちと判定
- 013452のAsk hintによるsub-route劣化を解剖
- primary confidenceだけではsub-route誤判定を検出できない問題を特定
- SafetyGate full、meta short-path、deterministic gateの抜け穴を整理
- Phase 1前に必要なEmergency／Security／処方／違法薬物／受診依頼／Store＋症状fixtureをP0指定
- SessionOpsはJev primary対象外、高リスクは既存gateとのOR二重確認を推奨

実装コードは変更していません。

