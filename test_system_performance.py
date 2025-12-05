"""
システム全体の性能テスト
網羅的なテストと性能調査
"""

import sys
import os
import io
import time
import statistics
from datetime import datetime

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from medicine_logic import rule_based_medicine_recommendation, client

# テストケース定義
TEST_CASES = {
    "風邪関連": [
        ("のどが痛いです。", {"age": 30, "gender": "男性"}),
        ("熱があって、のども痛いです。", {"age": 30, "gender": "男性"}),
        ("咳が出ます。", {"age": 25, "gender": "女性"}),
        ("鼻水とくしゃみが止まりません。", {"age": 35, "gender": "女性"}),
        ("鼻が詰まっています。", {"age": 30, "gender": "男性"}),
        ("痰が絡みます。", {"age": 30, "gender": "男性"}),
        ("寒気がします。", {"age": 30, "gender": "女性"}),
        ("関節が痛いです。", {"age": 30, "gender": "男性"}),
    ],
    "解熱鎮痛薬関連": [
        ("頭が痛いです。", {"age": 25, "gender": "女性"}),
        ("発熱があります。", {"age": 30, "gender": "男性"}),
        ("生理痛がひどいです。", {"age": 25, "gender": "女性"}),
        ("歯が痛いです。", {"age": 30, "gender": "男性"}),
    ],
    "胃腸薬関連": [
        ("胃が痛いです。", {"age": 30, "gender": "男性"}),
        ("お腹が痛いです。", {"age": 30, "gender": "女性"}),
        ("下痢が続いています。", {"age": 30, "gender": "男性"}),
        ("便秘が続いています。", {"age": 30, "gender": "女性"}),
        ("吐き気がします。", {"age": 30, "gender": "男性"}),
        ("胸やけがします。", {"age": 30, "gender": "女性"}),
        ("胃もたれがします。", {"age": 30, "gender": "男性"}),
    ],
    "外用薬関連": [
        ("かゆみがあります。", {"age": 30, "gender": "男性"}),
        ("発疹が出ています。", {"age": 30, "gender": "女性"}),
        ("湿疹が出ています。", {"age": 30, "gender": "男性"}),
        ("水虫が気になります。", {"age": 30, "gender": "男性"}),
        ("打撲しました。", {"age": 30, "gender": "女性"}),
        ("捻挫しました。", {"age": 30, "gender": "男性"}),
        ("肩がこります。", {"age": 30, "gender": "男性"}),
    ],
    "目薬関連": [
        ("目が充血しています。", {"age": 30, "gender": "男性"}),
        ("目が疲れます。", {"age": 30, "gender": "女性"}),
        ("目がかゆいです。", {"age": 30, "gender": "男性"}),
    ],
    "睡眠・精神関連": [
        ("眠れません。", {"age": 30, "gender": "男性"}),
        ("めまいがします。", {"age": 30, "gender": "女性"}),
        ("疲れが取れません。", {"age": 30, "gender": "男性"}),
        ("イライラします。", {"age": 30, "gender": "女性"}),
        ("不安です。", {"age": 30, "gender": "男性"}),
        ("ストレスがたまっています。", {"age": 30, "gender": "女性"}),
    ],
    "複合症状": [
        ("熱があって、のども痛く、咳も出ます。", {"age": 30, "gender": "男性"}),
        ("胃が痛くて、吐き気もします。", {"age": 30, "gender": "女性"}),
        ("かゆみと発疹があります。", {"age": 30, "gender": "男性"}),
    ],
}

