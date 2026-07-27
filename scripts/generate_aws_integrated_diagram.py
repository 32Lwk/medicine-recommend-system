#!/usr/bin/env python3
"""Generate AWS architecture draw.io diagrams (3-zone integrated + focused views)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DIAGRAMS = Path(__file__).resolve().parents[1] / "docs" / "diagrams"

ICON = (
    "sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
    "[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
    "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
    "outlineConnect=0;fontColor=#232F3E;fillColor={fill};strokeColor=#ffffff;dashed=0;"
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
    "compute": ("#FFF2E8", "#ED7100"),
    "network": ("#EDE7F6", "#8C4FFF"),
    "security": ("#FFEBEE", "#DD344C"),
    "storage": ("#E8F5E9", "#3F8624"),
    "integration": ("#FCE4EC", "#E7157B"),
    "ai": ("#E0F2F1", "#01A88D"),
    "database": ("#F5E6F7", "#C925D1"),
}

# Static colors for max draw.io / VS Code extension compatibility
ZONE_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#FAFAFA;strokeColor=#BBBBBB;"
    "strokeWidth=2;dashed=1;verticalAlign=top;fontStyle=1;fontSize=14;fontColor=#333333;"
    "fontFamily=Helvetica;align=left;spacingLeft=12;spacingTop=4;"
)

AWS_CLOUD_STYLE = (
    "points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],"
    "[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;"
    "html=1;whiteSpace=wrap;fontSize=12;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud;"
    "strokeColor=#232F3E;fillColor=#232F3E;fillOpacity=5;verticalAlign=top;align=left;"
    "spacingLeft=24;fontColor=#232F3E;dashed=0;container=0;pointerEvents=0;collapsible=0;"
    "fontFamily=Helvetica;"
)


def xml_attr(text: str) -> str:
    """Escape text for XML attribute values (draw.io html labels use &lt; etc.)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass
