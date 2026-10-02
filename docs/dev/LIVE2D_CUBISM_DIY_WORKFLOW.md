# Live2D Cubism Editor — 自前作業フロー（Character B）

> 対象: Cubism Editor を自分で回す場合。  
> 正本仕様: [`LIVE2D_CUBISM_PSD_SPEC.md`](LIVE2D_CUBISM_PSD_SPEC.md)  
> 作業フォルダ: `static/live2d/sage_cast_b/diy/`

---

## 0. 前提ソフト

| ソフト | 用途 |
|--------|------|
| **Live2D Cubism Editor**（無料版で開始可） | メッシュ・パラメータ・書き出し |
| Photoshop / Clip Studio Paint / GIMP のいずれか | パーツ切り分け PSD |
| （任意）Adobe Photoshop | `assemble_psd.jsx` で空レイヤー PSD を一括生成 |

Cubism SDK for Web はアプリ組み込み時。まず Editor で `.moc3` まで出せば十分。

---

## 1. リポジトリ側の準備（済・再実行可）

```bash
python scripts/live2d_prepare_cast_b.py
```

生成物:

```
static/live2d/sage_cast_b/
├── diy/
│   ├── reference/          … クロマキー透過した参照 PNG（表情・口・目）
│   ├── layers/             … 空の名前付き PNG（2048×2048）← ここに描く／切り出す
│   ├── parts.csv           … パーツ一覧
│   ├── parameters.csv      … Cubism パラメータ定義
│   ├── mouth_param_keys.csv
│   ├── expression_param_keys.csv
│   ├── LAYER_ORDER.txt     … 下→上の描画順
│   ├── GUIDE_e0_faint.png  … 薄いガイド（PSD に入れない）
│   └── assemble_psd.jsx    … Photoshop 用：layers → PSD
├── source/                 … 切り出し済み E0 / unified
├── textures/               … Editor 書き出し先（後で）
└── motions/
```

---

## 2. パーツ切り分け（イラスト側）

### 推奨手順

1. `source/sage_cast_b_e0_cutout.png`（または `diy/reference/e0-neutral.png`）を開く  
2. `diy/LAYER_ORDER.txt` の順でレイヤーを作成（**名前は `parts.csv` の `layer_id` と完全一致**）  
3. 髪・目・口・白衣・ピンなどを切り分けて各レイヤーへ  
4. 口形・表情は `diy/reference/mouth-*.png` / `e*.png` を横に並べて形状合わせ  
5. キャンバス **2048×2048**、原点は眉間付近（仕様書 §3）  
6. PSD を `static/live2d/sage_cast_b/source/sage_cast_b.psd` として保存  

### Photoshop で空 PSD を先に作る場合

1. `diy/layers/*.png` はすべて透明のまま  
2. Photoshop で `File > Scripts > Browse…` → `diy/assemble_psd.jsx`  
3. できた `diy/sage_cast_b_layers.psd` に切り分け絵を貼り付け  
4. 完成 PSD を `source/sage_cast_b.psd` へコピー  

### 切り分けの最低ライン（B・初回）

必須だけ先に切り、残りは後回しでも Editor に入れる:

- `face_base`, `nose`
- `eye_*`（L/R 各 4）
- `brow_L`, `brow_R`
- `mouth_base` + `mouth_open_{a,i,u,e,o}`
- `hair_back`, `hair_front`
- `coat_body`, `coat_lapel_L`, `pin_capsule`
- `inner_torso`, `inner_accessory`

`hair_extra` / `expression_overlay/*` は空のままでよい。

---

## 3. Cubism Editor 手順

### 3.1 インポート

1. Cubism Editor で新規モデル  
2. `source/sage_cast_b.psd` をインポート（レイヤー名が ArtMesh 名になる）  
3. テクスチャアトラスサイズは 2048 推奨  

### 3.2 メッシュ

| 優先 | パーツ | 密度 |
|------|--------|------|
| 高 | 口・目・眉 | 細かく |
| 中 | 顔・前髪 | 中 |
| 低 | 白衣・ピン | 粗く |

### 3.3 パラメータ作成

`diy/parameters.csv` のとおり追加（ID を一字一句合わせる）:

- `ParamEyeLOpen` / `ParamEyeROpen` … 参照 `reference/eye-half.png`, `eye-closed.png`
- `ParamMouthOpenY` / `ParamMouthForm` … `mouth_param_keys.csv`
- `ParamExpression` 0–5 … `expression_param_keys.csv`（**キーはスナップ**、連続補間しない）
- `ParamBreath`, `ParamAngleX/Y/Z`

### 3.4 表情・口形のキー打ち

1. `ParamExpression=0` で E0 基準  
2. 1〜5 をそれぞれ `reference/e1`…`e5` に合わせて眉・目・口を変形（または overlay 表示切替）  
3. 口形は口を閉じた状態から `mouth_param_keys.csv` の OpenY/Form を打つ  
4. **い** = Form +1（横広げ）、**え** = OpenY 0.55 + Form 0.2（開口）で差を維持  

