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

A〜D の 4 人とも同じ手順・同じ構成（`static/live2d/sage_cast_{a,b,c,d}/sprite/`）。

```bash
# 開発環境のみ: pip install opencv-python
python scripts/live2d_build_sprite.py --cast all             # 4 人分の sprite/ を再生成（--cast b で 1 人だけ）
python scripts/live2d_build_sprite.py --cast b --debug       # 合成確認 PNG を一時フォルダへ
python scripts/live2d_build_sprite.py --cast b --gestures-only  # パーツと手の重ね絵だけ作り直す
python scripts/live2d_preview_poses.py --cast b [--set gestures]  # 極端な姿勢・手の動きの確認シート（ブラウザ不要）
```

- 土台は腰より少し上まで写った 3:4 の `sage-x-w-base.jpg`。体・首・左右の耳・顔・目鼻口・髪に分け、パーツごとの視差で横向き・うなずきを出す（首の下・耳の裏・髪の下は補完済み）
  - 頭はあごの下（首の上端）を軸に回す。首は独立したパーツで、下端（襟元）を固定し、上端を頭に合わせてせん断＋半分の回転で曲げる（顎の二重・首のずれ・首だけ伸びるのを防ぐ）
  - 角度は横 28°・縦 28°・傾き 14° で頭打ち。傾きの 18% と横向きの一部は体（rig）が受け持ち、頭だけが動いて見えないようにする
- キャラごとの座標（顔の輪郭・首・耳の境界など）は `scripts/live2d_build_sprite.py` の `Cast` 設定にまとめてある
- 表情 12 種（`expressions-x/sage-x-e1..e5`, `sage-x-x-*`）は正方形の顔画像から特徴点で位置合わせし、顔の内側だけをパッチにする
- 半目は画像生成では安定しないため、上まつ毛の線を下へずらして合成する（表情ごとに生成）
- 手・腕 8 種（`expressions-x/sage-x-g-*.jpg`: 腰上の土台と同じ構図で腕だけ変えた生成画像）は、位置合わせ後に体ごと差し替える絵（元の腕が消え新しい腕が出る）と、背景や頭に重なる手の重ね絵に分ける。顔に触れる「あごに手」だけ頭と一緒に動く
  - 重ね絵は手だけでなく、手から袖をたどった前腕まで含め（手の大きさに比例した長さ、肘の先は帯状にぼかす）、肘を軸に回す。上げ下げも平行移動ではなく肘まわりの回転にして、手首だけが動いたり腕が途中で切れたりしないようにする。両手を合わせる絵は両手だけの固定の重ね絵
  - 前腕の下の体は差し替え前の土台に戻し、周囲 6px も土台に戻して古い腕の輪郭が残らないようにする
- 切り替えの見え方（`static/js/avatar/sage_avatar.js` / `sage_avatar_sprite.js`）
  - 手: 前の手を 0.28 秒で下ろし切ってから次の手を出す（2 本の腕が同時に見えない）。体の差し替えは出始めの短い間（量 0.15〜0.4）で済ませ、手は少し行き過ぎてから戻る振り上げ＋肩の小さな弾みで入る
  - 表情: まばたきで目を閉じた瞬間に差し替え、新しい表情を最前面で 0.11 秒かけて重ねてから古い表情を即座に消す（半透明どうしの重なりや古い口元の残りが出ない）
  - モーション: キーフレームは単調な 3 次補間（各キーで止まらない）、感情ごとの姿勢の偏りは臨界減衰ばねで滑らかに寄せる
- デモ: `/static/dev/avatar_demo.html`（キャラ切替・感情 12 種・モーション 9 種・手 8 種・台本タグ・読み上げ口パク）。公開先: `https://live2d.medicine.yutok.dev`

### 読み上げ（VOICEVOX）

ローカルでは VOICEVOX Engine の声で読み上げ、音素の長さ（モーラ）に合わせて口を動かす。エンジンにつながらないときや公開サイトでは、ブラウザの読み上げで代わりに話す。

```powershell
# 初回のみ（NVIDIA GPU 版。以後は Docker Desktop 起動時に自動で立ち上がる）
docker run -d --name voicevox-engine --restart unless-stopped --gpus all -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:nvidia-latest
```

| キャラ | 話者（ID） |
|--------|-----------|
| A（やわらか） | 玄野武宏（11） |
| B（落ち着き） | 青山龍星（13） |
| C（明るい） | 白上虎太郎（12） |
| D（かわいい） | 雨晴はう（10） |

- デモは `http://localhost:*` / `http://127.0.0.1:*` で開く（エンジンの CORS が既定でローカルのページだけを許可するため）
- VOICEVOX の声を使っている間は `VOICEVOX:話者名` のクレジットを表示する（各話者の利用規約に従う）
- `new SageAvatar(renderer, { ttsMode: 'voicevox', voicevox: { speaker: 11, params: { speedScale: 1.05 } } })` のように話者と合成パラメータ（`audio_query` の項目）を渡せる
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
