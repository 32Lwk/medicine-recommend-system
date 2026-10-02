# Live2D Cubism — パーツ分け・PSD 仕様（Sage キャスト A–D）

> **目的**: 選定 4 名（A/B/C/D）を Cubism Editor で rig 可能な PSD に落とし込むための**正本指示**。  
> **参照アート**: `static/img/live2d/concept/whitecoat/cast-unified/`  
> **表情キー**: `EXPRESSIONS_README.md` 各 `expressions-{a,b,c,d}/`  
> **アプリ連携方針**: 方式 A（既存 `POST /api/tts` + クライアント描画）。`docs/planning/notebooklm-history/CLAUDE_バーチャルヒューマン導入調査_要約_20260914.md`

---

## 1. 進め方（推奨順）

| 段階 | 内容 | 成果物 |
|------|------|--------|
| 1 | **B のみ** PSD 切り分け → rig → Web プレビュー | `sage_cast_b.model3.json` 等 |
| 2 | B のパラメータ表・命名を**テンプレート固定** | 本書 §5–§7 |
| 3 | A/C/D は **B と同一パーツツリー**、差分は髪・顔・中の服のみ | 3 モデル |
| 4 | Sage Terrace に `AVATAR_ENABLED` で載せる | 別 issue |

**理由**: 白衣・ピン・ポケット形状は全員共通。B が白衣正本のため、肩・襟・袖の deform 設定を B で一度決めると横展開が速い。

---

## 2. 入力素材の使い分け

| 用途 | ファイル | 使い方 |
|------|----------|--------|
| 体・白衣・中の服の**基準ポーズ** | `sage-cast-{a,b,c,d}-unified-coat.jpg` | E0 相当の全身バストを PSD 土台に |
| **表情** E0–E5 | `expressions-*/sage-*-e*.jpg` | 眉・目・口の**形状参照**（ArtMesh 差分 or deform 目標） |
| **口形** | `sage-*-mouth-*.jpg` | 口 ArtMesh の drawable 差分 or `ParamMouthForm` 校正 |
| **目** | `sage-*-eye-*.jpg` | `ParamEyeLOpen` / `ParamEyeROpen` の 0 / 0.5 / 1 キー |
| 白衣正本 | `coat-master-b.png` | 襟・ピン・ポケット位置の寸法参照 |

クロマキー緑は **PSD 化前に透過 PNG 化**（`#00FF00` 系、許容 ΔE は作業者判断で 5–15 程度）。  
**背景レイヤーは PSD に含めない**（Live2D は透過前提）。

---

## 3. キャンバス・座標

| 項目 | 推奨値 | 備考 |
|------|--------|------|
| キャンバス | **2048 × 2048 px** | バストアップ。縦長にする場合 1536×2048 も可（4 名同一サイズ必須） |
| 解像度 | 72–144 dpi | 実寸は px 基準 |
| 原点 | **キャンバス中央やや上**（眉間付近） | 全モデル同一。首回転の pivot と揃える |
| 出力 | RGBA PNG パーツ + `.psd` 正本 | Editor インポート用 |

---

## 4. PSD レイヤー構造（全キャラ共通ツリー）

Cubism Editor の**描画順 = 下から上**。以下の**グループ名・パーツ名は全キャラ同一**にする（A/C/D は中身の絵だけ差し替え）。

```
sage_cast_{a|b|c|d}/
├── body/                    … 首・肩・胸の肌（白衣の下）
├── inner/                   … 中の服（キャラ別・§8）
│   ├── inner_torso
│   ├── inner_collar
│   └── inner_accessory        … タイ／リボン／ベスト等
├── coat_back/               … 白衣後ろ襟・肩ライン
├── coat_body/               … 白衣本体（袖含む）
├── coat_lapel_L/            … 左襟（画面右）
├── coat_lapel_R/            … 右襟（画面左）
├── coat_pocket/             … 左胸四角パッチ
├── pin_capsule/             … 襟ピン（ミント×白・横向き）※ deform 最小
├── hair_back/               … 後ろ髪
├── hair_side_L/
├── hair_side_R/
├── hair_front/              … 前髪
├── hair_extra/              … ポニー／編み込み等（D/A 等）
├── face_base/               … 顔輪郭・頬・耳
├── nose/
├── mouth/
│   ├── mouth_base           … 閉口ベース（E0）
│   ├── mouth_open_a         … あ（差分 drawable 方式の場合）
│   ├── mouth_open_i
│   ├── mouth_open_u
│   ├── mouth_open_e
│   └── mouth_open_o
├── eye_L/
│   ├── eye_white_L
│   ├── eye_iris_L
│   ├── eye_highlight_L
│   └── eye_lash_L
├── eye_R/
│   └── （同上）
├── brow_L/
├── brow_R/
└── expression_overlay/      … 任意：E1–E5 用眉・目尻差分（差分方式時）
```

