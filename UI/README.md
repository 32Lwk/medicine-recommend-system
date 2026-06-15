# ユーザー向け UI パターン（プロトタイプ）

医薬品チャットツールのユーザー画面刷新案。**38パターン**の静的HTMLモックアップです。

## 確認方法

```bash
# リポジトリルートで
python -m http.server 8080
# → http://127.0.0.1:8080/UI/
```

または `UI/index.html` をブラウザで直接開いてください（`file://` でも動作します）。

## 収録パターン

### 基本刷新案（01〜10）

| # | ファイル | 系統 | 推奨表示 |
|---|----------|------|----------|
| 01 | `patterns/01-classic-green.html` | 現行緑・紫グラデ | 縦スタック |
| 02 | `patterns/02-sage-pharmacy.html` | /about セージ統一 | 縦スタック |
| 03 | `patterns/03-minimal-zen.html` | 禅・ミニマル | 縦スタック |
| 04 | `patterns/04-warm-care.html` | 温かみ・ケア | カルーセル |
| 05 | `patterns/05-line-carousel.html` | **LINE Flex 準拠** | カルーセル |
| 06 | `patterns/06-dark-clinical.html` | ダーク・クリニカル | カルーセル |
| 07 | `patterns/07-glass-morphism.html` | グラスモーフィズム | カルーセル |
| 08 | `patterns/08-compact-mobile.html` | モバイル・下部ナビ | カルーセル |
| 09 | `patterns/09-neubrutal.html` | ニューブルタリズム | カルーセル |
| 10 | `patterns/10-accessibility-first.html` | アクセシビリティ優先 | 縦スタック |

### クリエイティブ刷新案（11〜24）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 11 | `patterns/11-pharmacy-shelf.html` | マツキヨ等ドラッグストアアプリ | **棚（shelf）** |
| 12 | `patterns/12-story-swipe.html` | Instagram / TikTok Stories | **ストーリー（story）** |
| 13 | `patterns/13-concierge-card.html` | 高級ホテルコンシェルジュアプリ | スタック |
| 14 | `patterns/14-retro-terminal.html` | レトロCRTターミナル / ハッカー美学 | スタック |
| 15 | `patterns/15-apple-health.html` | Apple Health / iOS ヘルスケア | カルーセル |
| 16 | `patterns/16-notion-blocks.html` | Notion AI / ブロックエディタ | スタック |
| 17 | `patterns/17-duolingo-playful.html` | Duolingo / ゲーミフィケーション | カルーセル |
| 18 | `patterns/18-prescription-label.html` | 処方箋・調剤ラベル / 薬袋 | スタック |
| 19 | `patterns/19-split-diagnosis.html` | Ada Health / K Health | **分割（split）** |
| 20 | `patterns/20-floating-orb.html` | ChatGPT ボイスモード / AIオーブ | **オーブ（orb）** |
| 21 | `patterns/21-manga-panel.html` | 日本漫画コマ / 吹き出しUI | カルーセル |
| 22 | `patterns/22-night-pharmacy.html` | 24時間薬局ネオン看板 | カルーセル |
| 23 | `patterns/23-paper-receipt.html` | 感熱紙レシート / POSプリンタ | スタック |
| 24 | `patterns/24-pharma-carousel-pro.html` | **プロフェッショナルOTCカルーセル** | **カルーセル（pro）** |

### ヘルスケア・テレメディスン（25〜28）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 25 | `patterns/25-babylon-telehealth.html` | Babylon Health / Teladoc | **テレヘルス（telehealth）** + カルーセル |
| 26 | `patterns/26-symptom-bodymap.html` | Ada Health ボディマップ / 症状部位選択 | **ボディマップ（bodymap）** + カルーセル |
| 27 | `patterns/27-drug-facts-label.html` | FDA Drug Facts / 日本の薬情表示 | **薬情ラベル（label）** |
| 28 | `patterns/28-comparison-matrix.html` | 医療機器スペック比較表 / 価格.com | **比較表（matrix）** |

### コマース・ディスカバリー（29〜30）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 29 | `patterns/29-ecommerce-grid.html` | Amazon / 楽天市場 商品グリッド | **グリッド（grid）** + ドロワー |
| 30 | `patterns/30-single-focus-hero.html` | Spotify / Apple Music Now Playing | **ヒーロー（hero）** |

### プラットフォーム連携（31〜32）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 31 | `patterns/31-whatsapp-native.html` | WhatsApp Business / メッセージング | **WhatsApp（whatsapp）** + カルーセル |
| 32 | `patterns/32-wechat-mini.html` | 微信ミニプログラム / スーパーアプリ | **WeChat（wechat）** + カルーセル |

