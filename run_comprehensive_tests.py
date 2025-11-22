# -*- coding: utf-8 -*-
"""
包括的テストの実行と評価
"""
import sys
import io
import subprocess
import json

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*80)
print("包括的テストの実行と評価")
print("="*80)

# テストを実行
try:
    result = subprocess.run(
        [sys.executable, "test_comprehensive.py"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    print(result.stdout)
    if result.stderr:
        print("\n[エラー出力]")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"\n[警告] テストがエラーコード {result.returncode} で終了しました")
    else:
        print("\n[OK] テストが正常に完了しました")
        
except Exception as e:
    print(f"[ERROR] テスト実行中にエラーが発生しました: {e}")
    import traceback
    traceback.print_exc()

