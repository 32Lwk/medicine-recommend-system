"""
医療関連キーワードチェックのパフォーマンスベンチマーク
"""

import time
import statistics

# 現在のキーワードリスト（拡充後）
medical_keywords_extended = [
    # 基本キーワード（必須）
    "痛", "熱", "咳", "鼻", "喉", "頭", "胃", "下痢", "便秘", "吐", "めまい",
    "かゆ", "発疹", "不眠", "疲労", "症状", "病気", "薬", "医", "病",
    
    # 風邪関連症状（SYMPTOM_DICTIONARYから抽出）
    "発熱", "熱がある", "熱っぽい", "高熱", "微熱", "体温", "熱",
    "頭痛", "頭が痛い", "ズキズキ", "頭が重い", "偏頭痛",
    "のど", "喉", "咽頭", "声がれ", "のどの痛み", "喉の痛み", "喉の腫れ",
    "せき", "咳", "咳が出る", "咳込む", "空咳",
    "痰", "たん", "痰が絡む", "痰が出る",
    "鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい",
    "鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉",
    "くしゃみ", "クシャミ",
    "悪寒", "寒気", "さむけ", "ゾクゾク",
    "関節痛", "関節の痛み", "節々", "関節が痛い",
    "筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い",
    
    # 解熱鎮痛薬関連症状
    "生理痛", "月経痛", "生理の痛み", "下腹部痛", "生理", "月経",
    "歯痛", "歯が痛い", "歯の痛み", "歯",
    
    # 鼻炎用薬関連症状
    "鼻汁過多", "鼻水が多い", "鼻水がとまらない",
    "なみだ目", "涙目", "涙",
    
    # 胃腸薬関連症状
    "胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおち",
    "腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "お腹",
    "軟便", "水様便", "便がゆるい", "便",
    "便が出ない", "便通がない", "便が硬い",
    "吐き気", "むかつき", "気持ち悪い", "嘔吐感", "嘔吐",
    "胸やけ", "胸焼け", "胃もたれ", "胃の重い感じ", "消化が悪い", "胃の不快感",
    
    # 外用薬関連症状
    "かゆみ", "かゆい", "痒み", "皮膚のかゆみ",
    "ブツブツ", "赤い斑点", "皮膚の異常",
    "湿疹", "皮膚炎", "かぶれ", "皮膚の炎症", "皮膚",
    "水虫", "白癬", "足の水虫", "指の間",
    "打撲", "打ち身", "青あざ", "内出血",
    "捻挫", "くじいた", "靭帯損傷",
    "肩こり", "肩の凝り", "肩の痛み", "首肩", "肩", "こり",
    "腰痛", "腰", "腰の痛み",
    
    # 目薬関連症状
    "目の充血", "目が赤い", "充血", "目の血走り", "目", "眼",
    "目の疲れ", "眼精疲労", "目が疲れる", "目の重い感じ", "疲れ",
    "目のかゆみ", "目がかゆい", "目の痒み",
    
    # 睡眠・精神関連症状
    "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠", "睡眠",
    "眩暈", "ふらつき", "立ちくらみ",
    "乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う", "乗物酔い",
    "疲労感", "疲れ", "だるい", "倦怠感", "倦怠",
    "イライラ", "いらいら", "焦燥感", "落ち着かない",
    "不安", "心配", "憂鬱", "落ち込み",
    "ストレス", "緊張", "プレッシャー",
    
    # 重症疑い症状（RED_FLAG_SYMPTOMS）
    "呼吸困難", "呼吸が苦しい", "息苦しい", "息ができない", "息切れ",
    "38.5度以上", "39度", "40度", "熱が下がらない",
    "胸痛", "胸が痛い", "胸の痛み", "胸部痛", "心臓が痛い", "胸が締め付けられる",
    "意識障害", "意識がもうろう", "意識がない", "気を失う", "意識不明", "ぼーっと",
    "激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛", "頭が割れる", "耐えられない頭痛",
    "血便", "便に血が混じる", "黒い便", "タール便",
    "喀血", "血を吐く", "吐血",
    "激しい腹痛", "お腹が痛くて動けない", "耐えられない腹痛",
    "顔面麻痺", "顔が動かない", "口が曲がる", "顔の半分が動かない",
    "手足の麻痺", "手足が動かない", "力が入らない", "しびれが続く", "しびれ",
    "持続する嘔吐", "何度も吐く", "止まらない嘔吐", "嘔吐が続く",
    
    # その他の一般的な医療関連キーワード
    "耳", "耳の痛み", "耳鳴り",
    "口内炎", "口", "口の中",
    "喉頭", "気管", "気管支",
    "消化", "食欲", "食欲不振",
    "血圧", "血圧が高い", "血圧が低い",
    "動悸", "心拍", "脈",
    "発汗", "汗", "多汗",
    "冷え", "冷え性", "冷える",
    "むくみ", "浮腫",
    "しこり", "腫れ", "腫れる",
    "炎症", "感染", "菌",
    "ウイルス", "細菌",
    "アレルギー", "アレルギー症状",
    "かぶれ", "接触性皮膚炎",
    "やけど", "火傷", "熱傷",
    "切り傷", "擦り傷", "傷",
    "骨折", "骨",
    "筋肉", "筋",
    "神経", "神経痛",
    "リウマチ", "関節リウマチ",
    "痛風",
    "貧血", "貧血気味",
    "低血糖", "高血糖", "血糖",
    "コレステロール",
    "脂質",
    "肝臓", "肝機能",
    "腎臓", "腎機能",
    "膀胱", "尿", "排尿",
    "月経", "生理", "月経不順",
    "更年期", "ホルモン",
    "妊娠", "妊婦",
    "授乳", "母乳",
    "小児", "子供", "こども", "幼児", "乳児",
    "高齢者", "老人",
    "処方", "処方箋",
    "副作用", "効能", "効果",
    "用法", "用量", "服用", "飲む", "飲み",
    "錠剤", "カプセル", "粉薬", "シロップ", "液剤",
    "軟膏", "クリーム", "ローション", "スプレー",
    "点眼", "点鼻", "点耳"
]