### アクセシビリティ・デバイス（33〜34）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 33 | `patterns/33-pictogram-elder.html` | 自治体高齢者向けピクトサイン / JIS S 0032 | スタック + **ピクトグラムチップ** |
| 34 | `patterns/34-wearable-compact.html` | Apple Watch / Wear OS ヘルス | **ウェアラブル（wearable）** + カルーセル |

### ウェルネス・信頼・システム（35〜38）

| # | ファイル | インスピレーション | レイアウト |
|---|----------|-------------------|------------|
| 35 | `patterns/35-headspace-calm.html` | Headspace / Calm 瞑想アプリ | カルーセル |
| 36 | `patterns/36-pharmacist-trust.html` | 薬局カウンセリング / 登録販売者表示 | **薬剤師ストリップ（pharmacist）** + カルーセル |
| 37 | `patterns/37-clinical-swiss.html` | スイスタイポグラフィ / バウハウス | **比較表（matrix）** |
| 38 | `patterns/38-material-you-3.html` | Google Material Design 3 | カルーセル |

## 本番推奨トップ3（医薬品チャット）

| 順位 | パターン | 理由 |
|------|----------|------|
| **1** | **24 Pharma Carousel Pro** | OTC推奨のフラッグシップ。プロカード・症状チップ・横比較・PMDA風ディスクレーマーが最もバランス良い |
| **2** | **36 Pharmacist Trust** | 薬剤師監修・資格表示で信頼最大化。OTC相談の心理的ハードルを下げる |
| **3** | **05 LINE Carousel** | LINE Flex との情報構造共通化。Web/LINE 両方で一貫した推奨体験 |

## カルーセル設計方針

推奨医薬品の横スクロール表示は、**読む量を減らして一目で比較できる**ことを最優先にしています。

### UX（横スクロール）

- `scroll-snap-type: x mandatory` + モバイルは `center`、デスクトップは `start` でスナップ
- タッチスワイプ・トラックパッド・マウスホイール（縦→横変換）に対応
- ドット + `1/3` カウンター + 前後矢印（44px タップ領域、狭い画面では矢印非表示）
- フォーカス時の左右キー操作（`aria` 対応）
- `IntersectionObserver` でアクティブドットを同期（ライブラリ不要）
- `touch-action: pan-x` で縦スクロール（チャット全体）を阻害しない

### カード情報設計（`carouselStyle: 'pro'`）

| 要素 | 目的 |
|------|------|
| 順位バッジ + OTC バッジ | 信頼・規制区分の即時認識 |
| 製品名・メーカー（小） | 最小限のテキスト階層 |
| スコアリング（円形ゲージ） | ％テキストだけでなく視覚的比較 |
| 剤形アイコン + 医薬品種別 | 錠剤/微粒などを絵文字に頼らず表示 |
| 症状マッチチップ | 文章ではなくタグで適合症状を表示 |
| 効能・理由（2行省略 + 詳細） | プログレッシブディスクロージャ |
| 年齢適合アイコン | 服用対象のクイック確認 |
| PMDA風ディスクレーマー帯 | 参考情報であることの明示 |

### `carouselStyle` オプション

| 値 | 用途 |
|----|------|
| `'pro'`（カルーセル既定） | 薬局・OTC向けのプロフェッショナルカード。**24 Pharma Carousel Pro** がフラッグシップ |
| `'playful'` | Duolingo・漫画などゲーミフィケーション系。絵文字ヒーロー付きレガシーカード |

棚（shelf）・ストーリー（story）・分割（split）・比較表（matrix）・グリッド（grid）・ヒーロー（hero）・薬情ラベル（label）レイアウトは従来どおり独立しており、カルーセル改善の影響を受けません。

### 商品画像（`imageUrl`）

`UI/shared/shell.js` のデモデータ `MEDICINES` 各要素に `imageUrl` フィールドがあります。URL が設定されていれば `<img>` で表示し、未設定（`null` / 空）の場合は **Noimage** プレースホルダーを表示します。

```javascript
// デモデータ例
{ name: 'ルルアタックTR', imageUrl: null }           // → Noimage プレースホルダー
{ name: 'ルルアタックTR', imageUrl: '/static/med/lulu.jpg' }  // → 商品画像
```

本番連携時は API レスポンスの画像 URL を `imageUrl` にマッピングするか、`medicineImageHtml()` を拡張してください。レンダリングは `medicineImageHtml(m, { variant })` に集約されています（`pro` / `playful` / `thumb` / `hero`）。

