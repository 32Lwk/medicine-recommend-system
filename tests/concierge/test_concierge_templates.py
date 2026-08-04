"""Concierge カード HTML のスナップショット的検証"""
from src.services.concierge_templates import (
    format_concierge_architecture_card,
    format_concierge_capabilities_card,
    format_concierge_operator_card,
    structure_concierge_meta_display,
)


def test_capabilities_card_contains_otc():
    html = format_concierge_capabilities_card()
    assert "chat-status-card" in html
    assert "OTC" in html or "一般用" in html
    assert "処方" in html


def test_architecture_card_lists_agents():
    html = format_concierge_architecture_card()
    assert "ルールベース" in html
    assert "TriageAgent" in html
    assert "ConciergeAgent" in html
    assert "案内できません" not in html


def test_operator_card_has_clickable_links_without_personal_attributes():
    html = format_concierge_operator_card(
        intro_text="試験運用中のβ版です。",
    )
    assert "chat-status-card" in html
    assert "お問い合わせ・試験運用について" in html
    assert "試験運用中のβ版です。" in html
    assert 'href="https://forms.gle/UB8kZHd4VHenmRUN6"' in html
    assert 'href="mailto:weary-scoots.7y@icloud.com"' in html
    assert "川嶋" not in html
    assert "名古屋大学" not in html
    assert "GitHub" not in html


def test_deep_architecture_promotes_gcp_aws_answer_to_intro():
    body = (
        "マルチエージェントは、1つのチャットで複数の専門担当が役割分担して動く仕組みです。"
        "市販薬の候補はルールベースのスコアリングで選ばれます。"
        "\n\n"
        "GCP 本番は medicine.yutok.dev で Cloud Run 上に動き、DeepL 翻訳を使います。"
        "\n\n"
        "AWS ステージングは aws.medicine.yutok.dev で ECS 上に動き、Translate と Bedrock を使います。"
    )
    intro, sections = structure_concierge_meta_display(
        "architecture",
        body,
        deep=True,
        user_text="GCP と AWS の違いを詳しく",
    )
    assert "GCP 本番" in intro or "Cloud Run" in intro
    assert "AWS ステージング" in intro or "aws.medicine" in intro
    assert "マルチエージェント" not in intro.split("\n\n")[0]
    overview = next(
        (sec for sec in sections if sec.get("title") == "このサービスの概要"),
        None,
    )
    assert overview is not None
    assert any("マルチエージェント" in item for item in overview["items"])


def test_deep_architecture_promotes_codepipeline_answer_to_intro():
    body = (
        "最後に smoke テストとして、ヘルスチェックや翻訳、読み上げの確認を行う流れです。"
        "\n\n"
        "AWS ステージングの CodePipeline では、GitHub の main ブランチへの更新を起点に、"
        "CodeBuild で Docker イメージをビルドし ECR へ push します。"
    )
    intro, sections = structure_concierge_meta_display(
        "architecture",
        body,
        deep=True,
        user_text="CodePipeline のデプロイの流れは？",
    )
    assert "CodePipeline" in intro
    assert "smoke" not in intro.split("\n\n")[0]


def test_aws_architecture_keeps_gcp_and_aws_in_intro(monkeypatch):
    monkeypatch.setenv("AWS_STAGING", "1")
    body = (
        "つまり、どちらも同じ相談ツールですが、置いているクラウドに合わせて翻訳と読み上げのサービスが分かれています。"
        "\n\n"
        "GCP 本番は Cloud Run と DeepL、AWS ステージングは ECS と Translate/Polly です。"
        "\n\n"
        "もし必要なら、次に「本番とAWSで何が共通か」も短く説明できます。"
        "\n\n"
        "症状やお薬の選び方については、具体的な症状を入力していただければ別途ご案内します。"
    )
    intro, sections = structure_concierge_meta_display(
        "architecture",
        body,
        deep=True,
        user_text="GCPとAWSの違い",
    )
    first_para = intro.split("\n\n")[0]
    assert "もし必要なら" not in first_para
    assert "GCP" in intro or "Cloud Run" in intro
    assert "AWS" in intro or "ECS" in intro or "Translate" in intro
    offer_sections = [
        item
        for sec in sections
        for item in sec.get("items", [])
        if "もし必要なら" in item
    ]
    assert offer_sections
