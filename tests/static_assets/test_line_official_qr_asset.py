"""LINE 公式 QR 静的アセットの存在確認（デプロイ漏れ防止）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QR_PATH = ROOT / "static" / "line" / "line-official-qr.png"


def test_line_official_qr_png_exists_in_repo():
    assert QR_PATH.is_file(), (
        "static/line/line-official-qr.png がリポジトリにありません。"
        "AWS/GCP デプロイ前に追加してください。"
    )
    assert QR_PATH.stat().st_size > 1000, "QR 画像が小さすぎるか空です"
