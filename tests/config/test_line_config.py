from config import line_config


def test_normalize_line_account_url_from_basic_id():
    assert (
        line_config._normalize_line_account_url("@456olljz")
        == "https://line.me/R/ti/p/@456olljz"
    )


def test_get_line_official_account_url_defaults_to_lin_ee(monkeypatch):
    monkeypatch.delenv("LINE_OFFICIAL_ACCOUNT_URL", raising=False)
    line_config._BOT_INFO_CACHE = None
    monkeypatch.setattr(line_config, "_fetch_line_official_account_url_from_api", lambda: "")
    assert line_config.get_line_official_account_url(force_refresh=True) == "https://lin.ee/no4FYRe"


def test_get_line_official_account_qr_url_uses_r2_cdn_by_default(monkeypatch):
    monkeypatch.delenv("LINE_OFFICIAL_ACCOUNT_QR_URL", raising=False)
    import config.static_assets as static_assets

    monkeypatch.setattr(static_assets, "should_prefer_local_static_assets", lambda: False)
    assert (
        line_config.get_line_official_account_qr_url()
        == "https://images.yutok.dev/line/line-official-qr.png"
    )


def test_get_line_official_account_qr_url_uses_local_static_on_loopback(monkeypatch):
    monkeypatch.delenv("LINE_OFFICIAL_ACCOUNT_QR_URL", raising=False)
    import config.aws_features as aws_features
    import config.static_assets as static_assets

    monkeypatch.setattr(static_assets, "should_prefer_local_static_assets", lambda: True)
    monkeypatch.setattr(
        aws_features,
        "resolve_static_asset_url",
        lambda fn: f"/static/{fn.lstrip('/')}",
    )
    assert (
        line_config.get_line_official_account_qr_url()
        == "/static/line/line-official-qr.png"
    )
