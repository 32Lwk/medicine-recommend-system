# Cubism PSD 作業チェックリスト（作業者向け短版）

正本: [`docs/dev/LIVE2D_CUBISM_PSD_SPEC.md`](../../../../../docs/dev/LIVE2D_CUBISM_PSD_SPEC.md)

## 最初にやること

1. **Character B** から着手（白衣・ピン・ポケットの寸法正本）
2. 基準画: `sage-cast-b-unified-coat.jpg` + `expressions-b/sage-b-e0-neutral.jpg`
3. クロマキー緑 → 透過 PNG → PSD グループ §4 どおりに配置

## パーツ分け（必須）

- [ ] `hair_back` / `hair_front` 分割
- [ ] 目 L/R: 白目・虹彩・ハイライト・まつ毛
- [ ] 眉 L/R 独立
- [ ] 口: 閉口ベース +（差分 or Param）あいうえお
- [ ] 白衣: `coat_body` + 襟 L/R + `coat_pocket` + `pin_capsule`
- [ ] `inner/` のみキャラ差分（A/C/D）

## パラメータ（ID 固定）

- [ ] `ParamEyeLOpen` / `ParamEyeROpen`（目 JPG: 開/半/閉）
- [ ] `ParamMouthOpenY` / `ParamMouthForm`（口 JPG 6 種・**い/え差強調**）
- [ ] `ParamExpression` 0–5 = E0–E5（スナップ切替）
- [ ] `ParamBreath` idle
- [ ] `ParamAngleX/Y/Z` 首（E5 うなずきは Y 短アニメ）

## 表情参照 JPG

| Param | B のファイル |
|-------|----------------|
| 0 | `expressions-b/sage-b-e0-neutral.jpg` |
| 1 | `sage-b-e1-smile.jpg` |
| 2 | `sage-b-e2-thinking.jpg` |
| 3 | `sage-b-e3-empathy.jpg` |
| 4 | `sage-b-e4-surprise.jpg` |
| 5 | `sage-b-e5-nod.jpg` |

A/C/D は `expressions-{a,c,d}/` の同名 suffix を参照。

## B 完成後

- [ ] パーツツリー・パラメータ ID を変えず A → C → D を差し替え
- [ ] 4 モデル同一キャンバスサイズ・原点

## 納品

- [ ] `.psd` + `.moc3` + `model3.json` + textures
- [ ] Web プレビュー（Cubism SDK for Web）で E0–E5・口形・まばたき確認
