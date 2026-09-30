"""build-sources.mjs の後に実行し、生成された見出しをこのデッキ向けに置き換える。

一次調査は聞き取りではなくリポジトリ内の記録（データ・点検・履歴）なので、
スキル既定の「聞いた声」を「記録」に直す。
"""
from pathlib import Path

DECK = Path(__file__).resolve().parent.parent / "slides.html"
REPLACE = {
    "一次調査：自分たちで聞いた7件の声": "一次調査：自分たちで集めた7件の記録",
}

text = DECK.read_text(encoding="utf-8")
for old, new in REPLACE.items():
    text = text.replace(old, new)
DECK.write_text(text, encoding="utf-8")
print("postbuild: ok")
