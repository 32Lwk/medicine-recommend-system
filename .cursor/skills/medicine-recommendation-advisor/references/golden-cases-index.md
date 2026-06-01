# Golden cases 索引

評価時は **Case ID** で該当ファイルを開く。複数該当する場合は最も制約の強いペルソナ（妊娠・小児・赤旗）を優先。

| ファイル | 内容 | ID プレフィックス |
|----------|------|-------------------|
| [golden-cases-personas.md](golden-cases-personas.md) | 年齢・性別・妊娠授乳・持病・嗜好 | `GC-PERS` |
| [golden-cases-cold.md](golden-cases-cold.md) | 風邪の**型**（単純「風邪」ではない） | `GC-COLD` |
| [golden-cases-domains.md](golden-cases-domains.md) | のど・胃腸・痛み・皮膚・目鼻・精神 | `GC-DOM` |
| [golden-cases-safety-nlu.md](golden-cases-safety-nlu.md) | 赤旗・診断名・NLU 境界 | `GC-SAFE` |
| [golden-cases-menstrual.md](golden-cases-menstrual.md) | 月経・女性特有 | `GC-MEN` |
| [diagnosis-guard-policy.md](diagnosis-guard-policy.md) | 診断名ガード現状・ギャップ | — |
| [diagnosis-physical-block-matrix.md](diagnosis-physical-block-matrix.md) | 条件別 OTC/Physical 可否 | — |
| [diagnosis-counseling-orchestrator.md](diagnosis-counseling-orchestrator.md) | カウンセリング→Physical ゲート | — |
| [golden-cases-diagnosis-mental.md](golden-cases-diagnosis-mental.md) | mental_health 代表12件 | `GC-DX-MH` |
| [feedback-integration.md](feedback-integration.md) | Feedback UI / admin 連携設計 | — |

出典: `tests/test_comprehensive_integration.py`, `tests/test_recommendation_output.py`, `test_menstrual_recommendations.py`

## 件数（目安）

| ファイル | ケース数 |
|----------|----------|
| golden-cases-personas.md | 7 + ペルソナ表 |
| golden-cases-cold.md | 19 |
| golden-cases-domains.md | 22 |
| golden-cases-safety-nlu.md | 23 |
| golden-cases-menstrual.md | 10 |
| **合計** | **約 81** |

## `test_comprehensive_integration` の 300+ 件について

- **推奨方針**: 全件を手書き golden にしない。現状の **代表 81 件**で推奨ランキングをカバーし、integration 側は NLU・診断検出・方言の **自動回帰**に任せる。
- **将来**: `generate_test_cases()` からカテゴリ別に **NLU-only** ケース（`expected_has_symptom`）を JSON エクスポートし、`references/golden-cases-nlu-auto.json` として分割管理可。製品 rank まで含むケースは PMDA 照合コストが高いため手動代表に留める。
- **分割**: 領域ごとファイル（本リポジトリ構成）を維持。1 ファイルに 300 件はメンテ不可。