### 4.1 必須分離ルール

1. **髪**: `hair_back` と `hair_front` は必ず分割（首振り・呼吸で破綻しないため）。
2. **目**: 白目・虹彩・ハイライト・まつ毛を分離（まばたき = `ParamEye*Open`）。
3. **眉**: 口と独立（E2 思案・E3 共感は眉主導）。
4. **白衣**: 襟左右を分けると呼吸 idle が自然（任意だが推奨）。
5. **ピン**: 単独パーツ（アニメーション不要、親は `coat_lapel_L`）。
6. **中の服**: `inner/` のみキャラごとに差し替え。**`coat_*` は B 正本からコピー可**（色・形同一）。

### 4.2 禁止・注意

- 1 レイヤーに**両目**を含めない。
- 口形 6 種を**1 枚に焼き込まない**（差分 or パラメータで切替）。
- テキスト・読める名札・医療十字を描かない。
- 実写テクスチャ・写真コラージュ禁止。

---

## 5. パラメータ設計（全キャラ共通 ID）

Cubism 標準 + アプリ連携用カスタム。**ID 文字列は 4 モデルで完全一致**。

### 5.1 標準（Live2D 慣例）

| パラメータ ID | 範囲 | 用途 |
|---------------|------|------|
| `ParamAngleX` | -30 … 30 | 首 Yaw |
| `ParamAngleY` | -30 … 30 | 首 Pitch |
| `ParamAngleZ` | -30 … 30 | 首 Roll |
| `ParamBodyAngleX` | -10 … 10 | 上半身（任意・小さめ） |
| `ParamBreath` | 0 … 1 | 呼吸 idle |
| `ParamEyeLOpen` | 0 … 1 | 左目開閉（0=閉、1=開） |
| `ParamEyeROpen` | 0 … 1 | 右目開閉 |
| `ParamEyeBallX` | -1 … 1 | 視線 X |
| `ParamEyeBallY` | -1 … 1 | 視線 Y |
| `ParamMouthOpenY` | 0 … 1 | 口開き（あ・お方向） |
| `ParamMouthForm` | -1 … 1 | 口横広げ（い）↔ 中立 ↔ え/open |

### 5.2 表情（相談 UI 連動）

| パラメータ ID | 型 | 値 | 対応 |
|---------------|-----|-----|------|
| `ParamExpression` | 浮動 | 0 … 5 | **0=E0, 1=E1, … 5=E5**（線形補間しない・**スナップ**） |

**実装方式（推奨）**:  
- `ParamExpression` を **Part Opacity / Deform 切替**の入力にし、E0–E5 各キーを Editor 上で登録。  
- 口形リップシンク中は **E0 または E1 をベース**に `ParamMouthOpenY` / `ParamMouthForm` を上書き（E2–E5 中は口パラメータ優先度を設計）。

### 5.3 アプリ側カスタム（将来）

| パラメータ ID | 用途 |
|---------------|------|
| `ParamIdleMotion` | 待機モーション選択（0=通常） |
| `ParamProcessing` | SSE 処理中（0/1）→ E2 + フィラー発話連動 |

---

## 6. 表情 E0–E5 の rig 方針

コンセプト JPG は**見た目のターゲット**。Cubism では次の **ハイブリッド**を推奨。

| 表情 | 主な deform | 補助 |
|------|-------------|------|
| E0 通常 | 基準ポーズ | — |
| E1 微笑み | 口角 UP、目やや細め | `ParamExpression=1` |
| E2 思案 | 眉内側 UP、視線 `EyeBallY` やや上 | E2 時 `ParamProcessing` と連動可 |
| E3 共感 | 眉八の字、目柔らか | |
| E4 軽い驚き | 眉 UP、目やや開、口小開き | 強度は中（大げさ禁止） |
| E5 うなずき | `ParamAngleY` 短時間 -5→0 | 首アニメ＋微笑み |

**Drawable 差分方式**（AI 原画向け・短期）:  
`expression_overlay/` に E1–E5 用の眉・口形状を**半透明で重ねない**完全差分 ArtMesh として持ち、`ParamExpression` で表示切替。  
**Deform 方式**（長期・推奨）: E0 1 枚から Editor でキー打ち。コンセプト JPG は校正用。

---

## 7. 口形（あいうえお + 閉）と TTS

