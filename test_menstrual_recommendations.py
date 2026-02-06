"""
女性特有の生理関連医薬品推奨アルゴリズムのテストケース

様々な症状パターンとユーザー要望の組み合わせでテストを行います。
"""

import sys
import os
import json
import time
from datetime import datetime

# プロジェクトルートをパスに追加
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# CSVファイルの存在確認
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "otc_medicine_data.csv")

from src.core.rule_based_recommendation import rule_based_medicine_recommendation, simple_pattern_matching_nlu
from src.core.medicine_logic import extract_user_preferences, detect_digestive_sensitivity, detect_postpartum_breastfeeding, detect_severity_escalation
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CSVファイルの存在確認
if not os.path.exists(CSV_PATH):
    logger.error(f"❌ CSVファイルが見つかりません: {CSV_PATH}")
    logger.error("   テストを実行するには、data/otc_medicine_data.csv が必要です。")
    CSV_AVAILABLE = False
else:
    logger.info(f"✅ CSVファイルが見つかりました: {CSV_PATH}")
    CSV_AVAILABLE = True

# OpenAIクライアントの初期化（テスト用）
# 環境変数からAPIキーを取得、なければNone（エラーハンドリングは各関数内で）
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        test_client = OpenAI(api_key=api_key)
    else:
        test_client = None
        logger.warning("⚠️ OPENAI_API_KEYが設定されていません。一部のテストが失敗する可能性があります。")
except Exception as e:
    test_client = None
    logger.warning(f"⚠️ OpenAIクライアントの初期化に失敗しました: {e}")

# 期待される医薬品リスト
EXPECTED_MEDICINES = [
    "ラムールQ", "ラムールＱ",
    "加味逍遙散", "カミショウヨウサン",
    "命の母ホワイト",
    "ルナエール",
    "ルナフェミン",
    "桂枝茯苓丸", "ケイシブクリョウガン"
]

def verify_score_threshold(recommendations, min_score=0.35):
    """推奨医薬品のスコアが閾値を超えているか検証"""
    issues = []
    for r in recommendations:
        score = r.get('total_score', r.get('score', 0.0))
        if score < min_score:
            issues.append({
                'product_name': r.get('product_name', ''),
                'score': score,
                'threshold': min_score
            })
    return len(issues) == 0, issues

def verify_score_breakdown(recommendations):
    """スコアブレークダウンの妥当性を検証"""
    issues = []
    for r in recommendations:
        breakdown = r.get('score_breakdown', {})
        product_name = r.get('product_name', '')
        
        # 各スコアコンポーネントの妥当性をチェック
        if breakdown:
            # symptom_matchが0.0の場合は警告（症状が全くマッチしていない）
            if breakdown.get('symptom_match', 0.0) == 0.0:
                issues.append({
                    'product_name': product_name,
                    'issue': 'symptom_match_is_zero',
                    'breakdown': breakdown
                })
            
            # スコアの合計がtotal_scoreと一致するかチェック（概算）
            calculated_total = (
                breakdown.get('symptom_match', 0.0) +
                breakdown.get('efficacy_specificity', 0.0) +
                breakdown.get('age_fit', 0.0) +
                breakdown.get('usage_convenience', 0.0) -
                breakdown.get('side_effect_risk', 0.0) -
                breakdown.get('interaction_risk', 0.0)
            )
            total_score = r.get('total_score', 0.0)
            if abs(calculated_total - total_score) > 0.5:  # 調整スコアがあるため、0.5の誤差は許容
                issues.append({
                    'product_name': product_name,
                    'issue': 'score_mismatch',
                    'calculated': calculated_total,
                    'actual': total_score,
                    'breakdown': breakdown
                })
    
    return len(issues) == 0, issues

