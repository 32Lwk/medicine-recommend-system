#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
論文の文字数をカウントするスクリプト
"""

import re
import sys
import os

def count_chars():
    try:
        # LaTeXファイルを読み込む
        filename = 'paper_xelatex.tex'
        if not os.path.exists(filename):
            print(f'エラー: {filename}が見つかりませんでした')
            sys.exit(1)
            
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # 本文部分を抽出（はじめにからおわりにまで）
        body_match = re.search(
            r'\\section\{はじめに\}(.*?)\\section\{おわりに\}(.*?)\\end\{document\}',
            content,
            re.DOTALL
        )

        if not body_match:
            print('エラー: 本文が見つかりませんでした')
            sys.exit(1)

        text = body_match.group(1) + body_match.group(2)

        # LaTeXコマンドとコメントを除去
        text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)  # コメント
        text = re.sub(r'\\footnote\{[^}]*\}', '', text)  # 脚注
        text = re.sub(r'\\label\{[^}]*\}', '', text)  # ラベル
        text = re.sub(r'\\ref\{[^}]*\}', '', text)  # 参照
        text = re.sub(r'\\begin\{equation\}.*?\\end\{equation\}', '', text, flags=re.DOTALL)  # 数式環境
        text = re.sub(r'\\begin\{itemize\}.*?\\end\{itemize\}', '', text, flags=re.DOTALL)  # itemize
        text = re.sub(r'\\item', '', text)  # item
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)  # \command{content}
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # \command
        text = re.sub(r'[{}]', '', text)  # { }
        text = re.sub(r'\\', '', text)  # 残りの\
        text = re.sub(r'\$.*?\$', '', text)  # インライン数式
        text = re.sub(r'\\texttt\{[^}]*\}', '', text)  # \texttt

        # 空白を除去して文字数をカウント
        text_no_space = re.sub(r'\s+', '', text)
        char_count = len(text_no_space)

        print(f'本文文字数（空白除く）: {char_count}字')
        print(f'制限: 3,200字以内')

        if char_count <= 3200:
            print(f'✓ 制限内です（残り{3200 - char_count}字）')
            return 0
        else:
            print(f'✗ 制限超過です（{char_count - 3200}字超過）')
            return 1

    except FileNotFoundError:
        print(f'エラー: {filename}が見つかりませんでした')
        sys.exit(1)
    except Exception as e:
        print(f'エラー: {e}')
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(count_chars())
