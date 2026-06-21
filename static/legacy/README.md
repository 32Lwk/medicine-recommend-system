# Legacy static assets (archive)

Sage UI 一本化に伴い、旧 HTML/CSS/JS アセットは `legacy/` ディレクトリ（Python shim）へ退避しました。

- `legacy/html_formatter.py` — 旧 HTML 生成（参照用 shim）
- `legacy/recommendation_html_formatter.py` — 旧推奨 HTML（参照用）

新規 Web UI は `diagnosis v1` + `static/js/ui/*` レンダラのみを使用してください。