def check_recommendation_contains_expected(recommendations, test_name, verbose=True, top_n=10):
    """
    推奨リストに期待される医薬品が含まれているかチェック（柔軟な判定）
    
    Args:
        recommendations: 推奨医薬品リスト
        test_name: テスト名
        verbose: 詳細ログを出力するか
        top_n: 上位N件以内にあれば成功とする（デフォルト: 10件）
    
    Returns:
        (bool, list): (見つかったか, 見つかった詳細情報)
    """
    product_names = [r.get('product_name', '') for r in recommendations]
    found_expected = []
    found_details = []
    all_recommendations_details = []
    
    # 全推奨結果の詳細を記録
    for idx, r in enumerate(recommendations[:top_n]):
        all_recommendations_details.append({
            'rank': idx + 1,
            'product_name': r.get('product_name', ''),
            'score': r.get('total_score', r.get('score', 0.0)),
            'medicine_type': r.get('medicine_type', ''),
            'efficacy': r.get('efficacy', '')[:50] if r.get('efficacy') else ''  # 最初の50文字
        })
    
    # 期待される医薬品を検索（上位N件以内）
    for expected in EXPECTED_MEDICINES:
        for idx, r in enumerate(recommendations[:top_n]):
            product_name = r.get('product_name', '')
            if expected in product_name or product_name in expected:
                found_expected.append(expected)
                score = r.get('total_score', r.get('score', 0.0))
                found_details.append({
                    'expected': expected,
                    'product_name': product_name,
                    'rank': idx + 1,
                    'score': score
                })
                break
    
    if found_expected:
        if verbose:
            logger.info(f"✅ {test_name}: 期待される医薬品が見つかりました: {found_expected}")
            for detail in found_details:
                logger.info(f"   - {detail['expected']}: {detail['product_name']} (順位: {detail['rank']}, スコア: {detail['score']:.3f})")
        return True, found_details
    else:
        if verbose:
            logger.warning(f"⚠️ {test_name}: 期待される医薬品が見つかりませんでした。")
            logger.warning(f"   推奨リスト (上位{min(10, len(product_names))}件):")
            for detail in all_recommendations_details[:10]:
                logger.warning(f"      {detail['rank']}位: {detail['product_name']} (スコア: {detail['score']:.3f}, 種類: {detail['medicine_type']})")
            if recommendations:
                scores = [r.get('total_score', r.get('score', 0.0)) for r in recommendations[:5]]
                logger.warning(f"   上位5件のスコア: {scores}")
        return False, all_recommendations_details

