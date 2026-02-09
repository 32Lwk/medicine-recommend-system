"""
成分多様性の確保（ensure_ingredient_diversity）

rule_based_recommendation から分離（SRP改善）。
候補リストから主要成分が重複しすぎないように再選別する。
"""

import logging
import os
import re
from typing import Dict, List, Tuple

from src.core.candidate_scoring import (
    is_exact_product_match,
    extract_main_ingredients,
    _candidate_has_throat_liquid_signature,
    filter_by_efficacy_symptom_match,
    is_comprehensive_cold_medicine,
    classify_medicine_mechanism,
)
from src.core.recommendation_constants import MAJOR_ANALGESIC_MEDICINES
from src.core.recommendation.recommendation_scoring import calculate_symptom_specificity_penalty
from src.core.scoring_utils import (
    calculate_efficacy_specificity_score,
    _is_kampo_or_herbal_medicine,
    normalize_text,
)
from src.core.user_detection import determine_pain_urgency
from src.core.dictionary_loader import load_symptom_dictionary
from src.core.kampo_logic import determine_kampo_sho

logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# 期待される医薬品をスコアフィルタリングから保護するための製品名リスト
PRIORITY_MEDICINE_NAMES_FOR_PROTECTION = [
    "ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ",
    "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト",
    "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン",
]