# 以前のキーワードリスト（簡易版）
medical_keywords_simple = [
    "痛", "熱", "咳", "鼻", "喉", "頭", "胃", "下痢", "便秘", "吐", "めまい",
    "かゆ", "発疹", "不眠", "疲労", "症状", "病気", "薬", "医", "病"
]

def check_keywords_simple(text, keywords):
    """シンプルなキーワードチェック（any()を使用）"""
    return any(keyword in text for keyword in keywords)

def check_keywords_optimized(text, keywords):
    """最適化されたキーワードチェック（短いキーワードを優先）"""
    # 短いキーワードを先にチェック（早期終了の可能性が高い）
    sorted_keywords = sorted(keywords, key=len)
    return any(keyword in text for keyword in sorted_keywords)

def benchmark_keyword_check(test_cases, keywords, check_func, iterations=1000):
    """キーワードチェックのベンチマーク"""
    times = []
    
    for _ in range(iterations):
        for test_text in test_cases:
            start = time.perf_counter()
            result = check_func(test_text, keywords)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # ミリ秒に変換
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "total_time": sum(times),
        "iterations": iterations * len(test_cases)
    }

# テストケース
test_cases = [
    "のどが痛いです。",  # 短い入力、マッチあり
    "肩がこります。",  # 短い入力、マッチあり
    "痰が絡みます。",  # 短い入力、マッチあり
    "頭が痛くて、熱もあります。",  # 中程度の入力、マッチあり
    "最近、疲れが取れなくて、イライラします。",  # 長い入力、マッチあり
    "こんにちは、元気ですか？",  # マッチなし
    "今日はいい天気ですね。",  # マッチなし
    "テストテストテスト",  # マッチなし
    "熱があって、のども痛く、咳も出ます。",  # 複数マッチ
    "胃が痛くて、吐き気もします。",  # 複数マッチ
]