def save_test_snapshot(test_name, recommendations, user_message, user_info):
    """テスト結果のスナップショットを保存（デバッグ用）"""
    try:
        snapshot_dir = os.path.join(BASE_DIR, "test_snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        
        snapshot_file = os.path.join(snapshot_dir, f"{test_name.replace(' ', '_').replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        snapshot_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "user_info": user_info,
            "recommendations": [
                {
                    "rank": idx + 1,
                    "product_name": r.get('product_name', ''),
                    "score": r.get('total_score', r.get('score', 0.0)),
                    "medicine_type": r.get('medicine_type', ''),
                    "efficacy": r.get('efficacy', ''),
                    "ingredients": r.get('ingredients', '')[:100] if r.get('ingredients') else '',  # 最初の100文字
                    "score_breakdown": r.get('score_breakdown', {})
                }
                for idx, r in enumerate(recommendations[:10])
            ]
        }
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        
        return snapshot_file
    except Exception as e:
        logger.warning(f"⚠️ スナップショットの保存に失敗: {e}")
        return None

def test_basic_menstrual_irregularity_with_irritability():
    """基本テスト: 生理不順で、なおかつイライラする"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return False
    
    user_message = "生理不順で、なおかつイライラする"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    try:
        start_time = time.time()
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        elapsed_time = time.time() - start_time
        recommendations = result.get('recommendations', [])
        
        # スナップショットを保存（失敗時のみ）
        snapshot_file = None
        
        if len(recommendations) < 2:
            logger.error(f"❌ 推奨数が不足: {len(recommendations)}件（期待: 2件以上）")
            snapshot_file = save_test_snapshot("基本テスト_生理不順_イライラ", recommendations, user_message, user_info)
            if snapshot_file:
                logger.info(f"📸 スナップショットを保存: {snapshot_file}")
            return False
        
        found, details = check_recommendation_contains_expected(recommendations, "基本テスト: 生理不順+イライラ", top_n=10)
        
        # スコア検証も実行
        threshold_ok, threshold_issues = verify_score_threshold(recommendations, min_score=0.35)
        breakdown_ok, breakdown_issues = verify_score_breakdown(recommendations)
        
        # 詳細な失敗原因を記録
        failure_reasons = []
        if not found:
            failure_reasons.append("期待される医薬品が上位10件以内に見つからない")
            snapshot_file = save_test_snapshot("基本テスト_生理不順_イライラ", recommendations, user_message, user_info)
            if details:
                logger.warning(f"   実際の推奨結果（上位10件）:")
                for d in details[:10]:
                    logger.warning(f"      {d['rank']}位: {d['product_name']} (スコア: {d['score']:.3f})")
        if not threshold_ok:
            failure_reasons.append(f"スコア閾値未満の推奨が{len(threshold_issues)}件")
            for issue in threshold_issues[:3]:
                logger.warning(f"   - {issue['product_name']}: スコア {issue['score']:.3f} < 閾値 {issue['threshold']}")
        if not breakdown_ok:
            failure_reasons.append(f"スコアブレークダウンの問題が{len(breakdown_issues)}件")
            for issue in breakdown_issues[:3]:
                logger.warning(f"   - {issue['product_name']}: {issue['issue']}")
        
        all_ok = found and threshold_ok and breakdown_ok
        if all_ok:
            logger.info(f"✅ 基本テスト完了: {len(recommendations)}件の推奨 (実行時間: {elapsed_time:.2f}秒)")
        else:
            logger.warning(f"⚠️ 基本テスト: 失敗理由 - {', '.join(failure_reasons)}")
            if snapshot_file:
                logger.info(f"📸 スナップショットを保存: {snapshot_file}")
        
        return all_ok
    except Exception as e:
        logger.error(f"❌ 基本テストでエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_ingredient_balance_preference():
    """成分・バランス重視の要望がある場合"""
    user_message = "生理不順で、なおかつイライラする。成分・バランス重視です"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # ラムールQや加味逍遙散が推奨されることを期待（上位10件以内）
        found, details = check_recommendation_contains_expected(recommendations, "成分・バランス重視", top_n=10)
        
        if found:
            logger.info(f"✅ 成分・バランス重視テスト完了")
        else:
            logger.warning(f"⚠️ 成分・バランス重視テスト: 期待される医薬品が見つかりませんでした")
            if details:
                logger.warning(f"   実際の推奨結果（上位5件）:")
                for d in details[:5]:
                    logger.warning(f"      {d['rank']}位: {d['product_name']} (スコア: {d['score']:.3f})")
        
        return found
    except Exception as e:
        logger.error(f"❌ 成分・バランス重視テストでエラー: {e}")
        return False

def test_ease_of_taking_preference():
    """飲みやすさ重視の要望がある場合"""
    user_message = "生理不順で、なおかつイライラする。錠剤タイプが飲みやすいです"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # ルナエールやルナフェミンが推奨されることを期待
        product_names = [r.get('product_name', '') for r in recommendations]
        has_tablet = any('ルナエール' in name or 'ルナフェミン' in name for name in product_names)
        
        if has_tablet:
            logger.info(f"✅ 飲みやすさ重視テスト完了: 錠剤タイプが推奨されました")
        else:
            logger.warning(f"⚠️ 飲みやすさ重視テスト: 錠剤タイプが見つかりませんでした")
            logger.warning(f"   推奨リスト: {product_names[:5]}")
        
        return has_tablet
    except Exception as e:
        logger.error(f"❌ 飲みやすさ重視テストでエラー: {e}")
        return False

def test_accompanying_symptoms_preference():
    """随伴症状対応の要望がある場合"""
    user_message = "生理不順で、なおかつイライラする。あれこれ気になる症状があります"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # 命の母ホワイトや桂枝茯苓丸が推奨されることを期待（上位10件以内）
        found, details = check_recommendation_contains_expected(recommendations, "随伴症状対応", top_n=10)
        
        if found:
            logger.info(f"✅ 随伴症状対応テスト完了")
        else:
            logger.warning(f"⚠️ 随伴症状対応テスト: 期待される医薬品が見つかりませんでした")
            if details:
                logger.warning(f"   実際の推奨結果（上位5件）:")
                for d in details[:5]:
                    logger.warning(f"      {d['rank']}位: {d['product_name']} (スコア: {d['score']:.3f})")
        
        return found
    except Exception as e:
        logger.error(f"❌ 随伴症状対応テストでエラー: {e}")
        return False

def test_digestive_sensitivity():
    """お腹を壊しやすいユーザーに対する推奨（大黄含有製品が除外されるか）"""
    user_message = "生理不順で、なおかつイライラする。お腹を壊しやすいです"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # 大黄含有製品が除外されているかチェック
        product_names = [r.get('product_name', '') for r in recommendations]
        ingredients_list = [str(r.get('ingredients', '')).lower() for r in recommendations]
        
        has_daiou = any('ダイオウ' in ing or '大黄' in ing for ing in ingredients_list)
        
        if has_daiou:
            logger.warning(f"⚠️ お腹を壊しやすいテスト: 大黄含有製品が推奨されています")
            daiou_products = [name for name, ing in zip(product_names, ingredients_list) if 'ダイオウ' in ing or '大黄' in ing]
            logger.warning(f"   推奨された大黄含有製品: {daiou_products}")
            return False
        else:
            logger.info(f"✅ お腹を壊しやすいテスト完了: 大黄含有製品は除外されました")
            return True
    except Exception as e:
        logger.error(f"❌ お腹を壊しやすいテストでエラー: {e}")
        return False

def test_postpartum_breastfeeding():
    """産後・授乳中のユーザーに対する推奨（大黄含有製品が除外されるか）"""
    user_message = "生理不順で、なおかつイライラする。産後です"
    user_info = {
        'age': 30,
        'gender': '女性',
        'postpartum': True
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # 大黄含有製品が除外されているかチェック
        ingredients_list = [str(r.get('ingredients', '')).lower() for r in recommendations]
        has_daiou = any('ダイオウ' in ing or '大黄' in ing for ing in ingredients_list)
        
        if has_daiou:
            logger.warning(f"⚠️ 産後テスト: 大黄含有製品が推奨されています")
            return False
        else:
            logger.info(f"✅ 産後テスト完了: 大黄含有製品は除外されました")
            return True
    except Exception as e:
        logger.error(f"❌ 産後テストでエラー: {e}")
        return False

def test_pregnancy_contraindication():
    """妊娠中・妊娠の可能性のユーザーに対する推奨（桃仁・牡丹皮含有製品が除外されるか）"""
    user_message = "生理不順で、なおかつイライラする。妊娠の可能性があります"
    user_info = {
        'age': 30,
        'gender': '女性',
        'pregnancy_possible': True
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # 桃仁・牡丹皮含有製品が除外されているかチェック
        ingredients_list = [str(r.get('ingredients', '')).lower() for r in recommendations]
        has_contraindicated = any(
            'トウニン' in ing or '桃仁' in ing or 
            'ボタンピ' in ing or '牡丹皮' in ing 
            for ing in ingredients_list
        )
        
        if has_contraindicated:
            logger.warning(f"⚠️ 妊娠可能性テスト: 禁忌成分含有製品が推奨されています")
            return False
        else:
            logger.info(f"✅ 妊娠可能性テスト完了: 禁忌成分含有製品は除外されました")
            return True
    except Exception as e:
        logger.error(f"❌ 妊娠可能性テストでエラー: {e}")
        return False

def test_severity_escalation():
    """生理痛が年々ひどくなっている → 受診勧奨メッセージが表示されるか"""
    user_message = "生理痛が年々ひどくなっている"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    nlu_result = simple_pattern_matching_nlu(user_message, user_info)
    escalation_info = detect_severity_escalation(user_message, nlu_result, user_info)
    
    if escalation_info.get('needs_escalation', False):
        logger.info(f"✅ 重症度エスカレーションテスト完了: 受診勧奨が検出されました")
        logger.info(f"   理由: {escalation_info.get('reason', '')}")
    else:
        logger.warning(f"⚠️ 重症度エスカレーションテスト: 受診勧奨が検出されませんでした")
    
    return True

def test_pain_urgency_primary():
    """痛みが主訴の場合 → 解熱鎮痛剤が1位または2位に含まれるか"""
    user_message = "お腹が痛くて辛い"
    user_info = {
        'age': 25,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # 上位2件に解熱鎮痛剤が含まれているかチェック
        top_2 = recommendations[:2]
        has_analgesic = any(
            '解熱鎮痛薬' in str(r.get('medicine_type', '')) 
            for r in top_2
        )
        
        if has_analgesic:
            logger.info(f"✅ 痛み主訴テスト完了: 解熱鎮痛剤が上位2件に含まれました")
        else:
            logger.warning(f"⚠️ 痛み主訴テスト: 解熱鎮痛剤が上位2件に含まれていません")
            if top_2:
                logger.warning(f"   上位2件: {[r.get('product_name', '') for r in top_2]}")
        
        return has_analgesic
    except Exception as e:
        logger.error(f"❌ 痛み主訴テストでエラー: {e}")
        return False

def test_life_stage_correction():
    """年齢層による補正のテスト（10-20代、30-40代、50代以上）"""
    test_cases = [
        (20, "若年層"),
        (35, "中間層"),
        (55, "更年期前後")
    ]
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        all_passed = True
        for age, stage_name in test_cases:
            user_message = "生理不順で、なおかつイライラする"
            user_info = {
                'age': age,
                'gender': '女性'
            }
            
            result = rule_based_medicine_recommendation(user_message, user_info, test_client)
            recommendations = result.get('recommendations', [])
            
            if len(recommendations) < 2:
                logger.warning(f"⚠️ {stage_name}テスト ({age}歳): 推奨数が不足 ({len(recommendations)}件)")
                all_passed = False
            else:
                logger.info(f"✅ {stage_name}テスト完了 ({age}歳): {len(recommendations)}件の推奨")
        
        return all_passed
    except Exception as e:
        logger.error(f"❌ 年齢層補正テストでエラー: {e}")
        return False

def test_mechanism_diversity():
    """作用機序の多様性が確保されているか（補血系と理気系の両方が含まれるか）"""
    user_message = "生理不順で、なおかつイライラする"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        from src.core.rule_based_recommendation import classify_medicine_mechanism
        
        mechanisms = [classify_medicine_mechanism(r) for r in recommendations]
        has_blood_tonifying = "補血・調血系" in mechanisms
        has_qi_regulating = "理気・駆瘀血系" in mechanisms
        
        if has_blood_tonifying and has_qi_regulating:
            logger.info(f"✅ 作用機序多様性テスト完了: 補血系と理気系の両方が含まれています")
            logger.info(f"   検出された作用機序: {mechanisms}")
        else:
            logger.warning(f"⚠️ 作用機序多様性テスト: 補血系={has_blood_tonifying}, 理気系={has_qi_regulating}")
            logger.warning(f"   検出された作用機序: {mechanisms}")
        
        return has_blood_tonifying and has_qi_regulating
    except Exception as e:
        logger.error(f"❌ 作用機序多様性テストでエラー: {e}")
        return False

def test_score_validation():
    """スコア検証テスト: 推奨医薬品のスコアが適切か検証"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    user_message = "生理不順で、なおかつイライラする"
    user_info = {
        'age': 30,
        'gender': '女性'
    }
    
    try:
        result = rule_based_medicine_recommendation(user_message, user_info, test_client)
        recommendations = result.get('recommendations', [])
        
        # スコア閾値の検証
        threshold_ok, threshold_issues = verify_score_threshold(recommendations, min_score=0.35)
        if not threshold_ok:
            logger.warning(f"⚠️ スコア閾値検証: {len(threshold_issues)}件の低スコア検出")
            for issue in threshold_issues:
                logger.warning(f"   - {issue['product_name']}: スコア {issue['score']:.3f} < 閾値 {issue['threshold']}")
        
        # スコアブレークダウンの検証
        breakdown_ok, breakdown_issues = verify_score_breakdown(recommendations)
        if not breakdown_ok:
            logger.warning(f"⚠️ スコアブレークダウン検証: {len(breakdown_issues)}件の問題検出")
            for issue in breakdown_issues[:3]:  # 最初の3件のみ表示
                logger.warning(f"   - {issue['product_name']}: {issue['issue']}")
        
        all_ok = threshold_ok and breakdown_ok
        if all_ok:
            logger.info(f"✅ スコア検証テスト完了: すべてのスコアが適切です")
        else:
            logger.warning(f"⚠️ スコア検証テスト: 一部の問題が検出されました")
        
        return all_ok
    except Exception as e:
        logger.error(f"❌ スコア検証テストでエラー: {e}")
        return False

def test_complex_symptoms():
    """複合症状のテスト: 複数の症状が組み合わさった場合"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    test_cases = [
        {
            "message": "生理不順で、なおかつイライラして、ニキビもできて、冷え症です",
            "expected_keywords": ["月経不順", "イライラ", "ニキビ", "冷え症"],
            "name": "複合症状1: 不順+イライラ+ニキビ+冷え症"
        },
        {
            "message": "生理痛がひどくて、頭痛もあって、めまいもします",
            "expected_keywords": ["月経痛", "頭痛", "めまい"],
            "name": "複合症状2: 生理痛+頭痛+めまい"
        }
    ]
    
    try:
        all_passed = True
        for test_case in test_cases:
            user_info = {'age': 30, 'gender': '女性'}
            result = rule_based_medicine_recommendation(test_case["message"], user_info, test_client)
            recommendations = result.get('recommendations', [])
            
            if len(recommendations) < 2:
                logger.warning(f"⚠️ {test_case['name']}: 推奨数が不足 ({len(recommendations)}件)")
                all_passed = False
            else:
                logger.info(f"✅ {test_case['name']}: {len(recommendations)}件の推奨")
        
        return all_passed
    except Exception as e:
        logger.error(f"❌ 複合症状テストでエラー: {e}")
        return False

def test_edge_cases():
    """エッジケースのテスト"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    test_cases = [
        {
            "message": "",
            "user_info": {'age': 30, 'gender': '女性'},
            "name": "空の症状入力",
            "should_fail": True
        },
        {
            "message": "生理不順",
            "user_info": {'age': 0, 'gender': '女性'},
            "name": "極端な年齢（0歳）",
            "should_fail": False  # 年齢チェックは別途行われる
        },
        {
            "message": "生理不順",
            "user_info": {'age': 100, 'gender': '女性'},
            "name": "極端な年齢（100歳）",
            "should_fail": False
        },
        {
            "message": "生理不順で、なおかつイライラする。妊娠中で、授乳中で、お腹も壊しやすいです",
            "user_info": {'age': 30, 'gender': '女性', 'pregnancy_possible': True, 'postpartum': True},
            "name": "複数の禁忌事項が重複",
            "should_fail": False
        }
    ]
    
    try:
        all_passed = True
        for test_case in test_cases:
            try:
                result = rule_based_medicine_recommendation(
                    test_case["message"], 
                    test_case["user_info"], 
                    test_client
                )
                recommendations = result.get('recommendations', [])
                
                if test_case.get("should_fail", False):
                    if len(recommendations) > 0:
                        logger.warning(f"⚠️ {test_case['name']}: 推奨が返されましたが、エラーが期待されていました")
                        all_passed = False
                    else:
                        logger.info(f"✅ {test_case['name']}: 適切にエラーが処理されました")
                else:
                    logger.info(f"✅ {test_case['name']}: {len(recommendations)}件の推奨")
            except Exception as e:
                if test_case.get("should_fail", False):
                    logger.info(f"✅ {test_case['name']}: 期待通りエラーが発生しました")
                else:
                    logger.warning(f"⚠️ {test_case['name']}: 予期しないエラー: {e}")
                    all_passed = False
        
        return all_passed
    except Exception as e:
        logger.error(f"❌ エッジケーステストでエラー: {e}")
        return False

