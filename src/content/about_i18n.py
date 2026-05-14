"""Localized copy for /about static pages (ja / en / ko / zh)."""

from __future__ import annotations

from typing import Any

VALID_LANGS = frozenset({"ja", "en", "ko", "zh"})


def normalize_query_lang(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    if s in VALID_LANGS:
        return s
    if s.startswith("zh"):
        return "zh"
    return None


def _sec(title: str | None, *paragraphs: str) -> dict[str, Any]:
    return {"title": title, "paragraphs": list(paragraphs)}


# page_id -> lang -> bundle (html_title, meta_description, h1, intro?, sections, cta_aria_label?)
_ABOUT: dict[str, dict[str, dict[str, Any]]] = {
    "index": {
        "ja": {
            "html_title": "概要 | チャット型医薬品相談",
            "meta_description": "本サービスの目的、各説明ページへの案内、チャット開始までの導線です。",
            "h1": "このサイトについて",
            "intro": [
                "このサイトは、チャット型の市販薬（OTC）に関する案内ツールの説明用です。画面上の「チャット」では、症状や生活背景の文章に基づき、候補となる市販薬や注意点を整理して表示しますが、診断名の提示や治療方針の決定を行うものではありません。",
                "より安全にご利用いただくため、妊娠・授乳、小児、多くの併用薬、アレルギー歴などはチャット内のユーザー情報登録や会話で可能な範囲でお知らせください。表示内容に不安がある場合は、購入前に薬剤師・医師など専門家へ相談してください。",
                "上のナビから各ページへ進めます（アプリ概要、使い方・FAQ、規約・プライバシー、公的相談窓口など）。本文はチャット画面の ℹ 一覧と同一の内容です。緊急や急変のときは、迷わず医療機関・救急（日本国内では 119 番）・公的相談窓口をご利用ください。",
            ],
            "hero_image": "img/about/medicine_recommended.png",
            "hero_caption": "参考イメージ：候補の市販薬が表示される画面の一例。実際の UI はアップデートにより異なる場合があります。",
            "sections": [],
            "cta_aria_label": "チャット相談のトップページを開く",
        },
        "en": {
            "html_title": "Overview | Chat OTC consultation",
            "meta_description": "Purpose of this service, links to policies, and how to start the chat.",
            "h1": "About this site",
            "intro": [
                "This site documents the chat-based OTC (non-prescription) medicine guidance tool. In the chat, the app organizes possible OTC options and cautions from your text, but it does not provide a medical diagnosis or prescribe a treatment plan.",
                "For safer use, share pregnancy/breastfeeding status, age, other medicines, and allergies when you can—via the profile form or the conversation. If anything is unclear, consult a pharmacist or clinician before you buy or take a medicine.",
                "Use the navigation for the overview, app summary, guide & FAQ, terms & privacy, and public helplines. The article text matches the in-app ℹ help. In an emergency or sudden worsening, call local emergency services (e.g. 119 in Japan) or seek immediate in-person care.",
            ],
            "hero_image": "img/about/medicine_recommended.png",
            "hero_caption": "Illustrative screenshot of OTC suggestions in the chat UI; the live UI may differ after updates.",
            "sections": [],
            "cta_aria_label": "Open the chat consultation home page",
        },
        "ko": {
            "html_title": "개요 | 채팅형 일반의약품 상담",
            "meta_description": "서비스 목적, 안내 페이지 링크, 채팅 시작 안내입니다.",
            "h1": "이 사이트에 대하여",
            "intro": [
                "이 사이트는 채팅형 일반의약품(OTC) 안내 도구를 설명하기 위한 페이지입니다. 채팅에서는 증상·생활 정보를 바탕으로 후보 약과 주의점을 정리해 보여 주지만, 진단명 제시나 치료方針 결정을 대신하지 않습니다.",
                "임신·수유, 소아, 복용 중인 약, 알레르기 등은 가능한 범위에서 프로필이나 대화로 알려 주시면 더 안전한 안내에 도움이 됩니다. 표시 내용이 불안하면 구매·복용 전에 약사·의사 등 전문가와 상담하세요.",
                "상단 내비에서 개요, 앱 요약, 사용 안내·FAQ, 약관·개인정보, 공공 상담 등으로 이동할 수 있습니다. 본문은 채팅 화면 ℹ 목록과 동일합니다. 응급이나 급변 시에는 의료기관·응급(일본에서는 119번)·공공 상담 창구를 이용해 주세요.",
            ],
            "hero_image": "img/about/medicine_recommended.png",
            "hero_caption": "참고 이미지: 후보 일반의약품이 표시되는 화면 예시입니다. 실제 UI는 업데이트에 따라 달라질 수 있습니다.",
            "sections": [],
            "cta_aria_label": "채팅 상담 첫 화면으로 이동",
        },
        "zh": {
            "html_title": "概览 | 聊天式非处方药咨询",
            "meta_description": "服务目的、说明页面导航与开始聊天的入口。",
            "h1": "关于本站",
            "intro": [
                "本站用于说明聊天式非处方药（OTC）咨询工具。聊天会根据您描述的症状与情况整理候选药与注意事项，但不提供医学诊断，也不替代治疗方案的决定。",
                "为更安全地使用，请在可能范围内通过资料或对话说明妊娠/哺乳、年龄、正在服用的药物、过敏史等。若对展示内容有疑问，请在购药或服药前咨询药师或医生。",
                "可通过顶部导航浏览概览、应用概要、使用说明与常见问题、条款与隐私以及公共咨询等。正文与聊天内 ℹ 菜单中的说明一致。紧急或病情急变时，请立即前往医疗机构或拨打当地急救电话（日本为 119）等公共服务。",
            ],
            "hero_image": "img/about/medicine_recommended.png",
            "hero_caption": "示意图：聊天中展示非处方药候选的界面示例；实际界面可能随版本更新而变化。",
            "sections": [],
            "cta_aria_label": "打开聊天咨询首页",
        },
    },
    "info": {
        "ja": {
            "html_title": "アプリ概要・運営者情報 | チャット型医薬品相談",
            "meta_description": "β版の位置づけ、開発背景、利用目的、主な特徴、運用・技術情報、データ出典、注意事項、運営者情報。チャット内 ℹ と同一の本文です。",
            "h1": "アプリ概要・運営者情報",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "App overview & operator | Chat OTC consultation",
            "meta_description": "Beta scope, background, purpose, features, stack, data sources, notices, and contacts—same body as the in-app ℹ help.",
            "h1": "App overview & operator",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "앱 개요·운영자 정보 | 채팅형 일반의약품 상담",
            "meta_description": "β판 범위, 배경, 목적, 주요 기능, 운영·기술 정보, 데이터 출처, 주의, 연락처 등. 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "앱 개요·운영자 정보",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "应用概述与运营者 | 聊天式非处方药咨询",
            "meta_description": "测试版定位、背景、目的、主要特点、运营与技术信息、数据来源、注意事项与联系方式。正文与聊天内 ℹ 帮助一致。",
            "h1": "应用概述与运营者",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "privacy": {
        "ja": {
            "html_title": "プライバシーポリシー（β版）| チャット型医薬品相談",
            "meta_description": "第1条〜第8条相当の全文（試験運用における取得情報、利用目的、第三者提供、匿名加工情報、テスターの権利、改定など）。チャット内 ℹ と同一の本文です。",
            "h1": "プライバシーポリシー",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "Privacy Policy (Beta) | Chat OTC consultation",
            "meta_description": "Full beta privacy articles (collection, purposes, disclosure, anonymized data, rights, revisions)—same body as the in-app ℹ help.",
            "h1": "Privacy Policy",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "개인정보 취급방침(시험운용) | 채팅형 일반의약품 상담",
            "meta_description": "제1조~제8조에 해당하는 전문(시험운용 중 수집·이용·제3자 제공·익명가공·권리·개정 등). 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "개인정보 취급방침",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "隐私政策（测试版）| 聊天式非处方药咨询",
            "meta_description": "与第1至第8条相当的全文（测试运营中的收集、使用目的、第三方提供、匿名加工信息、权利与修订等）。正文与聊天内 ℹ 帮助一致。",
            "h1": "隐私政策",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "terms": {
        "ja": {
            "html_title": "免責事項・利用規約（β版）| チャット型医薬品相談",
            "meta_description": "第1条〜第8条相当の全文（試験運用、免責、禁止事項、準拠法・管轄など）。チャット内 ℹ と同一の本文です。",
            "h1": "免責事項・利用規約",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "Disclaimer & Terms (Beta) | Chat OTC consultation",
            "meta_description": "Full beta terms articles (testing scope, disclaimer, prohibited conduct, governing law)—same body as the in-app ℹ help.",
            "h1": "Disclaimer & Terms of Use",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "면책 및 이용약관(시험운용) | 채팅형 일반의약품 상담",
            "meta_description": "제1조~제8조에 해당하는 전문(시험운용, 면책, 금지, 준거법 등). 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "면책 및 이용약관",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "免责声明与使用条款（测试版）| 聊天式非处方药咨询",
            "meta_description": "与第1至第8条相当的全文（测试运营、免责、禁止事项、适用法律与管辖等）。正文与聊天内 ℹ 帮助一致。",
            "h1": "免责声明与使用条款",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "usage": {
        "ja": {
            "html_title": "使い方 | チャット型医薬品相談",
            "meta_description": "基本的な操作、便利機能、安全に使うための注意。チャット内 ℹ と同一の本文です。",
            "h1": "使い方",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "How to use | Chat OTC consultation",
            "meta_description": "Steps, features, and safety notes—same body as the in-app ℹ help.",
            "h1": "How to use",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "사용 방법 | 채팅형 일반의약품 상담",
            "meta_description": "기본 조작, 편의 기능, 안전 유의사항. 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "사용 방법",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "使用方法 | 聊天式非处方药咨询",
            "meta_description": "基本操作、便利功能与安全注意事项。正文与聊天内 ℹ 帮助一致。",
            "h1": "使用方法",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "faq": {
        "ja": {
            "html_title": "よくある質問（FAQ）| チャット型医薬品相談",
            "meta_description": "操作、薬剤師要請、推奨、データ・プライバシー、不具合などの Q&A。チャット内 ℹ と同一の本文です。",
            "h1": "よくある質問（FAQ）",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "FAQ | Chat OTC consultation",
            "meta_description": "Operations, pharmacist request, recommendations, privacy, and troubleshooting—same body as the in-app ℹ help.",
            "h1": "FAQ",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "자주 묻는 질문 (FAQ) | 채팅형 일반의약품 상담",
            "meta_description": "조작, 약사 요청, 추천, 데이터·프라이버시, 불구 등 Q&A. 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "자주 묻는 질문 (FAQ)",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "常见问题 (FAQ) | 聊天式非处方药咨询",
            "meta_description": "操作、药师咨询、推荐、数据与隐私、故障等问答。正文与聊天内 ℹ 帮助一致。",
            "h1": "常见问题 (FAQ)",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "policies": {
        "ja": {
            "html_title": "免責事項・利用規約 / プライバシー | チャット型医薬品相談",
            "meta_description": "β版の利用規約とプライバシーポリシーを同一ページに掲載しています。チャット内 ℹ と同一の本文です。",
            "h1": "免責事項・利用規約 / プライバシーポリシー",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "Terms & privacy (beta) | Chat OTC consultation",
            "meta_description": "Beta disclaimer/terms of use and privacy policy on one page—same body as the in-app ℹ help.",
            "h1": "Disclaimer & terms / Privacy policy",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "이용약관 / 개인정보 | 채팅형 일반의약품 상담",
            "meta_description": "β판 이용약관과 개인정보 처리방침을 한 페이지에 게시합니다. 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "면책·이용약관 / 개인정보 취급방침",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "条款与隐私（测试版）| 聊天式非处方药咨询",
            "meta_description": "测试版免责声明与使用条款及隐私政策合页展示。正文与聊天内 ℹ 帮助一致。",
            "h1": "免责声明与条款 / 隐私政策",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
    "consultation": {
        "ja": {
            "html_title": "医薬品相談先 | チャット型医薬品相談",
            "meta_description": "PMDA・厚生労働省等の公的リンクと緊急時の案内。チャット内 ℹ と同一の本文です。",
            "h1": "医薬品相談先",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "en": {
            "html_title": "Consultation resources | Chat OTC consultation",
            "meta_description": "Public links (PMDA, MHLW, emergencies)—same body as the in-app ℹ help.",
            "h1": "Medicine & health consultation (public)",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "ko": {
            "html_title": "의약품 상담 정보 | 채팅형 일반의약품 상담",
            "meta_description": "PMDA·후생노동성 등 공공 링크와 응급 안내. 채팅 내 ℹ 도움말과 동일한 본문입니다.",
            "h1": "의약품·건강 상담 창구",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
        "zh": {
            "html_title": "药品咨询信息 | 聊天式非处方药咨询",
            "meta_description": "PMDA、厚生劳动省等公共链接与紧急指引。正文与聊天内 ℹ 帮助一致。",
            "h1": "药品·健康咨询（公共信息）",
            "intro": [],
            "sections": [],
            "cta_aria_label": None,
        },
    },
}


def get_about_bundle(page_id: str, lang: str) -> dict[str, Any]:
    if page_id not in _ABOUT:
        raise KeyError(page_id)
    lg = lang if lang in VALID_LANGS else "ja"
    return dict(_ABOUT[page_id][lg])


def nav_labels(lang: str) -> dict[str, str]:
    lg = lang if lang in VALID_LANGS else "ja"
    labels = {
        "ja": {
            "index": "概要",
            "info": "アプリ概要",
            "usage_faq": "使い方・FAQ",
            "policies": "規約・プライバシー",
            "consultation": "相談先",
        },
        "en": {
            "index": "Overview",
            "info": "App overview",
            "usage_faq": "Guide & FAQ",
            "policies": "Terms & privacy",
            "consultation": "Helplines",
        },
        "ko": {
            "index": "개요",
            "info": "앱 개요",
            "usage_faq": "사용·FAQ",
            "policies": "약관·개인정보",
            "consultation": "상담 창구",
        },
        "zh": {
            "index": "概览",
            "info": "应用概要",
            "usage_faq": "使用与常见问题",
            "policies": "条款与隐私",
            "consultation": "咨询窗口",
        },
    }
    return labels[lg]


def about_path_prefix(app_base_path: str) -> str:
    bp = (app_base_path or "").strip().rstrip("/")
    return f"{bp}/about" if bp else "/about"


def about_shell_labels(lang: str, app_base_path: str = "") -> dict[str, str]:
    """Labels for about layout (skip link, nav aria, footer, CTA note)."""
    lg = lang if lang in VALID_LANGS else "ja"
    prefix = about_path_prefix(app_base_path)
    rows = {
        "ja": {
            "skip_to_content": "本文へスキップ",
            "site_name_label": "チャット型医薬品相談 · 説明",
            "lang_nav_label": "表示言語",
            "header_chat_title": "チャット画面を開く（同一タブ）",
            "breadcrumb_label": "パンくず",
            "section_nav_label": "サイト内のページ",
            "subpages_heading": "各トピックのページ",
            "cta_visible_text": "チャットを始める",
            "cta_footer_note": "",
            "footer_note": "本サイトはチャット型ツールの説明用です。診断や服薬の最終判断は医療専門家へご相談ください。",
            "footer_chat_label": "チャットへ",
            "footer_policies_label": "規約・プライバシー",
            "footer_rights": "© 2026 チャット型医薬品相談（説明サイト）",
        },
        "en": {
            "skip_to_content": "Skip to main content",
            "site_name_label": "Chat OTC assistant · About",
            "lang_nav_label": "Display language",
            "header_chat_title": "Open chat (same tab)",
            "breadcrumb_label": "Breadcrumb",
            "section_nav_label": "Pages on this site",
            "subpages_heading": "Topics",
            "cta_visible_text": "チャットを始める",
            "cta_footer_note": "The chat button label is intentionally shown in Japanese.",
            "footer_note": "This site documents the chat tool. For medical decisions, consult a qualified professional.",
            "footer_chat_label": "Open chat",
            "footer_policies_label": "Terms & privacy",
            "footer_rights": "© 2026 Chat OTC assistant (about site)",
        },
        "ko": {
            "skip_to_content": "본문으로 건너뛰기",
            "site_name_label": "채팅형 일반의약품 상담 · 안내",
            "lang_nav_label": "표시 언어",
            "header_chat_title": "채팅 화면 열기(같은 탭)",
            "breadcrumb_label": "이동 경로",
            "section_nav_label": "사이트 내 페이지",
            "subpages_heading": "주제별 페이지",
            "cta_visible_text": "チャットを始める",
            "cta_footer_note": "채팅 버튼 표기는 의도적으로 일본어로 고정되어 있습니다.",
            "footer_note": "본 사이트는 채팅 도구 안내용입니다. 의학적 판단은 전문가와 상담하세요.",
            "footer_chat_label": "채팅으로",
            "footer_policies_label": "약관·개인정보",
            "footer_rights": "© 2026 채팅형 일반의약품 상담(안내 사이트)",
        },
        "zh": {
            "skip_to_content": "跳到正文",
            "site_name_label": "聊天式非处方药咨询 · 说明",
            "lang_nav_label": "显示语言",
            "header_chat_title": "打开聊天（同一标签页）",
            "breadcrumb_label": "面包屑导航",
            "section_nav_label": "站内页面",
            "subpages_heading": "各主题页面",
            "cta_visible_text": "チャットを始める",
            "cta_footer_note": "聊天按钮上的文字按设计固定为日语。",
            "footer_note": "本站用于说明聊天工具。医疗与用药决策请咨询专业人员。",
            "footer_chat_label": "进入聊天",
            "footer_policies_label": "条款与隐私",
            "footer_rights": "© 2026 聊天式非处方药咨询（说明站点）",
        },
    }
    out = dict(rows[lg])
    out["footer_policies_href"] = f"{prefix}/policies"
    return out


def about_subpage_links(lang: str, app_base_path: str) -> list[dict[str, str]]:
    prefix = about_path_prefix(app_base_path)
    lab = nav_labels(lang)
    return [
        {"href": f"{prefix}/info", "label": lab["info"]},
        {"href": f"{prefix}/usage", "label": lab["usage_faq"]},
        {"href": f"{prefix}/policies", "label": lab["policies"]},
        {"href": f"{prefix}/consultation", "label": lab["consultation"]},
    ]


def about_nav_entries(page_id: str, lang: str, app_base_path: str) -> list[dict[str, Any]]:
    """Compact nav: overview, app, guide (usage+faq), legal (terms+privacy+policies), helplines."""
    prefix = about_path_prefix(app_base_path)
    lab = nav_labels(lang)

    def is_current(nav_id: str) -> bool:
        if nav_id == "guide":
            return page_id in ("usage", "faq")
        if nav_id == "policies":
            return page_id in ("terms", "privacy", "policies")
        return page_id == nav_id

    items = [
        ("index", prefix, lab["index"]),
        ("info", f"{prefix}/info", lab["info"]),
        ("guide", f"{prefix}/usage", lab["usage_faq"]),
        ("policies", f"{prefix}/policies", lab["policies"]),
        ("consultation", f"{prefix}/consultation", lab["consultation"]),
    ]
    return [
        {
            "id": pid,
            "href": href,
            "label": label,
            "current": is_current(pid),
        }
        for pid, href, label in items
    ]


def about_lang_switch_rows() -> list[tuple[str, str]]:
    return [("ja", "日本語"), ("en", "English"), ("ko", "한국어"), ("zh", "中文")]
