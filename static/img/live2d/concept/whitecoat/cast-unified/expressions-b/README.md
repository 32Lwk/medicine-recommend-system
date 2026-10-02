# Character B — Live2D レビュー用表情セット（確定）

白衣正本キャラ B。口形「い／え」は差強調版に差し替え済み。

## シート

| ファイル | 内容 |
|----------|------|
| `sheet-b-expressions.jpg` | E0–E5 表情シート |
| `sheet-b-mouths.jpg` | 口形 閉／あ／い／う／え／お |
| `sheet-b-eyes.jpg` | 開眼／半目／目閉じ |

## 表情一覧

| ID | 意味 | 相談での用途 | 個別ファイル |
|----|------|--------------|--------------|
| E0 | 通常 | 待機・基本 | `sage-b-e0-neutral.jpg` |
| E1 | 微笑み | 挨拶・安心 | `sage-b-e1-smile.jpg` |
| E2 | 思案 | 処理待ち・確認中 | `sage-b-e2-thinking.jpg` |
| E3 | 共感 | 症状ヒアリング | `sage-b-e3-empathy.jpg` |
| E4 | 軽い驚き | 想定外・注意の入口 | `sage-b-e4-surprise.jpg` |
| E5 | うなずき | 相槌 | `sage-b-e5-nod.jpg` |

## 口形・目

- 口形: Live2D リップシンク用キー（あいうえお＋閉口）
- 目: まばたき用（開／半／閉）。本番はパラメータ駆動を推奨

## 手・腕（スプライト版アバター用）

腰より少し上まで写った 3:4 の土台 `sage-b-w-base.jpg` を参照に、同じ構図のまま腕のポーズだけを変えて生成したもの。`scripts/live2d_build_sprite.py --cast b` が体の差し替え絵と手の重ね絵に分ける。A / C / D も同じファイル名規則（`sage-x-w-base.jpg`, `sage-x-g-*.jpg`）で `expressions-{a,c,d}/` にある。

| ファイル | 手 |
|----------|----|
| `sage-b-g-wave.jpg` | 手を振る |
| `sage-b-g-explain.jpg` | 手のひら差し出し |
| `sage-b-g-point.jpg` | 人差し指 |
| `sage-b-g-chest.jpg` | 胸に手 |
| `sage-b-g-chin.jpg` | あごに手 |
| `sage-b-g-fist.jpg` | こぶし |
| `sage-b-g-bow_hands.jpg` | 両手を合わせる |
| `sage-b-g-ok.jpg` | OK サイン |

## 共通仕様

- 白衣・中の服: 統一版 B を維持
- 背景: クロマキー緑
- 強度: 中程度（はっきり分かるが大げさでない）
- 画角: バストアップ正面・表情はやや寄り
