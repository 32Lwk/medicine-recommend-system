# Legacy UI 退避

Big Bang 移行後、本番では Sage UI + diagnosis v1 のみ使用します。

- `LEGACY_UI_FALLBACK=true` 環境変数で legacy UI バリアントを強制可能
- 旧 HTML formatter は `src/services/html_formatter.py` に残存（dual-write ログ用）
- 推奨結果 legacy HTML は `chat_recommendation_flow.py` 非 Sage 分岐（参照: `legacy/recommendation_html_formatter.py`）
