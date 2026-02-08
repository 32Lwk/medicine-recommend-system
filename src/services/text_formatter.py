"""
テキスト変換

medicine_logic から分離（SRP改善）。
Markdown→HTML変換、表示用テキスト整形を行う。
"""

import re


def convert_markdown_bold(text):
    """Markdown形式の太文字（**文字**）をHTML太文字タグに変換"""
    if text is None:
        return ""
    # **文字** を <strong>文字</strong> に変換
    result = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # ### で始まる行を除去
    result = re.sub(r'^###+\s*', '', result, flags=re.MULTILINE)
    # ## で始まる行を除去
    result = re.sub(r'^##+\s*', '', result, flags=re.MULTILINE)
    # # で始まる行を除去
    result = re.sub(r'^#+\s*', '', result, flags=re.MULTILINE)
    # 行頭の余分な空白を除去
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)
    return result


def format_text_for_display(text):
    """テキストを整形して見やすくする"""
    if text is None:
        return ""

    # ①、②、③などの丸数字の後に改行を追加
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])\s*', r'\1<br>', text)

    # 1.、2.、3.などの数字の後に改行を追加
    text = re.sub(r'(\d+\.)\s*', r'\1<br>', text)

    # - で始まる行の前に改行を追加
    text = re.sub(r'\n\s*-\s*', r'<br>- ', text)

    # ・ で始まる行の前に改行を追加
    text = re.sub(r'\n\s*・\s*', r'<br>・ ', text)

    # 改行を適切に処理（最初に改行を処理）
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')

    # 丸数字の後の改行を再度確認
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])(?!<br>)', r'\1<br>', text)

    # 数字の後の改行を再度確認
    text = re.sub(r'(\d+\.)(?!<br>)', r'\1<br>', text)

    # Markdown太文字をHTML太文字に変換
    text = convert_markdown_bold(text)

    return text