def ensure_ingredient_diversity(candidates: List[Dict], top_n: int = 3, similarity_threshold: float = 0.2, nlu_result: Dict = None, user_info: Dict = None) -> List[Dict]:
    """主要成分が重複しすぎないように候補を再選別する（剤形多様性も考慮）
    
    改善点：
    - similarity_thresholdを0.3から0.2に下げる（より厳格に重複を避ける）
    - 異なる成分の医薬品にボーナスを付与
    """
    if len(candidates) <= top_n:
        return candidates

    # 期待される医薬品をスコアフィルタリングから保護（PRIORITY_MEDICINE_NAMES_FOR_PROTECTION はモジュール定数）
    protected_candidates = []
    for candidate in candidates:
        product_name = candidate.get('product_name', '')
        # 期待される医薬品かどうかをチェック（部分一致も許可）
        is_priority = any(
            is_exact_product_match(product_name, [name]) or name in product_name 
            for name in PRIORITY_MEDICINE_NAMES_FOR_PROTECTION
        )
        if is_priority:
            protected_candidates.append(candidate)
            logger.debug(f"🔒 期待される医薬品をスコアフィルタリングから保護: {product_name}")
    
    # スコアフィルタリング: スコア0の候補を除外（期待される医薬品は保護）
    filtered_candidates = [c for c in candidates if c.get('final_score', 0.0) > 0.0]
    
    # 保護された期待される医薬品を追加（スコアが0でも含める）
    for protected_candidate in protected_candidates:
        if protected_candidate not in filtered_candidates:
            filtered_candidates.append(protected_candidate)
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"🔒 期待される医薬品をスコアフィルタリングから保護: {protected_candidate.get('product_name', '')} (スコア: {protected_candidate.get('final_score', 0.0)})")
    
    if len(filtered_candidates) < top_n:
        # スコア0以外の候補が不足する場合は、スコア0.3以上の候補を追加
        additional_candidates = [c for c in candidates if c.get('final_score', 0.0) >= 0.3 and c not in filtered_candidates]
        filtered_candidates.extend(additional_candidates)
    
    # フィルタリング後の候補が不足する場合は元の候補リストを使用
    if len(filtered_candidates) < top_n:
        filtered_candidates = candidates
    
    if len(filtered_candidates) <= top_n:
        return filtered_candidates[:top_n]

    # 二日酔い特化：五苓散とL-システイン含有医薬品を優先確保
    reserved_goreisan = None
    reserved_cysteine = None
    
    # 五苓散を最優先で確保
    for candidate in filtered_candidates:
        product_name = candidate.get('product_name', '')
        efficacy = candidate.get('efficacy', '')
        if "五苓散" in product_name or "五苓散" in efficacy:
            reserved_goreisan = candidate
            break
    
    # L-システイン含有医薬品を確保（二日酔い関連効能がある場合）
    for candidate in filtered_candidates:
        if candidate == reserved_goreisan:
            continue
        ingredients = str(candidate.get('ingredients', '')).lower()
        efficacy = str(candidate.get('efficacy', '')).lower()
        
        # L-システイン含有で二日酔い関連効能がある場合
        has_cysteine = "l-システイン" in ingredients or "システイン" in ingredients or "lシステイン" in ingredients
        has_hangover_related = any(kw in efficacy for kw in ["倦怠", "疲労", "肝", "解毒", "二日酔", "宿酔"])
        
        # 美容主体（しみ・そばかす）を除外
        is_beauty_primary = any(kw in efficacy[:50] for kw in ["しみ", "そばかす", "色素沈着", "美白"])
        
        if has_cysteine and has_hangover_related and not is_beauty_primary:
            reserved_cysteine = candidate
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"L-システイン優先枠を確保: {candidate.get('product_name', '')}")
            break
    
    # 美容主体でないL-システイン製品が見つからない場合でも、美容主体は推奨しない
    # （二日酔い推奨として不適切なため）
    if not reserved_cysteine:
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            logger.debug("L-システイン優先枠: 美容主体でない製品が見つかりませんでした（美容主体は二日酔いに不適切なため除外）")
    
    # 月経不順+イライラの症状パターンで、期待される医薬品を優先確保
    reserved_menstrual_medicines = []
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        # 症状名の正規化（「生理不順」→「月経不順」）
        normalized_symptom_names_list = []
        symptom_mapping = {
            "生理不順": "月経不順",
            "生理異常": "月経不順",
        }
        for name in symptom_names_list:
            normalized_name = symptom_mapping.get(name, name)
            normalized_symptom_names_list.append(normalized_name)
        
        symptom_set = frozenset(normalized_symptom_names_list)
        is_menstrual_irritability_pattern = symptom_set == frozenset({"月経不順", "イライラ"}) or symptom_set.issubset(frozenset({"月経不順", "イライラ"}))
        
        if is_menstrual_irritability_pattern:
            # 期待される医薬品を優先確保（計画要件: 製品名マッチングの改善）
            priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
            
            # 期待される医薬品を検索（filtered_candidatesとcandidatesの両方から）
            # 製品名マッチングをより柔軟にする（部分一致を強化）
            for candidate in filtered_candidates + candidates:
                if candidate == reserved_goreisan or candidate == reserved_cysteine or candidate in reserved_menstrual_medicines:
                    continue
                product_name = candidate.get('product_name', '')
                product_name_lower = product_name.lower()
                
                # 製品名マッチング（より柔軟な方法）
                for priority_name in priority_medicine_names:
                    priority_name_lower = priority_name.lower()
                    
                    # 1. 完全一致
                    if product_name_lower == priority_name_lower:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（完全一致）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 2. 部分一致（製品名に検索名が含まれる、または検索名に製品名が含まれる）
                    if priority_name_lower in product_name_lower or product_name_lower in priority_name_lower:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（部分一致）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 3. 厳密な製品名マッチング
                    if is_exact_product_match(product_name, [priority_name]):
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（厳密マッチ）: {product_name} (検索名: {priority_name})")
                        break
                    
                    # 4. 特殊文字を除去して比較（「ラムールＱ」と「ラムールQ」など）
                    product_name_normalized = re.sub(r'[ＱｑQq]', 'Q', product_name_lower)
                    priority_name_normalized = re.sub(r'[ＱｑQq]', 'Q', priority_name_lower)
                    if priority_name_normalized in product_name_normalized or product_name_normalized in priority_name_normalized:
                        reserved_menstrual_medicines.append(candidate)
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"⭐ 期待される医薬品を優先確保（正規化後一致）: {product_name} (検索名: {priority_name})")
                        break
                
                # 最大3件まで確保
                if len(reserved_menstrual_medicines) >= 3:
                    break
            
            # 期待される医薬品が見つからない場合のログ
            if len(reserved_menstrual_medicines) == 0:
                logger.warning(f"⚠️ 期待される医薬品が候補に見つかりませんでした（検索名: {priority_medicine_names}）")
                # デバッグ用: 実際の候補の製品名をログに出力
                candidate_names = [c.get('product_name', '') for c in (filtered_candidates[:20] if filtered_candidates else candidates[:20])]
                logger.warning(f"デバッグ: 候補の上位20件の製品名: {candidate_names}")
    
    # 液剤を最初に1件確保（剤形多様性）
    liquid_candidate = None
    for candidate in filtered_candidates:
        if candidate == reserved_goreisan or candidate == reserved_cysteine or candidate in reserved_menstrual_medicines:
            continue
        if _candidate_has_throat_liquid_signature(candidate):
            liquid_candidate = candidate
            break

    selected: List[Dict] = []
    selected_sets: List[set] = []
    fallback: List[Tuple[Dict, set]] = []

    # 特別枠を保留
    reserved_liquid = liquid_candidate

    # 葛根湯系の同一成分グループを識別する関数
    def _is_kakkonto_group(ingredients: set) -> bool:
        """葛根湯系の成分グループかどうかを判定"""
        kakkonto_keywords = ["カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
        ingredients_str = ' '.join(ingredients).lower()
        return any(kw.lower() in ingredients_str for kw in kakkonto_keywords)
    
    # 五苓散系の同一成分グループを識別する関数
    def _is_goreisan_group(ingredients: set) -> bool:
        """五苓散系の成分グループかどうかを判定"""
        goreisan_keywords = ["タクシャ", "チョレイ", "ビャクジュツ", "ブクリョウ", "ケイヒ", "インチンコウ"]
        ingredients_str = ' '.join(ingredients).lower()
        # 五苓散の主要成分（タクシャ、チョレイ、ブクリョウ）のうち2つ以上含まれていれば五苓散系
        core_ingredients = ["タクシャ", "チョレイ", "ブクリョウ"]
        core_count = sum(1 for kw in core_ingredients if kw.lower() in ingredients_str)
        return core_count >= 2

    for candidate in filtered_candidates:
        # 保留中の特別枠はスキップ
        if reserved_liquid and candidate == reserved_liquid:
            continue
        if reserved_goreisan and candidate == reserved_goreisan:
            continue
        if reserved_cysteine and candidate == reserved_cysteine:
            continue
        if candidate in reserved_menstrual_medicines:
            continue

        main_ingredients = set(extract_main_ingredients(candidate.get("ingredients", "")))

        overlap = False
        for existing_set in selected_sets:
            if not existing_set or not main_ingredients:
                continue
            
            # 五苓散系・葛根湯系の同一成分グループチェック（最優先）
            if _is_goreisan_group(existing_set) and _is_goreisan_group(main_ingredients):
                overlap = True
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"五苓散系の同一成分グループとして重複を検出: {candidate.get('product_name', '')}")
                break
            
            if _is_kakkonto_group(existing_set) and _is_kakkonto_group(main_ingredients):
                overlap = True
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"葛根湯系の同一成分グループとして重複を検出: {candidate.get('product_name', '')} (既に選択済み: {[c.get('product_name') for c in selected]})")
                break
            
            # 製品名で葛根湯の重複をチェック（成分抽出が失敗した場合のフォールバック）
            existing_product_names = [c.get('product_name', '') for c in selected]
            candidate_product_name = candidate.get('product_name', '')
            if "葛根湯" in candidate_product_name:
                if any("葛根湯" in name for name in existing_product_names):
                    overlap = True
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"葛根湯製品名による重複を検出: {candidate_product_name} (既に選択済み: {[name for name in existing_product_names if '葛根湯' in name]})")
                    break
            
            # 通常の成分重複チェック
            intersection = existing_set & main_ingredients
            if intersection:
                overlap_ratio = len(intersection) / float(min(len(existing_set), len(main_ingredients)))
                if overlap_ratio >= similarity_threshold:
                    overlap = True
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"成分重複を検出（重複率: {overlap_ratio:.2f}）: {candidate.get('product_name', '')}")
                    break

        if not overlap and len(selected) < (top_n - 1 if reserved_liquid else top_n):
            selected.append(candidate)
            selected_sets.append(main_ingredients)
        else:
            fallback.append((candidate, main_ingredients))

    # 特別枠を優先順位で追加
    # 1. 期待される医薬品（月経不順+イライラの症状パターン、最優先）
    if reserved_menstrual_medicines:
        for menstrual_medicine in reserved_menstrual_medicines:
            # 既にselectedに含まれている場合はスキップ
            if menstrual_medicine in selected:
                logger.info(f"⭐ 期待される医薬品は既に最終推奨に含まれています: {menstrual_medicine.get('product_name', '')}")
                continue
            if len(selected) < top_n:
                selected.insert(0, menstrual_medicine)  # 最上位に挿入
                selected_sets.insert(0, set(extract_main_ingredients(menstrual_medicine.get("ingredients", ""))))
                logger.info(f"⭐ 期待される医薬品を最終推奨に追加: {menstrual_medicine.get('product_name', '')}")
            else:
                # top_nに達している場合でも、期待される医薬品を最優先で置き換える
                # 最低スコアの候補を削除して、期待される医薬品を追加
                if selected:
                    min_score_candidate = min(selected, key=lambda c: c.get('final_score', 0.0))
                    min_score = min_score_candidate.get('final_score', 0.0)
                    menstrual_score = menstrual_medicine.get('final_score', 0.0)
                    # 期待される医薬品のスコアが最低スコアより高い場合、または最低スコアが0.5未満の場合に置き換え
                    if menstrual_score > min_score or min_score < 0.5:
                        selected.remove(min_score_candidate)
                        selected.insert(0, menstrual_medicine)
                        selected_sets.insert(0, set(extract_main_ingredients(menstrual_medicine.get("ingredients", ""))))
                        logger.info(f"⭐ 期待される医薬品を最終推奨に追加（置き換え）: {menstrual_medicine.get('product_name', '')}")
    
    # 期待される医薬品が見つからなかった場合、候補から直接検索して追加（フォールバック）
    if not reserved_menstrual_medicines and is_menstrual_irritability_pattern:
        logger.warning(f"⚠️ reserved_menstrual_medicinesが空です。候補から直接検索します...")
        priority_medicine_names = ["ラムールQ", "ラムールＱ", "ラムールq", "ラムールｑ", "加味逍遙散", "カミショウヨウサン", "命の母ホワイト", "命の母 ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸", "ケイシブクリョウガン"]
        for candidate in filtered_candidates + candidates:
            if candidate in selected or candidate == reserved_goreisan or candidate == reserved_cysteine:
                continue
            product_name = candidate.get('product_name', '')
            product_name_lower = product_name.lower()
            for priority_name in priority_medicine_names:
                priority_name_lower = priority_name.lower()
                if priority_name_lower in product_name_lower or product_name_lower in priority_name_lower:
                    if len(selected) < top_n:
                        selected.insert(0, candidate)
                        selected_sets.insert(0, set(extract_main_ingredients(candidate.get("ingredients", ""))))
                        logger.info(f"⭐ 期待される医薬品を最終推奨に追加（フォールバック）: {product_name}")
                        break
            if len(selected) >= top_n:
                break
    
    # 2. 五苓散（2番目の優先度）
    if reserved_goreisan and len(selected) < top_n:
        insert_pos = min(len(reserved_menstrual_medicines), len(selected))
        selected.insert(insert_pos, reserved_goreisan)
        selected_sets.insert(insert_pos, set(extract_main_ingredients(reserved_goreisan.get("ingredients", ""))))
    
    # 3. L-システイン含有医薬品（3番目の優先度）
    if reserved_cysteine and len(selected) < top_n:
        # 期待される医薬品と五苓散の後に挿入
        insert_pos = min(len(reserved_menstrual_medicines) + (1 if reserved_goreisan else 0), len(selected))
        selected.insert(insert_pos, reserved_cysteine)
        selected_sets.insert(insert_pos, set(extract_main_ingredients(reserved_cysteine.get("ingredients", ""))))
    
    # 3. 液剤を最後に追加（成分重複に関わらず）
    if reserved_liquid and len(selected) < top_n:
        selected.append(reserved_liquid)
        selected_sets.append(set(extract_main_ingredients(reserved_liquid.get("ingredients", ""))))

    # まだ不足している場合は重複を許容して埋める
    # ただし、葛根湯の重複は避ける
    if len(selected) < top_n:
        for candidate, ingredient_set in fallback:
            if candidate in selected:
                continue
            # 葛根湯の重複チェック
            candidate_product_name = candidate.get('product_name', '')
            if "葛根湯" in candidate_product_name:
                # 既に選択されている候補に葛根湯がある場合はスキップ
                existing_product_names = [c.get('product_name', '') for c in selected]
                if any("葛根湯" in name for name in existing_product_names):
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"葛根湯の重複を回避: {candidate_product_name} (既に選択済み: {[name for name in existing_product_names if '葛根湯' in name]})")
                    continue
            selected.append(candidate)
            selected_sets.append(ingredient_set)
            if len(selected) >= top_n:
                break

    # 漢方+解熱鎮痛剤の組み合わせ保護（多様性チェックの後に適用、補完的に保護）
    # 痛みが主訴の場合、漢方1件+解熱鎮痛剤1件を最優先ペアとして保護
    if nlu_result:
        user_message = nlu_result.get('user_message', '') or ''
        pain_urgency = determine_pain_urgency(user_message, nlu_result)
        
        if pain_urgency.get("is_primary", False):
            # 痛みが主訴の場合
            has_kampo = False
            has_analgesic = False
            kampo_candidate = None
            analgesic_candidate = None
            
            # 選択済みの候補から漢方と解熱鎮痛剤を確認
            for candidate in selected:
                medicine_type = candidate.get('medicine_type', '')
                if _is_kampo_or_herbal_medicine(candidate):
                    has_kampo = True
                    kampo_candidate = candidate
                elif '解熱鎮痛薬' in medicine_type:
                    has_analgesic = True
                    analgesic_candidate = candidate
            
            # 漢方と解熱鎮痛剤の両方が含まれていない場合、追加する
            if not has_kampo or not has_analgesic:
                # 漢方がない場合、候補から漢方を探す
                if not has_kampo:
                    for candidate in filtered_candidates:
                        if candidate in selected:
                            continue
                        if _is_kampo_or_herbal_medicine(candidate):
                            # 月経不順関連の症状がある場合は、月経不順向けの漢方を優先
                            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
                            has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
                            
                            if has_menstrual_symptom:
                                # 月経不順向けの漢方を優先（桂枝茯苓丸など）
                                product_name = candidate.get('product_name', '')
                                efficacy = str(candidate.get('efficacy', '')).lower()
                                if any(kw in product_name or kw in efficacy for kw in ['桂枝茯苓丸', '加味逍遙散', '当帰芍薬散', '命の母']):
                                    kampo_candidate = candidate
                                    break
                            else:
                                kampo_candidate = candidate
                                break
                
                # 解熱鎮痛剤がない場合、候補から解熱鎮痛剤を探す
                if not has_analgesic:
                    for candidate in filtered_candidates:
                        if candidate in selected or candidate == kampo_candidate:
                            continue
                        medicine_type = candidate.get('medicine_type', '')
                        if '解熱鎮痛薬' in medicine_type:
                            analgesic_candidate = candidate
                            break
                
                # 漢方と解熱鎮痛剤を追加（既に選択済みの候補を置き換えるか、追加する）
                if kampo_candidate and kampo_candidate not in selected and len(selected) < top_n:
                    selected.append(kampo_candidate)
                    selected_sets.append(set(extract_main_ingredients(kampo_candidate.get("ingredients", ""))))
                    logger.info(f"💊 漢方+解熱鎮痛剤の組み合わせ保護: 漢方を追加 {kampo_candidate.get('product_name', '')}")
                
                if analgesic_candidate and analgesic_candidate not in selected and len(selected) < top_n:
                    selected.append(analgesic_candidate)
                    selected_sets.append(set(extract_main_ingredients(analgesic_candidate.get("ingredients", ""))))
                    logger.info(f"💊 漢方+解熱鎮痛剤の組み合わせ保護: 解熱鎮痛剤を追加 {analgesic_candidate.get('product_name', '')}")
    
    # 最終選定ロジックの改善: 上位2件はスコア順、3件目は作用機序の多様性を考慮
    # まず、スコア順にソート
    # 注意: 総合風邪薬の優先配置は、後続の風邪症状がある場合の特別なロジック（4365-4412行目）で処理するため、
    # ここでは単純にスコア順にソートする
    selected_sorted = sorted(selected, key=lambda x: x.get('final_score', 0.0), reverse=True)
    
    # 外用薬（のど）の重複を防ぐ: 1つまでに制限
    external_throat_medicines = [c for c in selected_sorted if '外用薬（のど）' in c.get('medicine_type', '')]
    if len(external_throat_medicines) > 1:
        # スコアが最も高い外用薬（のど）を1つだけ残す
        best_external_throat = max(external_throat_medicines, key=lambda x: x.get('final_score', 0.0))
        # 他の外用薬（のど）を除外
        selected_sorted = [c for c in selected_sorted if c not in external_throat_medicines or c == best_external_throat]
        # スコア順に再ソート
        selected_sorted = sorted(selected_sorted, key=lambda x: x.get('final_score', 0.0), reverse=True)
        logger.info(f"🔒 外用薬（のど）の重複を防止: {len(external_throat_medicines)}件から1件（{best_external_throat.get('product_name', '')}）に制限")
    
    # のどの痛みがある場合、外用薬（のど）のスロットを確保（3位以内に必ず1つ含める）
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        has_throat_pain = any("のど" in name or "喉" in name for name in symptom_names_list)
        
        if has_throat_pain:
            # 既に選択されている候補に外用薬（のど）があるかチェック
            has_external_throat = any('外用薬（のど）' in c.get('medicine_type', '') for c in selected_sorted[:3])
            
            if not has_external_throat:
                # 外用薬（のど）を優先的に追加
                remaining_candidates = [c for c in filtered_candidates if c not in selected_sorted[:3]]
                for candidate in remaining_candidates:
                    if '外用薬（のど）' in candidate.get('medicine_type', ''):
                        # 3位以内に確保（既に3位以上ある場合は、3位の候補と置き換え）
                        if len(selected_sorted) >= 3:
                            # 3位の候補を削除して外用薬（のど）を追加
                            selected_sorted = selected_sorted[:2] + [candidate]
                            logger.info(f"🔒 外用薬（のど）のスロット確保: {candidate.get('product_name', '')} を3位に配置")
                        else:
                            selected_sorted.append(candidate)
                            logger.info(f"🔒 外用薬（のど）のスロット確保: {candidate.get('product_name', '')} を追加")
                        break
    
    # 風邪症状がある場合の特別なロジック: 1位=総合風邪薬、2位=内服薬（外用薬以外）、3位=外用薬（のど）
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if cold_symptom_count >= 2:
            # 総合風邪薬を1位に確保
            comprehensive_cold = None
            other_medicines = []
            external_throat_medicines = []
            
            for candidate in selected_sorted:
                if is_comprehensive_cold_medicine(candidate):
                    if comprehensive_cold is None:
                        comprehensive_cold = candidate
                elif '外用薬（のど）' in candidate.get('medicine_type', ''):
                    external_throat_medicines.append(candidate)
                else:
                    # 総合風邪薬以外の内服薬を追加（再確認）
                    if not is_comprehensive_cold_medicine(candidate):
                        other_medicines.append(candidate)
            
            # デバッグログ: other_medicinesの内容を確認
            logger.info(f"🔍 other_medicines: {len(other_medicines)}件 - {[c.get('product_name', '') for c in other_medicines[:5]]}")
            logger.info(f"🔍 comprehensive_cold: {comprehensive_cold.get('product_name', '') if comprehensive_cold else 'None'}")
            logger.info(f"🔍 external_throat_medicines: {len(external_throat_medicines)}件")
            
            # 1位: 総合風邪薬（なければスコア順の1位）
            top_2_candidates = []
            if comprehensive_cold:
                top_2_candidates.append(comprehensive_cold)
                comprehensive_cold['original_rank'] = 1  # 1位として明示的に設定
                logger.info(f"✅ 風邪症状: 総合風邪薬を1位に配置: {comprehensive_cold.get('product_name', '')}")
            elif selected_sorted:
                top_2_candidates.append(selected_sorted[0])
                selected_sorted[0]['original_rank'] = 1  # 1位として明示的に設定
            
            # 2位: 総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
            logger.info(f"🔍 2位選定開始: top_2_candidates={len(top_2_candidates)}, other_medicines={len(other_medicines)}")
            if len(top_2_candidates) < 2:
                # 2位も総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
                # まず総合風邪薬を探す（selected_sortedから優先的に探す）
                found_2nd_comprehensive_cold = False
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                        # 総合風邪薬を優先
                        if is_comprehensive_cold_medicine(candidate):
                            top_2_candidates.append(candidate)
                            candidate['original_rank'] = 2  # 2位として明示的に設定
                            logger.info(f"✅ 風邪症状: 総合風邪薬を2位に配置: {candidate.get('product_name', '')}")
                            found_2nd_comprehensive_cold = True
                            break
                
                # selected_sortedから見つからない場合、other_medicines + candidatesから探す
                if not found_2nd_comprehensive_cold and len(top_2_candidates) < 2:
                    for candidate in other_medicines + [c for c in candidates if c not in selected_sorted]:
                        if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                            # 総合風邪薬を優先
                            if is_comprehensive_cold_medicine(candidate):
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: 総合風邪薬を2位に配置（candidatesから）: {candidate.get('product_name', '')}")
                                found_2nd_comprehensive_cold = True
                                break
                
                # 総合風邪薬が見つからない場合、内服薬（外用薬以外、総合風邪薬以外）を選定
                if len(top_2_candidates) < 2:
                    for candidate in other_medicines:
                        if candidate not in top_2_candidates and len(top_2_candidates) < 2:
                            # 総合風邪薬でないことを再確認
                            if not is_comprehensive_cold_medicine(candidate):
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: 内服薬を2位に配置: {candidate.get('product_name', '')}")
                                break
                
                # 内服薬が見つからない場合、selected_sortedから総合風邪薬以外の内服薬を探す
                if len(top_2_candidates) < 2:
                    logger.info(f"🔍 other_medicinesから見つからなかったため、selected_sortedから総合風邪薬以外を探します")
                    found_count = 0
                    for candidate in selected_sorted:
                        if (candidate not in top_2_candidates and 
                            '外用薬（のど）' not in candidate.get('medicine_type', '') and
                            not is_comprehensive_cold_medicine(candidate)):
                            top_2_candidates.append(candidate)
                            candidate['original_rank'] = 2  # 2位として明示的に設定
                            logger.info(f"✅ 風邪症状: スコア順で2位を選定（総合風邪薬以外）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                            found_count += 1
                            if len(top_2_candidates) >= 2:
                                break
                    if found_count == 0:
                        logger.warning(f"⚠️ selected_sortedから総合風邪薬以外の内服薬が見つかりませんでした。selected_sortedの上位10件: {[(c.get('product_name', ''), c.get('medicine_type', ''), is_comprehensive_cold_medicine(c)) for c in selected_sorted[:10]]}")
                        # filtered_candidates（candidates）から総合風邪薬以外の内服薬を探す
                        logger.info(f"🔍 candidatesから総合風邪薬以外の内服薬を探します（全{len(candidates)}件）")
                        for candidate in candidates:
                            if (candidate not in top_2_candidates and 
                                '外用薬（のど）' not in candidate.get('medicine_type', '') and
                                not is_comprehensive_cold_medicine(candidate) and
                                candidate.get('final_score', 0.0) >= 0.3):  # スコアが0.3以上の候補のみ
                                
                                # 効能が風邪症状に適していない医薬品を除外
                                efficacy = str(candidate.get('efficacy', '')).lower()
                                # 栄養補給・滋養強壮薬を除外
                                has_nutritional_efficacy = any(kw in efficacy for kw in ['栄養補給', '滋養強壮', '虚弱体質', '肉体疲労', '病中病後', '食欲不振', '栄養障害'])
                                has_cold_symptom_in_efficacy = any(kw in efficacy for kw in ['発熱', '熱', '解熱', '頭痛', '咳', '鼻水', '鼻づまり', 'くしゃみ', '悪寒', '寒気', 'のど', '咽頭', '喉', '感冒', 'かぜ', 'せき', 'たん', '鎮痛', '歯痛', '筋肉痛', '関節痛', '腰痛', '神経痛', '咽頭痛', '打撲痛', '急性上気道炎'])
                                is_nutritional_only = has_nutritional_efficacy and not has_cold_symptom_in_efficacy
                                
                                if is_nutritional_only:
                                    logger.info(f"🚫 栄養補給・滋養強壮薬を除外（2位選定）: {candidate.get('product_name', '')} (効能: {efficacy[:80]}...)")
                                    continue
                                
                                # 効能特異性が低い医薬品を除外（_enforce_symptom_match_thresholdと同じ条件）
                                efficacy_specificity = calculate_efficacy_specificity_score(candidate, nlu_result)
                                symptom_specificity_penalty = calculate_symptom_specificity_penalty(candidate, nlu_result)
                                
                                # 効能特異性が0.0または非常に低い（0.1未満）かつ症状特異性ペナルティが-0.6以下の医薬品を除外
                                if efficacy_specificity < 0.1 and symptom_specificity_penalty <= -0.6:
                                    logger.info(f"🚫 効能特異性が低い医薬品を除外（2位選定）: {candidate.get('product_name', '')} (効能特異性: {efficacy_specificity:.2f}, 症状特異性ペナルティ: {symptom_specificity_penalty:.2f})")
                                    continue
                                
                                top_2_candidates.append(candidate)
                                candidate['original_rank'] = 2  # 2位として明示的に設定
                                logger.info(f"✅ 風邪症状: candidatesから2位を選定（総合風邪薬以外）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')}, final_score: {candidate.get('final_score', 0.0):.3f})")
                                if len(top_2_candidates) >= 2:
                                    break
                        if len(top_2_candidates) < 2:
                            logger.warning(f"⚠️ candidatesからも総合風邪薬以外の内服薬が見つかりませんでした。上位10件: {[(c.get('product_name', ''), c.get('medicine_type', ''), is_comprehensive_cold_medicine(c), c.get('final_score', 0.0)) for c in sorted(candidates, key=lambda x: x.get('final_score', 0.0), reverse=True)[:10]]}")
            
            # 3位用の候補リスト（特化薬を優先：解熱鎮痛薬、外用喉薬、喉薬、鼻炎薬など）
            remaining_candidates = []
            # 3位は症状に特化した医薬品を優先（総合感冒薬以外）
            # 優先順位: 1. 外用薬（のど）、2. 解熱鎮痛薬、3. 鼻炎用薬、4. その他
            priority_types_for_3rd = ['外用薬（のど）', '解熱鎮痛薬', '鼻炎用薬']
            
            # まず特化薬を探す（総合感冒薬以外）
            for priority_type in priority_types_for_3rd:
                for candidate in other_medicines + selected_sorted:
                    if (candidate not in top_2_candidates and 
                        candidate.get('product_name', '') not in {c.get('product_name', '') for c in remaining_candidates} and
                        priority_type in candidate.get('medicine_type', '') and
                        not is_comprehensive_cold_medicine(candidate)):
                        remaining_candidates.append(candidate)
                        candidate['original_rank'] = 3  # 3位として明示的に設定
                        logger.info(f"✅ 風邪症状: 特化薬（{priority_type}）を3位候補に追加: {candidate.get('product_name', '')}")
                        break  # 各タイプから1つずつ選定
                if len(remaining_candidates) >= 3:  # 3つまで追加
                    break
            
            # 特化薬が見つからない場合、その他の候補を追加（重複を防止）
            if len(remaining_candidates) == 0:
                added_product_names = {c.get('product_name', '') for c in top_2_candidates + remaining_candidates}
                for candidate in other_medicines + [c for c in selected_sorted if c not in top_2_candidates]:
                    # 既に選定された候補や、同じ製品名の候補を除外
                    if (candidate not in top_2_candidates and 
                        candidate.get('product_name', '') not in added_product_names and
                        not is_comprehensive_cold_medicine(candidate)):  # 総合感冒薬は除外
                        remaining_candidates.append(candidate)
                        added_product_names.add(candidate.get('product_name', ''))
                        if len(remaining_candidates) >= 3:  # 3つまで追加
                            break
        else:
            # 風邪症状がない場合、従来のロジック
            top_2_candidates = selected_sorted[:2] if len(selected_sorted) >= 2 else selected_sorted
            # remaining_candidatesを生成する際、除外ロジックを適用
            if nlu_result and len(selected_sorted) > 2:
                temp_candidates = selected_sorted[2:]
                remaining_candidates = filter_by_efficacy_symptom_match(temp_candidates, nlu_result)
            else:
                remaining_candidates = selected_sorted[2:] if len(selected_sorted) > 2 else []
    else:
        # nlu_resultがない場合、従来のロジック
        top_2_candidates = selected_sorted[:2] if len(selected_sorted) >= 2 else selected_sorted
    # remaining_candidatesを生成する際、除外ロジックを適用
    if nlu_result and len(selected_sorted) > 2:
        temp_candidates = selected_sorted[2:]
        remaining_candidates = filter_by_efficacy_symptom_match(temp_candidates, nlu_result)
    else:
        remaining_candidates = selected_sorted[2:] if len(selected_sorted) > 2 else []
    
    # 上位2件の作用機序を確認
    top_2_mechanisms = set()
    for candidate in top_2_candidates:
        mechanism = classify_medicine_mechanism(candidate)
        top_2_mechanisms.add(mechanism)
    
    # 3件目を選定: 作用機序の多様性を考慮
    third_candidate = None
    # remaining_candidatesが空の場合、selected_sortedから3件目を選定
    if not remaining_candidates and len(top_2_candidates) < top_n:
        # selected_sortedから、top_2_candidatesに含まれていない候補を探す
        for candidate in selected_sorted:
            if candidate not in top_2_candidates:
                # 除外ロジックを事前に適用（不適切な候補を除外）
                if nlu_result:
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                remaining_candidates.append(candidate)
                if len(remaining_candidates) >= 3:  # 3件まで追加
                    break
    
    if len(top_2_candidates) < top_n and remaining_candidates:
        # 期待される医薬品を優先（月経不順関連の症状がある場合）
        if nlu_result:
            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
            has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
            
            if has_menstrual_symptom:
                # 期待される医薬品を優先
                priority_medicine_names = ["ラムールQ", "ラムールＱ", "加味逍遙散", "命の母ホワイト", "ルナエール", "ルナフェミン", "桂枝茯苓丸"]
                for candidate in remaining_candidates:
                    product_name = candidate.get('product_name', '')
                    if any(priority_name in product_name for priority_name in priority_medicine_names):
                        third_candidate = candidate
                        logger.info(f"⭐ 3件目に期待される医薬品を選定: {product_name}")
                        break
        
        # 期待される医薬品が見つからない場合、作用機序の多様性を考慮
        if not third_candidate:
            # 補血・調血系と理気・駆瘀血系の両方が含まれているか確認
            has_blood_tonifying = "補血・調血系" in top_2_mechanisms
            has_qi_regulating = "理気・駆瘀血系" in top_2_mechanisms
            
            # 両方が含まれていない場合、不足している方の作用機序を持つ候補を優先
            if not has_blood_tonifying:
                for candidate in remaining_candidates:
                    mechanism = classify_medicine_mechanism(candidate)
                    if mechanism == "補血・調血系":
                        third_candidate = candidate
                        logger.info(f"🔬 3件目に補血・調血系を選定（作用機序の多様性確保）: {candidate.get('product_name', '')}")
                        break
            elif not has_qi_regulating:
                for candidate in remaining_candidates:
                    mechanism = classify_medicine_mechanism(candidate)
                    if mechanism == "理気・駆瘀血系":
                        third_candidate = candidate
                        logger.info(f"🔬 3件目に理気・駆瘀血系を選定（作用機序の多様性確保）: {candidate.get('product_name', '')}")
                        break
        
        # 作用機序の多様性が確保されている場合、スコア順で3件目を選定
        if not third_candidate and remaining_candidates:
            # remaining_candidatesから適切な候補を選定（除外ロジックを適用済み）
            for candidate in remaining_candidates:
                # 除外ロジックを再度適用（念のため）
                if nlu_result:
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                third_candidate = candidate
                if DEBUG_MODE or logger.level <= logging.DEBUG:
                    logger.debug(f"📊 3件目をスコア順で選定: {third_candidate.get('product_name', '')}")
                break
    
    # 最終選定リストを構築
    # 風邪症状がある場合、top_2_candidatesが2件未満の場合は2位を選定
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if len(top_2_candidates) < 2:
            if cold_symptom_count >= 2:
                # 2位: 総合風邪薬を優先（複数症状時は1,2つ目に総合感冒薬を推奨）
                for candidate in selected_sorted:
                    if (candidate not in top_2_candidates and 
                        is_comprehensive_cold_medicine(candidate)):
                        top_2_candidates.append(candidate)
                        logger.info(f"✅ 風邪症状: 最終チェックで2位を選定（総合風邪薬）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        if len(top_2_candidates) >= 2:
                            break
            else:
                # 単一症状の場合も2位、3位を選定（主要解熱鎮痛薬を優先）
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates:
                        # 主要解熱鎮痛薬を優先
                        is_major_analgesic = any(
                            major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                        )
                        if is_major_analgesic or len(top_2_candidates) < 2:
                            top_2_candidates.append(candidate)
                            logger.info(f"✅ 単一症状: {len(top_2_candidates)}位を選定: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                            if len(top_2_candidates) >= 2:
                                break
        
        # 単一症状の場合、3位も選定（主要解熱鎮痛薬を優先）
        if cold_symptom_count == 1 and len(top_2_candidates) >= 2 and not third_candidate:
            for candidate in selected_sorted:
                if candidate not in top_2_candidates:
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    
                    # 主要解熱鎮痛薬を優先
                    is_major_analgesic = any(
                        major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                    )
                    if is_major_analgesic:
                        third_candidate = candidate
                        logger.info(f"✅ 単一症状: 3位を選定（主要解熱鎮痛薬）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        break
            
            # 主要解熱鎮痛薬が見つからない場合、スコア順で3位を選定（除外ロジックを適用）
            if not third_candidate and selected_sorted:
                for candidate in selected_sorted:
                    if candidate not in top_2_candidates:
                        # 除外ロジックを事前に適用（不適切な候補を除外）
                        if nlu_result:
                            temp_list = [candidate]
                            filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                            if len(filtered_temp) == 0:
                                continue  # 除外される場合はスキップ
                        
                        third_candidate = candidate
                        logger.info(f"✅ 単一症状: 3位を選定（スコア順）: {candidate.get('product_name', '')} (medicine_type: {candidate.get('medicine_type', '')})")
                        break
    
    final_selected = top_2_candidates.copy()
    if third_candidate and len(final_selected) < top_n:
        final_selected.append(third_candidate)
        logger.info(f"✅ 3位候補を追加: {third_candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
    
    # 残りの候補を追加（top_nに達するまで）
    # 重複を防止: 既に選定された医薬品と同じ製品名の候補を除外
    # 単一症状の場合も3つ選定する（主要解熱鎮痛薬を優先）
    if len(final_selected) < top_n:
        selected_product_names = {c.get('product_name', '') for c in final_selected}
        
        # まずremaining_candidatesから主要解熱鎮痛薬を優先的に追加
        for candidate in remaining_candidates:
            if candidate == third_candidate:
                continue
            if candidate.get('product_name', '') in selected_product_names:
                continue
            # 除外ロジックを事前に適用（不適切な候補を除外）
            if nlu_result:
                temp_list = [candidate]
                filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                if len(filtered_temp) == 0:
                    continue  # 除外される場合はスキップ
            # 主要解熱鎮痛薬を優先
            is_major_analgesic = any(
                major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
            )
            if is_major_analgesic:
                final_selected.append(candidate)
                selected_product_names.add(candidate.get('product_name', ''))
                logger.info(f"✅ 単一症状: 主要解熱鎮痛薬を追加（remaining_candidates）: {candidate.get('product_name', '')}")
                if len(final_selected) >= top_n:
                    break
        
        # remaining_candidatesが空または不足している場合、selected_sortedから追加
        if len(final_selected) < top_n:
            # 単一症状の場合、主要解熱鎮痛薬を優先
            if nlu_result:
                symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
                cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
                
                if cold_symptom_count == 1:
                    # 主要解熱鎮痛薬を優先的に追加
                    for candidate in selected_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを事前に適用（不適切な候補を除外）
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                        is_major_analgesic = any(
                            major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                        )
                        if is_major_analgesic:
                            final_selected.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            logger.info(f"✅ 単一症状: 主要解熱鎮痛薬を追加（selected_sorted）: {candidate.get('product_name', '')}")
                            if len(final_selected) >= top_n:
                                break
            
            # 主要解熱鎮痛薬が不足している場合、remaining_candidatesから追加
            if len(final_selected) < top_n:
                for candidate in remaining_candidates:
                    if candidate == third_candidate:
                        continue
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    final_selected.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    logger.info(f"✅ 単一症状: 残りの候補を追加（remaining_candidates）: {candidate.get('product_name', '')}")
                    if len(final_selected) >= top_n:
                        break
            
            # まだ不足している場合、selected_sortedから追加（確実に3つ選定するため）
            if len(final_selected) < top_n:
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを事前に適用（不適切な候補を除外）
                    if nlu_result:
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                    final_selected.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    logger.info(f"✅ 単一症状: 残りの候補を追加（selected_sorted）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
                    if len(final_selected) >= top_n:
                        break
                
                # それでも不足している場合、candidatesから追加（確実に3つ選定するため）
                if len(final_selected) < top_n:
                    for candidate in candidates:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        if candidate.get('final_score', 0.0) >= 0.3:  # スコアが0.3以上の候補のみ
                            # 除外ロジックを事前に適用（不適切な候補を除外）
                            if nlu_result:
                                temp_list = [candidate]
                                filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                                if len(filtered_temp) == 0:
                                    continue  # 除外される場合はスキップ
                            final_selected.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            logger.info(f"✅ 単一症状: 残りの候補を追加（candidates）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected)})")
                            if len(final_selected) >= top_n:
                                break
    
    # カテゴリ多様性の確保と弱点補完ロジック（3症状以上の場合）
    if nlu_result and len(final_selected) >= top_n:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        symptom_count = len(symptom_names_list)
        
        if symptom_count >= 3:
            # 現在のカテゴリを確認
            medicine_types = [c.get('medicine_type', '') for c in final_selected[:top_n]]
            unique_types = set()
            for med_type in medicine_types:
                # カテゴリを抽出（"風邪薬"、"解熱鎮痛薬"、"外用薬（のど）"など）
                if '風邪薬' in med_type:
                    unique_types.add('風邪薬')
                elif '解熱鎮痛薬' in med_type:
                    unique_types.add('解熱鎮痛薬')
                elif '外用薬（のど）' in med_type:
                    unique_types.add('外用薬（のど）')
                elif '漢方薬' in med_type or any(kw in med_type for kw in ['葛根湯', '五苓散']):
                    unique_types.add('漢方薬')
            
            # 単一カテゴリのみの場合は、弱点補完ロジックを適用
            if len(unique_types) == 1:
                first_medicine_type = list(unique_types)[0]
                first_medicine = final_selected[0]
                
                # 1位の薬の弱点を補うカテゴリを決定（ルールベース + 症状ベース）
                complementary_category = None
                
                # ルールベース: 1位のカテゴリに応じた補完カテゴリ
                category_compensation_rules = {
                    "風邪薬": ["外用薬（のど）", "解熱鎮痛薬"],  # 総合感冒薬の弱点: 局所治療、強力な解熱
                    "解熱鎮痛薬": ["風邪薬", "外用薬（のど）"],  # 解熱鎮痛薬の弱点: 総合的な対応、局所治療
                    "外用薬（のど）": ["風邪薬", "解熱鎮痛薬"],  # 外用薬の弱点: 全身症状への対応
                }
                
                # 症状ベース: 症状に応じた優先順位
                has_throat_pain = any("のど" in name or "喉" in name for name in symptom_names_list)
                has_fever = "発熱" in symptom_names_list
                has_cough = "咳" in symptom_names_list
                
                if first_medicine_type == "風邪薬":
                    # のど痛みがあれば外用薬（のど）を優先、発熱が強ければ解熱鎮痛薬を優先
                    if has_throat_pain:
                        complementary_category = "外用薬（のど）"
                    elif has_fever:
                        complementary_category = "解熱鎮痛薬"
                    else:
                        complementary_category = category_compensation_rules.get(first_medicine_type, ["外用薬（のど）"])[0]
                elif first_medicine_type == "解熱鎮痛薬":
                    # のど痛みがあれば外用薬（のど）を優先、そうでなければ総合感冒薬を優先
                    if has_throat_pain:
                        complementary_category = "外用薬（のど）"
                    else:
                        complementary_category = "風邪薬"
                elif first_medicine_type == "外用薬（のど）":
                    # 発熱があれば解熱鎮痛薬を優先、そうでなければ総合感冒薬を優先
                    if has_fever:
                        complementary_category = "解熱鎮痛薬"
                    else:
                        complementary_category = "風邪薬"
                
                # 補完カテゴリの候補を探して追加
                if complementary_category:
                    # 既に選択されている候補以外から探す
                    remaining_for_compensation = [c for c in filtered_candidates if c not in final_selected[:top_n]]
                    for candidate in remaining_for_compensation:
                        candidate_type = candidate.get('medicine_type', '')
                        if complementary_category in candidate_type:
                            # 効能効果と症状のマッチングをチェック
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
                            
                            # 効能効果に症状が含まれているかチェック
                            has_symptom_match = False
                            for symptom_name in symptom_names_list:
                                normalized_symptom = normalize_text(symptom_name)
                                # 効能効果に症状名または同義語が含まれているかチェック
                                symptom_dict_entry = load_symptom_dictionary().get(symptom_name, {})
                                synonyms = [normalized_symptom] + [normalize_text(s) for s in symptom_dict_entry.get("synonyms", [])]
                                
                                # 効能効果に症状が含まれているか確認
                                if any(synonym in efficacy for synonym in synonyms if synonym):
                                    has_symptom_match = True
                                    break
                                
                                # 風邪症状の特別チェック
                                cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ"]
                                if symptom_name in cold_symptoms:
                                    # 効能効果に風邪症状が含まれているか
                                    if any(kw in efficacy for kw in ['発熱', '熱', '解熱', '咳', '鎮咳', '鼻水', '鼻炎', 'のど', '咽頭', '喉', '頭痛', '悪寒', 'くしゃみ']):
                                        has_symptom_match = True
                                        break
                            
                            # 効能効果に症状が含まれていない場合はスキップ
                            if not has_symptom_match:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"弱点補完候補をスキップ（効能効果に症状が含まれていない）: {candidate.get('product_name', '')} (効能: {efficacy[:100]}...)")
                                continue
                            
                            # 3位の候補と置き換え（または追加）
                            if len(final_selected) >= 3:
                                final_selected = final_selected[:2] + [candidate]
                                logger.info(f"🔬 弱点補完: {complementary_category} を追加 {candidate.get('product_name', '')}")
                            else:
                                final_selected.append(candidate)
                                logger.info(f"🔬 弱点補完: {complementary_category} を追加 {candidate.get('product_name', '')}")
                            break
    
    # 作用機序の多様性の強制: 補血・調血系と理気・駆瘀血系の両方を強制的に含める
    # 月経不順関連の症状がある場合のみ適用
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛", "血の道症", "血の道"]
        has_menstrual_symptom = any(symptom in symptom_names_list for symptom in menstrual_symptoms)
        
        if has_menstrual_symptom:
            # 最終選定リストの作用機序を確認
            final_selected_mechanisms = {}
            for candidate in final_selected:
                mechanism = classify_medicine_mechanism(candidate)
                if mechanism not in final_selected_mechanisms:
                    final_selected_mechanisms[mechanism] = []
                final_selected_mechanisms[mechanism].append(candidate)
            
            # 補血・調血系と理気・駆瘀血系の両方が含まれているか確認
            has_blood_tonifying = "補血・調血系" in final_selected_mechanisms
            has_qi_regulating = "理気・駆瘀血系" in final_selected_mechanisms
            
            # 証との連動: 虚証なら「補血系」、実証なら「駆瘀血系」から必ず1つはピックアップ
            if user_info:
                user_message = user_info.get('user_message', '') or ''
                sho_result = determine_kampo_sho(user_info, nlu_result, user_message)
                sho = sho_result.get('sho', '不明')
                confidence = sho_result.get('confidence', 0.0)
                
                # 確信度が高い場合（confidence >= 0.5）のみ証との連動を適用
                if confidence >= 0.5:
                    # 虚証の場合: 補血・調血系を優先的に含める
                    if sho == "虚証" and not has_blood_tonifying:
                        for candidate in filtered_candidates:
                            if candidate in final_selected:
                                continue
                            mechanism = classify_medicine_mechanism(candidate)
                            if mechanism == "補血・調血系":
                                # スコアが低くても、補血・調血系から最低1件は含める
                                if len(final_selected) < top_n:
                                    final_selected.append(candidate)
                                    logger.info(f"🔬 証との連動（虚証）: 補血・調血系を追加 {candidate.get('product_name', '')}")
                                    has_blood_tonifying = True
                                break
                    
                    # 実証の場合: 理気・駆瘀血系を優先的に含める
                    elif sho == "実証" and not has_qi_regulating:
                        for candidate in filtered_candidates:
                            if candidate in final_selected:
                                continue
                            mechanism = classify_medicine_mechanism(candidate)
                            if mechanism == "理気・駆瘀血系":
                                # スコアが低くても、理気・駆瘀血系から最低1件は含める
                                if len(final_selected) < top_n:
                                    final_selected.append(candidate)
                                    logger.info(f"🔬 証との連動（実証）: 理気・駆瘀血系を追加 {candidate.get('product_name', '')}")
                                    has_qi_regulating = True
                                break
            
            # 両方が含まれていない場合、追加する（証との連動で追加されなかった場合）
            if not has_blood_tonifying or not has_qi_regulating:
                # 補血・調血系がない場合、候補から補血・調血系を探す
                if not has_blood_tonifying:
                    for candidate in filtered_candidates:
                        if candidate in final_selected:
                            continue
                        mechanism = classify_medicine_mechanism(candidate)
                        if mechanism == "補血・調血系":
                            # スコアが低くても、補血・調血系から最低1件は含める
                            if len(final_selected) < top_n:
                                final_selected.append(candidate)
                                logger.info(f"🔬 作用機序の多様性確保: 補血・調血系を追加 {candidate.get('product_name', '')}")
                            break
                
                # 理気・駆瘀血系がない場合、候補から理気・駆瘀血系を探す
                if not has_qi_regulating:
                    for candidate in filtered_candidates:
                        if candidate in final_selected:
                            continue
                        mechanism = classify_medicine_mechanism(candidate)
                        if mechanism == "理気・駆瘀血系":
                            # スコアが低くても、理気・駆瘀血系から最低1件は含める
                            if len(final_selected) < top_n:
                                final_selected.append(candidate)
                                logger.info(f"🔬 作用機序の多様性確保: 理気・駆瘀血系を追加 {candidate.get('product_name', '')}")
                            break

    # original_rankに基づいて順序を復元（ランキング保護）
    # 風邪症状がある場合、総合風邪薬が含まれていない場合は強制的に追加
    if nlu_result:
        symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
        cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり"]
        cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
        
        if cold_symptom_count >= 2:
            # 現在の選定リストに総合風邪薬が含まれているかチェック
            has_comprehensive_cold = any(is_comprehensive_cold_medicine(c) for c in final_selected[:top_n])
            
            if not has_comprehensive_cold:
                # 総合風邪薬を候補から探す
                comprehensive_cold_candidates = [c for c in filtered_candidates if is_comprehensive_cold_medicine(c) and c not in final_selected]
                
                if comprehensive_cold_candidates:
                    # スコア順にソートして最上位の総合風邪薬を取得
                    comprehensive_cold_candidates_sorted = sorted(
                        comprehensive_cold_candidates,
                        key=lambda x: x.get('final_score', 0.0),
                        reverse=True
                    )
                    best_comprehensive_cold = comprehensive_cold_candidates_sorted[0]
                    
                    # 1位に配置（既存の1位を2位にずらす）
                    if len(final_selected) >= top_n:
                        # 既存の1位以降のoriginal_rankを1つずつずらす
                        for i, candidate in enumerate(final_selected[:top_n-1]):
                            candidate['original_rank'] = i + 2
                        final_selected = [best_comprehensive_cold] + final_selected[:top_n-1]
                    else:
                        # 既存の候補のoriginal_rankを1つずつずらす
                        for i, candidate in enumerate(final_selected):
                            candidate['original_rank'] = i + 2
                        final_selected = [best_comprehensive_cold] + final_selected
                    
                    # 総合風邪薬のoriginal_rankを1に設定（ランキング保護のため）
                    best_comprehensive_cold['original_rank'] = 1
                    
                    logger.info(f"✅ 総合風邪薬を強制配置（1位）: {best_comprehensive_cold.get('product_name', '')} (スコア: {best_comprehensive_cold.get('final_score', 0.0):.3f}, original_rank=1)")
    
    # 重複を除去: 同じ製品名の候補を除外（original_rankでソートする前に実行）
    seen_product_names = set()
    final_selected_deduplicated = []
    for candidate in final_selected[:top_n]:
        product_name = candidate.get('product_name', '')
        if product_name not in seen_product_names:
            final_selected_deduplicated.append(candidate)
            seen_product_names.add(product_name)
        else:
            if DEBUG_MODE or logger.level <= logging.DEBUG:
                logger.debug(f"重複を除去: {product_name} (original_rank={candidate.get('original_rank', 'N/A')})")
    
    # 最終チェック: 除外ロジックを再度適用（選定後に追加された候補を除外）
    if nlu_result:
        final_selected_filtered = filter_by_efficacy_symptom_match(final_selected_deduplicated, nlu_result)
        final_selected_deduplicated = final_selected_filtered
        
        # 除外後に3つ未満になった場合、再度候補を追加（確実に3つ選定するため）
        if len(final_selected_deduplicated) < top_n:
            symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            cold_symptoms = ["発熱", "咳", "鼻水", "のどの痛み", "頭痛", "悪寒", "くしゃみ", "鼻づまり", "痰", "たん"]
            cold_symptom_count = sum(1 for symptom in symptom_names_list if symptom in cold_symptoms)
            is_fever_only = cold_symptom_count == 1 and "発熱" in symptom_names_list
            is_single_symptom = cold_symptom_count == 1
            
            logger.info(f"🔍 除外後の再追加処理: final_selected_deduplicated={len(final_selected_deduplicated)}, top_n={top_n}, symptom_names_list={symptom_names_list}, cold_symptom_count={cold_symptom_count}, is_single_symptom={is_single_symptom}, is_fever_only={is_fever_only}")
            
            selected_product_names = {c.get('product_name', '') for c in final_selected_deduplicated}
            
            # 単一症状（発熱のみ）の場合、主要解熱鎮痛薬を優先的に追加
            if is_fever_only:
                # selected_sortedから主要解熱鎮痛薬を優先的に追加
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        continue
                    # 除外ロジックを再度適用（主要解熱鎮痛薬でも不適切なものは除外）
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        continue  # 除外される場合はスキップ
                    
                    is_major_analgesic = any(
                        major_name in candidate.get('product_name', '') for major_name in MAJOR_ANALGESIC_MEDICINES
                    )
                    if is_major_analgesic:
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        logger.info(f"✅ 除外後: 主要解熱鎮痛薬を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
                
                # それでも不足している場合、selected_sortedから追加
                if len(final_selected_deduplicated) < top_n:
                    for candidate in selected_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを再度適用
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            continue  # 除外される場合はスキップ
                        
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        logger.info(f"✅ 除外後: 残りの候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
            
            # 単一症状（発熱以外：咳、痰、鼻水など）の場合、適切な医薬品を追加
            elif is_single_symptom:
                logger.info(f"🔍 単一症状用の再追加処理開始: selected_sorted={len(selected_sorted)}件, selected_product_names={len(selected_product_names)}件")
                # selected_sortedから適切な候補を追加
                added_count = 0
                skipped_count = 0
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        skipped_count += 1
                        continue
                    # 除外ロジックを再度適用
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        skipped_count += 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                        continue  # 除外される場合はスキップ
                    
                    final_selected_deduplicated.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    added_count += 1
                    logger.info(f"✅ 除外後: 単一症状用の候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                    if len(final_selected_deduplicated) >= top_n:
                        break
                logger.info(f"🔍 単一症状用の再追加処理完了: 追加={added_count}件, スキップ={skipped_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                
                # selected_sortedから追加できなかった場合、candidatesから追加の候補を取得
                if len(final_selected_deduplicated) < top_n:
                    logger.info(f"🔍 selected_sortedから追加できなかったため、candidatesから追加の候補を取得: candidates={len(candidates)}件")
                    # 症状に応じた効能効果キーワードを取得
                    symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])] if nlu_result else []
                    # 効能効果に症状が含まれている候補を優先的に考慮
                    priority_keywords = []
                    for symptom_name in symptom_names_list:
                        if symptom_name in ["痰", "たん"]:
                            priority_keywords.extend(["たん", "痰", "去たん", "去痰"])
                        elif symptom_name in ["咳"]:
                            priority_keywords.extend(["咳", "せき", "咳嗽"])
                    
                    # candidatesを優先度順にソート（効能効果に症状が含まれている候補を優先、その後スコア順）
                    def get_priority_score(candidate):
                        efficacy = str(candidate.get('efficacy', '')).lower()
                        # 効能効果に症状が含まれている場合は優先度を高く
                        priority_score = 0
                        if priority_keywords:
                            for keyword in priority_keywords:
                                if keyword in efficacy:
                                    priority_score = 1
                                    break
                        # スコアを追加（優先度が同じ場合はスコア順）
                        return (priority_score, candidate.get('final_score', 0.0))
                    
                    candidates_sorted = sorted(candidates, key=get_priority_score, reverse=True)
                    
                    # 効能効果に症状が含まれている候補を優先的に追加
                    priority_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 1]
                    other_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 0]
                    
                    # 優先度の高い候補から追加
                    for candidate_list in [priority_candidates, other_candidates]:
                        for candidate in candidate_list:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 除外ロジックを再度適用
                            temp_list = [candidate]
                            filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                            if len(filtered_temp) == 0:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                                continue  # 除外される場合はスキップ
                            
                            final_selected_deduplicated.append(candidate)
                            selected_product_names.add(candidate.get('product_name', ''))
                            added_count += 1
                            logger.info(f"✅ 除外後: 単一症状用の候補を追加（candidatesから）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                            if len(final_selected_deduplicated) >= top_n:
                                break
                        if len(final_selected_deduplicated) >= top_n:
                            break
                    logger.info(f"🔍 candidatesからの追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
            
            # 複数症状の場合も、3つ未満の場合は追加
            elif len(final_selected_deduplicated) < top_n:
                logger.info(f"🔍 複数症状用の再追加処理開始: selected_sorted={len(selected_sorted)}件, selected_product_names={len(selected_product_names)}件")
                # selected_sortedから適切な候補を追加
                added_count = 0
                skipped_count = 0
                for candidate in selected_sorted:
                    if candidate.get('product_name', '') in selected_product_names:
                        skipped_count += 1
                        continue
                    # 除外ロジックを再度適用
                    temp_list = [candidate]
                    filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                    if len(filtered_temp) == 0:
                        skipped_count += 1
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                        continue  # 除外される場合はスキップ
                    
                    final_selected_deduplicated.append(candidate)
                    selected_product_names.add(candidate.get('product_name', ''))
                    added_count += 1
                    logger.info(f"✅ 除外後: 複数症状用の候補を追加: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                    if len(final_selected_deduplicated) >= top_n:
                        break
                logger.info(f"🔍 複数症状用の再追加処理完了: 追加={added_count}件, スキップ={skipped_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                
                # selected_sortedから追加できなかった場合、candidatesから追加の候補を取得
                if len(final_selected_deduplicated) < top_n:
                    logger.info(f"🔍 selected_sortedから追加できなかったため、candidatesから追加の候補を取得: candidates={len(candidates)}件")
                    # 症状に応じた効能効果キーワードを取得
                    symptom_names_list = [s.get("name", "") for s in nlu_result.get("symptoms", [])] if nlu_result else []
                    # 効能効果に症状が含まれている候補を優先的に考慮
                    priority_keywords = []
                    for symptom_name in symptom_names_list:
                        if symptom_name in ["痰", "たん"]:
                            priority_keywords.extend(["たん", "痰", "去たん", "去痰"])
                        elif symptom_name in ["咳"]:
                            priority_keywords.extend(["咳", "せき", "咳嗽"])
                    
                    # candidatesを優先度順にソート（効能効果に症状が含まれている候補を優先、その後スコア順）
                    def get_priority_score(candidate):
                        efficacy = str(candidate.get('efficacy', '')).lower()
                        # 効能効果に症状が含まれている場合は優先度を高く
                        priority_score = 0
                        if priority_keywords:
                            for keyword in priority_keywords:
                                if keyword in efficacy:
                                    priority_score = 1
                                    break
                        # スコアを追加（優先度が同じ場合はスコア順）
                        return (priority_score, candidate.get('final_score', 0.0))
                    
                    candidates_sorted = sorted(candidates, key=get_priority_score, reverse=True)
                    for candidate in candidates_sorted:
                        if candidate.get('product_name', '') in selected_product_names:
                            continue
                        # 除外ロジックを再度適用
                        temp_list = [candidate]
                        filtered_temp = filter_by_efficacy_symptom_match(temp_list, nlu_result)
                        if len(filtered_temp) == 0:
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"🚫 除外ロジックで除外: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...)")
                            continue  # 除外される場合はスキップ
                        
                        final_selected_deduplicated.append(candidate)
                        selected_product_names.add(candidate.get('product_name', ''))
                        added_count += 1
                        logger.info(f"✅ 除外後: 複数症状用の候補を追加（candidatesから）: {candidate.get('product_name', '')} (現在の選定数: {len(final_selected_deduplicated)})")
                        if len(final_selected_deduplicated) >= top_n:
                            break
                    logger.info(f"🔍 candidatesからの追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
                    
                    # それでも不足している場合、効能効果に症状が含まれている候補を強制的に追加（除外ロジックをスキップ）
                    if len(final_selected_deduplicated) < top_n and priority_keywords:
                        logger.info(f"🔍 除外ロジックをスキップして、効能効果に症状が含まれている候補を強制的に追加: priority_keywords={priority_keywords}")
                        # 優先度の高い候補を取得
                        priority_candidates = [c for c in candidates_sorted if get_priority_score(c)[0] == 1]
                        for candidate in priority_candidates:
                            if candidate.get('product_name', '') in selected_product_names:
                                continue
                            # 効能効果に症状が含まれているか確認
                            efficacy = str(candidate.get('efficacy', '')).lower()
                            has_priority_keyword = any(keyword in efficacy for keyword in priority_keywords)
                            if has_priority_keyword:
                                final_selected_deduplicated.append(candidate)
                                selected_product_names.add(candidate.get('product_name', ''))
                                added_count += 1
                                logger.info(f"✅ 強制的に追加: {candidate.get('product_name', '')} (効能: {candidate.get('efficacy', '')[:50]}...) (現在の選定数: {len(final_selected_deduplicated)})")
                                if len(final_selected_deduplicated) >= top_n:
                                    break
                        logger.info(f"🔍 強制的な追加処理完了: 追加={added_count}件, 現在の選定数={len(final_selected_deduplicated)}")
    
    final_selected_sorted = sorted(final_selected_deduplicated, key=lambda x: x.get('original_rank', 9999))
    
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ensure_ingredient_diversity: original_rankに基づいて順序を復元: {len(final_selected_sorted)}件")

    return final_selected_sorted[:top_n]
