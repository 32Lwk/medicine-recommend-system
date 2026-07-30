#!/usr/bin/env python3
"""Generate simplified flow-oriented AWS staging architecture draw.io XML."""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET

SCALE = 2
PAGE_W = 1587 * SCALE
PAGE_H = 1123 * SCALE

# Routing spines (base coords, scaled in geom)
SPINE_USER = 470
SPINE_AI = 820
SPINE_DEPLOY = 1240
SPINE_BOTTOM = 1780

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

EDGE = {
    "blue": "#1565C0",
    "purple": "#7B1FA2",
    "yellow": "#F9A825",
    "red": "#C62828",
    "green": "#2E7D32",
    "gray": "#616161",
}

cells: list[str] = []
cid = 0


def s(v: float) -> float:
    return v * SCALE


def nid(p: str = "n") -> str:
    global cid
    cid += 1
    return f"{p}-{cid}"


def esc(t: str) -> str:
    return html.escape(t, quote=True)


def geom(x: float, y: float, w: float, h: float) -> str:
    return f'<mxGeometry x="{s(x)}" y="{s(y)}" width="{s(w)}" height="{s(h)}" as="geometry" />'


def swim(gid: str, label: str, x: float, y: float, w: float, h: float, kind: str) -> str:
    fill, stroke = COLORS[kind]
    cells.append(
        f'<mxCell id="{gid}" parent="1" value="&lt;b&gt;{esc(label)}&lt;/b&gt;" '
        f'style="rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize={14 * SCALE};'
        f"fontFamily=Helvetica;container=1;collapsible=0;pointerEvents=0;strokeWidth=2;"
        f"fillColor={fill};strokeColor={stroke};fontColor=#333333;align=left;spacingLeft={8 * SCALE};"
        f'" vertex="1">{geom(x, y, w, h)}</mxCell>'
    )
    return gid


def icon_box(
    prefix: str,
    parent: str,
    cat: str,
    label: str,
    res: str,
    x: float,
    y: float,
    w: float = 110,
    h: float = 110,
    fc: str | None = None,
    dashed: bool = False,
    bold: bool = False,
) -> tuple[str, str]:
    gid, iid = nid(prefix), nid(prefix + "i")
    fill, stroke = COLORS[cat]
    gs = (
        f"rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontFamily=Helvetica;"
        f"container=1;collapsible=0;pointerEvents=0;shadow=1;strokeWidth={4 if bold else 2};"
        f"fillColor={fill};strokeColor={stroke};"
    )
    if dashed:
        gs += "dashed=1;dashPattern=8 8;"
    cells.append(f'<mxCell id="{gid}" parent="{parent}" value="" style="{gs}" vertex="1">{geom(x, y, w, h)}</mxCell>')
    fc_map = {
        "network": "#8C4FFF", "compute": "#ED7100", "aiml": "#01A88D", "storage": "#3F8624",
        "security": "#DD344C", "ops": "#666666", "cicd": "#E7157B", "external": "#232F3D",
    }
    ic = fc or fc_map.get(cat, "#232F3E")
    istyle = (
        "sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
        "[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
        "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
        f"outlineConnect=0;fontColor=#232F3E;fillColor={ic};strokeColor=#ffffff;"
        f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
        f"fontSize={10 * SCALE};aspect=fixed;shape=mxgraph.aws4.resourceIcon;"
        f"resIcon=mxgraph.aws4.{res};fontFamily=Helvetica;shadow=1;"
    )
    cells.append(
        f'<mxCell id="{iid}" parent="{gid}" value="{label}" style="{istyle}" vertex="1">'
        f'{geom((w - 48) / 2, 22, 48, 48)}</mxCell>'
    )
    return gid, iid


def tag(text: str, x: float, y: float, w: float, h: float, bg: str, fg: str = "#FFFFFF") -> None:
    cells.append(
        f'<mxCell id="{nid("tag")}" parent="1" value="{esc(text)}" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={bg};strokeColor=none;'
        f"fontSize={10 * SCALE};fontFamily=Helvetica;fontStyle=1;fontColor={fg};"
        f'align=center;verticalAlign=middle;" vertex="1">{geom(x, y, w, h)}</mxCell>'
    )


