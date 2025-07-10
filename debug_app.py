from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import os
import sys
import json
import time
import traceback
from datetime import datetime
import pandas as pd
from medicine_logic import df, client, CSV_PATH, api_key
from debug_logger import network_logs, add_network_log, performance_stats, reset_performance_stats
import threading
import queue
import uuid
from typing import Any, Dict, List
import urllib.request
import urllib.error
import psutil
import subprocess

app = Flask(__name__)
app.secret_key = 'debug-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# デバッグログを保存するリスト
debug_logs = []

# ログの最大保持数
MAX_LOGS = 200

# サーバー制御用のグローバル変数
main_server_process = None
main_server_running = False

def add_debug_log(message, level="INFO", details=None):
    """デバッグログを追加"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = {
        'id': str(uuid.uuid4())[:8],
        'timestamp': timestamp,
        'level': level,
        'message': message,
        'details': details
    }
    debug_logs.append(log_entry)
    # ログをMAX_LOGS件まで保持
    if len(debug_logs) > MAX_LOGS:
        debug_logs.pop(0)
    
    # WebSocketでリアルタイム通知
    socketio.emit('debug_log_update', {
        'log': log_entry,
        'total_logs': len(debug_logs)
    })

def broadcast_network_log():
    """ネットワークログをWebSocketでブロードキャスト"""
    socketio.emit('network_log_update', {
        'logs': network_logs,
        'performance_stats': performance_stats
    })

def get_system_resources():
    """システムリソース状況を取得"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_percent': memory.percent,
            'disk_total': disk.total,
            'disk_free': disk.free,
            'disk_percent': (disk.used / disk.total) * 100
        }
    except Exception as e:
        add_debug_log(f"リソース取得エラー: {str(e)}", "ERROR")
        return None