class DiagramBuilder:
    name: str
    page_w: int
    page_h: int
    cells: list[str] = field(default_factory=list)
    _id: int = 0

    def nid(self, prefix: str = "c") -> str:
        self._id += 1
        return f"{prefix}-{self._id}"

    def vertex(self, cid: str, value: str, style: str, x: int, y: int, w: int, h: int, parent: str = "1") -> None:
        self.cells.append(
            f'<mxCell id="{xml_attr(cid)}" parent="{parent}" value="{value}" style="{style}" vertex="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>'
        )

    def plain(self, cid: str, text: str, style: str, x: int, y: int, w: int, h: int, parent: str = "1") -> None:
        self.vertex(cid, xml_attr(text), style, x, y, w, h, parent)

    def edge(
        self,
        source: str,
        target: str,
        label: str = "",
        dashed: bool = False,
        points: list[tuple[int, int]] | None = None,
    ) -> None:
        eid = self.nid("e")
        dash = "dashed=1;" if dashed else ""
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            f"html=1;fontFamily=Helvetica;{dash}labelBackgroundColor=none;"
        )
        pts = ""
        if points:
            pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        self.cells.append(
            f'<mxCell id="{eid}" parent="1" source="{source}" target="{target}" edge="1" style="{style}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        if label:
            lid = self.nid("el")
            self.cells.append(
                f'<mxCell id="{lid}" parent="{eid}" value="{xml_attr(label)}" connectable="0" vertex="1" '
                f'style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];'
                f'fontSize=10;fontFamily=Helvetica;labelBackgroundColor=none;">'
                f'<mxGeometry relative="1" x="-0.2" y="-12" as="geometry">'
                f'<mxPoint as="offset" /></mxGeometry></mxCell>'
            )

    def title_block(self, title: str, subtitle: str, width: int = 2000) -> None:
        self.plain("title-text", title, "text;html=1;align=left;verticalAlign=top;fontSize=28;fontStyle=1;fontFamily=Helvetica;", 50, 24, width, 40)
        self.plain("subtitle-text", subtitle, "text;html=1;align=left;verticalAlign=top;fontSize=15;fontFamily=Helvetica;", 55, 62, width, 24)
        self.vertex("title-separator", "", "line;strokeWidth=2;html=1;strokeColor=#FF9900;fontFamily=Helvetica;", 55, 92, width - 10, 8)

    def zone(self, label: str, x: int, y: int, w: int, h: int) -> None:
        self.vertex(self.nid("zone"), f"&lt;b&gt;{xml_attr(label)}&lt;/b&gt;", ZONE_STYLE, x, y, w, h)

    def divider(self, x: int, y: int, h: int) -> None:
        self.vertex(self.nid("div"), "", "line;strokeWidth=2;html=1;strokeColor=#CCCCCC;fontFamily=Helvetica;", x, y, 4, h)

    def section_label(self, text: str, x: int, y: int) -> None:
        self.vertex(self.nid("lbl"), f"&lt;b&gt;{xml_attr(text)}&lt;/b&gt;", "text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=12;fontColor=#666666;fontFamily=Helvetica;", x, y, 200, 20)

    def service(self, cat: str, label: str, name: str, sub: str, icon: str, x: int, y: int) -> str:
        fill, stroke = CAT[cat]
        gid = self.nid("g")
        sid = self.nid("s")
        self.plain(gid, label, GRP.format(fill=fill, stroke=stroke), x, y, 120, 120)
        val = f"{xml_attr(name)}&lt;div&gt;&lt;i&gt;{xml_attr(sub)}&lt;/i&gt;&lt;/div&gt;" if sub else xml_attr(name)
        self.vertex(sid, val, ICON.format(fill=stroke, icon=icon), 36, 30, 48, 48, gid)
        return sid

    def external(self, label: str, icon: str, x: int, y: int) -> str:
        gid = self.nid("ext")
        iid = self.nid("exti")
        self.plain(
            gid,
            label,
            (
                "fillColor=#f5f5f5;strokeColor=#666666;rounded=1;whiteSpace=wrap;html=1;"
                "verticalAlign=top;fontStyle=1;fontSize=12;fontColor=#333333;fontFamily=Helvetica;"
                "container=1;collapsible=0;shadow=1;"
            ),
            x,
            y,
            120,
            98,
        )
        self.vertex(iid, "", ICON.format(fill="#232F3D", icon=icon), 36, 30, 48, 48, gid)
        return iid

    def note(self, text: str, x: int, y: int, w: int = 280) -> None:
        self.plain(self.nid("note"), text, "text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor=#666666;fontFamily=Helvetica;whiteSpace=wrap;", x, y, w, 50)

    def aws_cloud_box(self, x: int, y: int, w: int, h: int) -> None:
        self.plain("aws-cloud", "AWS Cloud (ap-northeast-1)", AWS_CLOUD_STYLE, x, y, w, h)

    def write(self, path: Path) -> None:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile host="Electron" agent="medicine-recommend-generator" version="29.6.1">\n'
            f'  <diagram name="{xml_attr(self.name)}" id="diagram-1">\n'
            f'    <mxGraphModel dx="{self.page_w}" dy="{self.page_h}" grid="0" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" '
            f'pageWidth="{self.page_w}" pageHeight="{self.page_h}" math="0" shadow="0">\n'
            "      <root>\n        <mxCell id=\"0\" />\n        <mxCell id=\"1\" parent=\"0\" />\n"
            + "\n".join(f"        {c}" for c in self.cells)
            + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
        )
        path.write_text(xml, encoding="utf-8", newline="\n")
        print(f"  wrote {path.name} ({len(self.cells)} cells)")


