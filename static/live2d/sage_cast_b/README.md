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
| `sprite/` | Cubism 完成までの代替アバター素材（`manifest.json` + WebP パッチ） |

## スプライト版アバター（Cubism 完成までの代替）

```bash
# 開発環境のみ: pip install opencv-python
python scripts/live2d_build_sprite_b.py                  # sprite/ を再生成
python scripts/live2d_build_sprite_b.py --debug          # 合成確認 PNG を一時フォルダへ
python scripts/live2d_build_sprite_b.py --gestures-only  # 手の重ね絵だけ作り直す
python scripts/live2d_preview_poses.py [--set gestures]  # 極端な姿勢・手の動きの確認シート（ブラウザ不要）
```

- 土台は `sage-b-mouth-closed.jpg`。体・左右の耳・顔・目鼻口・髪に分け、首の付け根を軸に頭を回し、パーツごとの視差で横向き・うなずきを出す（首の下・耳の裏・髪の下は補完済み）
- 表情 11 種（`expressions-b/sage-b-e1..e5`, `sage-b-x-*`）は特徴点で位置合わせし、顔の内側だけをパッチにする
- 半目は画像生成では安定しないため、上まつ毛の線を下へずらして合成する（表情ごとに生成）
- 手・腕 8 種（`expressions-b/sage-b-g-*.jpg`: 土台と同じ構図に手を足した生成画像）は、位置合わせ後に手と袖だけを切り抜く。切り抜き範囲・表示位置のずらし・揺れの支点はスクリプト内の `GESTURES` で指定する。顔に触れる「あごに手」だけ頭と一緒に動く
- デモ: `/static/dev/avatar_demo.html`（感情 12 種・モーション 9 種・手 8 種・台本タグ・読み上げ口パク）。公開先: `https://live2d.medicine.yutok.dev`
- JS: `static/js/avatar/sage_avatar.js`（制御: 待機の揺れ・感情の姿勢・キーフレームモーション・台本解析・リップシンク）+ `sage_avatar_sprite.js`（描画）
- Cubism 版は `load` / `applyPose` / `setExpression` / `setEyes` / `setMouth` / `destroy` を持つレンダラーを作れば `SageAvatar` をそのまま使える

台本の書き方（`avatar.speak(text, { autoEmotion: true })`）:

```text
[手を振る]こんにちは。[共感]なるほど、頭痛が続いているんですね。[真剣]急に激しく痛む場合は受診してください。[お辞儀]お大事に。
```

タグがない文は言葉から感情・動き・手を推定する（「申し訳」→申し訳なさ+お辞儀+両手を合わせる、「受診」→真剣+人差し指、「こんにちは」→手を振る、文末「？」→首かしげ など）。感情ごとの自動の手は `autoGesture: false` で止められる。

## ゴール

1. `source/sage_cast_b.psd` を完成  
2. Cubism Editor で `sage_cast_b.model3.json` + `.moc3` を書き出し  
3. A/C/D は同ツリーで差し替え  
