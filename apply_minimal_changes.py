#!/usr/bin/env python3
"""
最小限の変更のみを適用するスクリプト
"""

# ファイルを読み込む
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 変更1: 202行目のrender_templateをjsonifyに変更
old_1 = """                session['messages'].append(bot_response)
                return render_template('index.html', messages=session.get('messages', []), version=VERSION, username=session['username'])
            if not AI_AUTO_REPLY:"""

new_1 = """                session['messages'].append(bot_response)
                # ALL_SESSIONSを更新
                if sid and sid in ALL_SESSIONS:
                    ALL_SESSIONS[sid]['messages'] = session['messages'].copy()
                message_count = len(session['messages'])
                logger.info(f"✅ POST処理完了（チャット終了） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
            
            # ユーザーメッセージを追加（必ず先に追加）
            session['messages'].append({
                'type': 'user',
                'content': user_message
            })
            
            if not AI_AUTO_REPLY:"""

content = content.replace(old_1, new_1)

# 変更2: 230行目のrender_templateをjsonifyに変更
old_2 = """                if bot_response:
                    session['messages'].append(bot_response)
                session.modified = True
                return render_template('index.html', messages=session.get('messages', []), version=VERSION, username=session['username'])
            session['messages'].append({
                'type': 'user',
                'content': user_message
            })
            # AI自動応答がOFFの場合は手動返信待ちにする
            if not AI_AUTO_REPLY:"""

new_2 = """                if bot_response:
                    session['messages'].append(bot_response)
                session.modified = True
                # ALL_SESSIONSを更新
                if sid and sid in ALL_SESSIONS:
                    ALL_SESSIONS[sid]['messages'] = session['messages'].copy()
                message_count = len(session['messages'])
                logger.info(f"✅ POST処理完了（手動返信待ち） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
            
            # AI自動応答がONの場合の通常処理
            # 質問か症状入力かを判定
            is_question = not is_symptom_input(user_message)
            
            if is_question:"""

content = content.replace(old_2, new_2)

# ファイルに書き戻す
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Minimal changes applied successfully")

