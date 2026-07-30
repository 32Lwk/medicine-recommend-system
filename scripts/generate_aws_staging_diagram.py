#!/usr/bin/env python3
"""Generate AWS staging architecture draw.io XML per spec."""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET

SCALE = 1
BASE_PAGE_W = 1587
BASE_PAGE_H = 1123
PAGE_W = BASE_PAGE_W * SCALE
PAGE_H = BASE_PAGE_H * SCALE

ICON_PX = 48 * SCALE  # 96px icons on 2x canvas


def s(v: float) -> float:
    """Scale layout coordinate/size."""
    return v * SCALE


ICON_STYLE = (
    "sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
    "[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
    "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
    "outlineConnect=0;fontColor=#232F3E;fillColor={fc};strokeColor=#ffffff;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize={fs};"
    "fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};"
    "fontFamily=Helvetica;shadow=1;"
)

GROUP_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize={fs};"
    "fontFamily=Helvetica;container=1;collapsible=0;pointerEvents=0;shadow=1;strokeWidth=2;"
    "fillColor={fill};strokeColor={stroke};fontColor={stroke};"
)

SWIM_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize={fs};"
    "fontFamily=Helvetica;container=1;collapsible=0;pointerEvents=0;strokeWidth=2;"
    "fillColor={fill};strokeColor={stroke};fontColor=#333333;align=left;spacingLeft={sp};"
)

COLORS = {
    "user": ("#FFF3E0", "#FF9800"),
    "cicd": ("#E3F2FD", "#1976D2"),
    "compute": ("#E8F5E9", "#4CAF50"),
    "aiml": ("#F3E5F5", "#9C27B0"),
    "storage": ("#FFFDE7", "#FBC02D"),
    "ops": ("#FAFAFA", "#757575"),
    "external": ("#FCE4EC", "#E91E63"),
    "security": ("#FFEBEE", "#D32F2F"),
    "network": ("#E8F5E9", "#4CAF50"),
}

EDGE_COLORS = {
    "blue": "#1565C0",
    "purple": "#7B1FA2",
    "yellow": "#F9A825",
    "red": "#C62828",
    "green": "#2E7D32",
    "gray": "#616161",
}

cells: list[str] = []
cell_id = 0


def nid(prefix: str = "c") -> str:
    global cell_id
    cell_id += 1
    return f"{prefix}-{cell_id}"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def geom(x: float, y: float, w: float, h: float, relative: bool = False) -> str:
    if not relative:
        x, y, w, h = s(x), s(y), s(w), s(h)
    rel = ' relative="1"' if relative else ""
    return f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"{rel} />'