def badge(num: str, x: float, y: float) -> None:
    cells.append(
        f'<mxCell id="{nid("bdg")}" parent="1" value="{num}" '
        f'style="ellipse;whiteSpace=wrap;html=1;fillColor=#007CBD;strokeColor=#005A8C;'
        f"fontSize={11 * SCALE};fontFamily=Helvetica;fontStyle=1;fontColor=#FFFFFF;"
        f'align=center;verticalAlign=middle;" vertex="1">{geom(x, y, 22, 22)}</mxCell>'
    )


def note_box(nid_: str, text: str, x: float, y: float, w: float, h: float) -> None:
    cells.append(
        f'<mxCell id="{nid_}" parent="1" value="{text}" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#FBC02D;'
        f"strokeWidth=1;fontSize={9 * SCALE};fontFamily=Helvetica;align=center;"
        f'verticalAlign=middle;fontColor=#232F3E;" vertex="1">{geom(x, y, w, h)}</mxCell>'
    )


def hub_label(parent: str, text: str, x: float, y: float) -> str:
    hid = nid("hub")
    cells.append(
        f'<mxCell id="{hid}" parent="{parent}" value="&lt;b&gt;{esc(text)}&lt;/b&gt;" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F3E5F5;strokeColor=#9C27B0;'
        f"strokeWidth=1;fontSize={9 * SCALE};fontFamily=Helvetica;align=center;"
        f'verticalAlign=middle;fontColor=#232F3E;" vertex="1">{geom(x, y, 80, 28)}</mxCell>'
    )
    return hid


def edge(
    eid: str,
    src: str,
    tgt: str,
    color: str,
    *,
    dashed: bool = False,
    ex: float | None = None,
    ey: float | None = None,
    ix: float | None = None,
    iy: float | None = None,
    points: list[tuple[float, float]] | None = None,
) -> None:
    ds = "dashed=1;dashPattern=8 8;" if dashed else ""
    st = (
        f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
        f"html=1;fontFamily=Helvetica;strokeColor={color};strokeWidth={2 * SCALE};"
        f"endArrow=block;endFill=1;{ds}"
    )
    if ex is not None:
        st += f"exitX={ex};exitY={ey};entryX={ix};entryY={iy};"
    geo = '<mxGeometry relative="1" as="geometry">'
    if points:
        geo += "<Array as=\"points\">"
        for px, py in points:
            geo += f'<mxPoint x="{s(px)}" y="{s(py)}" />'
        geo += "</Array>"
    geo += "</mxGeometry>"
    cells.append(f'<mxCell id="{eid}" parent="1" source="{src}" target="{tgt}" edge="1" style="{st}">{geo}</mxCell>')


def spine_edge(eid: str, src: str, tgt: str, color: str, spine_x: float, tgt_y: float, **kw) -> None:
    """Route via vertical spine then horizontal to target."""
    dashed = kw.get("dashed", False)
    ex, ey = kw.get("ex", 1), kw.get("ey", 0.5)
    edge(eid, src, tgt, color, dashed=dashed, ex=ex, ey=ey, ix=0, iy=0.5, points=[(spine_x, tgt_y)])