def build_integrated() -> None:
    """4-band layout: User (top-left) | AWS Runtime (center) | CI/CD (right) | External SaaS (bottom)."""
    b = DiagramBuilder("統合 3 ゾーン", 2100, 1020)
    b.title_block(
        "medicine-recommend AWS 統合アーキテクチャ",
        "上: リクエスト経路  |  中央: AWS ランタイム  |  右: CI/CD  |  下: 外部 SaaS  —  aws.medicine.yutok.dev（ステージング）",
        2000,
    )

    # ── ゾーン枠 ──
    b.zone("① ユーザー", 40, 115, 240, 200)
    b.zone("② AWS ランタイム", 300, 115, 1040, 620)
    b.zone("③ CI/CD デプロイ", 1380, 115, 300, 620)
    b.zone("④ 外部 SaaS", 300, 760, 1040, 200)
    b.divider(285, 115, 665)
    b.divider(1355, 115, 665)
    b.aws_cloud_box(320, 140, 1000, 580)

    # ── ① ユーザー ──
    user_i = b.external("ブラウザ", "users", 100, 180)

    # ── ② リクエスト経路（上段・左→右） ──
    b.section_label("A. リクエスト経路", 340, 148)
    waf_i = b.service("security", "セキュリティ", "AWS WAF", "レート制限 + CRS", "waf", 340, 180)
    alb_i = b.service("network", "ロードバランサー", "Application LB", "HTTPS 終端", "elastic_load_balancing", 520, 180)
    ecs_i = b.service("compute", "コンピュート", "ECS Express", "FastAPI + SSE", "ecs", 700, 180)
    sec_i = b.service("security", "シークレット", "Secrets Manager", "API キー注入", "secrets_manager", 880, 180)

    # ── ② 静的 CDN（中段） ──
    b.section_label("B. 静的コンテンツ配信", 340, 310)
    s3s_i = b.service("storage", "ストレージ", "Amazon S3", "static/", "s3", 340, 340)
    cf_i = b.service("network", "CDN", "CloudFront", "JS / CSS 配信", "cloudfront", 520, 340)

    # ── ② AWS ネイティブ AI（下段） ──
    b.section_label("C. AWS AI / データ", 340, 470)
    tr_i = b.service("ai", "翻訳", "Amazon Translate", "多言語対応", "translate", 340, 500)
    po_i = b.service("ai", "音声合成", "Amazon Polly", "TTS", "polly", 500, 500)
    br_i = b.service("ai", "RAG", "Bedrock Knowledge Bases", "コンシェルジュ + 医薬品", "bedrock", 660, 500)
    rd_i = b.service("database", "キャッシュ", "Amazon ElastiCache", "Redis", "elasticache", 820, 500)

    # ── ② KB 取り込み + 監視 ──
    b.section_label("D. KB 取り込み / 監視", 340, 630)
    s3k_i = b.service("storage", "KB ソース", "Amazon S3", "docs / data", "s3", 340, 660)
    cw_i = b.service("integration", "監視", "CloudWatch", "ECS ログ", "cloudwatch", 820, 660)

    # ── ④ 外部 SaaS（最下段・横並び） ──
    openai_i = b.external("OpenAI API", "generic_application", 460, 810)
    neon_i = b.external("Neon PostgreSQL", "generic_database", 680, 810)
    r2_i = b.external("Cloudflare R2", "internet", 900, 810)

    # ── ③ CI/CD（右列・上→下） ──
    b.section_label("E. デプロイパイプライン", 1400, 148)
    gh_i = b.external("GitHub (main)", "internet", 1470, 180)
    cs_i = b.service("integration", "ソース", "CodeStar Connections", "GitHub 連携", "codecommit", 1470, 290)
    cp_i = b.service("integration", "パイプライン", "CodePipeline", "main ブランチ", "codepipeline", 1470, 400)
    cb_i = b.service("integration", "ビルド", "CodeBuild", "buildspec.yml", "codebuild", 1470, 510)
    ecr_i = b.service("compute", "レジストリ", "Amazon ECR", "Docker イメージ", "ecr", 1470, 620)

    # ── A. リクエスト経路 ──
    b.edge(user_i, waf_i, "① HTTPS")
    b.edge(waf_i, alb_i, "②")
    b.edge(alb_i, ecs_i, "③ POST /api/chat")
    b.edge(sec_i, ecs_i, "環境変数", dashed=True)

    # ── B. 静的 CDN ──
    b.edge(s3s_i, cf_i, "同期")
    b.edge(cf_i, user_i, "JS / CSS", points=[(580, 280), (160, 280)])

    # ── C. ECS → AWS AI（縦→横バスで整理） ──
    b.edge(ecs_i, tr_i, "翻訳", points=[(760, 460), (400, 460)])
    b.edge(ecs_i, po_i, "音声", points=[(760, 460), (560, 460)])
    b.edge(ecs_i, br_i, "RAG 検索", points=[(760, 460), (720, 460)])
    b.edge(ecs_i, rd_i, "キャッシュ", dashed=True, points=[(760, 460), (880, 460)])

    # ── D. KB / 監視 ──
    b.edge(s3k_i, br_i, "取り込み", dashed=True)
    b.edge(ecs_i, cw_i, "ログ", dashed=True, points=[(760, 620), (880, 620)])

    # ── ④ 外部 SaaS（ECS から下へ一括バス） ──
    b.edge(ecs_i, openai_i, "LLM 推論", points=[(760, 740), (520, 740)])
    b.edge(ecs_i, neon_i, "セッション DB", points=[(760, 740), (740, 740)])
    b.edge(ecs_i, r2_i, "画像 CDN", points=[(760, 740), (960, 740)])

    # ── E. CI/CD ──
    b.edge(gh_i, cs_i, "① push")
    b.edge(cs_i, cp_i, "②")
    b.edge(cp_i, cb_i, "③ ビルド")
    b.edge(cb_i, ecr_i, "④ イメージ push")
    b.edge(ecr_i, ecs_i, "⑤ 再デプロイ", points=[(1530, 680), (1120, 680), (1120, 240), (760, 240)])
    b.edge(cb_i, s3s_i, "静的同期", points=[(1470, 570), (1120, 570), (1120, 400), (400, 400)])
    b.edge(cb_i, s3k_i, "KB 同期", points=[(1470, 590), (1100, 590), (1100, 720), (400, 720)])

    b.note(
        "フロー概要: ブラウザ → WAF → ALB → ECS がメイン経路。"
        "ECS から AWS AI・外部 SaaS へ分岐。GitHub push で CI/CD が ECS / S3 を更新。",
        40,
        880,
        240,
    )

    b.write(DIAGRAMS / "aws-integrated-architecture.drawio")