def add_swim_lane(gid: str, parent: str, label: str, x: float, y: float, w: float, h: float, kind: str) -> str:
    fill, stroke = COLORS[kind]
    style = SWIM_STYLE.format(fill=fill, stroke=stroke, fs=14 * SCALE, sp=8 * SCALE)
    cells.append(
        f'<mxCell id="{gid}" parent="{parent}" value="&lt;b&gt;{esc(label)}&lt;/b&gt;" style="{style}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )
    return gid


def add_service_box(
    nid_prefix: str,
    parent: str,
    cat: str,
    label: str,
    icon: str,
    x: float,
    y: float,
    w: float = 150,
    h: float = 140,
    icon_fc: str | None = None,
    dashed: bool = False,
    emphasis: bool = False,
) -> tuple[str, str]:
    gid = nid(nid_prefix)
    iid = nid(nid_prefix + "i")
    fill, stroke = COLORS[cat]
    gs = GROUP_STYLE.format(fill=fill, stroke=stroke, fs=12 * SCALE)
    if dashed:
        gs += "dashed=1;dashPattern=8 8;"
    if emphasis:
        gs += "strokeWidth=4;"
    cells.append(
        f'<mxCell id="{gid}" parent="{parent}" value="" style="{gs}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )
    fc_map = {
        "network": "#8C4FFF",
        "compute": "#ED7100",
        "aiml": "#01A88D",
        "storage": "#3F8624",
        "security": "#DD344C",
        "ops": "#666666",
        "cicd": "#E7157B",
        "external": "#232F3D",
    }
    fc = icon_fc or fc_map.get(cat, "#232F3E")
    istyle = ICON_STYLE.format(fc=fc, icon=icon, fs=11 * SCALE)
    icon_x = (w - 48) / 2
    cells.append(
        f'<mxCell id="{iid}" parent="{gid}" value="{label}" style="{istyle}" vertex="1">'
        f'{geom(icon_x, 28, 48, 48)}</mxCell>'
    )
    return gid, iid


def add_text_box(tid: str, parent: str, label: str, x: float, y: float, w: float, h: float, **kw) -> None:
    fs = kw.get("fontSize", 12) * SCALE
    bold = kw.get("bold", False)
    fill = kw.get("fill", "none")
    stroke = kw.get("stroke", "none")
    align = kw.get("align", "left")
    style = (
        f"text;html=1;strokeColor={stroke};fillColor={fill};align={align};"
        f"verticalAlign=top;fontSize={fs};fontFamily=Helvetica;"
    )
    if bold:
        style += "fontStyle=1;"
    cells.append(
        f'<mxCell id="{tid}" parent="{parent}" value="{label}" style="{style}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )


def add_rect_box(
    bid: str,
    parent: str,
    label: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    stroke: str,
    stroke_w: float = 2,
    dashed: bool = False,
    font_size: float = 10,
) -> None:
    ds = "dashed=1;dashPattern=8 8;" if dashed else ""
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
        f"strokeWidth={stroke_w};fontSize={font_size * SCALE};fontFamily=Helvetica;"
        f"align=left;spacingLeft={6 * SCALE};verticalAlign=top;fontColor=#232F3E;{ds}"
    )
    cells.append(
        f'<mxCell id="{bid}" parent="{parent}" value="{label}" style="{style}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )


def add_edge(
    eid: str,
    source: str,
    target: str,
    label: str,
    color: str,
    dashed: bool = False,
    exit_x: float | None = None,
    exit_y: float | None = None,
    entry_x: float | None = None,
    entry_y: float | None = None,
    points: list[tuple[float, float]] | None = None,
) -> None:
    ds = "dashed=1;dashPattern=8 8;" if dashed else ""
    style = (
        f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
        f"html=1;fontFamily=Helvetica;strokeColor={color};strokeWidth={2 * SCALE};"
        f"endArrow=block;endFill=1;labelBackgroundColor=#FFFFFF;{ds}"
    )
    if exit_x is not None:
        style += f"exitX={exit_x};exitY={exit_y};"
    if entry_x is not None:
        style += f"entryX={entry_x};entryY={entry_y};"
    geo = '<mxGeometry relative="1" as="geometry">'
    if points:
        geo += '<Array as="points">'
        for px, py in points:
            geo += f'<mxPoint x="{s(px)}" y="{s(py)}" />'
        geo += "</Array>"
    geo += "</mxGeometry>"
    cells.append(
        f'<mxCell id="{eid}" parent="1" source="{source}" target="{target}" edge="1" style="{style}">'
        f"{geo}</mxCell>"
    )
    if label:
        lid = eid + "-lbl"
        cells.append(
            f'<mxCell id="{lid}" parent="{eid}" value="{esc(label)}" connectable="0" vertex="1" '
            f'style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];'
            f'fontSize={10 * SCALE};fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;">'
            f'<mxGeometry relative="1" x="-0.1" y="-12" as="geometry"><mxPoint as="offset" /></mxGeometry>'
            f"</mxCell>"
        )


def add_mini_node(
    nid_prefix: str,
    parent: str,
    label: str,
    x: float,
    y: float,
    w: float = 40,
    h: float = 24,
    fill: str = "#E8F4FC",
    stroke: str = "#147EBA",
    fs: float = 8,
    sub: str = "",
) -> str:
    """Compact pipeline node (minimal label)."""
    cid = nid(nid_prefix)
    val = f"&lt;b&gt;{label}&lt;/b&gt;"
    if sub:
        val += f"&lt;div style=&quot;font-size:6px;color:#666&quot;&gt;{sub}&lt;/div&gt;"
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
        f"strokeWidth=1.5;fontSize={fs * SCALE};fontFamily=Helvetica;"
        f"align=center;verticalAlign=middle;fontColor=#232F3E;"
    )
    cells.append(
        f'<mxCell id="{cid}" parent="{parent}" value="{val}" style="{style}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )
    return cid


def add_mini_icon_node(
    nid_prefix: str,
    parent: str,
    label: str,
    icon: str,
    x: float,
    y: float,
    fc: str = "#DD344C",
    w: float = 36,
    h: float = 36,
) -> str:
    """Icon-first mini node (short label under icon)."""
    gid = nid(nid_prefix)
    iid = nid(nid_prefix + "i")
    gs = (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor=#FAFAFA;strokeColor=#BDBDBD;"
        f"strokeWidth=1;fontSize={7 * SCALE};fontFamily=Helvetica;"
        f"align=center;verticalAlign=top;fontColor=#232F3E;container=1;"
    )
    cells.append(
        f'<mxCell id="{gid}" parent="{parent}" value="" style="{gs}" vertex="1">'
        f"{geom(x, y, w, h)}</mxCell>"
    )
    istyle = ICON_STYLE.format(fc=fc, icon=icon, fs=7 * SCALE)
    cells.append(
        f'<mxCell id="{iid}" parent="{gid}" value="{label}" style="{istyle}" vertex="1">'
        f"{geom(6, 2, 24, 24)}</mxCell>"
    )
    return gid


def add_ecs_internal_pipeline(parent: str) -> str:
    """Visual Chat Pipeline v2 inside ECS — icons, arrows, minimal text."""
    gid = "g-pipe-inner"
    style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=0;fontSize=8;"
        "fontFamily=Helvetica;container=1;collapsible=0;pointerEvents=0;"
        "strokeWidth=2;fillColor=#F1F8E9;strokeColor=#4CAF50;fontColor=#558B2F;"
        "align=left;spacingLeft=4;spacingTop=2;"
    )
    cells.append(
        f'<mxCell id="{gid}" parent="{parent}" value="" style="{style}" vertex="1">'
        f"{geom(12, 42, 285, 290)}</mxCell>"
    )

    # Row 1 — SafetyGate → Triage → Router → Dispatch
    sg = add_mini_icon_node("pipe-sg", gid, "SG", "waf", 8, 10, fc="#DD344C", w=34, h=34)
    add_mini_node("pipe-sg-sub", gid, "pre/post", 6, 44, 38, 10, "#FFEBEE", "#DD344C", fs=6)
    tri = add_mini_node("pipe-tri", gid, "Triage", 52, 12, 48, 28, "#F3E5F5", "#9C27B0", fs=7)
    for i, (tag, col) in enumerate(
        [("Phy", "#147EBA"), ("Emo", "#9C27B0"), ("Emg", "#DD344C"), ("Ask", "#01A88D"), ("O", "#757575")]
    ):
        add_mini_node(f"pipe-t{i}", gid, tag, 50 + i * 17, 42, 15, 10, "#FFFFFF", col, fs=6)
    ir = add_mini_node("pipe-ir", gid, "Router", 108, 14, 38, 24, "#F3E5F5", "#9C27B0", fs=7)
    ad = add_mini_node("pipe-ad", gid, "Dispatch", 152, 14, 42, 24, "#FFF2E8", "#ED7100", fs=7)
    add_edge("pipe-e1", sg, tri, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.3, entry_x=0, entry_y=0.5)
    add_edge("pipe-e2", tri, ir, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.3, entry_x=0, entry_y=0.5)
    add_edge("pipe-e3", ir, ad, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)

    # Row 2 — PhysicalOrchestrator → NLU → rule scoring
    p1 = add_mini_node("pipe-po", gid, "PhysOrch", 8, 70, 44, 22, "#E8F4FC", "#147EBA", fs=6)
    p2 = add_mini_node("pipe-nlu", gid, "NLU", 58, 70, 32, 22, "#E8F4FC", "#147EBA", fs=7)
    p3 = add_mini_icon_node("pipe-rule", gid, "Rule", "s3", 98, 66, fc="#3F8624", w=32, h=32)
    add_edge("pipe-e4", p1, p2, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)
    add_edge("pipe-e5", p2, p3, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)

    kb = add_mini_icon_node("pipe-kb", gid, "KB", "bedrock", 248, 88, fc="#01A88D", w=30, h=30)

    # RAG agents
    c1 = add_mini_node("pipe-con", gid, "Concierge", 8, 108, 46, 22, "#E8F4FC", "#147EBA", fs=6)
    a1 = add_mini_node("pipe-ask", gid, "Ask/Expl", 62, 108, 44, 22, "#E8F4FC", "#147EBA", fs=6)
    add_edge("pipe-e6", c1, kb, "RAG", EDGE_COLORS["purple"], dashed=True, exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)
    add_edge("pipe-e7", a1, kb, "RAG", EDGE_COLORS["purple"], dashed=True, exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.3)

    # Other agents
    add_mini_node("pipe-cou", gid, "Counsel", 8, 138, 40, 22, "#E8F4FC", "#147EBA", fs=7)
    e1 = add_mini_node("pipe-emg", gid, "Emergency", 56, 138, 48, 22, "#FFEBEE", "#DD344C", fs=6)
    e2 = add_mini_icon_node("pipe-q", gid, "Queue", "sqs", 112, 134, fc="#E7157B", w=30, h=30)
    add_mini_node("pipe-sto", gid, "Store", 150, 138, 36, 22, "#E8F4FC", "#147EBA", fs=7)
    add_edge("pipe-e8", e1, e2, "", EDGE_COLORS["red"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)

    # Session / memory
    add_mini_icon_node("pipe-so", gid, "SessOps", "ecs", 8, 180, fc="#ED7100", w=32, h=32)
    add_mini_icon_node("pipe-pm", gid, "Profile", "users", 48, 180, fc="#FF9800", w=32, h=32)
    add_mini_icon_node("pipe-es", gid, "Summary", "generic_document", 88, 180, fc="#757575", w=32, h=32)

    # Dispatch → agents (fan-out hint)
    add_edge("pipe-e9", ad, p1, "", EDGE_COLORS["gray"], dashed=True, exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)

    return gid


def build() -> str:
    global cells
    cells = []
    cell_id = 0

    # Title
    add_text_box(
        "title",
        "1",
        "チャット型医薬品相談ツール — AWS ステージング構成",
        40,
        20,
        1400,
        40,
        fontSize=24,
        bold=True,
    )
    add_text_box(
        "subtitle",
        "1",
        "AWS ステージング",
        40,
        58,
        1400,
        28,
        fontSize=16,
    )
    cells.append(
        '<mxCell id="title-sep" parent="1" value="" style="line;strokeWidth=3;html=1;'
        'strokeColor=#FF9900;fontFamily=Helvetica;" vertex="1">'
        f"{geom(40, 92, 1520, 8)}</mxCell>"
    )

    # Swim lanes (wider / taller base layout)
    g_user = add_swim_lane("g-user", "1", "エンドユーザー / クライアント", 30, 110, 240, 380, "user")
    g_net = add_swim_lane("g-net", "1", "ネットワーク / セキュリティ", 290, 110, 520, 190, "network")
    g_compute = add_swim_lane("g-compute", "1", "コンピュート / ECS アプリケーション", 290, 320, 520, 340, "compute")
    g_aiml = add_swim_lane("g-aiml", "1", "AI / ML サービス (AWS Managed)", 830, 110, 420, 520, "aiml")
    g_ext = add_swim_lane("g-ext", "1", "外部サービス", 830, 650, 420, 240, "external")
    g_storage = add_swim_lane("g-storage", "1", "ストレージ / データ", 290, 680, 520, 230, "storage")
    g_sec = add_swim_lane("g-sec", "1", "セキュリティ / 設定管理", 290, 930, 250, 150, "security")
    g_ops = add_swim_lane("g-ops", "1", "運用 / 監視 / コスト管理", 560, 930, 290, 150, "ops")
    g_cicd = add_swim_lane("g-cicd", "1", "CI/CD パイプライン (デプロイ側)", 1270, 110, 420, 970, "cicd")

    # Users
    _, a1 = add_service_box(
        "a1", g_user, "user",
        "Browser",
        "users", 40, 55, 180, 140, icon_fc="#FF9800",
    )
    _, a2 = add_service_box(
        "a2", g_user, "user",
        "LINE",
        "mobile", 40, 220, 180, 140, icon_fc="#FF9800",
    )

    # Network
    _, b1 = add_service_box(
        "b1", g_net, "network",
        "Amazon CloudFront",
        "cloudfront", 25, 50, 150, 120,
    )
    _, b2 = add_service_box(
        "b2", g_net, "security",
        "AWS WAF",
        "waf", 185, 50, 150, 120,
    )
    _, b3 = add_service_box(
        "b3", g_net, "network",
        "Application Load Balancer",
        "elastic_load_balancing", 345, 50, 150, 120,
    )

    # Compute: pipeline diagram (left) + ECS core (right) + ECR (bottom)
    add_ecs_internal_pipeline(g_compute)
    _, c2 = add_service_box(
        "c2", g_compute, "compute",
        "ECS Express",
        "ecs", 305, 42, 200, 145, emphasis=True,
    )
    _, c1 = add_service_box(
        "c1", g_compute, "compute",
        "Amazon ECR",
        "ecr", 305, 200, 200, 88,
    )

    # AI/ML (2-column grid, more spacing)
    _, d1 = add_service_box(
        "d1", g_aiml, "aiml",
        "Bedrock KB",
        "bedrock", 20, 50, 185, 110,
    )
    _, d2 = add_service_box(
        "d2", g_aiml, "aiml",
        "Bedrock KB",
        "bedrock", 215, 50, 185, 110,
    )
    _, d4 = add_service_box(
        "d4", g_aiml, "aiml",
        "Amazon Translate",
        "translate", 20, 180, 125, 100,
    )
    _, d5 = add_service_box(
        "d5", g_aiml, "aiml",
        "Amazon Polly",
        "polly", 155, 180, 125, 100,
    )
    _, d6 = add_service_box(
        "d6", g_aiml, "aiml",
        "Amazon Comprehend Medical",
        "comprehend_medical", 290, 180, 110, 100,
    )
    _, d7 = add_service_box(
        "d7", g_aiml, "aiml",
        "Amazon Personalize",
        "personalize", 20, 300, 185, 100, dashed=True,
    )

    # External
    _, d3 = add_service_box(
        "d3", g_ext, "external",
        "OpenAI API",
        "generic_application", 20, 50, 185, 110,
    )
    _, e4 = add_service_box(
        "e4", g_ext, "external",
        "Neon PostgreSQL",
        "rds", 215, 50, 185, 110,
    )
    _, e6 = add_service_box(
        "e6", g_ext, "external",
        "Cloudflare R2",
        "internet", 100, 140, 185, 85,
    )

    # Storage
    _, e1 = add_service_box(
        "e1", g_storage, "storage",
        "Amazon S3",
        "s3", 20, 50, 155, 110,
    )
    _, e2 = add_service_box(
        "e2", g_storage, "storage",
        "Amazon S3",
        "s3", 185, 50, 155, 110,
    )
    _, e3 = add_service_box(
        "e3", g_storage, "storage",
        "Amazon S3",
        "s3", 350, 50, 155, 110,
    )
    _, e5 = add_service_box(
        "e5", g_storage, "storage",
        "ElastiCache",
        "elasticache", 185, 150, 155, 70, dashed=True,
    )

    # Security
    _, f1 = add_service_box(
        "f1", g_sec, "security",
        "AWS Secrets Manager",
        "secrets_manager", 15, 50, 105, 90,
    )
    _, f2 = add_service_box(
        "f2", g_sec, "security",
        "AWS IAM",
        "identity_and_access_management", 130, 50, 105, 90,
    )

    # Ops (wider boxes in a row)
    ops_items = [
        ("g1", "CloudWatch Logs", "cloudwatch_2", 8),
        ("g2", "CloudWatch Alarms", "cloudwatch_2", 75),
        ("g3", "AWS Budgets", "budgets_2", 142),
        ("g4", "Amazon SNS", "sns", 209),
    ]
    ops_icons: dict[str, str] = {}
    for prefix, lbl, icon, ox in ops_items:
        _, iid = add_service_box(prefix, g_ops, "ops", lbl, icon, ox, 45, 62, 90)
        ops_icons[prefix] = iid
    g1, g2, g3, g4 = ops_icons["g1"], ops_icons["g2"], ops_icons["g3"], ops_icons["g4"]

    _, g5 = add_service_box(
        "g5", g_ops, "ops",
        "AWS Lambda",
        "lambda", 275, 45, 62, 90,
    )

    # CI/CD
    _, h1 = add_service_box(
        "h1", g_cicd, "external",
        "GitHub",
        "internet", 25, 50, 180, 110,
    )
    _, h2 = add_service_box(
        "h2", g_cicd, "cicd",
        "CodeStar Connection",
        "codestar", 25, 180, 180, 110,
    )
    _, h3 = add_service_box(
        "h3", g_cicd, "cicd",
        "CodePipeline",
        "codepipeline", 25, 310, 180, 110,
    )
    _, h5 = add_service_box(
        "h5", g_cicd, "cicd",
        "CodeBuild",
        "codebuild", 25, 440, 180, 120,
    )

    # Legend (bottom-right, fits A3 page height)
    legend_x, legend_y = 1270, 1025
    add_rect_box("legend-box", "1", "", legend_x, legend_y, 290, 88, "#FFFFFF", "#BDBDBD", stroke_w=1)
    add_text_box("legend-title", "1", "&lt;b&gt;凡例&lt;/b&gt;", legend_x + 8, legend_y + 4, 80, 16, fontSize=12, bold=True)
    legend_items = [
        ("#1565C0", False, "実線 青 → ユーザーリクエストフロー"),
        ("#7B1FA2", False, "実線 紫 → AI / ML API 呼び出し"),
        ("#F9A825", False, "実線 黄 → ストレージ読み書き"),
        ("#C62828", False, "実線 赤 → セキュリティ / 設定注入"),
        ("#2E7D32", False, "実線 緑 → CI/CD デプロイフロー"),
        ("#616161", False, "実線 グレー → 監視 / コスト管理"),
        ("#616161", True, "破線 → Phase 4 / 任意コンポーネント"),
    ]
    for i, (color, dashed, text) in enumerate(legend_items):
        ly = legend_y + 22 + i * 9
        ds = "dashed=1;dashPattern=4 4;" if dashed else ""
        cells.append(
            f'<mxCell id="leg-line-{i}" parent="1" value="" style="line;strokeWidth={3 * SCALE};'
            f'strokeColor={color};{ds}html=1;fontFamily=Helvetica;" vertex="1">'
            f"{geom(legend_x + 18, ly + 6, 40, 4)}</mxCell>"
        )
        add_text_box(f"leg-txt-{i}", "1", text, legend_x + 52, ly, 230, 10, fontSize=9)

    add_rect_box(
        "notes", "1",
        "※ GCP 本番は移行元 · 破線は任意コンポーネント",
        30, 1025, 1220, 40, "#FFFDE7", "#FBC02D", stroke_w=1, font_size=10,
    )

    # Edges
    add_edge("e1", a1, b1, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.3, entry_x=0, entry_y=0.5)
    add_edge("e2", b1, e1, "", EDGE_COLORS["yellow"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e3", a1, b2, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.7, entry_x=0, entry_y=0.5)
    add_edge("e4", a2, b2, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.8)
    add_edge("e5", b2, b3, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)
    add_edge("e6", b3, c2, "", EDGE_COLORS["blue"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)

    add_edge("e7", c2, d3, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.2, entry_x=0, entry_y=0.5)
    add_edge("e8", c2, d1, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.35, entry_x=0, entry_y=0.5)
    add_edge("e9", c2, d2, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)
    add_edge("e10", c2, d4, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.65, entry_x=0, entry_y=0.5)
    add_edge("e11", c2, d5, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.8, entry_x=0, entry_y=0.5)
    add_edge("e12", c2, d6, "", EDGE_COLORS["purple"], exit_x=1, exit_y=0.9, entry_x=0, entry_y=0.5)
    add_edge("e13", c2, d7, "", EDGE_COLORS["purple"], dashed=True, exit_x=0.8, exit_y=1, entry_x=0, entry_y=1)

    add_edge("e14", c2, e4, "", EDGE_COLORS["yellow"], exit_x=1, exit_y=0.4, entry_x=0, entry_y=0.5)
    add_edge("e15", c2, e5, "", EDGE_COLORS["yellow"], dashed=True, exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e16", a1, e6, "", EDGE_COLORS["blue"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5, points=[(270, 280), (920, 280)])

    add_edge("e17", e2, d1, "", EDGE_COLORS["yellow"], exit_x=1, exit_y=0.3, entry_x=0, entry_y=1)
    add_edge("e18", e2, d2, "", EDGE_COLORS["yellow"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=1)

    add_edge("e19", f1, c2, "", EDGE_COLORS["red"], exit_x=1, exit_y=0.3, entry_x=0, entry_y=0.8)
    add_edge("e20", f2, c2, "", EDGE_COLORS["red"], exit_x=1, exit_y=0.7, entry_x=0, entry_y=0.9)

    add_edge("e21", c2, g1, "", EDGE_COLORS["gray"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e22", g1, g2, "", EDGE_COLORS["gray"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)
    add_edge("e23", g2, g4, "", EDGE_COLORS["gray"], exit_x=1, exit_y=0.5, entry_x=0, entry_y=0.5)

    add_edge("e24", g3, g4, "", EDGE_COLORS["gray"], exit_x=0.5, exit_y=0, entry_x=0.5, entry_y=1)
    add_edge("e25", g4, g5, "", EDGE_COLORS["gray"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e26", g5, c2, "", EDGE_COLORS["gray"], exit_x=0, exit_y=0.5, entry_x=1, entry_y=0.6)

    add_edge("e27", h1, h2, "", EDGE_COLORS["green"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e28", h2, h3, "", EDGE_COLORS["green"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e29", h3, e3, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.5, entry_x=1, entry_y=0.5)
    add_edge("e30", h3, h5, "", EDGE_COLORS["green"], exit_x=0.5, exit_y=1, entry_x=0.5, entry_y=0)
    add_edge("e31", h5, c1, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.5, entry_x=1, entry_y=0.5)
    add_edge("e32", h5, c2, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.3, entry_x=1, entry_y=0.3)
    add_edge("e33", h5, e1, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.5, entry_x=1, entry_y=0.8)
    add_edge("e34", h5, b1, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.2, entry_x=1, entry_y=0.8)
    add_edge("e35", h5, e2, "", EDGE_COLORS["green"], exit_x=0, exit_y=0.7, entry_x=1, entry_y=0.5)

    body = "\n        ".join(cells)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Electron" agent="medicine-recommend-generator" version="29.6.1">
  <diagram name="AWS Staging Architecture" id="aws-staging-full">
    <mxGraphModel dx="{PAGE_W}" dy="{PAGE_H}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{PAGE_H}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


def main() -> None:
    out = "/Users/yuto/medicine recomended/docs/medicine-recommend-aws-staging-architecture.drawio"
    xml = build()
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    ET.fromstring(xml)
    print(f"Written: {out}")
    print(f"Page: {PAGE_W} x {PAGE_H} px (scale {SCALE}x)")
    print(f"Size: {len(xml)} bytes")


if __name__ == "__main__":
    main()