def build() -> str:
    global cells, cid
    cells, cid = [], 0

    # Title
    cells.append(
        f'<mxCell id="title" parent="1" value="AWS ステージング構成 — aws.medicine.yutok.dev" '
        f'style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;'
        f'fontSize={20 * SCALE};fontFamily=Helvetica;fontStyle=1;" vertex="1">'
        f'{geom(40, 18, 900, 32)}</mxCell>'
    )
    cells.append(
        f'<mxCell id="sub" parent="1" value="ap-northeast-1 · 290780119994" '
        f'style="text;html=1;strokeColor=none;fillColor=none;align=left;fontSize={10 * SCALE};'
        f'fontFamily=Helvetica;" vertex="1">{geom(40, 48, 600, 20)}</mxCell>'
    )

    tag("① ユーザーリクエスト →", 280, 78, 520, 28, "#1565C0")
    tag("② デプロイ ↓", 1270, 78, 200, 28, "#2E7D32")
    tag("③ データ / AI", 830, 78, 200, 28, "#7B1FA2")

    g_user = swim("g-user", "クライアント", 30, 110, 220, 300, "user")
    g_net = swim("g-net", "ネットワーク", 270, 110, 540, 170, "network")
    g_compute = swim("g-compute", "ECS", 270, 300, 540, 260, "compute")
    g_aiml = swim("g-aiml", "AI / ML", 830, 110, 400, 450, "aiml")
    g_ext = swim("g-ext", "外部", 830, 580, 400, 180, "external")
    g_storage = swim("g-storage", "ストレージ", 270, 580, 540, 170, "storage")
    g_sec = swim("g-sec", "セキュリティ", 270, 770, 240, 120, "security")
    g_ops = swim("g-ops", "運用 / 監視", 530, 770, 280, 120, "ops")
    g_cicd = swim("g-cicd", "CI/CD", 1260, 110, 300, 780, "cicd")

    _, a1 = icon_box("a1", g_user, "user", "ブラウザ", "users", 55, 55, 110, 110, fc="#FF9800")
    _, a2 = icon_box("a2", g_user, "user", "LINE", "mobile", 55, 190, 110, 110, fc="#FF9800")

    _, b1 = icon_box("b1", g_net, "network", "CloudFront", "cloudfront", 30, 50, 110, 110)
    _, b2 = icon_box("b2", g_net, "security", "WAF", "waf", 170, 50, 110, 110)
    _, b3 = icon_box("b3", g_net, "network", "ALB", "elastic_load_balancing", 310, 50, 110, 110)

    _, c2 = icon_box("c2", g_compute, "compute", "ECS Express", "ecs", 200, 45, 140, 120, bold=True)
    _, c1 = icon_box("c1", g_compute, "compute", "ECR", "ecr", 380, 150, 100, 100)

    hub_label(g_aiml, "API Hub", 160, 230)

    _, d1 = icon_box("d1", g_aiml, "aiml", "KB Concierge", "bedrock", 30, 50, 120, 100)
    _, d2 = icon_box("d2", g_aiml, "aiml", "KB Medicine", "bedrock", 170, 50, 120, 100)
    _, d4 = icon_box("d4", g_aiml, "aiml", "Translate", "translate", 30, 170, 100, 90)
    _, d5 = icon_box("d5", g_aiml, "aiml", "Polly", "polly", 145, 170, 100, 90)
    _, d6 = icon_box("d6", g_aiml, "aiml", "Comprehend", "comprehend_medical", 260, 170, 100, 90)
    _, d7 = icon_box("d7", g_aiml, "aiml", "Personalize", "personalize", 30, 280, 120, 90, dashed=True)

    _, d3 = icon_box("d3", g_ext, "external", "OpenAI", "generic_application", 30, 45, 110, 100)
    _, e4 = icon_box("e4", g_ext, "external", "Neon PG", "rds", 160, 45, 110, 100)
    _, e6 = icon_box("e6", g_ext, "external", "CF R2", "internet", 290, 45, 100, 100)

    _, e1 = icon_box("e1", g_storage, "storage", "S3 static", "s3", 30, 45, 110, 100)
    _, e2 = icon_box("e2", g_storage, "storage", "S3 KB", "s3", 160, 45, 110, 100)
    _, e3 = icon_box("e3", g_storage, "storage", "S3 artifacts", "s3", 290, 45, 110, 100)
    _, e5 = icon_box("e5", g_storage, "storage", "Redis", "elasticache", 420, 45, 100, 100, dashed=True)

    _, f1 = icon_box("f1", g_sec, "security", "Secrets", "secrets_manager", 25, 45, 90, 80)
    _, f2 = icon_box("f2", g_sec, "security", "IAM", "identity_and_access_management", 130, 45, 90, 80)

    ops = [
        ("g1", "CloudWatch", "cloudwatch_2", 10),
        ("g2", "Alarms", "cloudwatch_2", 68),
        ("g3", "Budgets", "budgets_2", 126),
        ("g4", "SNS", "sns", 184),
        ("g5", "Lambda", "lambda", 242),
    ]
    op_ids = {}
    for p, lb, ic, ox in ops:
        _, iid = icon_box(p, g_ops, "ops", lb, ic, ox, 40, 58, 72)
        op_ids[p] = iid

    _, h1 = icon_box("h1", g_cicd, "external", "GitHub", "internet", 95, 40, 110, 100)
    _, h2 = icon_box("h2", g_cicd, "cicd", "CodeStar", "codestar", 95, 160, 110, 100)
    _, h3 = icon_box("h3", g_cicd, "cicd", "Pipeline", "codepipeline", 95, 280, 110, 100)
    _, h5 = icon_box("h5", g_cicd, "cicd", "CodeBuild", "codebuild", 95, 400, 110, 100)

    tag("デプロイ先 →", 1260, 530, 300, 24, "#E3F2FD", "#1976D2")
    _, dep_ecr_i = icon_box("dep1", g_cicd, "compute", "ECR", "ecr", 20, 570, 58, 70)
    _, dep_ecs_i = icon_box("dep2", g_cicd, "compute", "ECS", "ecs", 85, 570, 58, 70)
    _, dep_s3_i = icon_box("dep3", g_cicd, "storage", "S3", "s3", 150, 570, 58, 70)
    _, dep_cf_i = icon_box("dep4", g_cicd, "network", "CF", "cloudfront", 215, 570, 58, 70)

    # Step badges — user request path
    badge("1", 248, 155)
    badge("2", 388, 155)
    badge("3", 528, 155)
    badge("4", 528, 295)
    badge("1", 1248, 155)
    badge("2", 1248, 275)
    badge("3", 1248, 395)
    badge("4", 1248, 515)

    # Legend (compact)
    lx, ly = 1260, 920
    cells.append(
        f'<mxCell id="leg" parent="1" value="" style="rounded=1;fillColor=#FFFFFF;strokeColor=#BDBDBD;" '
        f'vertex="1">{geom(lx, ly, 300, 130)}</mxCell>'
    )
    items = [
        ("#1565C0", False, "青 — ユーザー"),
        ("#7B1FA2", False, "紫 — AI/ML"),
        ("#F9A825", False, "黄 — ストレージ"),
        ("#C62828", False, "赤 — セキュリティ"),
        ("#2E7D32", False, "緑 — CI/CD"),
        ("#616161", False, "灰 — 監視"),
        ("#616161", True, "破線 — Phase 4"),
    ]
    for i, (c, d, t) in enumerate(items):
        yy = ly + 12 + i * 16
        ds = "dashed=1;" if d else ""
        cells.append(
            f'<mxCell id="ll{i}" parent="1" value="" style="line;strokeWidth={2 * SCALE};'
            f'strokeColor={c};{ds}html=1;" vertex="1">{geom(lx + 10, yy + 6, 24, 3)}</mxCell>'
        )
        cells.append(
            f'<mxCell id="lt{i}" parent="1" value="{t}" style="text;html=1;fontSize={8 * SCALE};'
            f'fontFamily=Helvetica;" vertex="1">{geom(lx + 40, yy, 240, 14)}</mxCell>'
        )

    note_box("notes", "※ GCP 本番は別環境 · 破線 = Phase 4 任意", 30, 920, 500, 36)

    # --- Edges: no labels ---

    # User flow (horizontal spine)
    edge("e-a1-cf", a1, b1, EDGE["blue"], ex=1, ey=0.25, ix=0, iy=0.5, points=[(SPINE_USER, 165)])
    edge("e-a1-waf", a1, b2, EDGE["blue"], ex=1, ey=0.75, ix=0, iy=0.5, points=[(SPINE_USER, 195)])
    edge("e-a2-waf", a2, b2, EDGE["blue"], ex=1, ey=0.5, ix=0, iy=0.85, points=[(SPINE_USER, 240)])
    edge("e-waf-alb", b2, b3, EDGE["blue"], ex=1, ey=0.5, ix=0, iy=0.5)
    edge("e-alb-ecs", b3, c2, EDGE["blue"], ex=0.5, ey=1, ix=0.5, iy=0, points=[(528, 295)])

    # Static CDN path (left corridor)
    edge("e-cf-s3", b1, e1, EDGE["yellow"], ex=0.5, ey=1, ix=0.5, iy=0, points=[(325, 560)])

    # Browser → R2 (bottom corridor)
    edge("e-a1-r2", a1, e6, EDGE["blue"], ex=0.5, ey=1, ix=0, iy=0.5, points=[(135, SPINE_BOTTOM), (880, SPINE_BOTTOM)])

    # ECS → AI via spine (one trunk + hub branches)
    spine_edge("e-ecs-d1", c2, d1, EDGE["purple"], SPINE_AI, 160)
    spine_edge("e-ecs-d2", c2, d2, EDGE["purple"], SPINE_AI + 20, 160)
    spine_edge("e-ecs-d4", c2, d4, EDGE["purple"], SPINE_AI, 255)
    spine_edge("e-ecs-d5", c2, d5, EDGE["purple"], SPINE_AI + 20, 255)
    spine_edge("e-ecs-d6", c2, d6, EDGE["purple"], SPINE_AI + 40, 255)
    spine_edge("e-ecs-d7", c2, d7, EDGE["purple"], SPINE_AI, 355, dashed=True)
    spine_edge("e-ecs-oai", c2, d3, EDGE["purple"], SPINE_AI + 60, 625)

    # Storage
    spine_edge("e-ecs-neon", c2, e4, EDGE["yellow"], SPINE_AI + 80, 625)
    edge("e-ecs-redis", c2, e5, EDGE["yellow"], dashed=True, ex=0.75, ey=1, ix=0, iy=0.5, points=[(700, 560)])
    edge("e-s3kb-d1", e2, d1, EDGE["yellow"], ex=1, ey=0.3, ix=0, iy=1, points=[(800, 680), (800, 160)])
    edge("e-s3kb-d2", e2, d2, EDGE["yellow"], ex=1, ey=0.5, ix=0, iy=1, points=[(810, 680), (810, 160)])

    # Security
    edge("e-sec1", f1, c2, EDGE["red"], ex=1, ey=0.3, ix=0, iy=1, points=[(450, 720)])
    edge("e-sec2", f2, c2, EDGE["red"], ex=1, ey=0.7, ix=0, iy=1, points=[(470, 720)])

    # Ops chain
    edge("e-ecs-cw", c2, op_ids["g1"], EDGE["gray"], ex=0.5, ey=1, ix=0.5, iy=0, points=[(370, 760)])
    edge("e-cw-al", op_ids["g1"], op_ids["g2"], EDGE["gray"], ex=1, ey=0.5, ix=0, iy=0.5)
    edge("e-al-sns", op_ids["g2"], op_ids["g4"], EDGE["gray"], ex=1, ey=0.5, ix=0, iy=0.5)
    edge("e-bg-sns", op_ids["g3"], op_ids["g4"], EDGE["gray"], ex=0.5, ey=0, ix=0.5, iy=1)
    edge("e-sns-lm", op_ids["g4"], op_ids["g5"], EDGE["gray"], ex=1, ey=0.5, ix=0, iy=0.5)
    edge("e-lm-ecs", op_ids["g5"], c2, EDGE["gray"], ex=0, ey=0.5, ix=1, iy=0.7, points=[(500, 800)])

    # CI/CD vertical
    edge("e-gh-cs", h1, h2, EDGE["green"], ex=0.5, ey=1, ix=0.5, iy=0)
    edge("e-cs-cp", h2, h3, EDGE["green"], ex=0.5, ey=1, ix=0.5, iy=0)
    edge("e-cp-cb", h3, h5, EDGE["green"], ex=0.5, ey=1, ix=0.5, iy=0)
    edge("e-cp-s3a", h3, e3, EDGE["green"], ex=0, ey=0.5, ix=1, iy=0.5, points=[(SPINE_DEPLOY, 390), (SPINE_DEPLOY, 625)])

    # CodeBuild → deploy hubs → targets (via deploy spine)
    for i, dep_iid in enumerate([dep_ecr_i, dep_ecs_i, dep_s3_i, dep_cf_i], start=1):
        edge(f"e-cb-dep{i}", h5, dep_iid, EDGE["green"], ex=0.5, ey=1, ix=0.5, iy=0)

    deploy_targets = [
        (dep_ecr_i, c1, 400, "ecr"),
        (dep_ecs_i, c2, 360, "ecs"),
        (dep_s3_i, e1, 625, "s3s"),
        (dep_cf_i, b1, 165, "cf"),
    ]
    for dep_iid, tgt, ty, slug in deploy_targets:
        edge(f"e-dep-{slug}", dep_iid, tgt, EDGE["green"], ex=0, ey=0.5, ix=1, iy=0.5, points=[(SPINE_DEPLOY, ty)])
    edge("e-dep-kb", dep_s3_i, e2, EDGE["green"], ex=0, ey=0.5, ix=1, iy=0.5, points=[(SPINE_DEPLOY, 655)])

    body = "\n        ".join(cells)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Electron" agent="medicine-recommend-flow" version="29.6.1">
  <diagram name="AWS Staging Flow" id="aws-staging-flow">
    <mxGraphModel dx="{PAGE_W}" dy="{PAGE_H}" grid="0" gridSize="10" guides="1" tooltips="1"
      connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{PAGE_H}"
      math="0" shadow="0">
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
    out = "/Users/yuto/medicine recomended/docs/medicine-recommend-aws-staging-architecture-flow.drawio"
    xml = build()
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    ET.fromstring(xml)
    print(f"Written: {out}")
    print(f"Page: {PAGE_W} x {PAGE_H} px")


if __name__ == "__main__":
    main()
