"""Tool ACL — Physical 以外は rule_based 推奨ツール直叩き禁止（grep 監査）"""
from pathlib import Path


def test_only_physical_flow_imports_recommendation_engine():
  root = Path(__file__).resolve().parents[1] / "src" / "handlers" / "chat"
  offenders = []
  for path in root.glob("*.py"):
      if path.name in ("chat_recommendation_flow.py", "chat_symptom_route.py", "chat_physical_route.py"):
          continue
      text = path.read_text(encoding="utf-8")
      if "recommend_medicines(" in text:
          offenders.append(str(path.name))
  assert offenders == []