def build_user_request_flow() -> None:
    b = DiagramBuilder("User Request Flow", 1500, 680)
    b.title_block("ユーザーリクエストフロー", "Browser → WAF → ALB → ECS → 外部/API", 1400)

    user_i = b.external("Web Browser", "users", 60, 260)
    waf_i = b.service("security", "Security", "AWS WAF", "Rate + CRS", "waf", 240, 260)
    alb_i = b.service("network", "Load Balancer", "Application LB", "HTTPS", "elastic_load_balancing", 420, 260)
    ecs_i = b.service("compute", "Compute", "ECS Express", "FastAPI + SSE", "ecs", 600, 260)
    cf_i = b.service("network", "CDN", "CloudFront", "JS/CSS", "cloudfront", 420, 440)

    openai_i = b.external("OpenAI", "generic_application", 820, 180)
    neon_i = b.external("Neon DB", "generic_database", 820, 300)
    r2_i = b.external("Cloudflare R2", "internet", 820, 420)
    tr_i = b.service("ai", "Translation", "Translate", "", "translate", 1020, 180)
    po_i = b.service("ai", "Speech", "Polly", "TTS", "polly", 1020, 300)
    br_i = b.service("ai", "RAG", "Bedrock KB", "retrieve", "bedrock", 1020, 420)

    b.edge(user_i, waf_i, "1 HTTPS")
    b.edge(waf_i, alb_i, "2")
    b.edge(alb_i, ecs_i, "3 POST /api/chat")
    b.edge(cf_i, user_i, "JS/CSS")
    b.edge(ecs_i, openai_i, "LLM")
    b.edge(ecs_i, neon_i, "DB")
    b.edge(ecs_i, r2_i, "images")
    b.edge(ecs_i, tr_i)
    b.edge(ecs_i, po_i)
    b.edge(ecs_i, br_i)

    b.write(DIAGRAMS / "aws-user-request-flow.drawio")


