#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コード行数カウンター
プロジェクト全体のコード行数と言語別の割合を計算
"""

import os
from pathlib import Path
from collections import defaultdict

# 除外するディレクトリ
EXCLUDE_DIRS = {
    '__pycache__',
    '.git',
    'node_modules',
    'venv',
    'env',
    '.venv',
    'log',
    'docs',
}

# 除外するファイル拡張子
EXCLUDE_EXTENSIONS = {
    '.pyc',
    '.pyo',
    '.pyd',
    '.log',
    '.pdf',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.ico',
    '.svg',
    '.aux',
    '.dvi',
    '.jsonl',
}

# 言語別の拡張子マッピング
LANGUAGE_EXTENSIONS = {
    'Python': {'.py'},
    'JavaScript': {'.js'},
    'HTML': {'.html'},
    'CSS': {'.css'},
    'Markdown': {'.md'},
    'CSV': {'.csv'},
    'LaTeX': {'.tex'},
    'Batch': {'.bat'},
    'Config': {'.txt', '.ini', '.conf', '.cfg'},
    'Other': set(),
}

def count_lines(file_path):
    """ファイルの行数をカウント"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        print(f"警告: {file_path} の読み込みに失敗: {e}")
        return 0

def get_language(file_path):
    """ファイルパスから言語を判定"""
    ext = Path(file_path).suffix.lower()
    
    for lang, extensions in LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            return lang
    
    # その他の拡張子がある場合はOtherに分類
    if ext:
        return 'Other'
    
    # 拡張子がない場合はファイル名で判定
    filename = Path(file_path).name.lower()
    if filename in ['requirements.txt', 'runtime.txt', 'procfile']:
        return 'Config'
    
    return 'Other'

def scan_directory(root_dir):
    """ディレクトリをスキャンしてファイルを収集"""
    stats = defaultdict(lambda: {'files': 0, 'lines': 0, 'file_list': []})
    
    root_path = Path(root_dir)
    
    for file_path in root_path.rglob('*'):
        # ディレクトリはスキップ
        if file_path.is_dir():
            continue
        
        # 除外ディレクトリ内のファイルはスキップ
        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue
        
        # 除外拡張子はスキップ
        if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
            continue
        
        # 言語を判定
        language = get_language(str(file_path))
        
        # 行数をカウント
        lines = count_lines(file_path)
        
        # 統計を更新
        stats[language]['files'] += 1
        stats[language]['lines'] += lines
        stats[language]['file_list'].append((str(file_path), lines))
    
    return stats

def main():
    """メイン処理"""
    root_dir = Path(__file__).parent
    
    print("コード行数をカウント中...")
    print(f"対象ディレクトリ: {root_dir}")
    print("-" * 60)
    
    stats = scan_directory(root_dir)
    
    # 合計を計算
    total_files = sum(s['files'] for s in stats.values())
    total_lines = sum(s['lines'] for s in stats.values())
    
    # 結果を表示
    print(f"\n{'言語':<15} {'ファイル数':<12} {'行数':<15} {'割合':<10}")
    print("-" * 60)
    
    # 行数でソート
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['lines'], reverse=True)
    
    for language, data in sorted_stats:
        if data['lines'] > 0:
            percentage = (data['lines'] / total_lines * 100) if total_lines > 0 else 0
            print(f"{language:<15} {data['files']:<12} {data['lines']:<15} {percentage:>6.2f}%")
    
    print("-" * 60)
    print(f"{'合計':<15} {total_files:<12} {total_lines:<15} {'100.00%':<10}")
    
    # 詳細情報（上位ファイル）
    print("\n\n各言語の主要ファイル（上位5ファイル）:")
    print("=" * 60)
    
    for language, data in sorted_stats:
        if data['lines'] > 0 and data['file_list']:
            print(f"\n【{language}】")
            # 行数でソート
            sorted_files = sorted(data['file_list'], key=lambda x: x[1], reverse=True)
            for file_path, lines in sorted_files[:5]:
                rel_path = os.path.relpath(file_path, root_dir)
                print(f"  {rel_path:<50} {lines:>6} 行")

if __name__ == '__main__':
    main()

