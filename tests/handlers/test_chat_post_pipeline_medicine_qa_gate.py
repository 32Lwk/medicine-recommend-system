"""chat_post_pipeline 早期 medicine_qa が QA ゲートを尊重する"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize(
    "message",
    [
        "GitlabとGithubの違いは？",
        "GitHubとGitLabの違いを教えて",
    ],
)
@patch("src.handlers.chat.chat_post_pipeline._run_moderation_if_needed")
@patch("src.handlers.chat.chat_counseling_flow.run_counseling_flow", return_value=(None, None))
@patch("src.handlers.chat.chat_post_pipeline._try_session_ops_handler", return_value=None)
@patch("src.handlers.chat.chat_emoji_route.try_emoji_pre_triage_route", return_value=None)
@patch("config.llm_flags.is_agent_enabled", return_value=False)
def test_early_medicine_qa_skipped_for_git_platform_question(
    _agent,
    _emoji,
    _session_ops,
    _counseling,
    _moderation,
    message,
):
    from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

    session = {"messages": [], "user_attributes": {}}
    client = MagicMock()
    client.user_agent = "test"
    client.client_ip = "127.0.0.1"

    with patch(
        "src.handlers.chat.chat_post_pipeline.parse_incoming_message",
        return_value=message,
    ):
        with patch(
            "src.handlers.chat.chat_preprocess_route.preprocess_user_message",
            return_value=(message, message),
        ):
            with patch(
                "src.handlers.chat.medicine_context_handlers.handle_medicine_information_qa"
            ) as mock_med_qa:
                with patch(
                    "src.handlers.chat.chat_category_route.route_triage_category",
                    return_value=({"status": "ok"}, 200),
                ):
                    run_chat_post_pipeline(
                        session,
                        client,
                        message,
                        "sid-git-gate",
                        MagicMock(),
                    )

    mock_med_qa.assert_not_called()
