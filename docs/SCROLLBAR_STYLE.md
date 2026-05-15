# スクロールバー統一ガイド

本アプリケーションでは、スクロールバーの見た目を **`static/css/scrollbar.css`** に一元化している。  
新規・変更時は **ブラウザ標準のグレースクロールバーや独自の `::-webkit-scrollbar` 定義を追加しない**。

## デザイン仕様

| 項目 | 値 |
|------|-----|
| トラック | `#f0f0f0`（`--app-scrollbar-track`） |
| サム | `--focus-color`（既定 `#4CAF50`） |
| サム（ホバー） | `#43a047`（`--app-scrollbar-thumb-hover`） |
| 幅（縦・横） | 7px |
| 形状 | 角丸（`border-radius: 999px`） |

Firefox では `scrollbar-width: thin` と `scrollbar-color` を使用する。  
WebKit 系では `::-webkit-scrollbar*` で上記と同等の見た目にする（詳細は `scrollbar.css` を参照）。

## 読み込み方法

各画面の CSS から次のいずれかで読み込む。

```css
@import url('scrollbar.css');
```

- **メイン UI**: `static/css/main.css`（先頭で import 済み）
- **管理画面**: `static/css/admin_chat.css`（先頭で import 済み）
- **About**: `static/css/about.css`（先頭で import 済み）
- **単体 HTML**（デバッグ画面など）: `<link rel="stylesheet" href=".../css/scrollbar.css">`  
  その際 `:root { --focus-color: #4CAF50; }` が無いページでは、フォールバック色が使われる。

**新しい CSS ファイルを追加する場合は、必ず `scrollbar.css` を import する。**

## 新しいスクロール領域を追加するとき

### 推奨: クラス `app-scrollbar`

HTML または JS で生成する要素に、スクロールさせたい要素へクラスを付与する。

```html
<div class="app-scrollbar" style="max-height: 400px; overflow-y: auto;">
  ...
</div>
```

```javascript
`<div class="app-scrollbar" style="overflow-y: auto; max-height: 60vh;">...</div>`
```

`overflow-y: auto`（または `overflow: auto`）と高さ制限（`max-height` / flex の `min-height: 0` など）をセットで指定する。

### 代替: `scrollbar.css` にセレクタを追加

再利用される固定の UI 部品（例: `.chat-messages`）は、`scrollbar.css` 内の **4 つのセレクタグループ**（`scrollbar-width` / `::-webkit-scrollbar` / `track` / `thumb` / `thumb:hover`）すべてに、同じ順序でセレクタを 1 行追加する。

**禁止事項**

- `main.css` / `admin_chat.css` / 各 HTML の `<style>` に `::-webkit-scrollbar` を重複定義しない
- グレーの細いバーなど、別デザインのスクロールバーを新設しない

## モーダル内スクロールのパターン

ヘッダーを固定し、**フォーム本体または `.modal-body` だけ**をスクロールさせる。

```
.modal-content          ← overflow: hidden, flex 縦
  .modal-header         ← flex-shrink: 0（固定）
  #xxxForm / .modal-body ← overflow-y: auto + app-scrollbar（または scrollbar.css 登録済み ID）
```

参考: `#userInfoModal` / `#attributeModal`（`templates/index.html` + `static/css/main.css`）。

## 意図的な例外

| 要素 | 理由 |
|------|------|
| `.mobile-queue-slider` | 横スワイプ UI のためスクロールバー非表示（`scrollbar.css` 末尾で定義） |

新たにスクロールバーを **非表示** にする場合は、`docs/SCROLLBAR_STYLE.md` の本表と `scrollbar.css` に理由をコメントで残す。

## 大きな角丸コンテナ内（オンボーディング・About）

`.onboarding-slide-scroll` と `body.about-page > .about-scroll` は、トラックの `margin-block: 20px` で角丸から離す（`scrollbar.css` 内の例外ルール）。  
同様の全画面オーバーレイを追加する場合は、必要なら同ブロックにセレクタを追加する。

## 互換用 CSS 変数

古いコードが参照する場合のエイリアス（`scrollbar.css` の `:root` で定義）:

- `--onb-scrollbar-track` → `--app-scrollbar-track`
- `--onb-scrollbar-thumb` → `--app-scrollbar-thumb`
- `--onb-scrollbar-thumb-hover` → `--app-scrollbar-thumb-hover`

新規コードでは `--app-scrollbar-*` を使う。

## チェックリスト（PR・実装時）

- [ ] スクロール領域に `app-scrollbar` を付与した、または `scrollbar.css` にセレクタを追加した
- [ ] ページ／CSS が `scrollbar.css` を import（または link）している
- [ ] 他ファイルに `::-webkit-scrollbar` の独自定義を増やしていない
- [ ] モーダルはヘッダー固定・本文スクロールの構成になっている（該当する場合）
- [ ] スクロールバー非表示が必要な場合、例外として文書化した

## 関連ファイル

- 実装: `static/css/scrollbar.css`
- Cursor ルール（AI 向け）: `.cursor/rules/scrollbar.mdc`
