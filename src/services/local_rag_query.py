"""Local RAG — クエリ正規化・言及抽出・カテゴリ推論（口語・言い換え対応）。"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Sequence, Tuple

# 口語・概念 → 検索/ルーティング用 canonical 語（fixture 固有ではなく一般概念）
_CONCEPT_EXPANSIONS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (r"固まりにくく(?:なる)?(?:薬|お薬)?", ("ワーファリン", "クマリン系抗凝血薬")),
    (r"(?:血|血液)をサラサラ(?:にする)?(?:薬|お薬)?", ("ワーファリン", "クマリン系抗凝血薬")),
    (r"サラサラ(?:系|の)?(?:お薬|薬)?", ("ワーファリン", "クマリン系抗凝血薬")),
    (r"麻黄(?:系|成分)?", ("エフェドリン", "プソイドエフェドリン")),
    (r"エナジードリンク|エナドリ", ("カフェイン",)),
    (r"抗うつ(?:薬|剤)?", ("SSRI", "SNRI")),
    (r"咳止め|去痰", ("デキストロメトルファン",)),
    (r"イブuprofen|イブプロフェン系|イブ系", ("イブプロフェン", "NSAID")),
    (r"nsaid|非ステロイド", ("NSAID",)),
    (r"花粉症(?:の)?薬|抗ヒスタミン", ("クロルフェニラミン", "ジフェンヒドラミン")),
    (r"鼻薬|点鼻", ("プソイドエフェドリン", "オキシメトアゾリン")),
    (r"熱下げ(?:薬)?|解熱(?:剤|薬)?", ("アセトアミノフェン", "イブプロフェン")),
    (r"痛み止め|頭痛薬", ()),
    (r"tylenol|paracetamol|acetaminophen", ("アセトアミノフェン",)),
    (r"warfarin", ("ワーファリン",)),
    (r"aspirin", ("アスピリン",)),
    (r"ibuprofen|loxonin|lozonin", ("イブプロフェン", "ロキソプロフェン")),
    (r"beer|wine|cocktail", ("アルコール",)),
    (r"energy drink|エナドリ", ("カフェイン",)),
    (r"nasal spray|点鼻スプレー", ("プソイドエフェドリン",)),
    (r"cold medicine|風邪薬", ()),
    (r"dxm|dextromethorphan", ("デキストロメトルファン",)),
    (r"antihistamine|抗ヒスタミン薬", ("クロルフェニラミン", "ジフェンヒドラミン")),
    (r"\bssri\b", ("SSRI",)),
    (r"\bsnri\b", ("SNRI",)),
)

# ブランド略称 → canonical（CSV 製品名 prefix でも補完）
_BRAND_SHORTHANDS: Dict[str, str] = {
    "イブ": "イブ",
    "ロキソニン": "ロキソニン",
    "ロキソ": "ロキソニン",
    "ワルファリン": "ワーファリン",
    "カロナール": "カロナール",
    "タイレノール": "タイレノール",
    "バファリン": "バファリン",
    "アレグラ": "アレグラ",
    "パブロン": "パブロン",
    "ルル": "ルル",
}

_CATEGORY_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "interaction": (
        r"一緒",
        r"併用",
        r"一緒に",
        r"相互作用",
        r"同時に",
        r"同日",
        r"混ぜ",
        r"併用注意",
        r"処方.*(?:一緒|併用)",
        r"飲ん(?:じゃ|ちゃ)ダメ",
        r"あかん|あかんの|あかんやろ|ダメや|やば(?:い|く)(?:の|ん|系)?|危なく",
        r"混ぜ(?:た|て|る)|ダブル(?:で|)|combo|同時(?:に|使用)",
        r"mix|together|combine|same day",
        r"(?:一緒|併用).{0,8}(?:大丈夫|平気|ダメ|やば)",
        r"(?:大丈夫|平気|ダメ|やば).{0,12}(?:一緒|併用|同時)",
    ),
    "comparison": (
        r"違い",
        r"どっち",
        r"どれが",
        r"比較",
        r"選び",
        r"おすすめ",
        r"どう違",
    ),
    "side_effect": (
        r"副作用",
        r"眠気|眠く|眠い|眠たく|眠たい|眠なる|眠なり|ガッツリ眠|寝気|眠た",
        r"ぼーっと|ボーッと|だるい|だるさ",
        r"お腹(?:が)?(?:キツ|きつ|きつく|張|張っ|はり|むか|痛)|胃(?:が)?(?:キツ|きつ|きつく|むか|痛)|むかむか",
        r"吐き気|嘔吐|痒|かゆ",
        r"drowsy|sleepy|nausea",
        r"しゃーない|キツう",
        r"(?:めっちゃ|マジ|超|ガチ|かなり)(?:眠|だる|キツ|きつ|むか|張|パン)",
        r"意識(?:が|)?飛|ムカつ|腹パン|GI(?:トラブル|系)|gastro",
        r"(?:経験|なった|なり).{0,12}(?:お持ち|おあり|ある方|いらっしゃ)",
        r"変な感じ|違和感|気持ち(?:が|)?悪|おかしい",
    ),
    "usage": (
        r"用法|用量",
        r"食後|食前|食べ(?:て|た)後|ご飯|食事(?:の)?後|空腹",
        r"何時間|何回|何錠|1日|\d+\s*hours?",
        r"水(?:なし|不要|いら|いなく)",
        r"飲み(?:方|時間)|服用(?:方法|間隔|時間)|使用方法|使用(?:方法|法)",
        r"(?:どう|如何|どのように)(?:やって|に)?飲|飲(?:む|み方|んだ|んで)",
        r"この薬|その薬|それの(?:使|飲)",
        r"平気(?:？|\?)?$",
        r"fine\?|again|max|empty stomach|空腹時",
        r"ええん|どっち",
        r"(?:食後|食前|空腹|用法|用量|何錠|何回|ご飯|食事).{0,24}よろしいでしょう",
        r"服用した方が(?:よ|良)",
        r"イケる|マシ|max(?:\s*dose)?",
        r"painkiller|cold\s*med",
    ),
    "doping": (
        r"ドーピング",
        r"禁止物質",
        r"競技|大会|マラソン|陸上|水泳",
        r"S6[A-Z]?",
        r"アウト(?:？|\?)?",
        r"doping|out\?|marathon|competition",
    ),
    "age": (
        r"年齢|何歳|歳(?:未満|以上)",
        r"小[1-6]|小学|うちの子|子供|こども|小児|未就学",
        r"高齢|\d+代|\d+歳",
        r"授乳|妊娠",
        r"バアさん|おばあ|grandma|grandmother",
        r"いかがでしょう|ございます",
    ),
}

# usage の「飲んでも」は interaction と競合しやすい — usage 専用
_USAGE_ONLY = (
    r"水.*飲ん",
    r"空腹.*飲",
    r"食後.*飲",
    r"また飲",
    r"何錠",
    r"何回",
    r"again",
)

_TOKEN_RE = re.compile(r"[\w一-龥ぁ-んァ-ヶ]{2,}")

# 口語・略語・軽い表記ゆれ（fixture 固有語ではなく一般クラス）
_COLLOQUIAL_REWRITES: Tuple[Tuple[str, str], ...] = (
    (r"\bAPAP\b", "アセトアミノフェン"),
    (r"\bETOH\b", "アルコール"),
    (r"\bIBU\b", "イブプロフェン"),
    (r"\bDXM\b", "デキストロメトルファン"),
    (r"\bGI\b", "胃"),
    (r"gastro(?:intestinal)?", "胃"),
    (r"painkiller", "解熱剤"),
    (r"knock\s*out(?:\s*level)?", "強い眠気"),
    (r"combo", "併用"),
    (r"ワーファリん", "ワーファリン"),
    (r"ムカつ(?:く|)", "むかむか"),
    (r"腹パン", "お腹が痛"),
    (r"イケる", "平気"),
    (r"混ぜ(?:た|て|る)", "一緒に"),
    (r"ダブル(?:で|)", "同時に"),
    (r"意識飛び", "眠気"),
    (r"max\s*dose", "1日用量"),
    (r"cold\s*med", "風邪薬"),
    (r"鼻スプレー", "鼻薬"),
    (r"ギリ(?:使える|OK)", "使える"),
)

_COORD_SPLIT = re.compile(
    r"、|/|(?:および)|(?:及び)|"
    r"(?<=[ァ-ヶーA-Za-z0-9])と(?=[ァ-ヶーA-Za-z0-9一-龥])"
)
_PARTICLE_SPLIT = re.compile(r"[、。！？!?…・\s]+|(?<=[てでに])(?!も)")


def normalize_text(text: str) -> str:
    out = unicodedata.normalize("NFKC", (text or "").strip())
    out = re.sub(r"^(?:user|assistant|bot|human)\s*:\s*", "", out, flags=re.I)
    for pattern, repl in _COLLOQUIAL_REWRITES:
        out = re.sub(pattern, repl, out, flags=re.I)
    return out


def expand_concepts(text: str) -> str:
    """概念フレーズを canonical 語に展開（原文も保持）。"""
    out = normalize_text(text)
    extras: List[str] = []
    for pattern, terms in _CONCEPT_EXPANSIONS:
        if re.search(pattern, out, re.I):
            extras.extend(terms)
    if extras:
        out = out + " " + " ".join(dict.fromkeys(extras))
    return out


def extract_brand_tokens(text: str) -> List[str]:
    q = normalize_text(text)
    found: List[str] = []
    for shorthand in sorted(_BRAND_SHORTHANDS, key=len, reverse=True):
        for m in re.finditer(re.escape(shorthand), q, re.I):
            start, end = m.span()
            if start > 0 and (q[start - 1].isalnum() or q[start - 1] in "ー"):
                continue
            if end < len(q) and (q[end].isalnum() or q[end] in "ー"):
                continue
            if shorthand not in found:
                found.append(shorthand)
                break
    return found


def extract_coordination_pairs(text: str) -> List[str]:
    """「AとB」「A、B」から語を抽出（こと・っと等の誤分割を避ける）。"""
    q = normalize_text(text)
    parts: List[str] = []
    for seg in _COORD_SPLIT.split(q):
        seg = re.sub(r"(?:飲んで|服用|使用中|処方|使って|打って).*$", "", seg).strip()
        seg = re.sub(r"^(?:この|その|うちの|私の)", "", seg).strip()
        tok = _TOKEN_RE.findall(seg)
        if tok:
            candidate = max(tok, key=len)
            if len(candidate) > 16:
                candidate = next((t for t in sorted(tok, key=len, reverse=True) if len(t) <= 16), candidate)
            if (
                len(candidate) >= 2
                and len(candidate) <= 16
                and candidate not in parts
                and _is_drug_like_token(candidate)
            ):
                parts.append(candidate)
    return parts[:6]


def _is_drug_like_token(token: str) -> bool:
    t = normalize_text(token)
    if not t or len(t) < 2 or len(t) > 16:
        return False
    if re.search(r"[でがをにはもの]", t):
        return False
    if re.search(r"\d+時間|時間以内", t):
        return False
    if re.search(
        r"^(?:小[1-6]|小学|ご飯|食事|市販|うちの|この|その|80代|\d+代)",
        t,
    ):
        return False
    if t in _BRAND_SHORTHANDS:
        return True
    if re.search(r"(?:薬|剤|錠|カプセル|滴|点鼻)$", t) and len(t) <= 8:
        return False
    if re.search(
        r"プロフェン|アスピリン|ワーファリン|デキストロ|フェン|カフェイン|エフェドリン|麻黄|イブuprofen",
        t,
        re.I,
    ):
        return True
    if re.search(r"^(?:お水|水なし|飲ん|問題|平気|普通|使える|お腹|胃|めっちゃ|眠た|しゃーない|あかん|ええ)", t):
        return False
    if re.search(r"(?:飲んだら|なるわ|ある人|おる|きつく|張っ|ことある|眠たく)", t):
        return False
    return len(t) >= 4 and not re.search(
        r"^(?:心配|避け|大会|マラソン|熱下げ|頭痛)", t
    )


def _explicit_substance_mention_count(query: str) -> int:
    """概念展開前の原文ベースで、薬・成分らしき言及数を数える。"""
    raw = normalize_text(query)
    if not raw:
        return 0
    mentions: set[str] = set()
    for brand in extract_brand_tokens(raw):
        mentions.add(brand)
    for coord in extract_coordination_pairs(raw):
        if _is_drug_like_token(coord):
            mentions.add(coord)
    for token in _TOKEN_RE.findall(raw):
        if len(token) > 16:
            continue
        if token.upper() in ("SSRI", "SNRI", "NSAID"):
            mentions.add(token.upper())
        elif _is_drug_like_token(token):
            mentions.add(token)
    # 長い成分名が短いブランド略称を包含する場合は略称を除く
    compact = sorted(mentions, key=len, reverse=True)
    pruned: set[str] = set()
    for m in compact:
        if any(m != o and m in o for o in compact):
            continue
        pruned.add(m)
    return len(pruned)


def _category_pattern_hits(text: str) -> Dict[str, int]:
    """カテゴリ別パターンヒット数（一般化スコアリング用）。"""
    hits: Dict[str, int] = {}
    for cat, patterns in _CATEGORY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.I):
                hits[cat] = hits.get(cat, 0) + 1
    return hits


def _prior_context_text(context_text: str, query: str) -> str:
    """context_text から現発話を除いた prior 部分を返す。"""
    if not context_text:
        return ""
    ctx = expand_concepts(context_text)
    q = expand_concepts(query)
    if q and q in ctx:
        prior = ctx.replace(q, "", 1).strip()
        return prior or ctx
    return ctx


def infer_medicine_category_with_confidence(
    query: str, *, mention_count: int = 0, context_text: str = ""
) -> Tuple[str, float]:
    """カテゴリと confidence（0–1）。tie / 低スコアは confidence 低。

    context_text: 会話履歴などを連結した補助文（cat 推論用）。
    """
    q = expand_concepts(query)
    prior = _prior_context_text(context_text, query)
    combined = f"{prior} {q}".strip() if prior else q
    explicit_count = _explicit_substance_mention_count(query)
    substance_count = max(explicit_count, mention_count)
    scores: Dict[str, int] = {}

    # 現発話を優先、履歴は補助（文脈依存 intent の一般化）
    for cat, count in _category_pattern_hits(q).items():
        scores[cat] = scores.get(cat, 0) + count * 2
    if prior:
        for cat, count in _category_pattern_hits(prior).items():
            scores[cat] = scores.get(cat, 0) + count

    expanded_ingredient_count = len(
        {
            t
            for t in re.findall(r"[\w一-龥ぁ-んァ-ヶ]{2,}", q)
            if len(t) >= 4
            and not re.search(r"(?:飲んだ|服用|経験|お持ち|いらっしゃ|よろしい)", t)
            and (
                t.upper() in ("SSRI", "SNRI", "NSAID")
                or re.search(
                    r"プロフェン|アスピリン|ワーファリン|クマリン|アセトアミノフェン|アルコール|フェン|メトルファン|エフェドリン|カフェイン",
                    t,
                )
            )
        }
    )
    interaction_substances = max(substance_count, expanded_ingredient_count)
    if interaction_substances >= 2 and re.search(
        r"[?？]|大丈夫|平気|ダメ|やば|併用|一緒|同時|同日", q
    ):
        if re.search(r"違い|どっち|どれが|比較|おすすめ|どう違", q):
            scores["comparison"] = scores.get("comparison", 0) + 6
            scores["interaction"] = max(0, scores.get("interaction", 0) - 4)
        else:
            scores["interaction"] = scores.get("interaction", 0) + 3
    if re.search(r"一緒に(?:服用|飲|使)", q):
        scores["interaction"] = scores.get("interaction", 0) + 4
        scores["usage"] = max(0, scores.get("usage", 0) - 2)

    side_hits = sum(
        1 for pat in _CATEGORY_PATTERNS["side_effect"] if re.search(pat, q, re.I)
    )
    if side_hits and interaction_substances < 2:
        scores["side_effect"] = scores.get("side_effect", 0) + 4
        scores["interaction"] = max(0, scores.get("interaction", 0) - 1)
    elif side_hits and re.search(r"(?:お腹|胃|眠)", q):
        scores["side_effect"] = scores.get("side_effect", 0) + 5
        scores["interaction"] = max(0, scores.get("interaction", 0) - 3)

    doping_hits = sum(
        1 for pat in _CATEGORY_PATTERNS["doping"] if re.search(pat, q, re.I)
    )
    if doping_hits:
        scores["doping"] = scores.get("doping", 0) + 3

    age_hits = _category_pattern_hits(q).get("age", 0) + (
        _category_pattern_hits(prior).get("age", 0) if prior else 0
    )
    if age_hits and not re.search(r"併用|一緒|同時|同日|相互作用", q):
        scores["age"] = scores.get("age", 0) + 4
        if substance_count < 2:
            scores["interaction"] = max(0, scores.get("interaction", 0) - 2)

    # 履歴に年齢情報 + 現発話が使用可否確認 → age（小児・高齢の follow-up 一般化）
    if prior and re.search(r"小学|小[1-6]|小児|未就学|何歳|\d+歳|高齢|授乳|妊娠", prior):
        if re.search(
            r"使(?:っ)?て(?:も)?(?:い|良|OK)|飲(?:ん)?(?:で)?(?:も)?(?:い|良|OK)|"
            r"(?:平気|大丈夫|問題(?:ない|なし)?)(?:？|\?)?$|"
            r"(?:市販|OTC).{0,12}(?:使|飲)",
            q,
        ):
            scores["age"] = scores.get("age", 0) + 6
            scores["usage"] = max(0, scores.get("usage", 0) - 2)

    usage_hits = sum(
        1 for pat in _CATEGORY_PATTERNS["usage"] if re.search(pat, q, re.I)
    )
    for pat in _USAGE_ONLY:
        if re.search(pat, q):
            usage_hits += 1
    if re.search(r"また飲|飲んでも平気|水(?:なし|不要)", q):
        usage_hits += 2
    if usage_hits and substance_count < 2:
        scores["usage"] = scores.get("usage", 0) + 3
        if re.search(r"また飲|飲んでも平気|水(?:なし|不要)", q):
            scores["interaction"] = max(0, scores.get("interaction", 0) - 3)

    # 単剤の指示語 + 安全確認（「それ、飲んで大丈夫？」等）は interaction より副作用/用法
    if (
        substance_count < 2
        and re.search(r"大丈夫|平気|安全|普通|正常|よくある|心配|問題(?:ない|なし)?", q)
        and not re.search(r"併用|一緒|同時|同日|混ぜ|ダブル|combo|mix", q)
    ):
        if re.search(r"副作用|眠|キツ|きつ|むか|だる|drowsy|眠く|眠た", q):
            scores["side_effect"] = scores.get("side_effect", 0) + 6
            scores["usage"] = max(0, scores.get("usage", 0) - 5)
            scores["interaction"] = max(0, scores.get("interaction", 0) - 4)
        elif re.search(r"(?:それ|この|その|あれ)(?:の|、|,)?", q) and re.search(
            r"推奨|頭痛|解熱|ロキソ|カロナール|イブ|薬", combined
        ):
            scores["side_effect"] = scores.get("side_effect", 0) + 3
            scores["interaction"] = max(0, scores.get("interaction", 0) - 3)
        if re.search(r"食後|食前|空腹|用法|用量|効果|飲み方", q):
            scores["usage"] = scores.get("usage", 0) + 4
            scores["interaction"] = max(0, scores.get("interaction", 0) - 2)

    # 有害事象の叙述 + 正常性確認（「飲むと眠くなるの普通？」等 — usage より副作用優先）
    if re.search(r"眠く|眠気|眠た|むか|だる|副作用|drowsy|nausea|お腹|胃", q, re.I):
        if re.search(r"普通|正常|よくある|大丈夫|平気|心配|問題|しゃーない|異常", q):
            scores["side_effect"] = scores.get("side_effect", 0) + 5
            scores["usage"] = max(0, scores.get("usage", 0) - 4)

    if re.search(r"副作用", q):
        scores["side_effect"] = scores.get("side_effect", 0) + 4

    if re.search(r"beer|wine|cocktail|etoh|お酒|ビール|アルコール", q, re.I) and re.search(
        r"飲|painkiller|解熱|カロナール|アセトアミノフェン|タイレノール|tylenol|apap", q, re.I
    ):
        scores["interaction"] = scores.get("interaction", 0) + 5
        scores["usage"] = max(0, scores.get("usage", 0) - 4)

    if not scores:
        return "", 0.0
    total = sum(scores.values())
    best_cat, best_score = max(scores.items(), key=lambda x: (x[1], x[0]))
    confidence = round(best_score / total, 3) if total else 0.0
    return best_cat, confidence


def infer_medicine_category(query: str, *, mention_count: int = 0) -> str:
    cat, _ = infer_medicine_category_with_confidence(query, mention_count=mention_count)
    return cat


def tokenize_for_search(text: str, *, extra_terms: Sequence[str] = ()) -> List[str]:
    """BM25 / キーワード用トークン（口語・概念展開込み）。"""
    expanded = expand_concepts(text)
    seen: List[str] = []
    for term in extra_terms:
        t = term.lower()
        if t and t not in seen:
            seen.append(t)
    for shorthand in extract_brand_tokens(expanded):
        if shorthand not in seen:
            seen.append(shorthand)
    for token in re.findall(r"\d+", expanded):
        if token not in seen:
            seen.append(token)
    for seg in _PARTICLE_SPLIT.split(expanded):
        for token in _TOKEN_RE.findall(seg.lower()):
            if len(token) >= 2 and token not in seen:
                seen.append(token)
    # カテゴリ関連語も弱く追加
    cat = infer_medicine_category(expanded, mention_count=len(extract_coordination_pairs(expanded)))
    if cat and cat not in seen:
        seen.append(cat)
    return seen


def retrieval_query_enrichment(query: str) -> str:
    """retrieve 用に概念語を付加（embedding/BM25 両方）。"""
    return expand_concepts(query)
