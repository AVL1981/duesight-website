import asyncio

import pytest

from app.core.production_policy import (
    ProductionPolicyError,
    assert_ai_route_allowed,
    is_production_runtime,
)
from app.services.ai_gateway import AIGateway


@pytest.fixture(autouse=True)
def clean_ai_policy_env(monkeypatch):
    for name in [
        "DUESIGHT_ENV",
        "DUESIGHT_ALLOW_LOCAL_AI",
        "DUESIGHT_ALLOW_CLI_AUTH",
        "DUESIGHT_ALLOW_FREE_FALLBACKS",
        "DUESIGHT_OLLAMA_ENABLED",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_development_runtime_allows_local_and_free_routes():
    assert not is_production_runtime()

    assert_ai_route_allowed(
        model_alias="pollinations",
        target_model="ollama/qwen",
        route="http://localhost:11434/api/chat",
    )


def test_production_blocks_ollama_and_local_ai(monkeypatch):
    monkeypatch.setenv("DUESIGHT_ENV", "production")

    with pytest.raises(ProductionPolicyError, match="local AI route"):
        assert_ai_route_allowed(
            model_alias="ollama/qwen",
            target_model="http://127.0.0.1:11434/api/chat",
        )


@pytest.mark.parametrize(
    "model_alias",
    [
        "pollinations",
        "github/gpt-4o",
        "groq/llama3",
        "sambanova/deepseek-r1",
        "nvidia/nemotron",
    ],
)
def test_production_blocks_free_or_developer_tier_fallbacks(monkeypatch, model_alias):
    monkeypatch.setenv("DUESIGHT_ENV", "production")

    with pytest.raises(ProductionPolicyError, match="free or developer-tier fallback route"):
        assert_ai_route_allowed(model_alias=model_alias, target_model=model_alias)


@pytest.mark.parametrize(
    "model_alias",
    ["codex/gpt-5", "claude_cli/sonnet", "antigravity/gemini", "gemini_cli/pro"],
)
def test_production_blocks_cli_auth_routes(monkeypatch, model_alias):
    monkeypatch.setenv("DUESIGHT_ENV", "production")

    with pytest.raises(ProductionPolicyError, match="CLI-auth AI route"):
        assert_ai_route_allowed(model_alias=model_alias)


def test_production_can_explicitly_allow_internal_fallbacks(monkeypatch):
    monkeypatch.setenv("DUESIGHT_ENV", "production")
    monkeypatch.setenv("DUESIGHT_ALLOW_FREE_FALLBACKS", "true")

    assert_ai_route_allowed(model_alias="pollinations")


def test_ai_gateway_blocks_production_fallback_before_litellm(monkeypatch):
    monkeypatch.setenv("DUESIGHT_ENV", "production")

    result = asyncio.run(AIGateway.think("Summarize this target.", model_alias="github/gpt-4o"))

    assert result.provider == "github"
    assert result.analysis == ""
    assert result.error
    assert result.error.startswith("production AI route blocked:")
