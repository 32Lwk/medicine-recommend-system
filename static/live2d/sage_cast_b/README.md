# sage_cast_b — Cubism 自前作業フォルダ

医薬品相談キャスト **Character B**（白衣正本）用。

## すぐ始める

```bash
# リポジトリルートで（参照 PNG・空レイヤーを再生成）
python scripts/live2d_prepare_cast_b.py
```

手順の正本: [`docs/dev/LIVE2D_CUBISM_DIY_WORKFLOW.md`](../../../docs/dev/LIVE2D_CUBISM_DIY_WORKFLOW.md)  
パーツ仕様: [`docs/dev/LIVE2D_CUBISM_PSD_SPEC.md`](../../../docs/dev/LIVE2D_CUBISM_PSD_SPEC.md)

## ディレクトリ

| パス | 内容 |
|------|------|
| `diy/reference/` | クロマキー済み参照（表情・口・目） |
| `diy/layers/` | 空 PNG（レイヤー名固定）— 切り分け絵をここへ |
| `diy/parts.csv` | パーツ一覧 |
| `diy/parameters.csv` | Cubism パラメータ |
| `diy/assemble_psd.jsx` | Photoshop で PSD 組み立て |
| `source/` | 切り出しベース・完成 PSD 置き場 |
| `textures/` | Editor 書き出しテクスチャ |
| `motions/` | motion3.json |

## ゴール

1. `source/sage_cast_b.psd` を完成  
2. Cubism Editor で `sage_cast_b.model3.json` + `.moc3` を書き出し  
3. A/C/D は同ツリーで差し替え  