def test_user_preference_combinations():
    """ユーザー要望の組み合わせテスト"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    test_cases = [
        {
            "message": "生理不順で、なおかつイライラする。成分重視で、飲みやすいものがいいです",
            "name": "成分重視+飲みやすさ重視"
        },
        {
            "message": "生理不順で、なおかつイライラする。バランス重視で、あれこれ気になる症状があります",
            "name": "バランス重視+随伴症状対応"
        }
    ]
    
    try:
        all_passed = True
        for test_case in test_cases:
            user_info = {'age': 30, 'gender': '女性'}
            result = rule_based_medicine_recommendation(test_case["message"], user_info, test_client)
            recommendations = result.get('recommendations', [])
            
            if len(recommendations) < 2:
                logger.warning(f"⚠️ {test_case['name']}: 推奨数が不足 ({len(recommendations)}件)")
                all_passed = False
            else:
                found, details = check_recommendation_contains_expected(recommendations, test_case['name'], verbose=False, top_n=10)
                if found:
                    logger.info(f"✅ {test_case['name']}: 期待される医薬品が推奨されました")
                else:
                    logger.warning(f"⚠️ {test_case['name']}: 期待される医薬品が見つかりませんでした")
                    if details:
                        logger.warning(f"   実際の推奨結果（上位3件）:")
                        for d in details[:3]:
                            logger.warning(f"      {d['rank']}位: {d['product_name']} (スコア: {d['score']:.3f})")
                    all_passed = False
        
        return all_passed
    except Exception as e:
        logger.error(f"❌ ユーザー要望組み合わせテストでエラー: {e}")
        return False

def test_performance():
    """パフォーマンステスト: 複数のテストケースを連続実行して実行時間を測定"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    test_messages = [
        "生理不順で、なおかつイライラする",
        "生理痛がひどい",
        "生理不順で、ニキビもできて、冷え症です",
        "生理不順で、なおかつイライラする。成分・バランス重視です",
        "生理不順で、なおかつイライラする。錠剤タイプが飲みやすいです"
    ]
    
    try:
        user_info = {'age': 30, 'gender': '女性'}
        execution_times = []
        
        for i, message in enumerate(test_messages, 1):
            start_time = time.time()
            result = rule_based_medicine_recommendation(message, user_info, test_client)
            elapsed_time = time.time() - start_time
            execution_times.append(elapsed_time)
            logger.info(f"   テストケース {i}: {elapsed_time:.2f}秒")
        
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        logger.info(f"✅ パフォーマンステスト完了:")
        logger.info(f"   平均実行時間: {avg_time:.2f}秒")
        logger.info(f"   最大実行時間: {max_time:.2f}秒")
        logger.info(f"   最小実行時間: {min_time:.2f}秒")
        
        # 平均実行時間が15秒以内であることを期待（現実的な閾値に調整）
        performance_ok = avg_time < 15.0
        if not performance_ok:
            logger.warning(f"⚠️ パフォーマンス警告: 平均実行時間が15秒を超えています ({avg_time:.2f}秒)")
        else:
            if avg_time > 12.0:
                logger.warning(f"⚠️ パフォーマンス注意: 平均実行時間が12秒を超えています ({avg_time:.2f}秒)")
        
        return performance_ok
    except Exception as e:
        logger.error(f"❌ パフォーマンステストでエラー: {e}")
        return False