## レイアウトモード（shell.js）

`UIShell.mount()` で指定可能な拡張オプション：

| オプション | 値 | 説明 |
|-----------|-----|------|
| `recoLayout` | `'carousel'` \| `'stack'` \| `'shelf'` \| `'story'` \| `'matrix'` \| `'grid'` \| `'hero'` \| `'label'` | 推奨医薬品の表示形式 |
| `layout` | `'default'` \| `'compact'` \| `'split'` \| `'orb'` \| `'bodymap'` \| `'telehealth'` \| `'pharmacist'` \| `'whatsapp'` \| `'wechat'` \| `'wearable'` | アプリ全体のレイアウト |
| `carouselStyle` | `'pro'` \| `'playful'` | カルーセル／スタック時のカード様式（既定: カルーセルは `pro`） |
| `a11yPictogram` | `true` | 症状チップをピクトグラム＋大文字ラベルに切替（**33** 向け） |

```javascript
// 例: プロフェッショナルカルーセル（推奨）
UIShell.mount('app', { theme: 'pharma-carousel-pro', recoLayout: 'carousel', carouselStyle: 'pro' });

// 例: 症状ボディマップ分割
UIShell.mount('app', { theme: 'symptom-bodymap', layout: 'bodymap', recoLayout: 'carousel', carouselStyle: 'pro' });

// 例: 3薬比較表
UIShell.mount('app', { theme: 'comparison-matrix', recoLayout: 'matrix', carouselStyle: 'pro' });

// 例: EC風グリッド + ドロワー
UIShell.mount('app', { theme: 'ecommerce-grid', recoLayout: 'grid', carouselStyle: 'pro' });

// 例: 薬剤師監修ストリップ
UIShell.mount('app', { theme: 'pharmacist-trust', layout: 'pharmacist', recoLayout: 'carousel', carouselStyle: 'pro' });

// 例: 高齢者向けピクトグラム
UIShell.mount('app', { theme: 'pictogram-elder', recoLayout: 'stack', a11yPictogram: true });
```

## 組み込み済み機能（デモ）

現行 `templates/index.html` + `static/js/main.js` と同等の UI 要素を配置しています。

- 言語切替（ja / en / ko / zh）
- ℹ️ 情報モーダル（概要・使い方・プライバシー・設定）
- 👤 ユーザー情報登録モーダル
- 📋 追加属性入力モーダル
- チャット（ユーザー/ボット吹き出し・処理中・薬剤師返信）
- **推奨医薬品**（最大3件・スコア・効能・推奨理由）
- **商品画像**（`imageUrl` ありは `<img>`、未設定時はプレースホルダー **Noimage**）
- スコア内訳・アレルギー/相互作用/使用注意/受診目安
- 👍👎 フィードバック → 詳細モーダル
- 🎤 音声入力 · 送信 · 症状チップ
- 🗑️ 履歴クリア · 🔄 新セッション · 👨‍⚕️ 薬剤師要請
- オンボーディング（「📖 ガイド」ボタン）
- 季節パーティクル（テーマによりON/OFF）

## デザインリファレンス一覧

各パターンが参考にしたサービス・美学（見た目のインスピレーションのみ、コピーではありません）：

| パターン | 参考サービス / 美学 |
|----------|---------------------|
| 05 LINE Carousel | LINE Flex Message カルーセル |
| 11 Pharmacy Shelf | マツモトキヨシアプリ、店頭商品棚 |
| 12 Story Swipe | Instagram Stories, TikTok 縦スワイプ |
| 13 Concierge Card | 高級ホテルコンシェルジュアプリ（Four Seasons等） |
| 14 Retro Terminal | 1980s CRT, Matrix green phosphor |
| 15 Apple Health | Apple Health, iOS Human Interface Guidelines |
| 16 Notion Blocks | Notion, Notion AI チャット |
| 17 Duolingo Playful | Duolingo, ゲーミフィケーション学習アプリ |
| 18 Prescription Label | 日本の調剤ラベル・薬袋 typography |
| 19 Split Diagnosis | Ada Health, K Health, Babylon Health |
| 20 Floating Orb | ChatGPT Advanced Voice, Siri orb |
| 21 Manga Panel | 日本漫画・LINEスタンプ吹き出し |
| 22 Night Pharmacy | 24h薬局ネオン看板、サイバーパンク薬局 |
| 23 Paper Receipt | コンビニ感熱レシート、EC-CUBEレシート |
| 25 Babylon Telehealth | Babylon Health, Teladoc, オンライン診療 |
| 26 Symptom Body Map | Ada Health ボディマップ, 症状部位選択UI |
| 27 Drug Facts Label | FDA Drug Facts Label, 日本の薬情表示様式 |
| 28 Comparison Matrix | 価格.com比較表, 医療機器スペックシート |
| 29 E-commerce Grid | Amazon, 楽天市場 商品一覧 |
| 30 Single Focus Hero | Spotify Now Playing, Apple Music |
| 31 WhatsApp Native | WhatsApp Business API, メッセージングUI |
| 32 WeChat Mini | 微信ミニプログラム, スーパーアプリ内嵌 |
| 33 Pictogram Elder | JIS S 0032 高齢者向けピクトサイン |
| 34 Wearable Compact | Apple Watch, Wear OS Health |
| 35 Headspace Calm | Headspace, Calm 瞑想・ウェルネスアプリ |
| 36 Pharmacist Trust | 薬局カウンセリング, 登録販売者表示 |
| 37 Clinical Swiss | スイスタイポグラフィ, バウハウス |
| 38 Material You 3 | Google Material Design 3, Android 14 |

