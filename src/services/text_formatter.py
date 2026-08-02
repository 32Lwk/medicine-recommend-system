"""
テキスト変換

medicine_logic から分離（SRP改善）。
Markdown→HTML変換、表示用テキスト整形を行う。
"""

import html
import re
from typing import Any


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


def _normalize_qa_text(text: Any) -> str:
    if not text:
        return ""
    if isinstance(text, list):
        lines = []
        for item in text:
            if isinstance(item, dict):
                name = item.get("製品名") or item.get("name") or ""
                comp = item.get("主成分") or item.get("成分") or ""
                use = item.get("用途") or item.get("efficacy") or ""
                summary = " / ".join(s for s in [name, comp, use] if s)
                if summary:
                    lines.append(summary)
            else:
                lines.append(str(item))
        return "\n".join(lines)
    if isinstance(text, dict):
        return "\n".join(f"{k}: {v}" for k, v in text.items())
    return str(text)


def _normalize_llm_html_fragments(text: str) -> str:
    """LLM が返した簡易 HTML を Markdown 風に直してから整形する。"""
    if not text or "<" not in text:
        return text
    result = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    result = re.sub(
        r"<strong>(.*?)</strong>",
        r"**\1**",
        result,
        flags=re.IGNORECASE | re.DOTALL,
    )
    result = re.sub(r"</?p>", "\n", result, flags=re.IGNORECASE)
    return result.strip()


def _qa_product_line_html(name: str, description: str) -> str:
    """製品名と説明を改行崩れしにくい HTML ブロックで返す。"""
    name_esc = html.escape(name.strip())
    desc_esc = html.escape(description.strip())
    if not name_esc:
        return f'<p class="ui-qa-product-line">{desc_esc}</p>' if desc_esc else ""
    return (
        f'<p class="ui-qa-product-line">'
        f'<span class="ui-qa-product-line__lead">'
        f"<strong>{name_esc}</strong>："
        f"</span>"
        f'<span class="ui-qa-product-line__body">{desc_esc}</span>'
        f"</p>"
    )


_MEDICINE_PRODUCT_CHUNK_SPLIT_RE = re.compile(
    r"(?:(?<=[。!！?？])\s+|\n+)"
    r"(?=[^\s：。]{2,45}(?:《[^》]*》)?[^：\s]*：)"
)
_MEDICINE_PRODUCT_CHUNK_PARSE_RE = re.compile(
    r"^(?:\*\*)?(?P<name>[^：\n*]+?)(?:\*\*)?：(?P<body>.+)$",
    re.DOTALL,
)


def _split_medicine_product_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = _MEDICINE_PRODUCT_CHUNK_SPLIT_RE.split(line)
        chunks.extend(part.strip() for part in parts if part.strip())
    return chunks


def format_medicine_product_lines_html(text: Any) -> str:
    """医薬品 Q&A の medicine_details を製品ごとの ui-qa-product-line HTML に整形する。"""
    normalized = _normalize_qa_text(text)
    if not normalized:
        return ""
    if "ui-qa-product-line" in normalized:
        return normalized.strip()
    normalized = _normalize_llm_html_fragments(normalized).strip()
    if not normalized:
        return ""

    blocks: list[str] = []
    for chunk in _split_medicine_product_chunks(normalized):
        match = _MEDICINE_PRODUCT_CHUNK_PARSE_RE.match(chunk)
        if not match:
            continue
        name = match.group("name").strip()
        body = match.group("body").strip()
        if name and body:
            blocks.append(_qa_product_line_html(name, body))
    if blocks:
        return "".join(blocks)
    return safe_format_qa_html(normalized)


def safe_format_qa_html(text: Any) -> str:
    """医薬品Q&A表示用: XSSエスケープ後にMarkdown太字・改行をHTML化"""
    normalized = _normalize_qa_text(text)
    if not normalized:
        return ""
    normalized = _normalize_llm_html_fragments(normalized)
    return format_text_for_display(html.escape(normalized))
