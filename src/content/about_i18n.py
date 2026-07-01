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
            "meta_description": "β版の位置づけ、課題、使い方、安全性、技術概要。専門関係者向けの研究・検証用説明サイトです。",
            "h1": "チャットで、市販薬選びの一助を",
            "intro": [],
            "hero_title": "チャットで、市販薬選びの一助を",
            "hero_subtitle": "ルールベース推奨 × LLM のハイブリッド。症状・体調・生活背景から OTC 候補と注意点を整理します。診断・処方の代替ではありません。",
            "beta_badge": "🔬 研究β版｜専門家向け・非診断",
            "scroll_hint": "スクロール",
            "hero_image": "img/about/generated/about/hero/hero-pharmacy-chat.png",
            "hero_alt": "薬局とチャットで相談するイメージ",
            "hero_cta": "チャットを試す",
            "problem_section_num": "01",
            "problem_section_tag": "課題",
            "problem_heading": "現場の3つの壁",
            "problem_lead": "少子高齢化・訪日外国人・EC の拡大のなか、薬局と利用者の双方に負荷が偏っています。",
            "how_section_num": "02",
            "how_section_tag": "使い方",
            "features_section_num": "03",
            "features_section_tag": "特徴",
            "safety_section_num": "04",
            "safety_section_tag": "安全",
            "tech_section_num": "05",
            "tech_section_tag": "技術",
            "trust_section_num": "06",
            "trust_section_tag": "信頼",
            "footer_cta_heading": "専門家向け β を試す",
            "footer_cta_lead": "ルールベース推奨と LLM の挙動を、チャットでご確認ください。",
            "problem_cards": [
                {
                    "emoji": "🌐",
                    "title": "言語の壁",
                    "body": "訪日外国人など、母語で相談しづらく、適切な市販薬選びが難しい場面があります。",
                },
                {
                    "emoji": "🏥",
                    "title": "人手不足",
                    "body": "薬局・ドラッグストアでは、相談時間の確保が難しく、利用者の不安が残ることがあります。",
                },
                {
                    "emoji": "💊",
                    "title": "選びにくさ",
                    "body": "症状に合う市販薬がわからず、安全性への不安が生じる利用者がいます。",
                },
            ],
            "how_heading": "3ステップで使える",
            "how_steps": [
                {
                    "num": "①",
                    "title": "症状を入力",
                    "body": "専門知識がなくても、会話のように症状や生活背景を文章で入力します。",
                },
                {
                    "num": "②",
                    "title": "候補を整理",
                    "body": "医薬品DB・薬学的知識・ルールベース推奨を中核に、LLMは補助的に活用。候補と注意点を表示します。",
                },
                {
                    "num": "③",
                    "title": "判断の参考に",
                    "body": "受診の目安や注意喚起を確認し、購入・服用前は薬剤師・医師へ相談してください。",
                },
            ],
            "how_demo_image": "img/about/generated/about/demo/demo-ipad-product.png",
            "how_demo_alt": "iPad 上のチャット型医薬品相談ツール（β版）の実画面スクリーンショット",
            "how_demo_caption": "実際のチャット画面（β版）。推奨医薬品・注意喚起などが表示されます。",
            "features_heading": "4つの強み",
            "feature_cards": [
                {
                    "emoji": "🛡️",
                    "title": "安全性設計",
                    "body": "ルールベース推奨を中核に。危険な症状では受診を推奨し、誤情報抑制を図ります。",
                },
                {
                    "emoji": "🧠",
                    "title": "ハイブリッド推奨",
                    "body": "ルールベースのスコアリングで薬選定を一貫。LLM は症状整理・質問生成などに補助し、根拠と言語理解を両立します。",
                },
                {
                    "emoji": "🌐",
                    "title": "4言語対応",
                    "body": "日本語・英語・中国語・韓国語（DeepL API による高速翻訳）。",
                },
                {
                    "emoji": "♿",
                    "title": "アクセシビリティ",
                    "body": "文字サイズの変更、音声読み上げ、折りたたみ可能な表示。コントラストは WCAG AA を意識した設計です。",
                },
            ],
            "safety_heading": "安全に使うために",
            "safety_lead": "本ツールは医療行為・診断・処方の代替ではありません。",
            "safety_items": [
                "重篤な症状や長期化する場合は、速やかに医療機関を受診してください。",
                "日本国内の緊急時は 119 番（救急）・医療機関・公的相談窓口をご利用ください。",
                "表示内容に不安がある場合は、購入・服用前に必ず薬剤師または医師にご相談ください。",
                "妊娠・授乳、小児、併用薬、アレルギー歴などは、可能な範囲でチャット内にお知らせください。",
            ],
            "pharmacist_note": "薬剤師への相談が必要な場合のエスカレーション機能を備えています（実装状況はアプリ版により異なります）。",
            "pharmacist_icon": "img/about/generated/about/icons/icon-pharmacist.png",
            "pharmacist_alt": "薬剤師への相談",
            "tech_heading": "技術スタック",
            "tech_lead": "β版の構成要素です。薬の選定ロジックはルールベースを中核とし、LLM は補助的に利用します。",
            "tech_bullets": [
                "推奨エンジン: 症状辞書・効能・年齢・副作用・相互作用などを統合する独自ルールベーススコアリング",
                "マルチエージェント: LLM_AGENT_ENABLED 時は ChatOrchestrator がトリアージ後に専門エージェントへハンドオフ（Triage / Physical / Concierge 等）",
                "フロントエンド: HTML/CSS/バニラ JS（レスポンシブ）",
                "ログ: JSONL 構造化ログ（アクセス・性能・セキュリティ監視）",
            ],
            "tech_details_label": "補足・詳細",
            "trust_heading": "運用体制",
            "trust_lead": "非営利・学術研究目的の β 試験運用です（アプリ概要ドキュメント準拠）。",
            "trust_cards": [
                {
                    "title": "ソース管理",
                    "body": "GitHub でバージョン管理。CI/CD は GCP Cloud Build と連携。",
                },
                {
                    "title": "本番ホスティング",
                    "body": "GCP Cloud Run（リージョン asia-northeast1）。Docker + Gunicorn。",
                },
                {
                    "title": "データベース",
                    "body": "Neon PostgreSQL（サーバーレス）。セッション・グローバル状態など。",
                },
                {
                    "title": "ログと監視",
                    "body": "JSONL 構造化ログ。アクセス・パフォーマンス・セキュリティを監視。",
                },
            ],
            "trust_beta_note": "公開範囲は医療・行政・研究機関・薬剤師など限られた関係者向けの実証・検証です。一般向けの正式公開は検討段階です。",
            "sections": [],
            "cta_aria_label": "チャット相談のトップページを開く",
        },
        "en": {
            "html_title": "Overview | Chat OTC consultation",
            "meta_description": "Beta scope, challenges, how it works, safety, and technical overview for specialist evaluation.",
            "h1": "Chat guidance for OTC choices",
            "intro": [],
            "hero_title": "Chat guidance for OTC choices",
            "hero_subtitle": "Rule-based scoring × LLM assist. Organizes OTC options and cautions from your symptoms—not a substitute for diagnosis or prescribing.",
            "beta_badge": "🔬 Research beta · specialists · non-diagnostic",
            "scroll_hint": "SCROLL",
            "hero_image": "img/about/generated/about/hero/hero-pharmacy-chat.png",
            "hero_alt": "Illustration of pharmacy chat consultation",
            "hero_cta": "Try the chat",
            "problem_section_num": "01",
            "problem_section_tag": "Challenges",
            "problem_heading": "Three pressures on the ground",
            "problem_lead": "Aging populations, language barriers, and e-commerce are shifting demand—and strain—on pharmacies and shoppers alike.",
            "how_section_num": "02",
            "how_section_tag": "How it works",
            "features_section_num": "03",
            "features_section_tag": "Features",
            "safety_section_num": "04",
            "safety_section_tag": "Safety",
            "tech_section_num": "05",
            "tech_section_tag": "Stack",
            "trust_section_num": "06",
            "trust_section_tag": "Trust",
            "footer_cta_heading": "Try the specialist beta",
            "footer_cta_lead": "Explore rule-based recommendations and LLM-assisted chat in the live UI.",
            "problem_cards": [
                {
                    "emoji": "🌐",
                    "title": "Language barriers",
                    "body": "Visitors and residents may struggle to consult in their language and choose appropriate OTC products.",
                },
                {
                    "emoji": "🏥",
                    "title": "Staffing pressure",
                    "body": "Pharmacies have limited time for counseling, leaving some users uncertain.",
                },
                {
                    "emoji": "💊",
                    "title": "Hard to choose",
                    "body": "Users may not know which OTC fits their symptoms and worry about safety.",
                },
            ],
            "how_heading": "Three steps to use",
            "how_steps": [
                {
                    "num": "①",
                    "title": "Describe symptoms",
                    "body": "Type symptoms and context in plain language—no medical jargon required.",
                },
                {
                    "num": "②",
                    "title": "See organized options",
                    "body": "Drug DB, pharmaceutical rules, and rule-based scoring are core; the LLM assists NLU and questions.",
                },
                {
                    "num": "③",
                    "title": "Use as reference",
                    "body": "Review cautions and when to seek care; consult a pharmacist or clinician before buying or taking medicine.",
                },
            ],
            "how_demo_image": "img/about/generated/about/demo/demo-ipad-product.png",
            "how_demo_alt": "Screenshot of the chat OTC consultation tool (beta) on iPad",
            "how_demo_caption": "Live chat UI (beta) showing recommendations and safety notices.",
            "features_heading": "Four strengths",
            "feature_cards": [
                {
                    "emoji": "🛡️",
                    "title": "Safety by design",
                    "body": "Rule-based core; refers to in-person care when symptoms are serious.",
                },
                {
                    "emoji": "🧠",
                    "title": "Hybrid recommendation",
                    "body": "Rule-based scoring drives drug selection; the LLM assists NLU and questions only.",
                },
                {
                    "emoji": "🌐",
                    "title": "Four languages",
                    "body": "Japanese, English, Chinese, and Korean via DeepL API.",
                },
                {
                    "emoji": "♿",
                    "title": "Accessibility",
                    "body": "Font sizing, text-to-speech, and collapsible sections; WCAG AA–oriented contrast.",
                },
            ],
            "safety_heading": "Use safely",
            "safety_lead": "This tool does not replace medical care, diagnosis, or prescribing.",
            "safety_items": [
                "Seek in-person care promptly for severe or prolonged symptoms.",
                "In Japan, call 119 for emergencies and use public helplines or clinics as needed.",
                "If unsure about displayed information, consult a pharmacist or clinician before use.",
                "Share pregnancy/breastfeeding, pediatrics, other medicines, and allergies when you can in chat.",
            ],
            "pharmacist_note": "Escalation to a pharmacist may be available depending on the deployed app version.",
            "pharmacist_icon": "img/about/generated/about/icons/icon-pharmacist.png",
            "pharmacist_alt": "Pharmacist consultation",
            "tech_heading": "Technology stack",
            "tech_lead": "Beta building blocks. Rule-based logic is core for drug selection; the LLM assists.",
            "tech_bullets": [
                "Recommendation: proprietary rule-based scoring (symptoms, efficacy, age, interactions, etc.)",
                "Multi-agent: with LLM_AGENT_ENABLED, ChatOrchestrator hands off after triage (Triage, Physical, Concierge, etc.)",
                "Frontend: HTML/CSS/vanilla JS (responsive)",
                "Logs: JSONL structured logs (access, performance, security)",
            ],
            "tech_details_label": "More detail",
            "trust_heading": "Operations",
            "trust_lead": "Non-profit academic beta trial (per app overview documentation).",
            "trust_cards": [
                {"title": "Source control", "body": "GitHub versioning; CI/CD via GCP Cloud Build."},
                {"title": "Production hosting", "body": "GCP Cloud Run (asia-northeast1). Docker + Gunicorn."},
                {"title": "Database", "body": "Neon PostgreSQL (serverless) for sessions and global state."},
                {"title": "Logs & monitoring", "body": "JSONL structured logs; access, performance, and security monitoring."},
            ],
            "trust_beta_note": "Limited to healthcare, government, research, and pharmacy specialists—not a general public launch.",
            "sections": [],
            "cta_aria_label": "Open the chat consultation home page",
        },
        "ko": {
            "html_title": "개요 | 채팅형 일반의약품 상담",
            "meta_description": "β판 범위, 과제, 사용 방법, 안전, 기술 개요. 전문가 평가용 안내 사이트입니다.",
            "h1": "채팅으로, OTC 선택을 돕습니다",
            "intro": [],
            "hero_title": "채팅으로, OTC 선택을 돕습니다",
            "hero_subtitle": "규칙 기반 추천 × LLM 하이브리드. 증상·생활 정보에서 OTC 후보와 주의점을 정리합니다. 진단·처방 대체가 아닙니다.",
            "beta_badge": "🔬 연구 β판｜전문가·비진단",
            "scroll_hint": "스크롤",
            "hero_image": "img/about/generated/about/hero/hero-pharmacy-chat.png",
            "hero_alt": "약국과 채팅 상담 이미지",
            "hero_cta": "채팅 체험",
            "problem_section_num": "01",
            "problem_section_tag": "과제",
            "problem_heading": "현장의 세 가지 벽",
            "problem_lead": "고령화·방문 외국인·EC 확대 속에서 약국과 이용자 모두에 부담이 쏠리고 있습니다.",
            "how_section_num": "02",
            "how_section_tag": "사용법",
            "features_section_num": "03",
            "features_section_tag": "특징",
            "safety_section_num": "04",
            "safety_section_tag": "안전",
            "tech_section_num": "05",
            "tech_section_tag": "기술",
            "trust_section_num": "06",
            "trust_section_tag": "신뢰",
            "footer_cta_heading": "전문가용 β 체험",
            "footer_cta_lead": "규칙 기반 추천과 LLM 동작을 채팅에서 확인해 보세요.",
            "problem_cards": [
                {
                    "emoji": "🌐",
                    "title": "언어 장벽",
                    "body": "방문 외국인 등 모국어로 상담하기 어려워 적절한 OTC 선택이 힘든 경우가 있습니다.",
                },
                {
                    "emoji": "🏥",
                    "title": "인력 부족",
                    "body": "약국·드럭스토어에서 상담 시간 확보가 어려워 이용자 불안이 남을 수 있습니다.",
                },
                {
                    "emoji": "💊",
                    "title": "선택의 어려움",
                    "body": "증상에 맞는 OTC를 모르거나 안전성에 대한 불안이 있는 이용자가 있습니다.",
                },
            ],
            "how_heading": "3단계로 이용",
            "how_steps": [
                {
                    "num": "①",
                    "title": "증상 입력",
                    "body": "전문 용어 없이 대화처럼 증상과 생활 배경을 입력합니다.",
                },
                {
                    "num": "②",
                    "title": "후보 정리",
                    "body": "의약품 DB·약학 지식·규칙 기반 추천을 중심으로 LLM은 보조적으로 활용합니다.",
                },
                {
                    "num": "③",
                    "title": "판단 참고",
                    "body": "진료 권고·주의를 확인하고 구매·복용 전 약사·의사와 상담하세요.",
                },
            ],
            "how_demo_image": "img/about/generated/about/demo/demo-ipad-product.png",
            "how_demo_alt": "iPad의 채팅형 OTC 상담 도구(β) 실제 화면",
            "how_demo_caption": "실제 채팅 화면(β). 추천 의약품·주의 안내가 표시됩니다.",
            "features_heading": "네 가지 강점",
            "feature_cards": [
                {
                    "emoji": "🛡️",
                    "title": "안전 설계",
                    "body": "규칙 기반 중심. 위험 증상 시 진료를 권장하고 오정보 억제를 도모합니다.",
                },
                {
                    "emoji": "🧠",
                    "title": "하이브리드 추천",
                    "body": "규칙 기반 스코어링으로 약 선택을 일관되게 수행하고, LLM은 증상 정리·질문 생성 등에 보조합니다.",
                },
                {
                    "emoji": "🌐",
                    "title": "4개 언어",
                    "body": "일본어·영어·중국어·한국어(DeepL API 고속 번역).",
                },
                {
                    "emoji": "♿",
                    "title": "접근성",
                    "body": "글자 크기, 음성 읽기, 접기 가능 UI. WCAG AA 대비를 고려합니다.",
                },
            ],
            "safety_heading": "안전하게 사용하기",
            "safety_lead": "본 도구는 의료행위·진단·처방을 대체하지 않습니다.",
            "safety_items": [
                "중증·장기화 증상은 신속히 의료기관을 방문하세요.",
                "일본 국내 응급 시 119번·의료기관·공공 상담을 이용하세요.",
                "표시 내용이 불안하면 구매·복용 전 약사·의사와 상담하세요.",
                "임신·수유, 소아, 복용 약, 알레르기 등은 가능한 범위에서 알려 주세요.",
            ],
            "pharmacist_note": "약사 상담 에스컬레이션 기능이 있을 수 있습니다(배포 버전에 따라 다름).",
            "pharmacist_icon": "img/about/generated/about/icons/icon-pharmacist.png",
            "pharmacist_alt": "약사 상담",
            "tech_heading": "기술 스택",
            "tech_lead": "β판 구성 요소. 약 선택은 규칙 기반 중심, LLM은 보조입니다.",
            "tech_bullets": [
                "추천: 증상·효능·연령·부작용·상호작용 통합 규칙 스코어링",
                "멀티 에이전트: LLM_AGENT_ENABLED 시 ChatOrchestrator가 트리아지 후 전문 에이전트로 핸드오프",
                "프론트엔드: HTML/CSS/바닐라 JS(반응형)",
                "로그: JSONL 구조화(접근·성능·보안)",
            ],
            "tech_details_label": "보충 설명",
            "trust_heading": "운영 체계",
            "trust_lead": "비영리·학술 목적 β 시험 운용(앱 개요 문서 기준).",
            "trust_cards": [
                {"title": "소스 관리", "body": "GitHub 버전 관리. CI/CD는 GCP Cloud Build 연동."},
                {"title": "운영 호스팅", "body": "GCP Cloud Run(asia-northeast1). Docker + Gunicorn."},
                {"title": "데이터베이스", "body": "Neon PostgreSQL(서버리스). 세션·글로벌 상태 등."},
                {"title": "로그·모니터링", "body": "JSONL 구조화 로그. 접근·성능·보안 모니터링."},
            ],
            "trust_beta_note": "의료·행정·연구·약사 등 제한 관계자 대상 실증·검증. 일반 공개는 검토 단계입니다.",
            "sections": [],
            "cta_aria_label": "채팅 상담 첫 화면으로 이동",
        },
        "zh": {
            "html_title": "概览 | 聊天式非处方药咨询",
            "meta_description": "测试版定位、课题、用法、安全与技术概要。面向专业人士的评估说明站。",
            "h1": "聊天助力，OTC 选择更安心",
            "intro": [],
            "hero_title": "聊天助力，OTC 选择更安心",
            "hero_subtitle": "规则推荐 × LLM 混合方式。根据症状与生活背景整理 OTC 候选与注意事项。非诊断或处方替代。",
            "beta_badge": "🔬 研究测试版｜专业人士·非诊断",
            "scroll_hint": "向下滚动",
            "hero_image": "img/about/generated/about/hero/hero-pharmacy-chat.png",
            "hero_alt": "药店与聊天咨询示意图",
            "hero_cta": "体验聊天",
            "problem_section_num": "01",
            "problem_section_tag": "课题",
            "problem_heading": "现场的三大压力",
            "problem_lead": "在老龄化、访日外国人与电商普及的背景下，药店与使用者双方都承受更大压力。",
            "how_section_num": "02",
            "how_section_tag": "用法",
            "features_section_num": "03",
            "features_section_tag": "特点",
            "safety_section_num": "04",
            "safety_section_tag": "安全",
            "tech_section_num": "05",
            "tech_section_tag": "技术",
            "trust_section_num": "06",
            "trust_section_tag": "可信",
            "footer_cta_heading": "体验面向专业人士的测试版",
            "footer_cta_lead": "在聊天中了解规则推荐与 LLM 辅助的实际表现。",
            "problem_cards": [
                {
                    "emoji": "🌐",
                    "title": "语言障碍",
                    "body": "访日外国人等可能难以用母语咨询，难以选择合适的OTC。",
                },
                {
                    "emoji": "🏥",
                    "title": "人手不足",
                    "body": "药店咨询时间有限，部分用户仍感不安。",
                },
                {
                    "emoji": "💊",
                    "title": "难以选择",
                    "body": "用户可能不清楚何种OTC适合症状，并担心安全性。",
                },
            ],
            "how_heading": "三步即可使用",
            "how_steps": [
                {
                    "num": "①",
                    "title": "输入症状",
                    "body": "无需专业术语，以对话方式描述症状与生活背景。",
                },
                {
                    "num": "②",
                    "title": "整理候选",
                    "body": "以药品数据库、药学知识与规则推荐为核心，LLM辅助理解。",
                },
                {
                    "num": "③",
                    "title": "作为参考",
                    "body": "确认就诊建议与注意事项；购药或服药前请咨询药师或医生。",
                },
            ],
            "how_demo_image": "img/about/generated/about/demo/demo-ipad-product.png",
            "how_demo_alt": "iPad 上的聊天式 OTC 咨询工具（测试版）实机截图",
            "how_demo_caption": "实际聊天界面（测试版），含推荐药品与安全提示。",
            "features_heading": "四大优势",
            "feature_cards": [
                {
                    "emoji": "🛡️",
                    "title": "安全设计",
                    "body": "以规则推荐为核心；危险症状时建议就医，并抑制误信息。",
                },
                {
                    "emoji": "🧠",
                    "title": "混合推荐",
                    "body": "规则评分统一选药；LLM 辅助症状整理与提问生成。",
                },
                {
                    "emoji": "🌐",
                    "title": "四种语言",
                    "body": "日语、英语、中文、韩语（DeepL API 高速翻译）。",
                },
                {
                    "emoji": "♿",
                    "title": "无障碍",
                    "body": "字号调整、语音朗读、可折叠区块；对比度按 WCAG AA 思路设计。",
                },
            ],
            "safety_heading": "安全使用",
            "safety_lead": "本工具不替代医疗行为、诊断或处方。",
            "safety_items": [
                "症状严重或长期持续请尽快就医。",
                "日本国内紧急时请拨打119或前往医疗机构及公共咨询。",
                "对显示内容有疑问，请在购药或服药前咨询药师或医生。",
                "请在可能范围内说明妊娠/哺乳、儿童、并用药物、过敏史等。",
            ],
            "pharmacist_note": "视部署版本可能提供向药师咨询的升级功能。",
            "pharmacist_icon": "img/about/generated/about/icons/icon-pharmacist.png",
            "pharmacist_alt": "药师咨询",
            "tech_heading": "技术栈",
            "tech_lead": "测试版组成。选药以规则为核心，LLM 为辅助。",
            "tech_bullets": [
                "推荐：整合症状、功效、年龄、副作用、相互作用的规则评分",
                "多智能体：启用 LLM_AGENT_ENABLED 时，ChatOrchestrator 在分流后交给各专业智能体",
                "前端：HTML/CSS/原生 JS（响应式）",
                "日志：JSONL 结构化（访问·性能·安全）",
            ],
            "tech_details_label": "补充说明",
            "trust_heading": "运营体制",
            "trust_lead": "非营利学术研究目的的测试运营（依据应用概要文档）。",
            "trust_cards": [
                {"title": "源码管理", "body": "GitHub 版本管理；CI/CD 经 GCP Cloud Build。"},
                {"title": "生产托管", "body": "GCP Cloud Run（asia-northeast1）。Docker + Gunicorn。"},
                {"title": "数据库", "body": "Neon PostgreSQL（无服务器），存会话等。"},
                {"title": "日志与监控", "body": "JSONL 结构化日志；访问·性能·安全监控。"},
            ],
            "trust_beta_note": "面向医疗、行政、研究、药师等限定关系者验证，非面向公众正式发布。",
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


# Shared icon sets for /about tech diagram (skillicons.dev official icons only).
_TECH_DIAGRAM_ICON_THEME = "dark"
# Official brand marks (user-provided PNGs under static/img/about/generated/tech/).
_TECH_BRAND_ASSETS: dict[str, str] = {
    "openai": "img/about/generated/tech/icon-openai.png",
    "deepl": "img/about/generated/tech/icon-deepl.png",
    "resend": "img/about/generated/tech/icon-resend.png",
    "neon": "img/about/generated/tech/icon-neon.png",
}
_TECH_DIAGRAM_ICONS: dict[str, list[dict[str, str]]] = {
    "frontend": [
        {"type": "skillicon", "name": "html"},
        {"type": "skillicon", "name": "css"},
        {"type": "skillicon", "name": "js"},
    ],
    "app": [
        {"type": "skillicon", "name": "python"},
        {"type": "skillicon", "name": "fastapi"},
        {"type": "skillicon", "name": "docker"},
    ],
    "agents": [
        {"type": "skillicon", "name": "python"},
        {"type": "brand", "brand": "openai", "src": _TECH_BRAND_ASSETS["openai"]},
    ],
    "external": [
        {"type": "brand", "brand": "openai", "src": _TECH_BRAND_ASSETS["openai"]},
        {"type": "brand", "brand": "deepl", "src": _TECH_BRAND_ASSETS["deepl"]},
    ],
    "data": [
        {"type": "brand", "brand": "neon", "src": _TECH_BRAND_ASSETS["neon"]},
        {"type": "skillicon", "name": "postgres"},
    ],
    "ops": [
        {"type": "skillicon", "name": "github"},
        {"type": "skillicon", "name": "gcp"},
        {"type": "skillicon", "name": "git"},
        {"type": "skillicon", "name": "linux"},
    ],
}

_TECH_DIAGRAM_LABELS: dict[str, dict[str, Any]] = {
    "ja": {
        "title": "インフラ構成（β版）",
        "aria": "フロントエンド、FastAPI バックエンド、マルチエージェント、外部 API、Neon PostgreSQL、GCP 運用の構成図",
        "boxes": {
            "ops": {"label": "運用・CI/CD", "note": "GitHub · GCP · Git · Linux"},
            "frontend": {"label": "フロントエンド", "note": "HTML · CSS · JavaScript"},
            "app": {"label": "バックエンド", "note": "Python · FastAPI · Docker · Gunicorn"},
            "agents": {
                "label": "マルチエージェント",
                "note": "自前オーケストレーション · Python · OpenAI API",
                "dashed": True,
            },
            "external": {
                "label": "外部 API",
                "note": "OpenAI API · DeepL API",
                "dashed": True,
            },
            "data": {"label": "データベース", "note": "Neon · PostgreSQL"},
        },
    },
    "en": {
        "title": "Infrastructure (beta)",
        "aria": "Diagram: frontend, FastAPI backend, multi-agent layer, external APIs, Neon PostgreSQL, GCP ops",
        "boxes": {
            "ops": {"label": "Ops & CI/CD", "note": "GitHub · GCP · Git · Linux"},
            "frontend": {"label": "Frontend", "note": "HTML · CSS · JavaScript"},
            "app": {"label": "Backend", "note": "Python · FastAPI · Docker · Gunicorn"},
            "agents": {
                "label": "Multi-agent",
                "note": "In-house orchestration · Python · OpenAI API",
                "dashed": True,
            },
            "external": {
                "label": "External APIs",
                "note": "OpenAI API · DeepL API",
                "dashed": True,
            },
            "data": {"label": "Database", "note": "Neon · PostgreSQL"},
        },
    },
    "ko": {
        "title": "인프라 구성(β)",
        "aria": "프론트엔드, FastAPI 백엔드, 멀티 에이전트, 외부 API, Neon PostgreSQL, GCP 운영 구성도",
        "boxes": {
            "ops": {"label": "운영·CI/CD", "note": "GitHub · GCP · Git · Linux"},
            "frontend": {"label": "프론트엔드", "note": "HTML · CSS · JavaScript"},
            "app": {"label": "백엔드", "note": "Python · FastAPI · Docker · Gunicorn"},
            "agents": {
                "label": "멀티 에이전트",
                "note": "자체 오케스트레이션 · Python · OpenAI API",
                "dashed": True,
            },
            "external": {
                "label": "외부 API",
                "note": "OpenAI API · DeepL API",
                "dashed": True,
            },
            "data": {"label": "데이터베이스", "note": "Neon · PostgreSQL"},
        },
    },
    "zh": {
        "title": "基础设施（测试版）",
        "aria": "示意图：前端、FastAPI 后端、多智能体、外部 API、Neon PostgreSQL、GCP 运维",
        "boxes": {
            "ops": {"label": "运维·CI/CD", "note": "GitHub · GCP · Git · Linux"},
            "frontend": {"label": "前端", "note": "HTML · CSS · JavaScript"},
            "app": {"label": "后端", "note": "Python · FastAPI · Docker · Gunicorn"},
            "agents": {
                "label": "多智能体",
                "note": "自研编排 · Python · OpenAI API",
                "dashed": True,
            },
            "external": {
                "label": "外部 API",
                "note": "OpenAI API · DeepL API",
                "dashed": True,
            },
            "data": {"label": "数据库", "note": "Neon · PostgreSQL"},
        },
    },
}

_TECH_DIAGRAM_BOX_ORDER = ("ops", "frontend", "app", "data", "external", "agents")


def build_tech_diagram(lang: str) -> dict[str, Any]:
    lg = lang if lang in VALID_LANGS else "ja"
    meta = _TECH_DIAGRAM_LABELS[lg]
    boxes: list[dict[str, Any]] = []
    for box_id in _TECH_DIAGRAM_BOX_ORDER:
        bmeta = meta["boxes"][box_id]
        boxes.append(
            {
                "id": box_id,
                "label": bmeta["label"],
                "note": bmeta.get("note", ""),
                "dashed": bool(bmeta.get("dashed")),
                "icons": list(_TECH_DIAGRAM_ICONS[box_id]),
            }
        )
    return {
        "title": meta["title"],
        "aria": meta["aria"],
        "icon_theme": _TECH_DIAGRAM_ICON_THEME,
        "boxes": boxes,
    }


def get_about_bundle(page_id: str, lang: str) -> dict[str, Any]:
    if page_id not in _ABOUT:
        raise KeyError(page_id)
    lg = lang if lang in VALID_LANGS else "ja"
    bundle = dict(_ABOUT[page_id][lg])
    if page_id == "index":
        bundle["tech_diagram"] = build_tech_diagram(lg)
    return bundle


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
            "cta_visible_text": "Start chat",
            "cta_footer_note": "",
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
            "cta_visible_text": "채팅 시작",
            "cta_footer_note": "",
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
            "cta_visible_text": "开始聊天",
            "cta_footer_note": "",
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