## LINE カルーセルとの関係

`05-line-carousel` は `src/handlers/line/flex_messages.py` の `build_recommendation_carousel` と同じ情報構造（順位・商品名・メーカー・効能・推奨理由・おすすめ度）を Web 横スクロール UI で再現しています。`24-pharma-carousel-pro` は同情報を**視覚優先のプロカード**（スコアリング・症状チップ・詳細折りたたみ）で表現した本番候補です。

## ファイル構成

```
UI/
  index.html          # ギャラリー（01〜38）
  README.md
  shared/
    shell.css         # レイアウト・コンポーネント（CSS変数でテーマ切替）
    shell.js          # デモ用 HTML 生成・モーダル操作
  patterns/
    01-classic-green.html … 38-material-you-3.html
```

## 本番への組み込み

1. 選定パターンの CSS 変数を `static/css/main.css` に移植
2. 推奨結果ブロックを `recoLayout: 'carousel' | 'stack' | 'shelf' | 'story' | 'matrix' | 'grid' | 'hero' | 'label'` で切替可能に
3. 全体レイアウトを `layout: 'default' | 'compact' | 'split' | 'orb' | 'bodymap' | 'telehealth' | 'pharmacist' | 'whatsapp' | 'wechat' | 'wearable'` で切替可能に
4. `shell.js` のカード HTML を `main.js` の推奨レンダラと統合
5. スクロール領域には引き続き `app-scrollbar` + `scrollbar.css` を使用

## 推奨の選び方（医薬品チャット特性）

| 優先事項 | 候補 |
|----------|------|
| 移行コスト最小 | 01 Classic Green |
| ブランド統一（/about） | 02 Sage Pharmacy |
| LINE/Web UI 共通化 | **05 LINE Carousel** |
| **OTC・薬局の信頼感（カルーセル）** | **24 Pharma Carousel Pro** |
| **薬剤師監修・信頼最大化** | **36 Pharmacist Trust** |
| テレヘルス・オンライン診療連携 | **25 Babylon Telehealth** |
| 視覚的症状入力 | **26 Symptom Body Map** |
| 法定表示・規制準拠感 | **27 Drug Facts Label** / 18 Prescription Label |
| 3薬横比較・データ重視 | **28 Comparison Matrix** / **37 Clinical Swiss** |
| EC・店頭購買体験 | **29 E-commerce Grid** / 11 Pharmacy Shelf |
| 第1候補の深掘り | **30 Single Focus Hero** |
| WhatsApp内展開 | **31 WhatsApp Native** |
| 中国市場・WeChat | **32 WeChat Mini** |
| 高齢者・読みやすさ | 03 Minimal Zen / 10 Accessibility / **33 Pictogram Elder** |
| ウェアラブル端末 | **34 Wearable Compact** |
| 不安軽減・相談感 | 04 Warm Care / **13 Concierge** / **35 Headspace Calm** |
| スマホ/LINEミニアプリ | 08 Compact Mobile / **12 Story Swipe** / 32 WeChat Mini |
| 症状の時系列把握 | **19 Split Diagnosis** |
| 若年層・差別化 | 09 Neubrutal / **17 Duolingo** / **21 Manga** |
| AI没入感・音声対話 | **20 Floating Orb** |
| 店頭・EC連携イメージ | **11 Pharmacy Shelf** |
| 公的信頼感・ラベル感 | **18 Prescription Label** / **23 Paper Receipt** |
| Android / クロスプラットフォーム | **38 Material You 3** / 15 Apple Health |
