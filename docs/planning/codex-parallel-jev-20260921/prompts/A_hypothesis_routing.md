あなたは Agent A（IntentRouter × Jev の精度仮説検証）。実装はしない。

まず `docs/planning/codex-parallel-jev-20260921/prompts/00_common.md` を読め。その制約に従え。

## 仮説候補（必須で扱い、追加仮説も可）
- H1: jev:minimal は現行 IntentRouter と同等以上の primary/sub 精度（10ケース×repeat）。
- H2: with_baseline_triage の Ask hint は medicine_qa を劣化させる（013452）。再発条件を一般化する。
- H3: Emergency/Security は Jev Noul + 既存 gate 二重でないと FN リスクが残る。
- H4: SessionOps は現行 fast-path の方が速く、Jev primary 化の価値が低い。
- H5: state に構造化メタ（last_recommended_medicines 等）を足すと follow-up 精度が上がる（またはノイズで下がる）。既存ログ/fixture から予測し、追加実験案を書く。
- H6: confidence floor 0.70 / high 0.85 は primary canary に妥当か。過信・過小信頼の兆候を answers から見る。

## やること
1. 013619 / 013452 の results をシナリオ別に分解。
2. `intent_router_llm` / `router` / `gate` / SafetyGate の分岐を読み、Jev 差し込み点と二重ゲート抜け穴を特定。
3. fixture ギャップ（emergency/security/prescription/illegal/医療受診/混在 Store+症状）を列挙。
4. 各仮説を採用/棄却/保留にし、Phase1 前に必須の追加 fixture を優先度付きで出す。

## 成果物（必ずこのパスに書く）
`docs/planning/codex-parallel-jev-20260921/JEV_HYPOTHESIS_ROUTING_20260921.md`

内容: 仮説表、失敗ケース解剖、fixture 追加案、Go 条件への影響、他エージェントへの依頼メモ。

完了したら短い要約を最後のメッセージに出す。
