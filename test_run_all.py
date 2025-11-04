"""
全テストを実行するメインスクリプト
"""

import sys
import os
import subprocess

def run_test(test_file):
    """テストファイルを実行"""
    print(f"\n{'='*80}")
    print(f"実行中: {test_file}")
    print('='*80)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("\n" + "="*80)
    print("デプロイ前包括的テストスイート実行")
    print("="*80)
    
    # テストファイルのリスト
    test_files = [
        'test_unit.py',
        'test_integration.py',
        'test_comprehensive_deployment.py',
    ]
    
    results = {}
    
    for test_file in test_files:
        if os.path.exists(test_file):
            success = run_test(test_file)
            results[test_file] = success
        else:
            print(f"[WARN] ファイルが見つかりません: {test_file}")
            results[test_file] = None
    
    # 結果サマリー
    print("\n" + "="*80)
    print("全テスト結果サマリー")
    print("="*80)
    
    for test_file, result in results.items():
        if result is None:
            status = "[SKIP]"
        elif result:
            status = "[PASS]"
        else:
            status = "[FAIL]"
        print(f"{status}: {test_file}")
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    print(f"\n[OK] 成功: {passed}")
    print(f"[FAIL] 失敗: {failed}")
    print(f"[SKIP] スキップ: {skipped}")
    print(f"[TOTAL] 合計: {len(results)}")
    print("="*80 + "\n")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