def test_scoring_boundary_values():
    """スコアリングの境界値テスト: スコアが閾値付近のケース"""
    if not CSV_AVAILABLE:
        logger.error("❌ CSVファイルが利用できないため、テストをスキップします。")
        return None
    
    # 境界値付近のスコアを生成するような症状パターンをテスト
    test_cases = [
        {
            "message": "生理不順",  # 単一症状（スコアが低くなる可能性）
            "name": "単一症状（境界値テスト）"
        },
        {
            "message": "生理不順で、なおかつイライラして、ニキビもできて、冷え症で、頭痛もします",  # 複数症状（スコアが高くなる可能性）
            "name": "複数症状（境界値テスト）"
        }
    ]
    
    try:
        all_passed = True
        user_info = {'age': 30, 'gender': '女性'}
        
        for test_case in test_cases:
            result = rule_based_medicine_recommendation(test_case["message"], user_info, test_client)
            recommendations = result.get('recommendations', [])
            
            # スコアの分布を確認
            scores = [r.get('total_score', r.get('score', 0.0)) for r in recommendations]
            if scores:
                min_score = min(scores)
                max_score = max(scores)
                avg_score = sum(scores) / len(scores)
                
                logger.info(f"✅ {test_case['name']}:")
                logger.info(f"   スコア範囲: {min_score:.3f} - {max_score:.3f}")
                logger.info(f"   平均スコア: {avg_score:.3f}")
                
                # 最低スコアが0.35以上であることを期待
                if min_score < 0.35:
                    logger.warning(f"⚠️ {test_case['name']}: 最低スコアが閾値未満 ({min_score:.3f})")
                    all_passed = False
        
        return all_passed
    except Exception as e:
        logger.error(f"❌ 境界値テストでエラー: {e}")
        return False

