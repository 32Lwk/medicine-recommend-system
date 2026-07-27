"""localhost ルーティング E2E — pytest ラッパー。"""
from __future__ import annotations

import os

import pytest

from scripts.routing_e2e_live_runner import (
    DEFAULT_BASE,
    LiveChatClient,
    load_scenarios,
    run_live_scenario,
    write_report,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_ROUTING_E2E_LIVE", "1") == "1",
    reason="set RUN_ROUTING_E2E_LIVE=1 to run HTTP E2E",
)


@pytest.fixture(scope="module")
def live_base_url() -> str:
    return os.getenv("ROUTING_E2E_BASE_URL", DEFAULT_BASE)


@pytest.fixture(scope="module")
def live_client(live_base_url: str) -> LiveChatClient:
    client = LiveChatClient(live_base_url)
    if not client.health():
        pytest.skip(f"localhost not reachable: {live_base_url}")
    return client


_SCENARIOS = load_scenarios()


@pytest.mark.live
@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[s.id for s in _SCENARIOS])
def test_routing_e2e_live_scenario(live_client: LiveChatClient, scenario):
    results = run_live_scenario(live_client, scenario)
    failures = []
    for tr in results:
        if not tr.passed:
            failures.append(
                f"user={tr.user!r} route={tr.route} kind={tr.kind} errors={tr.errors} "
                f"text={tr.bot_text[:120]!r}"
            )
    if len(results) < len(scenario.turns):
        failures.append(f"stopped early at turn {len(results)}/{len(scenario.turns)}")
    assert not failures, "\n".join(failures)


def test_write_report_smoke():
    """レポート関数のスモーク（HTTP 不要）。"""
    assert load_scenarios(category="tech_concierge")