def build_cicd_flow() -> None:
    b = DiagramBuilder("CI/CD Flow", 800, 1000)
    b.title_block("CI/CD デプロイフロー", "GitHub push → Pipeline → Build → ECR → ECS + S3", 750)

    gh_i = b.external("GitHub (main)", "internet", 340, 120)
    cs_i = b.service("integration", "Source", "CodeStar", "GitHub conn", "codecommit", 340, 230)
    cp_i = b.service("integration", "Pipeline", "CodePipeline", "main", "codepipeline", 340, 360)
    cb_i = b.service("integration", "Build", "CodeBuild", "buildspec.yml", "codebuild", 340, 490)
    ecr_i = b.service("compute", "Registry", "Amazon ECR", ":latest", "ecr", 340, 620)
    ecs_i = b.service("compute", "Deploy", "ECS Express", "redeploy", "ecs", 340, 750)

    s3s_i = b.service("storage", "Static", "Amazon S3", "static/", "s3", 580, 490)
    cf_i = b.service("network", "CDN", "CloudFront", "invalidate", "cloudfront", 580, 620)
    s3k_i = b.service("storage", "KB", "Amazon S3", "KB source", "s3", 100, 490)
    br_i = b.service("ai", "RAG", "Bedrock KB", "ingestion", "bedrock", 100, 620)

    b.edge(gh_i, cs_i, "1 push")
    b.edge(cs_i, cp_i, "2")
    b.edge(cp_i, cb_i, "3 build")
    b.edge(cb_i, ecr_i, "4 push")
    b.edge(ecr_i, ecs_i, "5 deploy")
    b.edge(cb_i, s3s_i, "sync")
    b.edge(s3s_i, cf_i)
    b.edge(cb_i, s3k_i, "sync")
    b.edge(s3k_i, br_i, "ingest", dashed=True)

    b.write(DIAGRAMS / "aws-cicd-flow.drawio")


def build_external_integrations() -> None:
    b = DiagramBuilder("External Integrations", 1100, 720)
    b.title_block("外部連携マップ", "ECS Express 中心 — OpenAI / Neon / R2 / AWS AI", 1050)

    ecs_i = b.service("compute", "Compute", "ECS Express", "FastAPI hub", "ecs", 480, 280)
    sec_i = b.service("security", "Secrets", "Secrets Manager", "env inject", "secrets_manager", 480, 100)

    openai_i = b.external("OpenAI API", "generic_application", 80, 160)
    neon_i = b.external("Neon PostgreSQL", "generic_database", 80, 340)
    r2_i = b.external("Cloudflare R2", "internet", 80, 520)

    tr_i = b.service("ai", "Translation", "Translate", "", "translate", 880, 160)
    po_i = b.service("ai", "Speech", "Polly", "TTS", "polly", 880, 340)
    br_i = b.service("ai", "RAG", "Bedrock KB", "bedrock_kb", "bedrock", 880, 520)
    rd_i = b.service("database", "Cache", "ElastiCache", "Redis", "elasticache", 480, 520)

    b.edge(sec_i, ecs_i, "secrets", dashed=True)
    b.edge(ecs_i, openai_i, "LLM")
    b.edge(ecs_i, neon_i, "DATABASE_URL")
    b.edge(ecs_i, r2_i, "images CDN")
    b.edge(ecs_i, tr_i)
    b.edge(ecs_i, po_i)
    b.edge(ecs_i, br_i, "retrieve")
    b.edge(ecs_i, rd_i, "cache", dashed=True)

    b.write(DIAGRAMS / "aws-external-integrations.drawio")