### 7.1 コンセプト JPG との対応

| ファイル suffix | ParamMouthOpenY | ParamMouthForm |
|-----------------|-----------------|----------------|
| `mouth-closed` | 0 | 0 |
| `mouth-a` | **1.0** | 0 |
| `mouth-i` | 0.2 | **+1.0**（横広げ・差強調版） |
| `mouth-u` | 0.3 | -0.3（すぼめ） |
| `mouth-e` | **0.55** | **+0.2**（開口・差強調版） |
| `mouth-o` | 0.85 | -0.2 |

Editor で上記を**キー**として保存し、実機で `/api/tts` 再生中はクライアントが **音量 or 音素タイミング**から OpenY/Form を補間。

### 7.2 リップシンク（方式 A）

1. TTS 再生開始  
2. 無音区間 → `ParamMouthOpenY=0`  
3. 簡易: 音量 RMS → `ParamMouthOpenY` のみ（最小実装）  
4. 拡張: 日本語母音推定 → OpenY + Form 同時（精度向上）

**注意**: 口形 6 枚を**フレーム列として焼く**のではなく、**2 パラメータ + 必要なら mouth drawable 差分**で連続動作させる。

---

## 8. キャラ別差分（中の服のみ）

| ID | 中の服（`inner/`） | 備考 |
|----|-------------------|------|
| A | クリームリブニット + テラコッタ縁 | 襟元は `inner_collar` |
| B | スレートブルーシャツ + 紺ネクタイ | **テンプレート正本** |
| C | スカイブルー開襟 + テラコッタベスト | タイなし |
| D | クリームブラウス + テラコッタリボン | 女性・襟元リボン |

髪は `hair_*` 全差し替え。`coat_*` / `pin_capsule` は B から流用可（ピン位置固定）。

---

## 9. メッシュ・deform ガイド

| 部位 | メッシュ密度 | 備考 |
|------|--------------|------|
| 顔輪郭 | 中 | 首回転と連動 |
| 髪 | 中〜高 | 前髪は動き大 |
| 目・口 | **高** | 表情・リップシンク |
| 白衣 | 低〜中 | 呼吸のみ |
| ピン | 低 | 剛体に近い |

**Physics（任意）**: `hair_front` / `hair_extra` のみ軽い揺れ。白衣は Physics なし（薬剤師誤認を増やさないため過剰な動き禁止）。

---

## 10. 納品チェックリスト（1 キャラあたり）

- [ ] `.psd` 正本 + 透過 PNG パーツ一式
- [ ] Cubism Editor プロジェクト（`.cmo3` 推奨）
- [ ] 書き出し: `.moc3` + `model3.json` + textures/
- [ ] パラメータ ID が §5 と一致
- [ ] `ParamExpression` 0–5 がコンセプトシートと視覚一致
- [ ] 口形 6 種が §7.1 の OpenY/Form で再現可能
- [ ] まばたき 0.15–0.2s で自然
- [ ] クロマキー残り・白フリンジなし
- [ ] 商用 Cubism ライセンス条件を満たす（店舗展開時）

---

## 11. ファイル命名（リポジトリ配置案）

```
static/live2d/
├── sage_cast_b/
│   ├── source/sage_cast_b.psd
│   ├── textures/
│   ├── sage_cast_b.model3.json
│   └── motions/          … idle, nod, blink（任意）
├── sage_cast_a/
├── sage_cast_c/
└── sage_cast_d/
```

現段階では **concept のみ** Git 管理。`.moc3` 等はサイズ・ライセンスに応じて LFS または配布チャネル分離。

---

## 12. 法務・UI（rig 時の固定要件）

バーチャルヒューマン調査どおり、**モデルと別レイヤー**で常時表示:

- 「AI です／薬剤師・医師ではありません」（HTML オーバーレイ可、Live2D 内テキスト不可）
- アバター OFF トグル、テキストチャット常時利用可

---

## 13. 関連ドキュメント

- **自前 Cubism 作業フロー**: [`LIVE2D_CUBISM_DIY_WORKFLOW.md`](LIVE2D_CUBISM_DIY_WORKFLOW.md)
- **B 作業フォルダ**: `static/live2d/sage_cast_b/`（`python3 scripts/live2d_prepare_cast_b.py`）
- `static/img/live2d/concept/whitecoat/cast-unified/EXPRESSIONS_README.md`
- `static/img/live2d/concept/whitecoat/cast-unified/CUBISM_PSD_CHECKLIST.md`（作業者向け短版）
- `docs/planning/notebooklm-history/CLAUDE_バーチャルヒューマン導入調査_要約_20260914.md`
