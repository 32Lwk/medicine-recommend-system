#!/usr/bin/env python3
"""Generate multi-page AWS staging architecture draw.io (complete edition).

Output: docs/medicine-recommend-aws-staging-complete.drawio

Pages:
  00 目次
  01 全体構成          (full AWS staging — from generate_aws_staging_diagram)
  02 統合 3 ゾーン
  03 ユーザーリクエスト
  04 CI/CD パイプライン
  05 外部連携マップ
  06 クロスクラウド比較
  07 Chat Pipeline v2
  08 症状相談 Physical
  09 Bedrock KB RAG
  10 運用・コスト管理
  11 LINE Webhook (AWS)
  12 シークレット・データ
"""

from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "medicine-recommend-aws-staging-complete.drawio"

ICON = (
    "sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
    "[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
    "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
    "outlineConnect=0;fontColor=#232F3E;fillColor={fc};strokeColor=#ffffff;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;"
    "aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};"
    "fontFamily=Helvetica;shadow=1;"
)

GRP = (
    "fillColor={fill};strokeColor={stroke};rounded=1;whiteSpace=wrap;html=1;"
    "verticalAlign=top;fontStyle=1;fontSize=12;fontColor={stroke};fontFamily=Helvetica;"
    "container=1;collapsible=0;shadow=1;strokeWidth=1.5;"
)

CAT = {
    "compute": ("#FFF2E8", "#ED7100", "#ED7100"),
    "network": ("#EDE7F6", "#8C4FFF", "#8C4FFF"),
    "security": ("#FFEBEE", "#DD344C", "#DD344C"),
    "storage": ("#E8F5E9", "#3F8624", "#3F8624"),
    "integration": ("#FCE4EC", "#E7157B", "#E7157B"),
    "ai": ("#E0F2F1", "#01A88D", "#01A88D"),
    "database": ("#F5E6F7", "#C925D1", "#C925D1"),
}


def xa(text: str) -> str:
    return html.escape(text, quote=True)


