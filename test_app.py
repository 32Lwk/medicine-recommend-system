from flask import Flask, render_template, request, jsonify, session
import os
import json
import time
from datetime import datetime
import pandas as pd
from openai import OpenAI
from medicine_logic import df, CSV_PATH, api_key, csv_load_status
from debug_logger import add_network_log, performance_stats

app = Flask(__name__)
app.secret_key = 'test-secret-key-here'

# テストモードの設定
TEST_MODE = os.getenv('TEST_MODE', 'api')  # 'api' または 'mock'

# medicine_logicからAPIキーを取得
API_KEY = api_key

# テスト用のモックデータ
MOCK_RESPONSES = {
    'symptom_matching': {
        '喉が痛くて熱がある': ['喉 - 痛み', '全身 - 発熱'],
        '頭が痛くて吐き気がする': ['頭 - 痛み', '胃 - 吐き気'],
        '腹痛と下痢': ['腹部 - 痛み', '腹部 - 下痢'],
        '咳と鼻水': ['呼吸器 - 咳', '鼻 - 鼻水'],
        '関節痛とだるさ': ['関節 - 痛み', '全身 - だるさ'],
        'めまいと吐き気': ['頭 - めまい', '胃 - 吐き気'],
        '足がかゆい': [],  # 未登録症状
        '昨日から喉が痛くて、夜になると熱が上がる': ['喉 - 痛み', '全身 - 発熱'],
        '長文複雑症状': ['頭 - 痛み', '全身 - 発熱', '胃 - 吐き気']
    },
    'cautions': {
        '喉 - 痛み': '① 考えられる病気：風邪、扁桃炎\n② 注意点：うがいを頻繁に行い、十分な水分補給を\n③ 受診が必要な場合：高熱が続く、呼吸困難がある場合',
        '全身 - 発熱': '① 考えられる病気：風邪、インフルエンザ\n② 注意点：安静にし、水分補給を十分に\n③ 受診が必要な場合：39度以上の高熱、意識障害がある場合',
        '頭 - 痛み': '① 考えられる病気：緊張性頭痛、片頭痛\n② 注意点：ストレスを避け、十分な睡眠を\n③ 受診が必要な場合：激しい痛み、嘔吐を伴う場合',
        '胃 - 吐き気': '① 考えられる病気：急性胃炎、食中毒\n② 注意点：消化の良い食事を少量ずつ\n③ 受診が必要な場合：激しい腹痛、血便がある場合',
        '腹部 - 痛み': '① 考えられる病気：急性胃炎、腸炎\n② 注意点：消化の良い食事を避け、安静に\n③ 受診が必要な場合：激しい痛み、血便がある場合',
        '腹部 - 下痢': '① 考えられる病気：急性腸炎、食中毒\n② 注意点：水分補給を十分に、消化の良い食事を\n③ 受診が必要な場合：血便、高熱がある場合',
        '未登録': '該当する注意点はありません。',
    },
    'combination_advice': {
        'default': '症状に対して適した医薬品候補群の中から一つだけ選んで服用してください。成分の重複や併用禁忌がないか確認し、体調に変化があった場合は専門家にご相談ください。',
        '禁忌例': 'ロキソプロフェンとアセトアミノフェンは併用注意です。どちらか一方を選んで服用してください。バファリンも同系統の成分が含まれるため、重複服用は避けてください。'
    },
    'conversation': {
        'default': 'ご質問にお答えします。詳しくは登録販売者にお声掛けください。体調に変化があった場合は専門家にご相談ください。',
        '副作用': '市販薬の副作用について説明します。一般的に軽度の副作用が現れることがありますが、重篤な症状が出た場合はすぐに使用を中止し、医師に相談してください。',
        '服用方法': '市販薬の服用方法について説明します。必ず添付文書を確認し、用法・用量を守って服用してください。',
        '保存方法': '市販薬の保存方法について説明します。直射日光を避け、湿気の少ない涼しい場所に保管してください。',
        '天気': '病気や医薬品以外の質問には回答する事ができません。詳しくはお近くのスタッフにお問い合わせください。',
        '好きな食べ物': '病気や医薬品以外の質問には回答する事ができません。詳しくはお近くのスタッフにお問い合わせください。'
    }
}

# OpenAIクライアント（APIモードの場合のみ初期化）
client = None
if TEST_MODE == 'api' and API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
        print("OpenAI client initialized for API mode")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        TEST_MODE = 'mock'
        print("Switching to mock mode due to API initialization error")
else:
    print(f"API mode: {TEST_MODE}, API Key available: {bool(API_KEY)}")
    if not API_KEY:
        TEST_MODE = 'mock'
        print("No API key available, switching to mock mode")