def run_performance_test():
    """性能テストの実行"""
    print("\n" + "="*80)
    print("システム全体の性能テスト")
    print("="*80)
    
    total_tests = 0
    successful_tests = 0
    failed_tests = 0
    
    all_response_times = []
    all_scores = []
    all_medicine_counts = []
    
    category_stats = {}
    
    for category, test_cases in TEST_CASES.items():
        print(f"\n{'='*80}")
        print(f"カテゴリ: {category}")
        print(f"{'='*80}")
        
        category_response_times = []
        category_scores = []
        category_medicine_counts = []
        
        for user_text, user_info in test_cases:
            user_info_full = {
                **user_info,
                "pregnant": False,
                "breastfeeding": False,
                "current_medications": [],
                "allergies": []
            }
            
            total_tests += 1
            print(f"\nテスト {total_tests}: {user_text}")
            
            try:
                start_time = time.time()
                result = rule_based_medicine_recommendation(user_text, user_info_full, client)
                response_time = time.time() - start_time
                
                if result.get('status') == 'success':
                    successful_tests += 1
                    medicines = result.get('recommended_medicines', [])
                    medicine_count = len(medicines)
                    
                    if medicines:
                        scores = [m.get('score', 0) for m in medicines[:3]]
                        category_scores.extend(scores)
                        all_scores.extend(scores)
                        
                        print(f"  ✅ 成功: {medicine_count}件の医薬品を推奨（応答時間: {response_time:.2f}秒）")
                        print(f"     スコア範囲: {min(scores):.3f} - {max(scores):.3f}")
                    else:
                        print(f"  ⚠️ 成功だが推奨医薬品が0件（応答時間: {response_time:.2f}秒）")
                    
                    category_response_times.append(response_time)
                    category_medicine_counts.append(medicine_count)
                    all_response_times.append(response_time)
                    all_medicine_counts.append(medicine_count)
                else:
                    failed_tests += 1
                    print(f"  ❌ 失敗: {result.get('reason', '不明なエラー')}（応答時間: {response_time:.2f}秒）")
                    
            except Exception as e:
                failed_tests += 1
                print(f"  ❌ 例外発生: {e}")
                import traceback
                traceback.print_exc()
        
        # カテゴリ別統計
        if category_response_times:
            category_stats[category] = {
                "response_times": category_response_times,
                "scores": category_scores,
                "medicine_counts": category_medicine_counts,
                "success_rate": (len(category_response_times) / len(test_cases)) * 100
            }
            
            print(f"\n【{category}の統計】")
            print(f"  成功率: {category_stats[category]['success_rate']:.1f}%")
            print(f"  平均応答時間: {statistics.mean(category_response_times):.2f}秒")
            if category_scores:
                print(f"  平均スコア: {statistics.mean(category_scores):.3f}")
                print(f"  スコア範囲: {min(category_scores):.3f} - {max(category_scores):.3f}")
    
    # 全体統計
    print(f"\n{'='*80}")
    print("全体統計")
    print(f"{'='*80}")
    print(f"総テスト数: {total_tests}")
    print(f"成功: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"失敗: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    
    if all_response_times:
        print(f"\n【応答時間】")
        print(f"  平均: {statistics.mean(all_response_times):.2f}秒")
        print(f"  中央値: {statistics.median(all_response_times):.2f}秒")
        print(f"  最小: {min(all_response_times):.2f}秒")
        print(f"  最大: {max(all_response_times):.2f}秒")
        print(f"  標準偏差: {statistics.stdev(all_response_times) if len(all_response_times) > 1 else 0:.2f}秒")
    
    if all_scores:
        print(f"\n【スコア統計】")
        print(f"  平均スコア: {statistics.mean(all_scores):.3f}")
        print(f"  中央値: {statistics.median(all_scores):.3f}")
        print(f"  最小スコア: {min(all_scores):.3f}")
        print(f"  最大スコア: {max(all_scores):.3f}")
        print(f"  標準偏差: {statistics.stdev(all_scores) if len(all_scores) > 1 else 0:.3f}")
        
        # 0.7-0.98の範囲に収まっているか確認
        scores_in_range = [s for s in all_scores if 0.7 <= s <= 0.98]
        percentage = (len(scores_in_range) / len(all_scores)) * 100 if all_scores else 0
        print(f"  0.7-0.98の範囲内: {len(scores_in_range)}/{len(all_scores)} ({percentage:.1f}%)")
        
        # スコアの分散を確認
        if statistics.stdev(all_scores) > 0.05:
            print(f"  ✅ スコアの分散が確保されています")
        else:
            print(f"  ⚠️ スコアの分散が不足しています")
    
    if all_medicine_counts:
        print(f"\n【推奨医薬品数】")
        print(f"  平均: {statistics.mean(all_medicine_counts):.1f}件")
        print(f"  中央値: {statistics.median(all_medicine_counts):.0f}件")
        print(f"  最小: {min(all_medicine_counts)}件")
        print(f"  最大: {max(all_medicine_counts)}件")
    
    # カテゴリ別詳細統計
    print(f"\n{'='*80}")
    print("カテゴリ別詳細統計")
    print(f"{'='*80}")
    for category, stats in category_stats.items():
        print(f"\n【{category}】")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        print(f"  平均応答時間: {statistics.mean(stats['response_times']):.2f}秒")
        if stats['scores']:
            print(f"  平均スコア: {statistics.mean(stats['scores']):.3f}")
            print(f"  スコア範囲: {min(stats['scores']):.3f} - {max(stats['scores']):.3f}")

def test_edge_cases():
    """エッジケースのテスト"""
    print("\n" + "="*80)
    print("エッジケースのテスト")
    print("="*80)
    
    edge_cases = [
        ("", {"age": 30, "gender": "男性"}),  # 空の入力
        ("頭が痛いです。" * 100, {"age": 30, "gender": "男性"}),  # 非常に長い入力
        ("のどが痛いです。", {"age": None, "gender": None}),  # 属性未入力
        ("のどが痛いです。", {"age": 5, "gender": "男性"}),  # 7歳未満
        ("のどが痛いです。", {"age": 30, "gender": "女性", "pregnant": True}),  # 妊娠中
        ("のどが痛いです。", {"age": 30, "gender": "女性", "breastfeeding": True}),  # 授乳中
        ("のどが痛いです。", {"age": 30, "gender": "男性", "allergies": ["イブプロフェン"]}),  # アレルギー
        ("のどが痛いです。", {"age": 30, "gender": "男性", "current_medications": ["アスピリン"]}),  # 相互作用
    ]
    
    for i, (user_text, user_info) in enumerate(edge_cases, 1):
        user_info_full = {
            **user_info,
            "pregnant": user_info.get("pregnant", False),
            "breastfeeding": user_info.get("breastfeeding", False),
            "current_medications": user_info.get("current_medications", []),
            "allergies": user_info.get("allergies", [])
        }
        
        print(f"\nエッジケース {i}: {user_text[:50]}...")
        print(f"  ユーザー情報: age={user_info.get('age')}, gender={user_info.get('gender')}, "
              f"pregnant={user_info.get('pregnant')}, breastfeeding={user_info.get('breastfeeding')}")
        
        try:
            result = rule_based_medicine_recommendation(user_text, user_info_full, client)
            
            if result.get('status') == 'success':
                medicines = result.get('recommended_medicines', [])
                print(f"  ✅ 成功: {len(medicines)}件の医薬品を推奨")
            elif result.get('status') == 'escalation_required':
                print(f"  ✅ エスカレーション: {result.get('reason', '不明')}")
            else:
                print(f"  ⚠️ 失敗: {result.get('reason', '不明なエラー')}")
                
        except Exception as e:
            print(f"  ❌ 例外発生: {e}")

def main():
    """メイン実行関数"""
    print("\n" + "="*80)
    print("システム全体の性能テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    try:
        # 1. スコアリング修正の検証
        print("\n" + "="*80)
        print("フェーズ1: スコアリング修正の検証")
        print("="*80)
        from test_scoring_fix import (
            test_score_range,
            test_specialized_medicine_bonus,
            test_inappropriate_medicine_penalty,
            test_score_diversity,
            test_relative_score,
            test_max_score_limit,
            test_bonus_penalty_effectiveness
        )
        
        test_score_range()
        test_specialized_medicine_bonus()
        test_inappropriate_medicine_penalty()
        test_score_diversity()
        test_relative_score()
        test_max_score_limit()
        test_bonus_penalty_effectiveness()
        
        # 2. システム全体の性能テスト
        print("\n" + "="*80)
        print("フェーズ2: システム全体の性能テスト")
        print("="*80)
        run_performance_test()
        
        # 3. エッジケースのテスト
        print("\n" + "="*80)
        print("フェーズ3: エッジケースのテスト")
        print("="*80)
        test_edge_cases()
        
        print("\n" + "="*80)
        print(f"[OK] 全テスト完了")
        print(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