def build_runtime_services() -> None:
    b = DiagramBuilder("AWS Runtime Services", 1300, 720)
    b.title_block("AWS ランタイムサービス", "WAF / ALB / ECS / CloudFront / Bedrock / Translate / Polly", 1200)

    b.aws_cloud_box(80, 120, 1140, 540)

    waf_i = b.service("security", "Security", "AWS WAF", "Rate + CRS", "waf", 120, 180)
    alb_i = b.service("network", "Load Balancer", "Application LB", "HTTPS", "elastic_load_balancing", 300, 180)
    ecs_i = b.service("compute", "Compute", "ECS Express", "512/1024", "ecs", 480, 180)
    sec_i = b.service("security", "Secrets", "Secrets Mgr", "aws-staging/*", "secrets_manager", 660, 180)

    s3s_i = b.service("storage", "Storage", "Amazon S3", "static/", "s3", 120, 360)
    cf_i = b.service("network", "CDN", "CloudFront", "CDN", "cloudfront", 300, 360)
    s3k_i = b.service("storage", "KB Source", "Amazon S3", "kb-source", "s3", 480, 360)

    tr_i = b.service("ai", "Translation", "Translate", "", "translate", 120, 520)
    po_i = b.service("ai", "Speech", "Polly", "TTS", "polly", 300, 520)
    br_i = b.service("ai", "RAG", "Bedrock KB", "Managed KB", "bedrock", 480, 520)
    rd_i = b.service("database", "Cache", "ElastiCache", "Redis", "elasticache", 660, 520)
    cw_i = b.service("integration", "Monitoring", "CloudWatch", "/ecs/logs", "cloudwatch", 840, 520)

    b.edge(waf_i, alb_i)
    b.edge(alb_i, ecs_i)
    b.edge(sec_i, ecs_i, "inject", dashed=True)
    b.edge(s3s_i, cf_i)
    b.edge(s3k_i, br_i, "ingestion", dashed=True)
    b.edge(ecs_i, tr_i)
    b.edge(ecs_i, po_i)
    b.edge(ecs_i, br_i, "retrieve")
    b.edge(ecs_i, rd_i, "cache", dashed=True)
    b.edge(ecs_i, cw_i, "logs", dashed=True)

    b.write(DIAGRAMS / "aws-runtime-services.drawio")


def build_cross_cloud_overview() -> None:
    b = DiagramBuilder("Cross-Cloud Overview", 1400, 620)
    b.title_block("クロスクラウド概要", "GCP 本番 / AWS ステージング / 共通 R2", 1300)

    b.zone("GCP 本番", 40, 120, 400, 440)
    b.zone("AWS ステージング", 480, 120, 400, 440)
    b.zone("共通 Cloudflare", 920, 120, 260, 440)

    cr_i = b.service("compute", "Compute", "Cloud Run", "medicine.yutok.dev", "container_1", 100, 200)
    gcp_ai = b.external("DeepL + WebSpeech", "generic_application", 100, 360)

    ecs_i = b.service("compute", "Compute", "ECS Express", "aws.medicine...", "ecs", 540, 200)
    aws_ai = b.service("ai", "AI", "Translate/Polly/KB", "AWS native", "bedrock", 540, 360)

    r2_i = b.external("Cloudflare R2", "internet", 980, 260)
    neon_g = b.external("Neon (GCP)", "generic_database", 100, 480)
    neon_a = b.external("Neon (AWS)", "generic_database", 540, 480)

    b.edge(cr_i, gcp_ai)
    b.edge(ecs_i, aws_ai)
    b.edge(cr_i, r2_i, "images", points=[(220, 420), (880, 420), (880, 309)])
    b.edge(ecs_i, r2_i, "images", points=[(660, 420), (880, 420), (880, 309)])
    b.edge(cr_i, neon_g, "sessions")
    b.edge(ecs_i, neon_a, "sessions")

    b.write(DIAGRAMS / "aws-cross-cloud-overview.drawio")


def main() -> None:
    print("Generating AWS architecture diagrams...")
    build_integrated()
    build_user_request_flow()
    build_cicd_flow()
    build_external_integrations()
    build_runtime_services()
    build_cross_cloud_overview()
    print("Done. Open .drawio files directly in draw.io or VS Code Draw.io extension.")


if __name__ == "__main__":
    main()
