# AI 生成スプライト・装飾のライセンスとプロンプト記録

## 方針

- **本番ランタイムでは外部の画像生成 API を呼ばない**。開発時に生成した PNG をリポジトリへコミットする。
- **透明背景**、**32〜64px 程度**のタイル、**淡色・中間色**（黒ベタ・濃いグレーの主色を避ける）。
- 追加・差し替え時は **本ファイルまたは CHANGELOG に追記**する（監査・権利確認のため）。

## 記録項目（追記テンプレート）

| ファイル（リポジトリ相対） | 生成日 | ツール / モデル | ライセンス注意 | プロンプト要約 |
|----------------------------|--------|-----------------|------------------|----------------|
| `static/img/particles/valentine/heart-glow.png` | 2026-05-11 | Cursor 画像生成（本リポジトリ用プロンプト） | 生成ツールの利用条件に従う | 淡色ピンクのハート、透明背景、医療系チャット向けに黒ベタなし |
| `static/img/particles/halloween/pumpkin-soft.png` | 2026-05-11 | Cursor 画像生成（本リポジトリ用プロンプト） | 同上 | 淡いオレンジのかぼちゃアイコン、透明背景、ホラー表現なし |

### 使用プロンプト全文（粒子・Cursor 画像生成）

**heart-glow.png**

> Small UI particle asset, 64x64 pixel style: soft pastel pink and white heart shape with gentle outer glow, centered, semi-transparent soft edges, fully transparent background (checkerboard clear), no text, no black fill, flat friendly icon for medical chat overlay on light gray, PNG aesthetic crisp edges suitable for downsizing to 1em in browser.

**pumpkin-soft.png**

> Small UI particle asset, 64x64 pixel style: cute minimalist orange pumpkin, soft rounded body, tiny brown stem, very subtle highlight, pastel not scary, centered, fully transparent background, no black background, flat icon for medical chat particle on light gray, PNG crisp edges.

### 粒子スプライト一括（2026-05・Cursor 画像生成）

以下はいずれも **64×64 前後の UI 粒子**、**透明背景**、**黒ベタ禁止**、**医療系チャット向けの淡色・非ホラー**を英語プロンプトで指定して生成した。ファイルは `static/img/particles/<行事>/` に配置し、`PARTICLE_PROFILES` に登録済み。

| ファイル名（リーフ） | プロンプト要約（英語全文は生成時ログに相当） |
|----------------------|-----------------------------------------------|
| `soybean-soft.png` | 節分・淡色の豆形、透明背景 |
| `car-soft.png` / `plane-soft.png` | GW・車・飛行機のシルエット、透明背景 |
| `carp-streamer-soft.png` / `kabuto-soft.png` | こいのぼり・兜、透明背景 |
| `tanzaku-soft.png` / `bamboo-soft.png` | 七夕・短冊・竹、透明背景 |
| `firework-soft.png` | 夏・花火、透明背景（波用スプライトは未コミットのため未登録） |
| `hina-doll-soft.png` | ひな祭り・人形シルエット抽象、透明背景 |
| `gift-soft.png` | ホワイトデー・ギフト箱、透明背景 |
| `cap-soft.png` / `bag-soft.png` | 卒業角帽・ランドセル、透明背景 |
| `petal-soft.png` / `butterfly-soft.png` | 花びら・蝶、透明背景 |
| `carnation-particle-soft.png` | 敬老・カーネーション、透明背景 |
| `fan-soft.png` | 七五三・扇子風、透明背景 |
| `kadomatsu-soft.png` / `ornament-soft.png` | 正月門松・クリスマスオーナメント、透明背景 |
| `maple-soft.png` / `tulip-soft.png` | 秋もみじ・母の日チューリップ、透明背景（冬の雪結晶スプライトは未コミットのため未登録） |

※ ツール出力の PNG は **真の完全アルファ**にならない場合がある。縁が気になる場合は画像編集でアルファ調整する。

### 左右装飾（`static/img/events/`）

`SEASON_CONFIG` の七夕・敬老・ハロウィン・七五三用。いずれも **Cursor 画像生成**、**透明背景**・**黒ベタなし**・**医療系 UI 向け淡色**を英語プロンプトで指定（チャット角装飾 120px 風）。

| ファイル（リポジトリ相対） | プロンプト要約 |
|----------------------------|----------------|
| `static/img/events/tanabata/tanabata-streamer.png` | 七夕・短冊カラー紙垂れ、透明背景 |
| `static/img/events/tanabata/tanabata-bamboo.png` | 七夕・竹と葉、透明背景 |
| `static/img/events/keiro/keiro-carnation-soft.png` | 敬老・ピンクカーネーション花束、透明背景 |
| `static/img/events/keiro/keiro-gift-soft.png` | 敬老・リボン付きギフト箱、透明背景 |
| `static/img/events/halloween/halloween-moon-soft.png` | ハロウィン・三日月と小星、非ホラー、透明背景 |
| `static/img/events/halloween/halloween-star-soft.png` | ハロウィン・パステル星とキラ、透明背景 |
| `static/img/events/shichigosan/shichigosan-chouchin-soft.png` | 七五三・提灯ちょうちん、透明背景 |
| `static/img/events/shichigosan/shichigosan-motif-soft.png` | 七五三・菊紋様の和柄円形、透明背景 |

※ 粒子用 `static/img/particles/` と同様、**完全なアルファ**はツール次第。必要なら後処理で調整する。

商用の画像生成サービスを使う場合は、**利用規約の帰属・再配布条件**を確認し、上表に URL または条文要約を追記する。
