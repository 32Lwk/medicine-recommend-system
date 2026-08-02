"""小児専用製品判定（_is_pediatric_specific）のテスト"""
from src.core.medicine_classifiers import (
    _is_pediatric_specific,
    _usage_indicates_pediatric_only,
)

_SHINJIKININ_USAGE = """次の1回量を(添付の計量カップではかり)食後なるべく30分以内に服用してください
3歳以上7歳未満:1回4mL
1歳以上3歳未満:1回3mL
1日3回服用
1歳未満:服用しないこと
1.小児に服用させる場合には、保護者の指導監督のもとに服用させてください
2.7歳未満の小児には、医師の診療を受けさせることを優先してください"""


class TestPediatricSpecificClassifier:
    def test_detects_shin_jikinin_syrup_by_product_name(self):
        candidate = {
            "product_name": "新小児ジキニンシロップ",
            "efficacy": "せき、発熱、頭痛、くしゃみ、鼻水、鼻づまり、のどの痛み",
            "usage": _SHINJIKININ_USAGE,
        }
        assert _is_pediatric_specific(candidate)

    def test_detects_pediatric_brand_without_yo_suffix(self):
        assert _is_pediatric_specific(
            {
                "product_name": "新チルニン小児シロップ",
                "efficacy": "発熱、せき",
                "usage": _SHINJIKININ_USAGE,
            }
        )
        assert _is_pediatric_specific(
            {
                "product_name": "赤井筒薬小児六神丸",
                "efficacy": "発熱",
                "usage": "3歳以上:1回2丸",
            }
        )

    def test_does_not_flag_adult_cold_medicines(self):
        assert not _is_pediatric_specific(
            {
                "product_name": "新スカイブブロンゴールド微粒",
                "efficacy": "かぜの諸症状(発熱、のどの痛み)の緩和",
                "usage": "成人(15歳以上)  1回1包 12歳以上15歳未満 1回2/3包 12歳未満      服用しないでください。",
            }
        )
        assert not _is_pediatric_specific(
            {
                "product_name": "バファリンかぜEX錠《瓶》",
                "efficacy": "発熱、のどの痛み",
                "usage": "15歳以上:1回2錠 15歳未満:服用しないこと",
            }
        )

    def test_usage_helper_requires_no_adult_line(self):
        assert _usage_indicates_pediatric_only(_SHINJIKININ_USAGE)
        assert not _usage_indicates_pediatric_only(
            "成人(15歳以上)  1回1包 12歳未満      服用しないでください。"
        )
