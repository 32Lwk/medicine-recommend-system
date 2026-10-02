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

---

## 7. 困ったとき

| 症状 | 対処 |
|------|------|
| 緑フチが残る | `live2d_prepare_cast_b.py` のキーを再実行、または手で消し込み |
| 口形が似る | `mouth_param_keys.csv` のい／えを再確認。差分 drawable に切替 |
| PSD レイヤー名不一致 | `parts.csv` の `layer_id` にリネーム |
| Editor が重い | 白衣メッシュを減らす、テクスチャ 2048→1024（プレビュー時） |
