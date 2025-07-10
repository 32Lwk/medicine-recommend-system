#!/usr/bin/env python3
"""
医薬品相談AI サーバー起動スクリプト
"""

import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def print_banner():
    """バナーを表示"""
    print("=" * 60)
    print("🏥 医薬品相談AI サーバー起動スクリプト")
    print("=" * 60)
    print()

def check_dependencies():
    """依存関係をチェック"""
    print("📋 依存関係をチェック中...")
    
    required_packages = [
        'flask',
        'pandas',
        'openai',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (未インストール)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  以下のパッケージが不足しています: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ すべての依存関係が満たされています")
    return True

def check_files():
    """必要なファイルをチェック"""
    print("\n📁 ファイルチェック中...")
    
    required_files = [
        'app.py',
        'debug_app.py',
        'test_app.py',
        'medicine_logic.py',
        '症状-薬.csv',
        'templates/index.html',
        'templates/debug_index.html',
        'templates/test_index.html'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (見つかりません)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  以下のファイルが不足しています: {', '.join(missing_files)}")
        return False
    
    print("✅ すべてのファイルが存在します")
    return True

def start_server(script_name, port, description):
    """サーバーを起動"""
    print(f"\n🚀 {description}を起動中... (ポート: {port})")
    
    try:
        # 環境変数を設定
        env = os.environ.copy()
        env['FLASK_ENV'] = 'development'
        
        # サーバーを起動
        process = subprocess.Popen(
            [sys.executable, script_name],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 少し待ってからプロセスが正常に起動したかチェック
        time.sleep(2)
        
        if process.poll() is None:
            print(f"✅ {description}が正常に起動しました")
            print(f"🌐 URL: http://localhost:{port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {description}の起動に失敗しました")
            if stderr:
                print(f"エラー: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ {description}の起動中にエラーが発生しました: {e}")
        return None

def main():
    """メイン関数"""
    print_banner()
    
    # 依存関係とファイルをチェック
    if not check_dependencies():
        print("\n❌ 依存関係のチェックに失敗しました")
        return
    
    if not check_files():
        print("\n❌ ファイルチェックに失敗しました")
        return
    
    print("\n🎯 起動するサーバーを選択してください:")
    print("1. 本番サーバー (医薬品相談AI) - ポート 5000")
    print("2. デバッグ・保守サーバー - ポート 5001")
    print("3. テストサーバー - ポート 5002")
    print("4. すべてのサーバーを起動")
    print("5. 終了")
    
    while True:
        try:
            choice = input("\n選択してください (1-5): ").strip()
            
            if choice == '1':
                # 本番サーバーのみ起動
                process = start_server('app.py', 5000, '本番サーバー')
                if process:
                    print("\n本番サーバーが起動しました。Ctrl+Cで停止できます。")
                    try:
                        process.wait()
                    except KeyboardInterrupt:
                        process.terminate()
                        print("\n本番サーバーを停止しました。")
                break
                
            elif choice == '2':
                # デバッグサーバーのみ起動
                process = start_server('debug_app.py', 5001, 'デバッグ・保守サーバー')
                if process:
                    print("\nデバッグ・保守サーバーが起動しました。Ctrl+Cで停止できます。")
                    try:
                        process.wait()
                    except KeyboardInterrupt:
                        process.terminate()
                        print("\nデバッグ・保守サーバーを停止しました。")
                break
                
            elif choice == '3':
                # テストサーバーのみ起動
                process = start_server('test_app.py', 5002, 'テストサーバー')
                if process:
                    print("\nテストサーバーが起動しました。Ctrl+Cで停止できます。")
                    try:
                        process.wait()
                    except KeyboardInterrupt:
                        process.terminate()
                        print("\nテストサーバーを停止しました。")
                break
                
            elif choice == '4':
                # すべてのサーバーを起動
                print("\n🚀 すべてのサーバーを起動します...")
                
                processes = []
                
                # 本番サーバー
                prod_process = start_server('app.py', 5000, '本番サーバー')
                if prod_process:
                    processes.append(('本番サーバー', prod_process))
                
                # デバッグサーバー
                debug_process = start_server('debug_app.py', 5001, 'デバッグ・保守サーバー')
                if debug_process:
                    processes.append(('デバッグ・保守サーバー', debug_process))
                
                # テストサーバー
                test_process = start_server('test_app.py', 5002, 'テストサーバー')
                if test_process:
                    processes.append(('テストサーバー', test_process))
                
                if processes:
                    print(f"\n✅ {len(processes)}個のサーバーが起動しました")
                    print("\n🌐 アクセスURL:")
                    print("• 本番サーバー: http://localhost:5000")
                    print("• デバッグ・保守サーバー: http://localhost:5001")
                    print("• テストサーバー: http://localhost:5002")
                    print("\nCtrl+Cで全てのサーバーを停止できます。")
                    
                    try:
                        # すべてのプロセスが終了するまで待機
                        while any(p.poll() is None for _, p in processes):
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n🛑 すべてのサーバーを停止中...")
                        for name, process in processes:
                            if process.poll() is None:
                                process.terminate()
                                print(f"✅ {name}を停止しました")
                        print("すべてのサーバーを停止しました。")
                else:
                    print("❌ サーバーの起動に失敗しました")
                break
                
            elif choice == '5':
                print("終了します。")
                break
                
            else:
                print("❌ 無効な選択です。1-5の数字を入力してください。")
                
        except KeyboardInterrupt:
            print("\n\n終了します。")
            break
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")

if __name__ == '__main__':
    main() 