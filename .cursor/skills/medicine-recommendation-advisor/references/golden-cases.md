# Golden cases（メイン入口）

**索引**: [golden-cases-index.md](golden-cases-index.md) — 全 **60+ ケース**（風邪サブタイプ・ペルソナ・領域・安全・月経）

## 使い方

1. 入力文から **風邪の型**（[golden-cases-cold.md](golden-cases-cold.md) の COLD-* 表）と **ペルソナ**（[golden-cases-personas.md](golden-cases-personas.md)）を特定
2. 該当 Case ID の **期待 / 避ける** と実際の top3 を比較
3. 評価後は **必ず** `log/reviews/YYYY-MM-DD_<slug>_<id>.md` に保存（[evaluation-report-template.md](evaluation-report-template.md)）

## クイック参照: 風邪の型

| 型 | 例入力キーワード |
|----|------------------|
| COLD-NAS | 鼻水, くしゃみ, 花粉 |
| COLD-THR | のど痛み, 咽頭 |
| COLD-DRY | 乾いた咳, 痰少 |
| COLD-PROD | たん, 痰, ゼロゼロ |
| COLD-FEV | 発熱のみ |
| COLD-SYS | 熱+咳+鼻+のど |
| COLD-FLU | インフル, 高熱+関節痛 |
| COLD-GI | 下痢, 吐き気, 胃腸炎 |
| COLD-ALL | アレルギー性鼻炎 |
| COLD-HOV | 二日酔い, 宿酔 |

詳細ケースは [golden-cases-cold.md](golden-cases-cold.md)。

## レガシー ID（後方互換）

GC-001〜006 は以下に移行:

| 旧 ID | 新 ID |
|-------|-------|
| GC-001 | GC-COLD-PROD-001 |
| GC-002 | GC-DOM-COU-001 |
| GC-003 | GC-MEN-001 |
| GC-004 | GC-MEN-005 |
| GC-005 | GC-MEN-008（授乳は GC-PERS-004） |
| GC-006 | GC-MEN-006 |
