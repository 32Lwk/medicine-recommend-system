"""
医薬品CSVデータの読み込み・管理モジュール

CSVの読み込み、クリーニング、症状・種類による検索の責務を持つ。
"""
import os
import re
import logging
import pandas as pd

from src import PROJECT_ROOT
from src.core.dictionary_loader import load_ingredient_dictionary

logger = logging.getLogger(__name__)

BASE_DIR = PROJECT_ROOT
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "otc_medicine_data.csv")

logger.info(f"CSVファイル絶対パス: {CSV_PATH}")
logger.info(f"ファイル存在: {os.path.exists(CSV_PATH)}")


def clean_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    CSVデータのクリーニング: 成分名の表記ゆれの統一、欠損値の補完、効能効果の正規化
    """
    if df is None or df.empty:
        logger.warning("CSVデータが空です。クリーニングをスキップします。")
        return df

    logger.info("CSVデータのクリーニングを開始します...")
    df_cleaned = df.copy()

    # 1. 成分名の表記ゆれの統一
    if "成分" in df_cleaned.columns:
        try:
            ingredient_dict = load_ingredient_dictionary()
            ingredient_mapping = {}
            for canonical_name, info in ingredient_dict.items():
                synonyms = info.get("synonyms", [])
                for synonym in synonyms:
                    ingredient_mapping[synonym.lower()] = canonical_name

            def normalize_ingredient_name(ingredients_str):
                if pd.isna(ingredients_str) or not isinstance(ingredients_str, str):
                    return ingredients_str
                parts = re.split(r"[\n、,/，／・]+", ingredients_str)
                normalized_parts = []
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    part_lower = part.lower()
                    if part_lower in ingredient_mapping:
                        normalized_parts.append(ingredient_mapping[part_lower])
                    else:
                        normalized_parts.append(part)
                unique_parts = list(dict.fromkeys(normalized_parts))
                return "\n".join(unique_parts)

            df_cleaned["成分"] = df_cleaned["成分"].apply(normalize_ingredient_name)
            logger.info("成分名の表記ゆれを統一しました。")
        except Exception as e:
            logger.warning(f"成分辞書の読み込みに失敗しました。成分名の正規化をスキップします: {e}")

    # 2. 欠損値の補完
    if "効能効果" in df_cleaned.columns:
        missing_efficacy_count = df_cleaned["効能効果"].isna().sum()
        if missing_efficacy_count > 0:
            default_efficacy_map = {
                "解熱鎮痛薬": "発熱、頭痛、生理痛",
                "風邪薬": "風邪の諸症状",
                "胃腸薬": "胃腸の不調",
                "漢方薬": "体質改善",
                "外用薬（のど）": "のどの痛み",
                "外用薬（皮膚）": "皮膚の炎症",
            }
            if "医薬品の種類" in df_cleaned.columns:
                for idx, row in df_cleaned.iterrows():
                    if pd.isna(row["効能効果"]):
                        medicine_type = row.get("医薬品の種類", "")
                        if medicine_type in default_efficacy_map:
                            df_cleaned.at[idx, "効能効果"] = default_efficacy_map[medicine_type]
            logger.info(f"効能効果の欠損値を補完しました（{missing_efficacy_count}件）。")

    if "成分" in df_cleaned.columns:
        missing_ingredient_count = df_cleaned["成分"].isna().sum()
        if missing_ingredient_count > 0:
            df_cleaned["成分"] = df_cleaned["成分"].fillna("")
            logger.info(f"成分の欠損値を補完しました（{missing_ingredient_count}件）。")

    # 3. 効能効果の正規化
    if "効能効果" in df_cleaned.columns:
        efficacy_normalization_map = {
            "生理不順": "月経不順",
            "生理異常": "月経不順",
            "生理痛": "月経痛",
            "生理の痛み": "月経痛",
            "血の道症": "月経不順",
            "血の道": "月経不順",
        }

        def normalize_efficacy(efficacy_str):
            if pd.isna(efficacy_str) or not isinstance(efficacy_str, str):
                return efficacy_str
            normalized = efficacy_str
            for old_term, new_term in efficacy_normalization_map.items():
                pattern = r"\b" + re.escape(old_term) + r"\b"
                normalized = re.sub(pattern, new_term, normalized)
            return normalized

        df_cleaned["効能効果"] = df_cleaned["効能効果"].apply(normalize_efficacy)
        logger.info("効能効果の正規化を完了しました。")

    logger.info("CSVデータのクリーニングが完了しました。")
    return df_cleaned


# モジュールロード時にCSVを読み込み
df = None
csv_load_status = {
    "success": False,
    "encoding": None,
    "error": None,
    "row_count": 0,
    "col_count": 0,
    "columns": [],
    "path": CSV_PATH,
}
encodings = ["utf-8", "shift_jis", "cp932", "euc-jp"]

for encoding in encodings:
    try:
        df = pd.read_csv(CSV_PATH, encoding=encoding)
        df = clean_csv_data(df)
        csv_load_status["success"] = True
        csv_load_status["encoding"] = encoding
        csv_load_status["row_count"] = len(df)
        csv_load_status["col_count"] = len(df.columns)
        csv_load_status["columns"] = list(df.columns)
        logger.info(f"CSVファイルを正常に読み込みました（エンコーディング: {encoding}）。")
        break
    except UnicodeDecodeError:
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            logger.debug(f"エンコーディング {encoding} で読み込みに失敗しました。")
        continue
    except FileNotFoundError:
        csv_load_status["error"] = "FileNotFoundError"
        logger.error("エラー: otc_medicine_data.csvファイルが見つかりません。")
        break
    except Exception as e:
        csv_load_status["error"] = str(e)
        logger.error(f"CSVファイルの読み込みエラー: {e}")
        break

if not csv_load_status["success"]:
    logger.error("すべてのエンコーディングでCSVファイルの読み込みに失敗しました。")


def get_medicines_by_symptom(symptom_text, df_param=None):
    """症状テキストが効能効果に部分一致する市販薬を取得"""
    use_df = df_param if df_param is not None else df
    if use_df is None:
        return ["データが読み込まれていません"]
    if "効能効果" not in use_df.columns:
        return ["CSVに効能効果カラムがありません"]
    matched = use_df[use_df["効能効果"].astype(str).str.contains(symptom_text, na=False)]
    if matched.empty:
        return ["該当する市販薬情報が見つかりませんでした。"]
    result = []
    for _, row in matched.iterrows():
        info = f"製品名: {row['製品名']} / メーカー: {row['メーカー名']} / 分類: {row['分類']}\n効能効果: {row['効能効果']}\n成分: {row['成分']}"
        result.append(info)
    return result


def find_otc_candidates(symptoms, df_otc, max_candidates=20):
    """症状名リストのいずれかが効能効果に含まれる市販薬を抽出"""
    mask = df_otc["効能効果"].astype(str).apply(lambda x: any(s in x for s in symptoms))
    return df_otc[mask].head(max_candidates)


def get_medicines_by_type(medicine_type, df_param=None):
    """医薬品の種類に基づいてotc_medicine_dataから医薬品リストを取得"""
    use_df = df_param if df_param is not None else df
    if use_df is None:
        logger.warning("データフレームが読み込まれていません")
        return []
    if "医薬品の種類" not in use_df.columns:
        logger.warning("CSVに医薬品の種類カラムがありません")
        return []
    if medicine_type is None or str(medicine_type).strip() == "":
        logger.warning("医薬品の種類が未指定です")
        return []
    matched = use_df[use_df["医薬品の種類"].astype(str).str.contains(medicine_type, na=False)]
    medicines = []
    for _, row in matched.iterrows():
        medicine_info = {
            "製品名": row.get("製品名", ""),
            "メーカー名": row.get("メーカー名", ""),
            "分類": row.get("分類", ""),
            "医薬品の種類": row.get("医薬品の種類", ""),
            "効能効果": row.get("効能効果", ""),
            "成分": row.get("成分", ""),
            "使用上の注意": row.get("使用上の注意", ""),
        }
        medicines.append(medicine_info)
    logger.info(f"医薬品の種類 '{medicine_type}' で {len(medicines)} 件の医薬品を抽出しました")
    return medicines