@dataclass
class Sheet:
    name: str
    sid: str
    pw: int
    ph: int
    cells: list[str] = field(default_factory=list)
    _id: int = 0

    def nid(self, p: str = "c") -> str:
        self._id += 1
        return f"{p}-{self._id}"

    def v(self, cid: str, val: str, style: str, x: int, y: int, w: int, h: int, parent: str = "1") -> None:
        self.cells.append(
            f'<mxCell id="{cid}" parent="{parent}" value="{val}" style="{style}" vertex="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
        )

    def title(self, title: str, subtitle: str, w: int = 1500) -> None:
        self.v("t-1", xa(title), "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;fontSize=24;fontFamily=Helvetica;fontStyle=1;", 40, 20, w, 36)
        self.v("t-2", xa(subtitle), "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;fontSize=14;fontFamily=Helvetica;", 40, 56, w, 24)
        self.v("sep", "", "line;strokeWidth=3;html=1;strokeColor=#FF9900;fontFamily=Helvetica;", 40, 88, w - 40, 6)

    def box(self, label: str, x: int, y: int, w: int = 150, h: int = 45, stroke: str = "#ED7100", fill: str = "#FFF2E8", fs: int = 11) -> str:
        cid = self.nid("b")
        self.v(
            cid, label,
            f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=2;"
            f"fontSize={fs};fontFamily=Helvetica;align=center;verticalAlign=middle;fontColor=#232F3E;",
            x, y, w, h,
        )
        return cid

    def note(self, text: str, x: int, y: int, w: int = 700, h: int = 40) -> None:
        self.v(
            self.nid("note"), text,
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#FBC02D;strokeWidth=1;"
            "fontSize=10;fontFamily=Helvetica;align=left;spacingLeft=8;verticalAlign=top;fontColor=#232F3E;",
            x, y, w, h,
        )

    def ext(self, label: str, icon: str, x: int, y: int) -> str:
        gid, iid = self.nid("ex"), self.nid("xi")
        self.v(
            gid, label,
            "fillColor=#f5f5f5;strokeColor=#666666;rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;"
            "fontStyle=1;fontSize=12;fontColor=#333333;fontFamily=Helvetica;container=1;collapsible=0;shadow=1;",
            x, y, 120, 98,
        )
        self.v(iid, "", ICON.format(fc="#232F3D", icon=icon), 36, 30, 48, 48, gid)
        return iid

    def svc(self, cat: str, grp: str, name: str, sub: str, icon: str, x: int, y: int, dashed: bool = False) -> str:
        fill, stroke, fc = CAT[cat]
        gid, sid = self.nid("g"), self.nid("s")
        gs = GRP.format(fill=fill, stroke=stroke)
        if dashed:
            gs += "dashed=1;dashPattern=8 8;"
        self.v(gid, grp, gs, x, y, 120, 120)
        val = f"{xa(name)}&lt;div&gt;&lt;i&gt;{xa(sub)}&lt;/i&gt;&lt;/div&gt;" if sub else xa(name)
        self.v(sid, val, ICON.format(fc=fc, icon=icon), 36, 30, 48, 48, gid)
        return sid

    def lane(self, label: str, x: int, y: int, w: int, h: int, fill: str, stroke: str) -> str:
        lid = self.nid("lane")
        self.v(
            lid,
            f"&lt;b&gt;{xa(label)}&lt;/b&gt;",
            f"rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize=13;"
            f"fontFamily=Helvetica;container=1;collapsible=0;pointerEvents=0;strokeWidth=2;"
            f"fillColor={fill};strokeColor={stroke};fontColor=#333333;align=left;spacingLeft=10;spacingTop=6;",
            x, y, w, h,
        )
        return lid

    def step(self, num: str, label: str, x: int, y: int, w: int = 130, h: int = 48, stroke: str = "#ED7100") -> str:
        cid = self.nid("st")
        self.v(
            cid,
            f"&lt;b&gt;{num}&lt;/b&gt; {label}",
            f"rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2E8;strokeColor={stroke};strokeWidth=2;"
            f"fontSize=10;fontFamily=Helvetica;align=center;verticalAlign=middle;fontColor=#232F3E;",
            x, y, w, h,
        )
        return cid

    def phase_hdr(self, text: str, x: int, y: int, w: int = 400) -> None:
        self.v(
            self.nid("ph"),
            f"&lt;b&gt;{xa(text)}&lt;/b&gt;",
            "text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=13;fontColor=#666666;fontFamily=Helvetica;fontStyle=1;",
            x, y, w, 22,
        )

    def edge(
        self,
        src: str,
        tgt: str,
        label: str = "",
        color: str = "#232F3E",
        dashed: bool = False,
        points: list[tuple[int, int]] | None = None,
    ) -> None:
        eid = self.nid("e")
        ds = "dashed=1;dashPattern=8 8;" if dashed else ""
        pts = ""
        if points:
            pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        self.cells.append(
            f'<mxCell id="{eid}" parent="1" source="{src}" target="{tgt}" edge="1" '
            f'style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;'
            f'fontFamily=Helvetica;strokeColor={color};strokeWidth=2;endArrow=block;{ds}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        if label:
            lid = self.nid("el")
            self.cells.append(
                f'<mxCell id="{lid}" parent="{eid}" value="{xa(label)}" connectable="0" vertex="1" '
                f'style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];'
                f'fontSize=10;fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;">'
                f'<mxGeometry relative="1" x="-0.1" y="-12" as="geometry"><mxPoint as="offset" /></mxGeometry></mxCell>'
            )

    def render(self) -> str:
        body = "\n        ".join(self.cells)
        return f"""  <diagram name="{xa(self.name)}" id="{self.sid}">
    <mxGraphModel dx="{self.pw}" dy="{self.ph}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{self.pw}" pageHeight="{self.ph}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {body}
      </root>
    </mxGraphModel>
  </diagram>"""


def _extract_diagram_body(xml: str) -> str:
    m = re.search(r"<root>\s*(.*?)\s*</root>", xml, re.DOTALL)
    if not m:
        raise RuntimeError("Failed to parse diagram body from XML")
    body = m.group(1).strip()
    body = re.sub(r'<mxCell id="0"\s*/>\s*', "", body, count=1)
    body = re.sub(r'<mxCell id="1" parent="0"\s*/>\s*', "", body, count=1)
    return body.strip()


def sheet_page1_from_staging() -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_aws_staging_diagram import build, PAGE_W, PAGE_H  # noqa: WPS433

    body = _extract_diagram_body(build())
    return f"""  <diagram name="01 全体構成" id="sheet-01-full">
    <mxGraphModel dx="{PAGE_W}" dy="{PAGE_H}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{PAGE_W}" pageHeight="{PAGE_H}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {body}
      </root>
    </mxGraphModel>
  </diagram>"""


def build_index() -> Sheet:
    s = Sheet("00 目次", "sheet-00-index", 1400, 900)
    s.title("medicine-recommend アーキテクチャ図 — 目次", "12 ページ構成 / draw.io で各タブを選択")
    rows = [
        ("01", "全体構成", "AWS ステージング全コンポーネント（ユーザー / ECS / CI/CD / AI / 外部）"),
        ("02", "統合 3 ゾーン", "ユーザー / AWS ランタイム / CI/CD / 外部 SaaS の俯瞰"),
        ("03", "ユーザーリクエスト", "Web + LINE → WAF → ALB → ECS → 外部 API"),
        ("04", "CI/CD パイプライン", "GitHub → CodePipeline → CodeBuild → ECR/ECS/S3/KB"),
        ("05", "外部連携マップ", "ECS 中心: OpenAI / Neon / R2 / Translate / Polly / Bedrock"),
        ("06", "クロスクラウド比較", "GCP 移行元 vs AWS（LINE 含む） vs 共通 R2"),
        ("07", "Chat Pipeline v2", "5 フェーズ全体像 + ルート振分表 + エージェント詳細（swim lane）"),
        ("08", "症状相談 Physical", "番号付きフロー: NLU → ルールスコア → カード/SSE"),
        ("09", "Concierge / KB RAG", "番号付きフロー: 同期 → ingestion → retrieve → 生成"),
        ("10", "運用・コスト管理", "CloudWatch / Budget 6 段階 / Lambda 縮小 / IAM"),
        ("11", "LINE Webhook (AWS)", "LINE → WAF → ALB → ECS → Pipeline v2 → Messaging API 返信"),
        ("12", "シークレット・データ", "Secrets Manager / Neon / ログ / Web vs LINE 保存"),
    ]
    y = 120
    for num, name, desc in rows:
        s.v(
            s.nid("row"),
            f"&lt;b&gt;{num} {xa(name)}&lt;/b&gt;&lt;br&gt;{xa(desc)}",
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#FAFAFA;strokeColor=#BDBDBD;strokeWidth=1;"
            "fontSize=11;fontFamily=Helvetica;align=left;spacingLeft=12;verticalAlign=middle;fontColor=#232F3E;",
            40, y, 1320, 52,
        )
        y += 58
    s.note(
        "draw.io で各タブを選択してページを切り替え",
        40, 820, 500, 30,
    )
    return s


def build_integrated_zones() -> Sheet:
    """02 — user / AWS runtime / CI/CD / external SaaS."""
    s = Sheet("02 統合 3 ゾーン", "sheet-02-integrated", 2100, 1020)
    s.title(
        "統合アーキテクチャ",
        "ユーザー · AWS ランタイム · CI/CD · 外部 SaaS",
        2000,
    )

    s.lane("① ユーザー", 40, 110, 240, 200, "#FFF3E0", "#FF9800")
    s.lane("② AWS ランタイム", 300, 110, 1040, 620, "#FFF2E8", "#ED7100")
    s.lane("③ CI/CD", 1380, 110, 300, 620, "#E3F2FD", "#1976D2")
    s.lane("④ 外部 SaaS", 300, 760, 1040, 200, "#FCE4EC", "#E91E63")

    browser = s.ext("Browser", "users", 100, 160)
    line = s.ext("LINE Platform", "mobile", 100, 280)

    waf = s.svc("security", "Security", "AWS WAF", "", "waf", 340, 160)
    alb = s.svc("network", "Network", "ALB", "", "elastic_load_balancing", 520, 160)
    ecs = s.svc("compute", "Compute", "ECS Express", "", "ecs", 700, 160)
    sm = s.svc("security", "Secrets", "Secrets Manager", "", "secrets_manager", 880, 160)

    s3s = s.svc("storage", "Storage", "Amazon S3", "", "s3", 340, 320)
    cf = s.svc("network", "CDN", "CloudFront", "", "cloudfront", 520, 320)
    tr = s.svc("ai", "Translate", "Amazon Translate", "", "translate", 340, 480)
    po = s.svc("ai", "TTS", "Amazon Polly", "", "polly", 500, 480)
    br = s.svc("ai", "RAG", "Bedrock KB", "", "bedrock", 660, 480)
    cache = s.svc("database", "Cache", "ElastiCache", "", "elasticache", 820, 480, dashed=True)
    s3k = s.svc("storage", "KB", "Amazon S3", "", "s3", 340, 640)
    cw = s.svc("integration", "Ops", "CloudWatch", "", "cloudwatch", 820, 640)

    gh = s.ext("GitHub", "internet", 1420, 160)
    cs = s.svc("integration", "Source", "CodeStar", "", "codestar", 1420, 300)
    cp = s.svc("integration", "Pipe", "CodePipeline", "", "codepipeline", 1420, 440)
    cb = s.svc("integration", "Build", "CodeBuild", "", "codebuild", 1420, 580)
    ecr = s.svc("compute", "Registry", "Amazon ECR", "", "ecr", 1560, 580)

    oai = s.ext("OpenAI API", "generic_application", 460, 790)
    neon = s.ext("Neon PostgreSQL", "generic_database", 680, 790)
    r2 = s.ext("Cloudflare R2", "internet", 900, 790)

    s.edge(browser, waf, "", "#1565C0")
    s.edge(line, waf, "", "#1565C0")
    s.edge(waf, alb, "", "#1565C0")
    s.edge(alb, ecs, "", "#1565C0")
    s.edge(sm, ecs, "", "#C62828", dashed=True)
    s.edge(s3s, cf, "", "#F9A825")
    s.edge(cf, browser, "", "#1565C0", points=[(580, 300), (160, 300)])
    s.edge(ecs, tr, "", "#7B1FA2")
    s.edge(ecs, po, "", "#7B1FA2")
    s.edge(ecs, br, "", "#7B1FA2")
    s.edge(ecs, neon, "", "#F9A825")
    s.edge(ecs, oai, "", "#7B1FA2")
    s.edge(ecs, r2, "", "#1565C0")
    s.edge(ecs, cw, "", "#616161")
    s.edge(s3k, br, "", "#F9A825", dashed=True)
    s.edge(gh, cs, "", "#2E7D32")
    s.edge(cs, cp, "", "#2E7D32")
    s.edge(cp, cb, "", "#2E7D32")
    s.edge(cb, ecr, "", "#2E7D32")
    s.edge(ecr, ecs, "", "#2E7D32", points=[(1620, 700), (1620, 740), (760, 740)])
    return s


def build_external_map() -> Sheet:
    """05 — ECS hub and external integrations."""
    s = Sheet("05 外部連携マップ", "sheet-05-ext", 1300, 800)
    s.title(
        "ECS 中心の外部連携",
        "Secrets · OpenAI · Neon · R2 · AWS AI",
    )

    ecs = s.svc("compute", "Hub", "ECS Express", "", "ecs", 560, 300)
    sm = s.svc("security", "Secrets", "Secrets Manager", "", "secrets_manager", 560, 120)
    iam = s.svc("security", "IAM", "IAM", "", "identity_and_access_management", 760, 120)

    oai = s.ext("OpenAI API", "generic_application", 80, 200)
    neon = s.ext("Neon PostgreSQL", "generic_database", 80, 380)
    r2 = s.ext("Cloudflare R2", "internet", 80, 560)
    deepl = s.ext("DeepL", "generic_application", 80, 680)

    tr = s.svc("ai", "Translate", "Amazon Translate", "", "translate", 1040, 200)
    po = s.svc("ai", "TTS", "Amazon Polly", "", "polly", 1040, 320)
    kb1 = s.svc("ai", "KB", "Bedrock KB", "", "bedrock", 1040, 440)
    kb2 = s.svc("ai", "KB", "Bedrock KB", "", "bedrock", 1040, 560)
    cm = s.svc("ai", "NLU", "Comprehend Medical", "", "comprehend_medical", 880, 680)
    cache = s.svc("database", "Cache", "ElastiCache", "", "elasticache", 1040, 680, dashed=True)
    pz = s.svc("ai", "Rank", "Personalize", "", "personalize", 1200, 680, dashed=True)

    s.edge(sm, ecs, "", "#C62828", dashed=True)
    s.edge(iam, ecs, "", "#C62828", dashed=True)
    s.edge(ecs, oai, "", "#7B1FA2")
    s.edge(ecs, neon, "", "#F9A825")
    s.edge(ecs, r2, "", "#1565C0")
    s.edge(ecs, tr, "", "#7B1FA2")
    s.edge(ecs, po, "", "#7B1FA2")
    s.edge(ecs, kb1, "", "#7B1FA2")
    s.edge(ecs, kb2, "", "#7B1FA2")
    s.edge(ecs, cm, "", "#7B1FA2", dashed=True)
    s.edge(ecs, cache, "", "#7B1FA2", dashed=True)
    s.edge(ecs, pz, "", "#7B1FA2", dashed=True)
    return s


def build_ops_cost() -> Sheet:
    """10 — monitoring, budgets, cost actions."""
    s = Sheet("10 運用・コスト管理", "sheet-10-ops", 1400, 900)
    s.title(
        "運用・コスト管理",
        "CloudWatch · Budgets · SNS · Lambda",
    )

    ecs = s.svc("compute", "App", "ECS Express", "", "ecs", 560, 280)
    logs = s.svc("integration", "Logs", "CloudWatch Logs", "", "cloudwatch", 300, 280)
    alarms = s.svc("integration", "Alarm", "CloudWatch Alarms", "", "cloudwatch", 300, 420)
    budgets = s.svc("integration", "Cost", "AWS Budgets", "", "budgets", 300, 560)
    sns = s.svc("integration", "Notify", "Amazon SNS", "", "sns", 560, 560)
    lam = s.svc("compute", "Action", "Lambda", "", "lambda", 820, 560)
    cb = s.svc("integration", "Build", "CodeBuild", "", "codebuild", 820, 280)

    s.edge(ecs, logs, "", "#616161")
    s.edge(logs, alarms, "", "#616161")
    s.edge(alarms, sns, "", "#616161")
    s.edge(budgets, sns, "", "#616161")
    s.edge(sns, lam, "", "#616161")
    s.edge(lam, ecs, "", "#616161", points=[(880, 620), (880, 340), (620, 340)])
    s.edge(lam, cb, "", "#616161")
    return s


def build_line_aws() -> Sheet:
    """11 — LINE Messaging API on AWS (WAF → ALB → ECS)."""
    s = Sheet("11 LINE Webhook (AWS)", "sheet-11-line", 1900, 1050)
    s.title(
        "LINE Messaging API — AWS 経路",
        "LINE → WAF → ALB → ECS",
        1800,
    )

    s.lane("Phase 1 — エッジ", 40, 105, 1820, 100, "#FFF3E0", "#FF9800")
    s.lane("Phase 2 — Webhook 受信", 40, 215, 1820, 110, "#FFEBEE", "#DD344C")
    s.lane("Phase 3 — 会話パイプライン", 40, 335, 1820, 100, "#E8F4FC", "#147EBA")
    s.lane("Phase 4 — LINE 返信", 40, 445, 1820, 100, "#E3F2FD", "#1976D2")
    s.lane("Phase 5 — 外部連携", 40, 555, 1820, 130, "#E0F2F1", "#01A88D")

    line = s.ext("LINE Platform", "mobile", 60, 120)
    waf = s.svc("security", "Edge", "AWS WAF", "", "waf", 200, 110)
    alb = s.svc("network", "LB", "ALB", "", "elastic_load_balancing", 360, 110)
    ecs = s.svc("compute", "App", "ECS Express", "", "ecs", 520, 110)
    sm = s.svc("security", "Secrets", "Secrets Manager", "", "secrets_manager", 680, 110)

    s.edge(line, waf, "", "#1565C0")
    s.edge(waf, alb, "", "#1565C0")
    s.edge(alb, ecs, "", "#1565C0")
    s.edge(sm, ecs, "", "#C62828", dashed=True)

    b1 = s.box("SafetyGate", 60, 235, 100, stroke="#DD344C", fill="#FFEBEE")
    b2 = s.box("200 OK", 180, 235, 90)
    b3 = s.box("Dedup", 290, 235, 90)
    b4 = s.box("LineEvents", 400, 235, 110)
    b5 = s.box("ChatAsync", 530, 235, 110)
    b6 = s.box("Pipeline v2", 660, 235, 110, stroke="#147EBA", fill="#E8F4FC")

    s.edge(ecs, b1, "", "#1565C0", points=[(580, 220), (110, 220)])
    s.edge(b1, b2, "①")
    s.edge(b2, b3, "②")
    s.edge(b3, b4, "③")
    s.edge(b4, b5, "④")
    s.edge(b5, b6, "⑤")

    orch = s.box("AgentDispatcher", 60, 355, 130, h=55, stroke="#9C27B0", fill="#F3E5F5")
    neon = s.ext("Neon PostgreSQL", "generic_database", 220, 350)

    s.edge(b6, orch, "⑥", "#7B1FA2")
    s.edge(orch, neon, "⑦", "#F9A825")

    flex = s.box("LINE Messaging API", 60, 465, 160, h=55, stroke="#1976D2", fill="#E3F2FD")

    s.edge(orch, flex, "⑧", "#1565C0", points=[(125, 410), (125, 440), (140, 440)])
    s.edge(flex, line, "", "#1565C0", points=[(140, 560), (120, 560), (120, 218)])

    oai = s.ext("OpenAI API", "generic_application", 60, 580)
    tr = s.svc("ai", "AI", "Amazon Translate", "", "translate", 220, 565)
    r2 = s.ext("Cloudflare R2", "internet", 400, 580)

    s.edge(orch, oai, "", "#7B1FA2")
    s.edge(orch, tr, "", "#7B1FA2")
    s.edge(orch, r2, "", "#1565C0")

    legacy = s.box("Cloud Run", 560, 580, 100, 50, stroke="#4285F4", fill="#E8F0FE", fs=10)
    s.edge(legacy, line, "", "#4285F4", dashed=True, points=[(610, 650), (120, 650), (120, 218)])
    return s


def build_cross_cloud_comparison() -> Sheet:
    """06 — GCP legacy vs AWS target (LINE on both)."""
    s = Sheet("06 クロスクラウド比較", "sheet-06-cross", 1500, 920)
    s.title(
        "GCP 本番 vs AWS ステージング vs 共通サービス",
        "移行元 · 移行先 · 共通",
        1400,
    )

    s.lane("GCP 本番 — 移行元", 40, 105, 420, 540, "#FFF3E0", "#FF9800")
    s.lane("AWS ステージング — 移行先", 500, 105, 420, 540, "#FFF2E8", "#ED7100")
    s.lane("共通", 960, 105, 320, 540, "#FCE4EC", "#E91E63")

    cr = s.svc("compute", "Compute", "Cloud Run", "", "container_1", 80, 180)
    line_gcp = s.ext("LINE", "mobile", 80, 320)
    deepl = s.ext("DeepL", "generic_application", 80, 420)
    gcp_tts = s.ext("Google TTS", "generic_application", 180, 420)
    neon_g = s.ext("Neon PostgreSQL", "generic_database", 280, 420)

    ecs = s.svc("compute", "Compute", "ECS Express", "", "ecs", 540, 180)
    waf = s.svc("security", "Edge", "AWS WAF", "", "waf", 660, 180)
    alb = s.svc("network", "LB", "ALB", "", "elastic_load_balancing", 780, 180)
    line_aws = s.ext("LINE", "mobile", 540, 320)
    tr = s.svc("ai", "AI", "Amazon Translate", "", "translate", 540, 420)
    po = s.svc("ai", "AI", "Amazon Polly", "", "polly", 660, 420)
    br = s.svc("ai", "AI", "Bedrock KB", "", "bedrock", 780, 420)
    neon_a = s.ext("Neon PostgreSQL", "generic_database", 540, 520)

    r2 = s.ext("Cloudflare R2", "internet", 1000, 220)
    oai = s.ext("OpenAI API", "generic_application", 1000, 360)
    gh = s.ext("GitHub", "internet", 1000, 500)

    s.edge(cr, line_gcp, "", "#1565C0")
    s.edge(cr, deepl, "", "#7B1FA2")
    s.edge(cr, gcp_tts, "", "#7B1FA2")
    s.edge(cr, neon_g, "", "#F9A825")
    s.edge(line_aws, waf, "", "#1565C0")
    s.edge(waf, alb, "", "#1565C0")
    s.edge(alb, ecs, "", "#1565C0")
    s.edge(ecs, tr, "", "#7B1FA2")
    s.edge(ecs, po, "", "#7B1FA2")
    s.edge(ecs, br, "", "#7B1FA2")
    s.edge(ecs, neon_a, "", "#F9A825")
    s.edge(cr, r2, "", "#1565C0", points=[(200, 580), (920, 580), (920, 269)])
    s.edge(ecs, r2, "", "#1565C0", points=[(660, 580), (920, 580), (920, 269)])
    s.edge(cr, oai, "", "#7B1FA2", points=[(200, 600), (940, 600), (940, 409)])
    s.edge(ecs, oai, "", "#7B1FA2", points=[(660, 600), (940, 600), (940, 409)])
    s.edge(gh, ecs, "", "#2E7D32", points=[(1060, 580), (1060, 240), (660, 240)])
    return s


def build_secrets_data() -> Sheet:
    s = Sheet("12 シークレット・データ", "sheet-12-secrets", 1600, 900)
    s.title(
        "シークレット注入・データ永続化",
        "Secrets Manager · ECS · Neon · CloudWatch",
    )

    sm = s.svc("security", "AWS", "Secrets Manager", "", "secrets_manager", 40, 180)
    ecs = s.svc("compute", "App", "ECS Express", "", "ecs", 320, 180)
    gcp_sm = s.svc("security", "GCP", "Secret Manager", "", "secrets_manager", 320, 330)
    cr = s.svc("compute", "GCP", "Cloud Run", "", "container_1", 320, 430, dashed=True)

    neon = s.ext("Neon PostgreSQL", "generic_database", 560, 180)
    cw = s.svc("integration", "Logs", "CloudWatch", "", "cloudwatch", 840, 180)
    gcp_log = s.svc("integration", "Logs", "Cloud Logging", "", "cloudwatch", 840, 330)

    web = s.box("Web", 560, 480, 100, 55)
    line = s.box("LINE", 680, 480, 100, 55)

    s.edge(sm, ecs, "", "#C62828", dashed=True)
    s.edge(gcp_sm, cr, "", "#C62828", dashed=True)
    s.edge(ecs, neon, "", "#F9A825")
    s.edge(cr, neon, "", "#F9A825", dashed=True)
    s.edge(ecs, cw, "", "#616161")
    s.edge(cr, gcp_log, "", "#616161", dashed=True)
    s.edge(neon, web, "", "#1565C0")
    s.edge(neon, line, "", "#1565C0")
    return s


def build_user_request_flow() -> Sheet:
    """03 — numbered HTTP request path (Web + LINE)."""
    s = Sheet("03 ユーザーリクエスト", "sheet-03-user", 1800, 920)
    s.title(
        "リクエストパス — Web + LINE",
        "Browser / LINE → WAF → ALB → ECS",
        1700,
    )

    s.lane("① 静的アセット", 40, 110, 1720, 130, "#FFFDE7", "#FBC02D")
    s.lane("② Web チャット", 40, 260, 1720, 120, "#E3F2FD", "#1976D2")
    s.lane("②b LINE Webhook", 40, 400, 1720, 120, "#FFF3E0", "#FF9800")
    s.lane("③ 外部サービス", 40, 540, 1720, 200, "#F3E5F5", "#9C27B0")

    browser = s.ext("Browser", "users", 70, 290)
    line = s.ext("LINE Platform", "mobile", 70, 430)
    waf = s.svc("security", "Edge", "AWS WAF", "", "waf", 220, 360)
    alb = s.svc("network", "LB", "ALB", "", "elastic_load_balancing", 380, 360)
    ecs = s.svc("compute", "App", "ECS Express", "", "ecs", 540, 360)
    pipe = s.box("Chat Pipeline v2", 700, 290, 130, 48)
    line_pipe = s.box("Chat Pipeline v2", 700, 430, 130, 48)
    line_api = s.box("LINE Messaging API", 880, 430, 140, 48)

    cf = s.svc("network", "CDN", "CloudFront", "", "cloudfront", 220, 150)
    s3s = s.svc("storage", "Origin", "Amazon S3", "", "s3", 400, 150)
    s.edge(browser, waf, "", "#1565C0")
    s.edge(line, waf, "", "#1565C0", points=[(130, 480), (130, 520), (280, 520), (280, 420)])
    s.edge(waf, alb, "", "#1565C0")
    s.edge(alb, ecs, "", "#1565C0")
    s.edge(ecs, pipe, "", "#1565C0", points=[(600, 390), (765, 390), (765, 314)])
    s.edge(ecs, line_pipe, "", "#FF9800", points=[(600, 420), (765, 420), (765, 454)])
    s.edge(line_pipe, line_api, "", "#FF9800")
    s.edge(line_api, line, "", "#1565C0", points=[(950, 520), (130, 520)])
    s.edge(s3s, cf, "", "#F9A825")
    s.edge(cf, browser, "", "#1565C0", points=[(280, 130), (130, 130)])

    oai = s.ext("OpenAI API", "generic_application", 80, 590)
    neon = s.ext("Neon PostgreSQL", "generic_database", 240, 590)
    r2 = s.ext("Cloudflare R2", "internet", 400, 590)
    tr = s.svc("ai", "AI", "Amazon Translate", "", "translate", 560, 575)
    po = s.svc("ai", "AI", "Amazon Polly", "", "polly", 720, 575)
    br = s.svc("ai", "AI", "Bedrock KB", "", "bedrock", 880, 575)
    s.edge(ecs, oai, "", "#7B1FA2", points=[(600, 510), (140, 510)])
    s.edge(ecs, neon, "", "#F9A825", points=[(600, 530), (300, 530)])
    s.edge(ecs, r2, "", "#1565C0", points=[(600, 550), (460, 550)])
    s.edge(ecs, tr, "", "#7B1FA2")
    s.edge(ecs, po, "", "#7B1FA2")
    s.edge(ecs, br, "", "#7B1FA2")
    return s


def build_cicd_pipeline() -> Sheet:
    """04 — CI/CD with post_build branches."""
    s = Sheet("04 CI/CD パイプライン", "sheet-04-cicd", 1200, 1100)
    s.title(
        "CI/CD デプロイフロー",
        "GitHub → CodePipeline → CodeBuild → デプロイ",
        1100,
    )

    gh = s.ext("GitHub", "internet", 520, 110)
    cs = s.svc("integration", "Source", "CodeStar", "", "codestar", 520, 220)
    cp = s.svc("integration", "Pipe", "CodePipeline", "", "codepipeline", 520, 340)
    cb = s.svc("integration", "Build", "CodeBuild", "", "codebuild", 520, 470)
    ecr = s.svc("compute", "Registry", "Amazon ECR", "", "ecr", 520, 600)
    ecs = s.svc("compute", "Deploy", "ECS Express", "", "ecs", 520, 730)

    s3s = s.svc("storage", "Static", "Amazon S3", "", "s3", 120, 470)
    cf = s.svc("network", "CDN", "CloudFront", "", "cloudfront", 120, 600)
    s3k = s.svc("storage", "KB", "Amazon S3", "", "s3", 920, 470)
    br = s.svc("ai", "RAG", "Bedrock KB", "", "bedrock", 920, 600)
    alb = s.svc("network", "Health", "ALB", "", "elastic_load_balancing", 920, 730)

    s.edge(gh, cs, "①", "#2E7D32")
    s.edge(cs, cp, "②", "#2E7D32")
    s.edge(cp, cb, "③", "#2E7D32")
    s.edge(cb, ecr, "④", "#2E7D32")
    s.edge(ecr, ecs, "⑤", "#2E7D32")
    s.edge(cb, s3s, "", "#2E7D32")
    s.edge(s3s, cf, "", "#2E7D32")
    s.edge(cb, s3k, "", "#2E7D32")
    s.edge(s3k, br, "", "#F9A825", dashed=True)
    s.edge(cb, alb, "", "#2E7D32")
    return s


def build_chat_pipeline_overview() -> Sheet:
    """07 — 5-phase swim lane + agent fan-out."""
    s = Sheet("07 Chat Pipeline v2", "sheet-07-pipeline", 2100, 1200)
    s.title(
        "Chat Pipeline v2",
        "入口 → 前処理 → ルーティング → エージェント → 応答",
        2000,
    )

    s.lane("Phase 1 — 入口", 40, 105, 2020, 85, "#FFF3E0", "#FF9800")
    s.lane("Phase 2 — 前処理", 40, 200, 2020, 95, "#FFEBEE", "#DD344C")
    s.lane("Phase 3 — ルーティング", 40, 305, 2020, 120, "#F3E5F5", "#9C27B0")
    s.lane("Phase 4 — エージェント", 40, 435, 2020, 280, "#E8F4FC", "#147EBA")
    s.lane("Phase 5 — 応答", 40, 725, 2020, 100, "#E3F2FD", "#1976D2")

    user = s.ext("User", "users", 60, 120)
    p1 = [
        s.step("1", "API", 200, 125, 100),
        s.step("2", "Pipeline", 320, 125, 110),
        s.step("3", "Budget", 450, 125, 100),
    ]
    for i in range(len(p1) - 1):
        s.edge(p1[i], p1[i + 1], "", "#1565C0")
    s.edge(user, p1[0], "", "#1565C0")

    p2 = [
        s.step("4", "SafetyGate", 60, 220, 120, stroke="#DD344C"),
        s.step("5", "SessionOps", 200, 220, 120),
        s.step("6", "TriageAgent", 340, 220, 110),
        s.step("7", "SafetyGate", 470, 220, 120, stroke="#DD344C"),
        s.step("8", "SessionOps", 610, 220, 120),
        s.step("9", "Routing", 750, 220, 110),
    ]
    s.edge(p1[-1], p2[0], "", "#1565C0", points=[(500, 170), (500, 200), (120, 200)])
    for i in range(len(p2) - 1):
        s.edge(p2[i], p2[i + 1], "", "#1565C0")

    ir = s.step("10", "IntentRouter", 900, 340, 120, stroke="#9C27B0")
    gate = s.step("11", "Gate", 1040, 340, 90, stroke="#9C27B0")
    disp = s.step("12", "AgentDispatcher", 1150, 340, 130, stroke="#ED7100")
    orch = s.box("ChatOrchestrator", 1300, 340, 120, 55, stroke="#666666", fill="#F5F5F5", fs=10)
    s.edge(p2[-1], ir, "", "#7B1FA2")
    s.edge(ir, gate, "", "#7B1FA2")
    s.edge(gate, disp, "", "#7B1FA2")
    s.edge(disp, orch, "", "#616161", dashed=True)

    agents = [
        ("PhysicalOrchestrator", 60, 460),
        ("NLUAgent", 230, 460),
        ("ConciergeAgent", 400, 460),
        ("AskAgent", 570, 460),
        ("ExplanationAgent", 740, 460),
        ("EmergencyRouter", 910, 460, "#DD344C"),
        ("CounselingManager", 60, 560),
        ("StoreInquiryAgent", 230, 560),
        ("SessionOps", 400, 560),
        ("ProfileMemoryAgent", 570, 560),
        ("EpisodeSummaryAgent", 740, 560),
    ]
    agent_ids: list[str] = []
    for item in agents:
        name, x, y = item[0], item[1], item[2]
        stroke = item[3] if len(item) > 3 else "#147EBA"
        agent_ids.append(s.box(name, x, y, 150, 55, stroke=stroke, fill="#E8F4FC", fs=10))
    s.edge(disp, agent_ids[0], "", "#7B1FA2", points=[(1215, 420), (135, 420)])

    fin = s.step("13", "Finalize", 60, 750, 120)
    sse = s.box("SSE", 210, 745, 100, 55, stroke="#1976D2", fill="#E3F2FD", fs=10)
    ui = s.box("Sage Terrace UI", 340, 745, 140, 55, stroke="#1976D2", fill="#E3F2FD", fs=10)
    db = s.ext("Neon PostgreSQL", "generic_database", 520, 740)
    s.edge(agent_ids[0], fin, "", "#1565C0", points=[(135, 530), (135, 700), (120, 700)])
    s.edge(fin, sse, "", "#1565C0")
    s.edge(sse, ui, "", "#1565C0")
    s.edge(fin, db, "", "#F9A825")

    s.lane("外部サービス", 40, 850, 2020, 130, "#E0F2F1", "#01A88D")
    s.svc("ai", "LLM", "OpenAI", "", "generic_application", 60, 870)
    s.svc("storage", "Data", "Amazon S3", "", "s3", 220, 870)
    s.svc("ai", "RAG", "Bedrock KB", "", "bedrock", 380, 870)
    s.svc("ai", "AI", "Amazon Translate", "", "translate", 540, 870)
    s.svc("ai", "AI", "Amazon Polly", "", "polly", 700, 870)
    return s


def build_physical_flow() -> Sheet:
    """08 — Physical orchestrator flow."""
    s = Sheet("08 症状相談 Physical", "sheet-08-physical", 1700, 800)
    s.title(
        "PhysicalOrchestrator",
        "症状相談パイプライン",
        1600,
    )

    s.lane("入力 → NLU → スコアリング", 40, 100, 1620, 180, "#E8F4FC", "#147EBA")
    s.lane("出力 → メディア → 永続化", 40, 300, 1620, 200, "#E3F2FD", "#1976D2")
    s.lane("推奨後 Q&amp;A", 40, 520, 1620, 180, "#F3E5F5", "#9C27B0")

    inp = s.step("1", "症状入力", 60, 150, 110)
    nlu = s.box("NLUAgent", 200, 145, 120, 55, stroke="#147EBA", fill="#E8F4FC", fs=10)
    cm = s.svc("ai", "NLU", "Comprehend Medical", "", "comprehend_medical", 370, 130, dashed=True)
    rb = s.box("RuleBasedScoring", 530, 140, 160, 55, stroke="#4CAF50", fill="#E8F5E9", fs=10)
    csv = s.svc("storage", "Master", "Amazon S3", "", "s3", 760, 130)
    pz = s.svc("ai", "Rank", "Personalize", "", "personalize", 920, 130, dashed=True)

    s.edge(inp, nlu, "", "#1565C0")
    s.edge(inp, cm, "", "#7B1FA2", dashed=True)
    s.edge(nlu, rb, "", "#1565C0")
    s.edge(cm, rb, "", "#7B1FA2", dashed=True)
    s.edge(csv, rb, "", "#F9A825")
    s.edge(rb, pz, "", "#7B1FA2", dashed=True)

    card = s.step("2", "推奨カード", 60, 350, 120)
    sse = s.step("3", "SSE", 220, 350, 100)
    r2 = s.ext("Cloudflare R2", "internet", 370, 335)
    tr = s.svc("ai", "AI", "Amazon Translate", "", "translate", 530, 320)
    po = s.svc("ai", "AI", "Amazon Polly", "", "polly", 690, 320)
    neon = s.ext("Neon PostgreSQL", "generic_database", 850, 335)
    cw = s.svc("integration", "Log", "CloudWatch", "", "cloudwatch", 1010, 320)

    s.edge(rb, card, "", "#1565C0", points=[(610, 220), (610, 280), (120, 280)])
    s.edge(card, sse, "", "#1565C0")
    s.edge(rb, r2, "", "#1565C0")
    s.edge(rb, tr, "", "#7B1FA2")
    s.edge(rb, po, "", "#7B1FA2")
    s.edge(rb, neon, "", "#F9A825")
    s.edge(rb, cw, "", "#616161")

    qa_in = s.step("A", "推奨後 Q&amp;A", 60, 570, 120)
    ask = s.box("AskAgent", 210, 565, 120, 55, stroke="#9C27B0", fill="#F3E5F5", fs=10)
    mkb = s.svc("ai", "RAG", "Bedrock KB", "", "bedrock", 430, 550)
    s.edge(qa_in, ask, "", "#1565C0")
    s.edge(mkb, ask, "", "#7B1FA2")
    s.edge(ask, tr, "", "#7B1FA2")
    s.edge(ask, neon, "", "#F9A825")
    return s


def build_kb_rag_flow() -> Sheet:
    """09 — Concierge/Medicine KB pipeline."""
    s = Sheet("09 Concierge / KB RAG", "sheet-09-kb", 1700, 850)
    s.title(
        "Bedrock Knowledge Base",
        "データ同期 · Retrieve · 生成",
        1600,
    )

    s.lane("A. データパイプライン", 40, 100, 1620, 160, "#E8F5E9", "#3F8624")
    s.lane("B. ConciergeAgent", 40, 280, 1620, 200, "#F3E5F5", "#9C27B0")
    s.lane("C. AskAgent", 40, 500, 1620, 160, "#E0F2F1", "#01A88D")

    repo = s.box("GitHub", 60, 140, 120, 55, stroke="#3F8624", fill="#E8F5E9", fs=10)
    cb = s.svc("integration", "Trigger", "CodeBuild", "", "codebuild", 280, 125)
    s3 = s.svc("storage", "Source", "Amazon S3", "", "s3", 440, 125)
    kb1 = s.svc("ai", "KB", "Bedrock KB", "", "bedrock", 620, 110)
    kb2 = s.svc("ai", "KB", "Bedrock KB", "", "bedrock", 620, 200)

    s.edge(repo, cb, "", "#2E7D32")
    s.edge(cb, s3, "", "#2E7D32")
    s.edge(s3, kb1, "", "#F9A825", dashed=True)
    s.edge(s3, kb2, "", "#F9A825", dashed=True)

    user = s.ext("User", "users", 60, 320)
    ca = s.box("ConciergeAgent", 200, 315, 130, 50, stroke="#9C27B0", fill="#F3E5F5", fs=10)
    ret = s.box("Bedrock Retrieve", 530, 315, 150, 50, stroke="#01A88D", fill="#E0F2F1", fs=10)
    cache = s.svc("database", "Cache", "ElastiCache", "", "elasticache", 720, 300, dashed=True)
    brt = s.svc("ai", "Runtime", "Bedrock", "", "bedrock", 880, 300)
    oai = s.ext("OpenAI API", "generic_application", 1040, 305)
    ui = s.box("SSE", 1200, 315, 100, 50, stroke="#1976D2", fill="#E3F2FD", fs=10)

    s.edge(user, ca, "", "#1565C0")
    s.edge(ca, ret, "", "#7B1FA2")
    s.edge(ret, cache, "", "#F9A825", dashed=True)
    s.edge(ret, brt, "", "#7B1FA2")
    s.edge(ret, ca, "", "#7B1FA2", points=[(605, 290), (265, 290)])
    s.edge(ca, oai, "", "#7B1FA2")
    s.edge(ca, ui, "", "#1565C0")

    ask = s.box("AskAgent", 200, 530, 120, 50, stroke="#01A88D", fill="#E0F2F1", fs=10)
    s.edge(kb2, ask, "", "#7B1FA2", points=[(680, 260), (1200, 260), (1200, 530), (260, 530)])
    return s


def _fix_xml_ampersands(block: str) -> str:
    """Escape bare & inside value=\"...\" attributes (draw.io HTML labels)."""

    def repl(match: re.Match[str]) -> str:
        val = match.group(1)
        fixed = re.sub(r"&(?!amp;|lt;|gt;|quot;|#)", "&amp;", val)
        return f'value="{fixed}"'

    return re.sub(r'value="([^"]*)"', repl, block)


def load_existing_by_name(path: Path, skip_names: set[str]) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"(  <diagram name=\".*?\" id=\".*?>.*?</diagram>)", text, re.DOTALL)
    result: dict[str, str] = {}
    for block in blocks:
        m = re.search(r'name="([^"]+)"', block)
        if m and m.group(1) not in skip_names:
            result[m.group(1)] = _fix_xml_ampersands(block)
    return result


def main() -> None:
    print("Generating multi-page architecture diagram...")
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="Electron" agent="medicine-recommend-multisheet" version="29.6.1">',
    ]

    sheet_list: list[str] = [
        build_index().render(),
        sheet_page1_from_staging(),
        build_integrated_zones().render(),
        build_user_request_flow().render(),
        build_cicd_pipeline().render(),
        build_external_map().render(),
        build_cross_cloud_comparison().render(),
        build_chat_pipeline_overview().render(),
        build_physical_flow().render(),
        build_kb_rag_flow().render(),
        build_ops_cost().render(),
        build_line_aws().render(),
        build_secrets_data().render(),
    ]
    for sh in sheet_list:
        if sh:
            parts.append(sh)
    parts.append("</mxfile>")
    xml = "\n".join(parts) + "\n"
    OUT.write_text(xml, encoding="utf-8")
    ET.fromstring(xml)
    print(f"Written: {OUT}")
    print(f"  regenerated all {len(sheet_list)} sheets")
    print(f"Size: {len(xml):,} bytes · diagrams: {xml.count('<diagram ')}")


if __name__ == "__main__":
    main()