def get_server_logs():
    """サーバーログを取得（標準出力の代替）"""
    try:
        # 現在のプロセス情報を取得
        current_process = psutil.Process()
        
        # メモリ使用量
        memory_info = current_process.memory_info()
        
        # プロセス情報
        process_info = {
            'pid': current_process.pid,
            'name': current_process.name(),
            'status': current_process.status(),
            'memory_rss': memory_info.rss,
            'memory_vms': memory_info.vms,
            'cpu_percent': current_process.cpu_percent(),
            'create_time': datetime.fromtimestamp(current_process.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
            'num_threads': current_process.num_threads(),
            'connections': len(current_process.connections())
        }
        
        return {
            'process_info': process_info,
            'debug_logs_count': len(debug_logs),
            'network_logs_count': len(network_logs),
            'last_debug_log': debug_logs[-1] if debug_logs else None,
            'last_network_log': network_logs[-1] if network_logs else None
        }
    except Exception as e:
        add_debug_log(f"サーバーログ取得エラー: {str(e)}", "ERROR")
        return None

@app.route('/')
def index():
    """デバッグ・保守用メインページ"""
    return render_template('debug_index.html')

@app.route('/admin')
def admin_chat():
    """AI制御・手動返信管理画面"""
    return render_template('admin_chat.html')

@app.route('/status')
def status():
    try:
        # CSVファイルの状態
        csv_exists = False
        row_count = 0
        col_count = 0
        columns = []
        last_modified = None
        size = 0
        encoding = 'utf-8'
        error = None
        try:
            csv_exists = os.path.exists(CSV_PATH)
            if csv_exists:
                size = int(os.path.getsize(CSV_PATH))
                last_modified = datetime.fromtimestamp(os.path.getmtime(CSV_PATH)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            error = f"CSVファイル情報取得エラー: {e}"
        try:
            row_count = int(len(df)) if df is not None else 0
            col_count = int(len(df.columns)) if df is not None else 0
            columns = [str(col) for col in df.columns] if df is not None else []
        except Exception as e:
            error = f"DataFrame情報取得エラー: {e}"
        csv_status = {
            'success': df is not None,
            'encoding': encoding,
            'error': error if error else (None if df is not None else 'CSVファイルが読み込まれていません'),
            'row_count': int(row_count),
            'col_count': int(col_count),
            'columns': columns,
            'path': CSV_PATH if 'CSV_PATH' in globals() else None,
            'exists': bool(csv_exists),
            'size': int(size),
            'last_modified': last_modified
        }
        # DataFrameの状態
        df_status = {
            'loaded': df is not None,
            'rows': int(row_count),
            'columns': columns,
            'memory_usage': int(df.memory_usage(deep=True).sum()) if df is not None else 0
        }
        # OpenAI APIの状態
        api_status = {
            'client_initialized': client is not None if 'client' in globals() else False,
            'api_key_set': bool(api_key) if 'api_key' in globals() else False,
            'api_key_length': int(len(api_key)) if 'api_key' in globals() and api_key else 0
        }
        # システム情報
        system_info = {
            'python_version': sys.version,
            'current_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'working_directory': os.getcwd()
        }
        # パフォーマンス統計の数値もintでラップ
        perf_stats = {k: int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for k, v in performance_stats.items()}
        return jsonify({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'csv_status': csv_status,
            'df_status': df_status,
            'api_status': api_status,
            'system_info': system_info,
            'performance_stats': perf_stats
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/logs')
def get_logs():
    """デバッグログを取得"""
    # debug_logsが配列でない場合は空配列を返す
    if not isinstance(debug_logs, list):
        return jsonify([])
    return jsonify(debug_logs)

@app.route('/network_logs')
def get_network_logs():
    """ネットワーク監視ログを取得"""
    # network_logsが配列でない場合は空配列を返す
    if not isinstance(network_logs, list):
        return jsonify([])
    return jsonify(network_logs)

@app.route('/performance_stats')
def get_performance_stats():
    """パフォーマンス統計を取得"""
    return jsonify(performance_stats)

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """デバッグログをクリア"""
    global debug_logs
    debug_logs = []
    add_debug_log("Logs cleared by user")
    return jsonify({'message': 'Logs cleared successfully'})

@app.route('/clear_network_logs', methods=['POST'])
def clear_network_logs():
    """ネットワークログをクリア"""
    from debug_logger import network_logs
    network_logs.clear()
    add_debug_log("Network logs cleared by user")
    return jsonify({'message': 'Network logs cleared successfully'})

@app.route('/test_csv')
def test_csv():
    """CSVファイルの内容をテスト"""
    try:
        if df is None:
            return jsonify({'error': 'CSV file not loaded'}), 400
        
        # 最初の5行を取得
        sample_data = df.head().to_dict('records')
        
        # 統計情報
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'column_names': list(df.columns),
            'missing_values': df.isnull().sum().to_dict()
        }
        
        add_debug_log("CSV file test completed successfully", "INFO", stats)
        return jsonify({
            'sample_data': sample_data,
            'stats': stats
        })
    except Exception as e:
        add_debug_log(f"CSV test error: {str(e)}", "ERROR", {'traceback': traceback.format_exc()})
        return jsonify({'error': str(e)}), 500

@app.route('/test_api')
def test_api():
    """OpenAI APIの接続をテスト"""
    try:
        if client is None:
            add_network_log('GET', '/test_api', None, None, None, 'error', 'OpenAI client not initialized')
            return jsonify({'error': 'OpenAI client not initialized'}), 400
        
        # 簡単なテストリクエスト
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'API test successful' in Japanese."}
        ]
        
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=test_messages,  # type: ignore
            max_tokens=50
        )
        end_time = time.time()
        
        response_time = round(end_time - start_time, 3)
        response_data = {
            'success': True,
            'response': response.choices[0].message.content,
            'response_time': response_time,
            'model': response.model,
            'usage': response.usage.dict() if response.usage else None
        }
        
        # ネットワークログに記録
        add_network_log('POST', 'OpenAI API', test_messages, response_data, response_time, 'success')
        add_debug_log(f"API test successful: {response_time}s", "INFO", response_data)
        
        # WebSocketでリアルタイム通知
        broadcast_network_log()
        
        return jsonify(response_data)
    except Exception as e:
        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        add_network_log('POST', 'OpenAI API', test_messages, None, None, 'error', error_details)
        add_debug_log(f"API test error: {str(e)}", "ERROR", error_details)
        
        # WebSocketでリアルタイム通知
        broadcast_network_log()
        
        return jsonify({'error': str(e)}), 500

@app.route('/detailed_api_test')
def detailed_api_test():
    """詳細なAPIテスト（症状マッチング、注意点生成、薬の組み合わせチェック）"""
    try:
        if client is None:
            return jsonify({'error': 'OpenAI client not initialized'}), 400
        
        test_results = []
        
        # 1. 症状マッチングテスト
        test_symptom = "頭痛と発熱"
        start_time = time.time()
        
        # medicine_logic.pyのmatch_symptom_pairs関数を模擬
        prompt_data = "\n".join(
            f"{row['部位']} - {row['症状']}" for _, row in df.iterrows()
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "以下は体の部位と関連する症状の対応です。\n"
                    "ユーザーの症状文から、該当する症状をすべて日本語で返してください。\n"
                    "見つからなければ「該当なし」とだけ返してください。\n"
                    f"データ:\n{prompt_data}\n\n"
                    "出力は「部位 - 症状」の形式でカンマで区切ってください。"
                )
            },
            {"role": "user", "content": f"症状: {test_symptom}"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,  # type: ignore
            temperature=0
        )
        end_time = time.time()
        
        symptom_result = {
            'test_type': '症状マッチング',
            'input': test_symptom,
            'response': response.choices[0].message.content,
            'response_time': round(end_time - start_time, 3),
            'usage': response.usage.dict() if response.usage else None
        }
        test_results.append(symptom_result)
        
        # 2. 注意点生成テスト
        start_time = time.time()
        caution_messages = [
            {"role": "system", "content": (
                "あなたは日本の登録販売者AIです。\n"
                "以下の症状の組み合わせに対し、専門家として、以下の3点を具体的に、かつ分かりやすく記述してください。\n"
                "① 考えられる病気の候補（1〜2個）：登録販売者の視点から、可能性のある病名を挙げてください。\n"
                "② 使用上の一般的な注意点：市販薬を使う場合の一般的な注意や、日常生活でのケアについて簡潔に説明してください。\n"
                "③ 医師の受診が必要な場合：どのような症状が出たら、すぐに医師に相談すべきか、簡潔に兆候を明確に示してください。\n"
                "市販薬の具体的な商品名は含めないでください。専門用語は避け、一般の方にも理解できるように平易な言葉遣いを心がけてください。"
            )},
            {"role": "user", "content": f"症状の組み合わせ：頭 - 頭痛"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=caution_messages  # type: ignore
        )
        end_time = time.time()
        
        caution_result = {
            'test_type': '注意点生成',
            'input': '頭 - 頭痛',
            'response': response.choices[0].message.content,
            'response_time': round(end_time - start_time, 3),
            'usage': response.usage.dict() if response.usage else None
        }
        test_results.append(caution_result)
        
        # 3. 薬の組み合わせチェックテスト
        start_time = time.time()
        combination_messages = [
            {"role": "system", "content": (
                "あなたは日本の薬剤師または登録販売者AIです。\n"
                "以下の市販薬リストに含まれるすべての薬について、成分の重複や一般的な併用禁忌がないか詳細に判断してください。\n"
                "症状に対して適した医薬品候補群の中から一つだけ選んで服用し、成分が異なっていても、一つの症状から複数の医薬品を使うことは推奨しないでください\n"
                "もし症状をまたいで薬の成分に重複や併用注意がある場合(例:総合感冒薬＋解熱薬など)は具体的な成分名に言及し、どちらか一方を選ぶべきか、あるいはどのような症状に注意すべきかなど、実践的で具体的な判断基準やアドバイスを提供した上で、「登録販売者にお問い合わせください。」を加えてください。\n"
                "体力の低下などが見られる場合は必要に応じて食事療法や栄養ドリンクを進めるようにしてください。\n"
                "薬の名前だけでなく、なぜそのアドバイスが必要なのか、理由も簡潔に説明してください。\n"
                "個別の医薬品の説明どのよう主成分と効果のみ説明してください。\n"
                "症状に対しては○○が原因の場合という風に伝えてください。\n\n"
                "すべての内容は簡潔に伝えるようにしてください。\n\n\n"
                "すべての内容は簡潔に伝えるようにしてください。\n\n\n"
                "リストに挙げられた薬全体として特に大きな問題がなければ、「症状ごとの医薬品の飲み合わせに特に問題ありません。ただし、体調に変化があった場合は専門家にご相談ください。」のように、安全に関する注意を添えて返してください。\n\n"
                "市販薬リスト: バファリン, ロキソニン, イブ"
            )},
            {"role": "user", "content": "以下の市販薬についてアドバイスをください: バファリン, ロキソニン, イブ"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=combination_messages,  # type: ignore
            temperature=0.2
        )
        end_time = time.time()
        
        combination_result = {
            'test_type': '薬の組み合わせチェック',
            'input': 'バファリン, ロキソニン, イブ',
            'response': response.choices[0].message.content,
            'response_time': round(end_time - start_time, 3),
            'usage': response.usage.dict() if response.usage else None
        }
        test_results.append(combination_result)
        
        # 各テスト結果をネットワークログに記録
        for result in test_results:
            add_network_log('POST', f'OpenAI API - {result["test_type"]}', 
                          {'input': result['input']}, 
                          {'response': result['response'], 'usage': result['usage']}, 
                          result['response_time'], 'success')
        
        add_debug_log("Detailed API test completed successfully", "INFO", {'results': test_results})
        
        # WebSocketでリアルタイム通知
        broadcast_network_log()
        
        return jsonify({
            'success': True,
            'results': test_results,
            'total_tests': len(test_results)
        })
    except Exception as e:
        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        add_network_log('POST', 'OpenAI API - Detailed Test', None, None, None, 'error', error_details)
        add_debug_log(f"Detailed API test error: {str(e)}", "ERROR", error_details)
        
        # WebSocketでリアルタイム通知
        broadcast_network_log()
        
        return jsonify({'error': str(e)}), 500

@app.route('/reload_csv', methods=['POST'])
def reload_csv():
    """CSVファイルを再読み込み"""
    try:
        global df
        # medicine_logic.pyのCSV読み込み処理を再実行
        encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(CSV_PATH, encoding=encoding)
                add_debug_log(f"CSV reloaded successfully with encoding: {encoding}", "INFO", {'rows': len(df)})
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                add_debug_log(f"CSV reload error with {encoding}: {str(e)}", "ERROR", {'traceback': traceback.format_exc()})
                continue
        
        if df is not None:
            return jsonify({'message': 'CSV reloaded successfully', 'rows': len(df)})
        else:
            return jsonify({'error': 'Failed to reload CSV'}), 500
    except Exception as e:
        add_debug_log(f"CSV reload error: {str(e)}", "ERROR", {'traceback': traceback.format_exc()})
        return jsonify({'error': str(e)}), 500

@app.route('/export_logs')
def export_logs():
    """ログをJSONファイルとしてエクスポート"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_logs_{timestamp}.json"
        
        export_data = {
            'debug_logs': debug_logs,
            'network_logs': network_logs,
            'performance_stats': performance_stats,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        add_debug_log(f"Logs exported to {filename}", "INFO", {'filename': filename})
        return jsonify({'message': f'Logs exported to {filename}'})
    except Exception as e:
        add_debug_log(f"Log export error: {str(e)}", "ERROR", {'traceback': traceback.format_exc()})
        return jsonify({'error': str(e)}), 500

@app.route('/reset_performance_stats', methods=['POST'])
def reset_performance_stats_route():
    """パフォーマンス統計をリセット"""
    reset_performance_stats()
    add_debug_log("Performance stats reset by user")
    return jsonify({'message': 'Performance stats reset successfully'})

@app.route('/api/main_status')
def main_status():
    """メインサイトのシステム状況を取得して返す"""
    try:
        req = urllib.request.Request('http://localhost:5000/api/status')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/main_performance')
def main_performance():
    """メインサイトのパフォーマンス統計を取得して返す"""
    try:
        req = urllib.request.Request('http://localhost:5000/api/performance')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/main_logs')
def main_logs():
    """メインサイトの通信ログを取得して返す"""
    try:
        req = urllib.request.Request('http://localhost:5000/api/logs')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # データが配列でない場合は空配列を返す
            if not isinstance(data, list):
                add_debug_log(f"Main logs data is not a list: {type(data)}", "WARNING", {'data_type': str(type(data))})
                return jsonify([])
            
            return jsonify(data)
    except Exception as e:
        add_debug_log(f"Failed to fetch main logs: {str(e)}", "ERROR", {'error': str(e)})
        return jsonify([])  # エラーの場合は空配列を返す

@app.route('/api/server_logs')
def api_server_logs():
    """サーバーログを取得"""
    try:
        logs = get_server_logs()
        if logs:
            return jsonify(logs)
        else:
            return jsonify({'error': 'Failed to get server logs'}), 500
    except Exception as e:
        add_debug_log(f"Server logs API error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system_resources')
def api_system_resources():
    """システムリソース状況を取得"""
    try:
        resources = get_system_resources()
        if resources:
            return jsonify(resources)
        else:
            return jsonify({'error': 'Failed to get system resources'}), 500
    except Exception as e:
        add_debug_log(f"System resources API error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500

@app.route('/api/main_sessions')
def api_main_sessions():
    """メインサイトの全セッション情報を取得"""
    try:
        add_debug_log("メインサイト全セッション情報取得開始", "INFO")
        req = urllib.request.Request('http://localhost:5000/api/all_sessions')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            add_debug_log("メインサイト全セッション情報取得成功", "INFO", {'sessions_count': len(data)})
            return jsonify(data)
    except Exception as e:
        error_msg = f"メインサイト全セッション情報取得エラー: {str(e)}"
        add_debug_log(error_msg, "ERROR", {'error_type': 'Exception', 'error': str(e), 'traceback': traceback.format_exc()})
        return jsonify({'error': error_msg, 'details': str(e)}), 500

@app.route('/api/main_ai_control', methods=['GET', 'POST'])
def api_main_ai_control():
    """メインサイトのAI制御"""
    try:
        if request.method == 'GET':
            req = urllib.request.Request('http://localhost:5000/api/ai_control')
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                return jsonify(data)
        elif request.method == 'POST':
            data = request.get_json()
            req = urllib.request.Request(
                'http://localhost:5000/api/ai_control',
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                result = json.loads(response.read().decode('utf-8'))
                add_debug_log(f"AI制御変更: {data.get('mode', 'unknown')}", "INFO", result)
                return jsonify(result)
    except Exception as e:
        add_debug_log(f"AI制御エラー: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/api/main_manual_reply_queue', methods=['GET', 'POST'])
def api_main_manual_reply_queue():
    """メインサイトの手動返信キュー"""
    try:
        if request.method == 'GET':
            req = urllib.request.Request('http://localhost:5000/api/manual_reply_queue')
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                return jsonify(data)
        elif request.method == 'POST':
            data = request.get_json()
            req = urllib.request.Request(
                'http://localhost:5000/api/manual_reply_queue',
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                result = json.loads(response.read().decode('utf-8'))
                add_debug_log(f"手動返信送信: {data.get('session_id', 'unknown')}", "INFO", result)
                return jsonify(result)
    except Exception as e:
        add_debug_log(f"手動返信エラー: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Method not allowed'}), 405

# WebSocketイベントハンドラー
@socketio.on('connect')
def handle_connect():
    """クライアント接続時の処理"""
    add_debug_log("Client connected")
    emit('connected', {'message': 'Connected to debug server'})

@socketio.on('disconnect')
def handle_disconnect():
    """クライアント切断時の処理"""
    add_debug_log("Client disconnected")

@socketio.on('request_update')
def handle_request_update():
    """クライアントからの更新要求"""
    broadcast_network_log()

if __name__ == '__main__':
    add_debug_log("Debug application started", "INFO", {'port': 5001})
    socketio.run(app, debug=True, port=5001)