def add_test_log(message, level="INFO"):
    """テストログを追加"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message,
        'mode': TEST_MODE
    }
    
    # リクエストコンテキスト内でのみセッションを使用
    try:
        if 'test_logs' not in session:
            session['test_logs'] = []
        session['test_logs'].append(log_entry)
        # ログを50件まで保持
        if len(session['test_logs']) > 50:
            session['test_logs'].pop(0)
    except RuntimeError:
        # リクエストコンテキスト外の場合はコンソールに出力
        print(f"[{timestamp}] [{level}] [{TEST_MODE}] {message}")

def log_test_api_call(endpoint, request_data, response_data, response_time, status, error_details=None):
    """テストAPI呼び出しをログに記録"""
    add_network_log(
        request_type='POST',
        endpoint=f'テストサイト:{endpoint}',
        request_data=request_data,
        response_data=response_data,
        response_time=response_time,
        status=status,
        error=error_details
    )

@app.route('/')
def index():
    """テスト用メインページ"""
    return render_template('test_index.html', test_mode=TEST_MODE)

@app.route('/api/mode', methods=['GET', 'POST'])
def api_mode():
    """APIモードの切り替え"""
    global TEST_MODE, client
    
    if request.method == 'POST':
        data = request.get_json()
        new_mode = data.get('mode', 'api')
        
        if new_mode == 'api':
            if API_KEY:
                try:
                    client = OpenAI(api_key=API_KEY)
                    TEST_MODE = 'api'
                    add_test_log("Switched to API mode")
                    return jsonify({'success': True, 'mode': 'api', 'message': 'APIモードに切り替えました'})
                except Exception as e:
                    add_test_log(f"Failed to switch to API mode: {str(e)}", "ERROR")
                    return jsonify({'success': False, 'error': f'API初期化エラー: {str(e)}'}), 500
            else:
                return jsonify({'success': False, 'error': 'APIキーが設定されていません'}), 400
        else:
            TEST_MODE = 'mock'
            client = None
            add_test_log("Switched to mock mode")
            return jsonify({'success': True, 'mode': 'mock', 'message': 'モックモードに切り替えました'})
    
    return jsonify({'mode': TEST_MODE})

@app.route('/api/test_symptom', methods=['POST'])
def test_symptom():
    """症状マッチングのテスト"""
    try:
        data = request.get_json()
        symptom_text = data.get('symptom', '')
        
        if not symptom_text:
            return jsonify({'error': '症状が入力されていません'}), 400
        
        add_test_log(f"Testing symptom matching: {symptom_text}")
        
        if TEST_MODE == 'api' and client:
            # 実際のAPIを使用
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
                {"role": "user", "content": f"症状: {symptom_text}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            result_str = response.choices[0].message.content
            if result_str:
                result_str = result_str.strip()
            else:
                result_str = "該当なし"
            
            if result_str == "該当なし":
                symptom_pairs = []
            else:
                symptom_pairs = [pair.strip() for pair in result_str.split(",") if pair.strip()]
            
            tokens_used = response.usage.total_tokens if response.usage else None
            
            add_test_log(f"API response: {result_str} (took {response_time}s)")
            
            # ログに記録
            log_test_api_call('症状マッチング', {'symptom': symptom_text}, {'result': symptom_pairs}, response_time, 'success')
            
        else:
            # モックデータを使用
            symptom_pairs = MOCK_RESPONSES['symptom_matching'].get(symptom_text, [])
            add_test_log(f"Mock response: {symptom_pairs}")
            
            # モックモードでもログに記録
            log_test_api_call('症状マッチング', {'symptom': symptom_text}, {'result': symptom_pairs}, 0.001, 'success')
        
        # 薬の情報を取得
        medicines = []
        for pair in symptom_pairs:
            matched_row = df[(df['部位'] + ' - ' + df['症状']) == pair]
            if not matched_row.empty:
                medicine_list = [med for med in matched_row.iloc[0][['医薬品1', '医薬品2', '医薬品3']].dropna().tolist()]
                medicines.extend(medicine_list)
        
        return jsonify({
            'symptom_pairs': symptom_pairs,
            'medicines': medicines,
            'mode': TEST_MODE
        })
        
    except Exception as e:
        error_msg = f"Symptom test error: {str(e)}"
        add_test_log(error_msg, "ERROR")
        log_test_api_call('症状マッチング', {'symptom': symptom_text}, None, None, 'error', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_cautions', methods=['POST'])
def test_cautions():
    """注意点生成のテスト"""
    try:
        data = request.get_json()
        symptom_pair = data.get('symptom_pair', '')
        
        if not symptom_pair:
            return jsonify({'error': '症状の組み合わせが入力されていません'}), 400
        
        add_test_log(f"Testing cautions generation: {symptom_pair}")
        
        if TEST_MODE == 'api' and client:
            # 実際のAPIを使用
            messages = [
                {"role": "system", "content": (
                    "あなたは日本の登録販売者AIです。\n"
                    "以下の症状の組み合わせに対し、専門家として、以下の3点を具体的に、かつ分かりやすく記述してください。\n"
                    "① 考えられる病気の候補（1〜2個）：登録販売者の視点から、可能性のある病名を挙げてください。\n"
                    "② 使用上の一般的な注意点：市販薬を使う場合の一般的な注意や、日常生活でのケアについて簡潔に説明してください。\n"
                    "③ 医師の受診が必要な場合：どのような症状が出たら、すぐに医師に相談すべきか、簡潔に兆候を明確に示してください。\n"
                    "市販薬の具体的な商品名は含めないでください。専門用語は避け、一般の方にも理解できるように平易な言葉遣いを心がけてください。"
                )},
                {"role": "user", "content": f"症状の組み合わせ：{symptom_pair}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            cautions = response.choices[0].message.content
            if cautions:
                cautions = cautions.strip()
            add_test_log(f"API cautions generated (took {response_time}s)")
            
            # ログに記録
            log_test_api_call('注意点生成', {'symptom_pair': symptom_pair}, {'result': cautions}, response_time, 'success')
            
        else:
            # モックデータを使用
            cautions = MOCK_RESPONSES['cautions'].get(symptom_pair, MOCK_RESPONSES['cautions']['未登録'])
            add_test_log(f"Mock cautions generated")
            
            # モックモードでもログに記録
            log_test_api_call('注意点生成', {'symptom_pair': symptom_pair}, {'result': cautions}, 0.001, 'success')
        
        return jsonify({
            'cautions': cautions,
            'mode': TEST_MODE
        })
        
    except Exception as e:
        error_msg = f"Cautions test error: {str(e)}"
        add_test_log(error_msg, "ERROR")
        log_test_api_call('注意点生成', {'symptom_pair': symptom_pair}, None, None, 'error', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_combination', methods=['POST'])
def test_combination():
    """薬の組み合わせチェックのテスト"""
    try:
        data = request.get_json()
        medicines = data.get('medicines', [])
        
        if not medicines:
            return jsonify({'error': '薬のリストが入力されていません'}), 400
        
        add_test_log(f"Testing combination check: {medicines}")
        
        if TEST_MODE == 'api' and client:
            # 実際のAPIを使用
            prompt = (
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
                f"市販薬リスト: {', '.join(medicines)}"
            )
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"以下の市販薬についてアドバイスをください: {', '.join(medicines)}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            advice = response.choices[0].message.content
            if advice:
                advice = advice.strip()
            add_test_log(f"API combination advice generated (took {response_time}s)")
            
            # ログに記録
            log_test_api_call('薬の組み合わせチェック', {'medicines': medicines}, {'result': advice}, response_time, 'success')
            
        else:
            # モックデータを使用
            advice = MOCK_RESPONSES['combination_advice']['default']
            add_test_log(f"Mock combination advice generated")
            
            # モックモードでもログに記録
            log_test_api_call('薬の組み合わせチェック', {'medicines': medicines}, {'result': advice}, 0.001, 'success')
        
        return jsonify({
            'advice': advice,
            'mode': TEST_MODE
        })
        
    except Exception as e:
        error_msg = f"Combination test error: {str(e)}"
        add_test_log(error_msg, "ERROR")
        log_test_api_call('薬の組み合わせチェック', {'medicines': medicines}, None, None, 'error', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_conversation', methods=['POST'])
def test_conversation():
    """会話継続のテスト"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        symptom_pairs = data.get('symptom_pairs', [])
        medicines = data.get('medicines', [])
        
        if not question:
            return jsonify({'error': '質問が入力されていません'}), 400
        
        add_test_log(f"Testing conversation: {question}")
        
        if TEST_MODE == 'api' and client:
            # 実際のAPIを使用
            context_symptom = symptom_pairs[0] if len(symptom_pairs) == 1 else ", ".join(symptom_pairs)
            
            prompt = (
                "あなたは日本の薬剤師または登録販売者AIです。\n"
                "医薬品や病気に関する質問にのみ解答するようにして、関係のない質問に関しては「病気や医薬品以外の質問には回答する事ができません。詳しくはお近くのスタッフにお問い合わせください」と返信してください。\n"
                "すべての質問に簡潔に解答し、最後には必ず「詳しくは登録販売者にお声掛けください」と付け加えてください。\n"
                "また、「体調に変化があった場合は専門家にご相談ください。」という注意書きを添えてください。\n"
                f"現在の症状の組み合わせ: {context_symptom}\n"
                f"市販薬リスト: {', '.join(medicines) if medicines else 'なし'}"
            )
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"質問: {question}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            answer = response.choices[0].message.content
            if answer:
                answer = answer.strip()
            add_test_log(f"API conversation response generated (took {response_time}s)")
            
            # ログに記録
            log_test_api_call('会話継続', {'question': question, 'symptom_pairs': symptom_pairs, 'medicines': medicines}, {'result': answer}, response_time, 'success')
            
        else:
            # モックデータを使用
            if '副作用' in question:
                answer = MOCK_RESPONSES['conversation']['副作用']
            elif '服用' in question:
                answer = MOCK_RESPONSES['conversation']['服用方法']
            elif '保存' in question:
                answer = MOCK_RESPONSES['conversation']['保存方法']
            else:
                answer = MOCK_RESPONSES['conversation']['default']
            add_test_log(f"Mock conversation response generated")
            
            # モックモードでもログに記録
            log_test_api_call('会話継続', {'question': question, 'symptom_pairs': symptom_pairs, 'medicines': medicines}, {'result': answer}, 0.001, 'success')
        
        return jsonify({
            'answer': answer,
            'mode': TEST_MODE
        })
        
    except Exception as e:
        error_msg = f"Conversation test error: {str(e)}"
        add_test_log(error_msg, "ERROR")
        log_test_api_call('会話継続', {'question': question, 'symptom_pairs': symptom_pairs, 'medicines': medicines}, None, None, 'error', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_full_flow', methods=['POST'])
def test_full_flow():
    """完全な診断フローのテスト"""
    try:
        data = request.get_json()
        symptom_text = data.get('symptom', '')
        
        if not symptom_text:
            return jsonify({'error': '症状が入力されていません'}), 400
        
        add_test_log(f"Testing full flow: {symptom_text}")
        
        # 1. 症状マッチング
        if TEST_MODE == 'api' and client:
            # 実際のAPIを使用
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
                {"role": "user", "content": f"症状: {symptom_text}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            result_str = response.choices[0].message.content
            if result_str:
                result_str = result_str.strip()
            else:
                result_str = "該当なし"
            
            if result_str == "該当なし":
                symptom_pairs = []
            else:
                symptom_pairs = [pair.strip() for pair in result_str.split(",") if pair.strip()]
            
            add_test_log(f"API symptom matching: {symptom_pairs} (took {response_time}s)")
            
            # ログに記録
            log_test_api_call('統合テスト:症状マッチング', {'symptom': symptom_text}, {'result': symptom_pairs}, response_time, 'success')
            
        else:
            # モックデータを使用
            symptom_pairs = MOCK_RESPONSES['symptom_matching'].get(symptom_text, [])
            add_test_log(f"Mock symptom matching: {symptom_pairs}")
            
            # モックモードでもログに記録
            log_test_api_call('統合テスト:症状マッチング', {'symptom': symptom_text}, {'result': symptom_pairs}, 0.001, 'success')
        
        # 薬の情報を取得
        medicines = []
        for pair in symptom_pairs:
            matched_row = df[(df['部位'] + ' - ' + df['症状']) == pair]
            if not matched_row.empty:
                medicine_list = [med for med in matched_row.iloc[0][['医薬品1', '医薬品2', '医薬品3']].dropna().tolist()]
                medicines.extend(medicine_list)
        
        # 2. 注意点生成
        cautions_results = []
        for pair in symptom_pairs:
            if TEST_MODE == 'api' and client:
                # 実際のAPIを使用
                messages = [
                    {"role": "system", "content": (
                        "あなたは日本の登録販売者AIです。\n"
                        "以下の症状の組み合わせに対し、専門家として、以下の3点を具体的に、かつ分かりやすく記述してください。\n"
                        "① 考えられる病気の候補（1〜2個）：登録販売者の視点から、可能性のある病名を挙げてください。\n"
                        "② 使用上の一般的な注意点：市販薬を使う場合の一般的な注意や、日常生活でのケアについて簡潔に説明してください。\n"
                        "③ 医師の受診が必要な場合：どのような症状が出たら、すぐに医師に相談すべきか、簡潔に兆候を明確に示してください。\n"
                        "市販薬の具体的な商品名は含めないでください。専門用語は避け、一般の方にも理解できるように平易な言葉遣いを心がけてください。"
                    )},
                    {"role": "user", "content": f"症状の組み合わせ：{pair}"}
                ]
                
                start_time = time.time()
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                end_time = time.time()
                response_time = round(end_time - start_time, 3)
                
                cautions = response.choices[0].message.content
                if cautions:
                    cautions = cautions.strip()
                
                # ログに記録
                log_test_api_call('統合テスト:注意点生成', {'symptom_pair': pair}, {'result': cautions}, response_time, 'success')
                
            else:
                # モックデータを使用
                cautions = MOCK_RESPONSES['cautions'].get(pair, MOCK_RESPONSES['cautions']['未登録'])
                
                # モックモードでもログに記録
                log_test_api_call('統合テスト:注意点生成', {'symptom_pair': pair}, {'result': cautions}, 0.001, 'success')
            
            cautions_results.append({
                'symptom_pair': pair,
                'cautions': cautions
            })
        
        # 3. 組み合わせアドバイス
        if TEST_MODE == 'api' and client and medicines:
            # 実際のAPIを使用
            prompt = (
                "あなたは日本の薬剤師または登録販売者AIです。\n"
                "以下の市販薬リストに含まれるすべての薬について、成分の重複や一般的な併用禁忌がないか詳細に判断してください。\n"
                "症状に対して適した医薬品候補群の中から一つだけ選んで服用し、成分が異なっていても、一つの症状から複数の医薬品を使うことは推奨しないでください\n"
                "もし症状をまたいで薬の成分に重複や併用注意がある場合(例:総合感冒薬＋解熱薬など)は具体的な成分名に言及し、どちらか一方を選ぶべきか、あるいはどのような症状に注意すべきかなど、実践的で具体的な判断基準やアドバイスを提供した上で、「登録販売者にお問い合わせください。」を加えてください。\n"
                "体力の低下などが見られる場合は必要に応じて食事療法や栄養ドリンクを進めるようにしてください。\n"
                "薬の名前だけでなく、なぜそのアドバイスが必要なのか、理由も簡潔に説明してください。\n"
                "個別の医薬品の説明どのよう主成分と効果のみ説明してください。\n"
                "症状に対しては○○が原因の場合という風に伝えてください。\n\n"
                "すべての内容は簡潔に伝えるようにしてください。\n\n\n"
                f"市販薬リスト: {', '.join(medicines)}"
            )
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"以下の市販薬についてアドバイスをください: {', '.join(medicines)}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2
            )
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            combination_advice = response.choices[0].message.content
            if combination_advice:
                combination_advice = combination_advice.strip()
            
            # ログに記録
            log_test_api_call('統合テスト:薬の組み合わせチェック', {'medicines': medicines}, {'result': combination_advice}, response_time, 'success')
            
        else:
            # モックデータを使用
            combination_advice = MOCK_RESPONSES['combination_advice']['default']
            
            # モックモードでもログに記録
            log_test_api_call('統合テスト:薬の組み合わせチェック', {'medicines': medicines}, {'result': combination_advice}, 0.001, 'success')
        
        return jsonify({
            'symptom_pairs': symptom_pairs,
            'medicines': medicines,
            'cautions': cautions_results,
            'combination_advice': combination_advice,
            'mode': TEST_MODE
        })
        
    except Exception as e:
        error_msg = f"Full flow test error: {str(e)}"
        add_test_log(error_msg, "ERROR")
        log_test_api_call('統合テスト', {'symptom': symptom_text}, None, None, 'error', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """テストログを取得"""
    return jsonify(session.get('test_logs', []))

@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    """テストログをクリア"""
    session['test_logs'] = []
    add_test_log("Test logs cleared")
    return jsonify({'message': 'Logs cleared successfully'})

@app.route('/api/status')
def status():
    """システム状況を返す（CSV読み込み状況も含む）"""
    status = {
        "test_mode": TEST_MODE,
        "api_key_set": bool(API_KEY),
        "openai_client": client is not None,
        "csv_load_status": csv_load_status,
        # 他の情報も必要に応じて追加
    }
    return jsonify(status)

@app.route('/api/mock_data')
def get_mock_data():
    """モックデータの一覧を取得"""
    return jsonify({
        'symptom_examples': list(MOCK_RESPONSES['symptom_matching'].keys()),
        'cautions_examples': list(MOCK_RESPONSES['cautions'].keys()),
        'conversation_examples': list(MOCK_RESPONSES['conversation'].keys())
    })

if __name__ == '__main__':
    print(f"Test application started in {TEST_MODE} mode")
    print(f"API Key set: {bool(API_KEY)}")
    print(f"OpenAI Client initialized: {client is not None}")
    app.run(debug=True, port=5002)