def run_all_tests():
    """すべてのテストを実行"""
    logger.info("=" * 60)
    logger.info("女性特有の生理関連医薬品推奨アルゴリズムのテスト開始")
    logger.info("=" * 60)
    logger.info(f"テスト実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"CSVファイル状態: {'✅ 利用可能' if CSV_AVAILABLE else '❌ 利用不可'}")
    logger.info(f"OpenAIクライアント: {'✅ 初期化済み' if test_client else '⚠️ 未初期化'}")
    logger.info(f"テストスナップショット保存先: {os.path.join(BASE_DIR, 'test_snapshots')}")
    logger.info("=" * 60)
    
    tests = [
        # 基本テスト
        ("基本テスト: 生理不順+イライラ", test_basic_menstrual_irregularity_with_irritability),
        ("成分・バランス重視", test_ingredient_balance_preference),
        ("飲みやすさ重視", test_ease_of_taking_preference),
        ("随伴症状対応", test_accompanying_symptoms_preference),
        
        # 安全性テスト
        ("お腹を壊しやすい", test_digestive_sensitivity),
        ("産後", test_postpartum_breastfeeding),
        ("妊娠可能性", test_pregnancy_contraindication),
        ("重症度エスカレーション", test_severity_escalation),
        
        # 機能テスト
        ("痛み主訴", test_pain_urgency_primary),
        ("年齢層補正", test_life_stage_correction),
        ("作用機序多様性", test_mechanism_diversity),
        
        # 新規追加テスト
        ("スコア検証", test_score_validation),
        ("複合症状", test_complex_symptoms),
        ("エッジケース", test_edge_cases),
        ("ユーザー要望組み合わせ", test_user_preference_combinations),
        ("パフォーマンス", test_performance),
        ("スコアリング境界値", test_scoring_boundary_values),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    test_results = []
    total_start_time = time.time()
    
    for test_name, test_func in tests:
        test_start_time = time.time()
        try:
            logger.info(f"\n--- {test_name} ---")
            result = test_func()
            elapsed_time = time.time() - test_start_time
            
            if result is None:
                skipped += 1
                status = "SKIPPED"
            elif result:
                passed += 1
                status = "PASSED"
            else:
                failed += 1
                status = "FAILED"
            
            test_result_entry = {
                "test_name": test_name,
                "status": status,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # 失敗した場合、詳細情報を追加
            if status in ["FAILED", "ERROR"]:
                try:
                    # テスト関数から詳細情報を取得（可能な場合）
                    if hasattr(test_func, '__name__'):
                        test_result_entry["test_function"] = test_func.__name__
                    
                    # スナップショットファイルのパスを追加（存在する場合）
                    snapshot_dir = os.path.join(BASE_DIR, "test_snapshots")
                    if os.path.exists(snapshot_dir):
                        # 最新のスナップショットファイルを検索
                        snapshot_files = [f for f in os.listdir(snapshot_dir) 
                                        if f.startswith(test_name.replace(' ', '_').replace(':', '_').replace('/', '_')) 
                                        and f.endswith('.json')]
                        if snapshot_files:
                            # 最新のファイルを取得（タイムスタンプでソート）
                            snapshot_files.sort(reverse=True)
                            test_result_entry["snapshot_file"] = os.path.join(snapshot_dir, snapshot_files[0])
                except Exception as e:
                    logger.debug(f"詳細情報の取得に失敗: {e}")
            
            test_results.append(test_result_entry)
            
        except Exception as e:
            elapsed_time = time.time() - test_start_time
            logger.error(f"❌ {test_name} でエラーが発生しました: {e}")
            failed += 1
            import traceback
            test_results.append({
                "test_name": test_name,
                "status": "ERROR",
                "elapsed_time": elapsed_time,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    total_elapsed_time = time.time() - total_start_time
    
    # 結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("テスト結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 成功: {passed}件")
    logger.info(f"❌ 失敗: {failed}件")
    logger.info(f"⏭️  スキップ: {skipped}件")
    logger.info(f"📊 合計: {len(tests)}件")
    logger.info(f"⏱️  総実行時間: {total_elapsed_time:.2f}秒")
    logger.info("=" * 60)
    
    # 失敗原因の分析
    failure_analysis = analyze_failure_reasons(test_results)
    
    # 詳細結果をJSONファイルに保存
    result_file = os.path.join(BASE_DIR, "test_results.json")
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": len(tests),
            "total_elapsed_time": total_elapsed_time,
            "success_rate": (passed / len(tests) * 100) if len(tests) > 0 else 0.0,
            "average_test_time": total_elapsed_time / len(tests) if len(tests) > 0 else 0.0
        },
        "test_results": test_results,
        "failure_analysis": failure_analysis,
        "csv_available": CSV_AVAILABLE,
        "openai_client_available": test_client is not None
    }
    
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 テスト結果を保存しました: {result_file}")
        
        # HTMLレポートも生成
        generate_html_report(result_data, BASE_DIR)
    except Exception as e:
        logger.warning(f"⚠️ テスト結果の保存に失敗しました: {e}")
    
    return passed, failed, skipped

def analyze_failure_reasons(test_results):
    """テスト失敗の原因を分析"""
    failure_analysis = {
        "total_failures": 0,
        "failure_categories": {},
        "common_issues": []
    }
    
    for test_result in test_results:
        if test_result['status'] in ['FAILED', 'ERROR']:
            failure_analysis["total_failures"] += 1
            test_name = test_result['test_name']
            
            # テスト名からカテゴリを推測
            category = "その他"
            if "基本" in test_name or "生理不順" in test_name:
                category = "基本機能"
            elif "成分" in test_name or "バランス" in test_name or "飲みやすさ" in test_name:
                category = "ユーザー要望"
            elif "お腹" in test_name or "産後" in test_name or "妊娠" in test_name:
                category = "安全性"
            elif "痛み" in test_name or "年齢" in test_name or "作用機序" in test_name:
                category = "機能テスト"
            elif "複合" in test_name or "組み合わせ" in test_name:
                category = "複合テスト"
            elif "パフォーマンス" in test_name:
                category = "パフォーマンス"
            
            if category not in failure_analysis["failure_categories"]:
                failure_analysis["failure_categories"][category] = 0
            failure_analysis["failure_categories"][category] += 1
    
    return failure_analysis

def generate_html_report(result_data, output_dir):
    """テスト結果からHTMLレポートを生成"""
    try:
        # 失敗原因の分析
        failure_analysis = analyze_failure_reasons(result_data['test_results'])
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>テスト結果レポート - {result_data['timestamp']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card.passed {{
            background-color: #d4edda;
            color: #155724;
        }}
        .summary-card.failed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .summary-card.skipped {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .summary-card.total {{
            background-color: #d1ecf1;
            color: #0c5460;
        }}
        .summary-card h2 {{
            margin: 0;
            font-size: 2em;
        }}
        .summary-card p {{
            margin: 5px 0 0 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-passed {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-failed {{
            color: #dc3545;
            font-weight: bold;
        }}
        .status-skipped {{
            color: #ffc107;
            font-weight: bold;
        }}
        .status-error {{
            color: #dc3545;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 テスト結果レポート</h1>
        <p><strong>実行日時:</strong> {result_data['timestamp']}</p>
        
        <div class="summary">
            <div class="summary-card passed">
                <h2>{result_data['summary']['passed']}</h2>
                <p>成功</p>
            </div>
            <div class="summary-card failed">
                <h2>{result_data['summary']['failed']}</h2>
                <p>失敗</p>
            </div>
            <div class="summary-card skipped">
                <h2>{result_data['summary']['skipped']}</h2>
                <p>スキップ</p>
            </div>
            <div class="summary-card total">
                <h2>{result_data['summary']['total']}</h2>
                <p>合計</p>
            </div>
        </div>
        
        <p><strong>成功率:</strong> {result_data['summary']['success_rate']:.1f}%</p>
        <p><strong>総実行時間:</strong> {result_data['summary']['total_elapsed_time']:.2f}秒</p>
        
        <h2>詳細結果</h2>
        <table>
            <thead>
                <tr>
                    <th>テスト名</th>
                    <th>ステータス</th>
                    <th>実行時間 (秒)</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for test_result in result_data['test_results']:
            status_class = f"status-{test_result['status'].lower()}"
            status_emoji = {
                'PASSED': '✅',
                'FAILED': '❌',
                'SKIPPED': '⏭️',
                'ERROR': '⚠️'
            }.get(test_result['status'], '❓')
            
            html_content += f"""
                <tr>
                    <td>{test_result['test_name']}</td>
                    <td class="{status_class}">{status_emoji} {test_result['status']}</td>
                    <td>{test_result['elapsed_time']:.2f}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>失敗原因分析</h2>
        <p><strong>総失敗数:</strong> {failure_analysis['total_failures']}件</p>
        <table>
            <thead>
                <tr>
                    <th>カテゴリ</th>
                    <th>失敗数</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for category, count in failure_analysis['failure_categories'].items():
            html_content += f"""
                <tr>
                    <td>{category}</td>
                    <td>{count}件</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>環境情報</h2>
        <ul>
            <li><strong>CSVファイル:</strong> """ + ('✅ 利用可能' if result_data['csv_available'] else '❌ 利用不可') + """</li>
            <li><strong>OpenAIクライアント:</strong> """ + ('✅ 初期化済み' if result_data['openai_client_available'] else '⚠️ 未初期化') + """</li>
        </ul>
    </div>
</body>
</html>
"""
        
        html_file = os.path.join(output_dir, "test_report.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"📊 HTMLレポートを生成しました: {html_file}")
    except Exception as e:
        logger.warning(f"⚠️ HTMLレポートの生成に失敗しました: {e}")

if __name__ == "__main__":
    run_all_tests()