### 3.5 まばたき・うなずき

- まばたき: `ParamEye*Open` 1→0→1（0.15–0.2s）をモーションまたは物理で  
- E5: `ParamAngleY` を短く -5→0 + 微笑み  

### 3.6 書き出し

```
static/live2d/sage_cast_b/
├── sage_cast_b.model3.json
├── sage_cast_b.moc3
├── textures/
└── (任意) motions/*.motion3.json
```

`.cmo3` プロジェクトは `source/` に置く（サイズ大なら Git LFS またはローカルのみ）。

---

## 4. 動作確認（Editor 内）

- [ ] まばたきが自然  
- [ ] あいうえおで口が区別できる（特にい／え）  
- [ ] E0–E5 がコンセプトシートと対応  
- [ ] 呼吸 idle で白衣が壊れない  
- [ ] ピンが襟に追従  

---

## 5. A / C / D への横展開

1. B の `.cmo3` を複製  
2. `inner/*` と `hair_*` と顔パーツだけ差し替え（`coat_*` / `pin_capsule` は流用）  
3. パラメータ ID は変更しない  
4. `scripts/live2d_prepare_cast_b.py` をベースに `prepare_cast_{a,c,d}` を後で追加可  

---

## 6. アプリ組み込み（後続）

方式 A: Cubism SDK for Web + 既存 `POST /api/tts`。  
フラグ案: `AVATAR_ENABLED`。詳細は VH 調査要約と `LIVE2D_CUBISM_PSD_SPEC.md` §7.2。

### 6.1 先行実装: スプライト版アバター

`.moc3` 完成前の代替として、土台画像をパーツ（体・耳・顔・目鼻口・髪）に分けて視差で動かす 2.5D アバターがある（`static/live2d/sage_cast_b/README.md` 参照）。手・腕はジェスチャー 8 種（手を振る・手のひら差し出し・人差し指・胸に手・あごに手・こぶし・両手を合わせる・OK）を重ね絵で出す。

| 層 | ファイル | Cubism 移行時 |
|----|----------|---------------|
| 制御 | `static/js/avatar/sage_avatar.js`（`SageAvatar`: 感情・モーション・まばたき・台本・リップシンク） | そのまま流用 |
| 描画 | `static/js/avatar/sage_avatar_sprite.js`（`SpriteAvatarRenderer`） | Cubism レンダラーに差し替え |
| 素材 | `static/live2d/sage_cast_b/sprite/`（`scripts/live2d_build_sprite_b.py` で生成, manifest v2） | 不要になる |

制御側は毎フレーム `applyPose(params)` を呼ぶ。Cubism レンダラーでの対応付け:

| レンダラー API | Cubism パラメータ |
|----------------|-------------------|
| `applyPose({angleX, angleY, angleZ})` | `ParamAngleX` / `ParamAngleY` / `ParamAngleZ`（-30..30） |
| `applyPose({bodyAngleZ, lean, bow})` | `ParamBodyAngleZ`、前傾・お辞儀は `ParamBodyAngleY` 系の独自パラメータ |
| `applyPose({hop, breath})` | 位置オフセット / `ParamBreath` |
| `applyPose({gestures: [{key, amount, sway, lift}]})` | 腕パーツ（`ParamArmL/R` 系の独自パラメータ）またはジェスチャーごとの motion3.json。スプライト版は手の重ね絵を下からせり上げて肘を支点に揺らす |
| `setExpression(key)` | 表情 exp3（neutral, smile, thinking, empathy, surprise, relief, worry, sorry, serious, cheer, shy, confused） |
| `setEyes('open'/'half'/'closed')` | `ParamEyeLOpen` / `ParamEyeROpen` = 1 / 0.5 / 0 |
| `setMouth(null/'a'/'i'/'u'/'e'/'o')` | `diy/mouth_param_keys.csv` の OpenY / Form |

視線（黒目だけの移動）はスプライト版では未対応。頭の向きと目鼻口の視差で表現している。Cubism 版では `ParamEyeBallX/Y` を追加する。

デモ: `/static/dev/avatar_demo.html`（チャット画面には未組み込み）。当面の公開先は `https://live2d.medicine.yutok.dev`（`workers/live2d-demo/README.md`）。

---

## 7. 困ったとき

| 症状 | 対処 |
|------|------|
| 緑フチが残る | `live2d_prepare_cast_b.py` のキーを再実行、または手で消し込み |
| 口形が似る | `mouth_param_keys.csv` のい／えを再確認。差分 drawable に切替 |
| PSD レイヤー名不一致 | `parts.csv` の `layer_id` にリネーム |
| Editor が重い | 白衣メッシュを減らす、テクスチャ 2048→1024（プレビュー時） |
