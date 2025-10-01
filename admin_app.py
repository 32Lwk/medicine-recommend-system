#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
管理者画面専用アプリケーション（ポート5001）
"""

from flask import Flask, render_template, jsonify, request
import requests
import json
import threading
import time

app = Flask(__name__)

# メインアプリケーション（ポート5000）のベースURL
MAIN_APP_URL = "http://localhost:5000"

@app.route('/')
def admin():
    """管理者画面"""
    return render_template('admin_chat.html')

@app.route('/api/main_sessions')
def get_main_sessions():
    """メインアプリケーションからセッション情報を取得"""
    try:
        response = requests.get(f"{MAIN_APP_URL}/api/main_sessions")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([]), response.status_code
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return jsonify([]), 500

@app.route('/api/admin/sessions', methods=['GET'])
def get_all_sessions():
    """全セッション情報を取得"""
    try:
        response = requests.get(f"{MAIN_APP_URL}/api/admin/sessions")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([]), response.status_code
    except Exception as e:
        print(f"Error fetching admin sessions: {e}")
        return jsonify([]), 500

@app.route('/api/admin/send_message', methods=['POST'])
def admin_send_message():
    """管理者からのメッセージ送信"""
    try:
        response = requests.post(f"{MAIN_APP_URL}/api/admin/send_message", 
                               json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Error sending admin message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin_mode', methods=['POST'])
def api_admin_mode():
    """管理者モード切り替え"""
    try:
        response = requests.post(f"{MAIN_APP_URL}/api/admin_mode")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Error switching admin mode: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/request_admin', methods=['POST'])
def request_admin():
    """管理者対応要請"""
    try:
        response = requests.post(f"{MAIN_APP_URL}/api/request_admin", 
                               json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Error requesting admin: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai_auto_reply', methods=['POST'])
def toggle_ai_auto_reply():
    """AI自動返信の切り替え"""
    try:
        response = requests.post(f"{MAIN_APP_URL}/api/ai_auto_reply", 
                               json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Error toggling AI auto reply: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_session', methods=['POST'])
def clear_session():
    """セッションクリア"""
    try:
        response = requests.post(f"{MAIN_APP_URL}/api/clear_session", 
                               json=request.json)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Error clearing session: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Admin Application on port 5001...")
    print("📱 Admin Panel: http://localhost:5001/")
    print("🔗 Main App: http://localhost:5000/")
    app.run(debug=True, port=5001, host='0.0.0.0')
