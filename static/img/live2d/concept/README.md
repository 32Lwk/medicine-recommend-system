# Live2D キャラクターコンセプト（選定用）

医薬品相談エージェント「Sage」向け Live2D モデル調達のためのコンセプト画像。  
パレットは Sage Terrace（slate-blue `#5b7c99` / terracotta `#c9846a` / cream）。

## 共通方針

- スタイライズド 2D（フォトリアル禁止）
- 白衣・名札・聴診器・薬局カウンターなど職能記号なし
- 画像内テキストなし
- 上半身バストアップ（Live2D 顔・口・表情向け）

## パターン一覧

| # | ファイル | コンセプト | Live2D 向きメモ |
|---|----------|------------|-----------------|
| 01 | `sage-char-01-slate-sweater.jpg` | スレートブルー髪＋クリームセーター | 定番案。髪・顔の分離がしやすい |
| 02 | `sage-char-02-cream-cardigan.jpg` | 男性寄り・クリームカーディガン | 性別バリエーション |
| 03 | `sage-char-03-hoodie-guide.jpg` | 中性寄り・フーディーガイド | 若年層・親しみ |
| 04 | `sage-char-04-warm-counselor.jpg` | 眼鏡・テラコッタブラウス | 落ち着き。眼鏡レイヤー要検討 |
| 05 | `sage-char-05-pixie-energetic.jpg` | ピクシーカット・元気系 | 短髪でトラッキングが軽い |
| 06 | `sage-char-06-longhair-listener.jpg` | 長髪・聞き役 | 髪物理が映える。工数はやや増 |
| 07 | `sage-char-07-soft-mascot.jpg` | 耳付きソフトマスコット | 薬剤師誤認リスクが低い |
| 08 | `sage-char-08-botanical-sage.jpg` | セージ葉モチーフ | ブランド連想が強い |
| 09 | `sage-char-09-chat-companion.jpg` | ちび寄りチャット相棒 | デモ映え。表情レンジは要確認 |
| 10 | `sage-char-10-casual-buddy.jpg` | カジュアル・バディ | 店頭キオスクでも自然 |

## 白衣系バリエーション

薬剤師・登録販売者イメージ（白衣っぽい見た目）は [`whitecoat/`](whitecoat/) を参照（女の子 5・男の子 5）。

## 次のステップ

1. 1〜2 案に絞る（本番用＋予備）
2. 正面／斜め／表情差分（喜・驚・思案・相槌）を追加生成または外注
3. Live2D Cubism 用 PSD 切り分け仕様へ落とし込む
