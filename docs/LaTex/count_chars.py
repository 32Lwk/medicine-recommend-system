import re

# ファイルを読み込む
with open('paper_xelatex.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# 本文部分を抽出（\section{はじめに}から\section*{図表}まで）
start = content.find('\\section{はじめに}')
end = content.find('\\section*{図表}')

if start == -1:
    print("エラー: \\section{はじめに}が見つかりません")
    exit(1)

if end == -1:
    # 図表が見つからない場合は、参考文献の前まで
    end = content.find('\\begin{thebibliography}')

if end == -1:
    text = content[start:]
else:
    text = content[start:end]

# 数式環境全体を除去（\begin{equation}...\end{equation}）
text = re.sub(r'\\begin\{equation\}.*?\\end\{equation\}', '', text, flags=re.DOTALL)
# インライン数式を除去（$...$）
text = re.sub(r'\$[^$]*\$', '', text)
# LaTeXコマンドを除去（\command{...}）
text = re.sub(r'\\[a-zA-Z]+\*?\{[^}]*\}', '', text)
# 単独のLaTeXコマンドを除去
text = re.sub(r'\\[a-zA-Z]+', '', text)
# パーセント記号のエスケープを除去
text = text.replace('\\%', '')
# 空白、改行、タブを除去
text = re.sub(r'[\s\n\r\t]', '', text)
# 特殊文字を除去（{}[]など）
text = re.sub(r'[{}[\]()]', '', text)

# 日本語文字のみをカウント（ひらがな、カタカナ、漢字、句読点など）
japanese_chars = re.findall(r'[ぁ-んァ-ヶ一-龠々ー。、，．]', text)
char_count = len(japanese_chars)

# 英数字も含めた全体の文字数
all_chars = len(text)

print(f'日本語文字数: {char_count}文字')
print(f'全体文字数（英数字含む）: {all_chars}文字')
print(f'制限（3200字）との差: {char_count - 3200}文字')