if __name__ == "__main__":
    print("="*80)
    print("医療関連キーワードチェックのパフォーマンスベンチマーク")
    print("="*80)
    
    print(f"\nキーワード数:")
    print(f"  簡易版: {len(medical_keywords_simple)}語")
    print(f"  拡充版: {len(medical_keywords_extended)}語")
    print(f"  増加率: {len(medical_keywords_extended) / len(medical_keywords_simple):.1f}倍")
    
    print(f"\nテストケース数: {len(test_cases)}")
    print(f"反復回数: 1000回/ケース")
    print(f"総実行回数: {1000 * len(test_cases)}回")
    
    # 簡易版のベンチマーク
    print("\n" + "="*80)
    print("簡易版キーワードリスト（19語）")
    print("="*80)
    result_simple = benchmark_keyword_check(test_cases, medical_keywords_simple, check_keywords_simple)
    print(f"平均時間: {result_simple['mean']:.4f}ms")
    print(f"中央値: {result_simple['median']:.4f}ms")
    print(f"最小時間: {result_simple['min']:.4f}ms")
    print(f"最大時間: {result_simple['max']:.4f}ms")
    print(f"標準偏差: {result_simple['stdev']:.4f}ms")
    print(f"総時間: {result_simple['total_time']:.2f}ms")
    
    # 拡充版のベンチマーク（通常のany()）
    print("\n" + "="*80)
    print("拡充版キーワードリスト（通常のany()、約200語）")
    print("="*80)
    result_extended = benchmark_keyword_check(test_cases, medical_keywords_extended, check_keywords_simple)
    print(f"平均時間: {result_extended['mean']:.4f}ms")
    print(f"中央値: {result_extended['median']:.4f}ms")
    print(f"最小時間: {result_extended['min']:.4f}ms")
    print(f"最大時間: {result_extended['max']:.4f}ms")
    print(f"標準偏差: {result_extended['stdev']:.4f}ms")
    print(f"総時間: {result_extended['total_time']:.2f}ms")
    
    # 拡充版のベンチマーク（最適化版）
    print("\n" + "="*80)
    print("拡充版キーワードリスト（最適化版、短いキーワード優先）")
    print("="*80)
    result_optimized = benchmark_keyword_check(test_cases, medical_keywords_extended, check_keywords_optimized)
    print(f"平均時間: {result_optimized['mean']:.4f}ms")
    print(f"中央値: {result_optimized['median']:.4f}ms")
    print(f"最小時間: {result_optimized['min']:.4f}ms")
    print(f"最大時間: {result_optimized['max']:.4f}ms")
    print(f"標準偏差: {result_optimized['stdev']:.4f}ms")
    print(f"総時間: {result_optimized['total_time']:.2f}ms")
    
    # 比較
    print("\n" + "="*80)
    print("パフォーマンス比較")
    print("="*80)
    speedup = result_simple['mean'] / result_extended['mean']
    print(f"簡易版 vs 拡充版（通常）: {speedup:.2f}倍の速度差")
    print(f"拡充版（通常） vs 拡充版（最適化）: {result_extended['mean'] / result_optimized['mean']:.2f}倍の速度差")
    
    # 影響の評価
    print("\n" + "="*80)
    print("影響の評価")
    print("="*80)
    print(f"拡充版の平均チェック時間: {result_extended['mean']:.4f}ms")
    print(f"1リクエストあたりの追加時間: {result_extended['mean'] - result_simple['mean']:.4f}ms")
    
    if result_extended['mean'] < 1.0:
        print("✅ 影響は軽微（1ms未満）")
    elif result_extended['mean'] < 5.0:
        print("⚠️ 影響は小さい（1-5ms）")
    else:
        print("❌ 影響が大きい（5ms以上）")
    
    # 推奨
    print("\n" + "="*80)
    print("推奨事項")
    print("="*80)
    if result_extended['mean'] < 1.0:
        print("✅ 現在の実装で問題ありません。")
        print("   - キーワードチェックは1リクエストあたり1回のみ実行")
        print("   - any()の短絡評価により、マッチした時点で処理が停止")
        print("   - 処理時間は1ms未満で、全体の処理時間に占める割合は極めて小さい")
    else:
        print("⚠️ 最適化を検討してください。")
        print("   - 短いキーワードを優先的にチェック")
        print("   - よく使われるキーワードを先頭に配置")
        print("   - セット（set）を使用してO(1)検索を実現")

