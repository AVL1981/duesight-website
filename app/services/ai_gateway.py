import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.core.ai_budget import AIBudgetExceeded, finalize_ai_call, reserve_ai_call
from app.core.production_policy import ProductionPolicyError, assert_ai_route_allowed

try:
    from tools.rate_limiter import tracker as _rate_tracker
except ImportError:
    _rate_tracker = None

try:
    import litellm
except ImportError:
    litellm = None

# Opt-in to LiteLLM JSON schema validation if needed, or set defaults
if litellm:
    litellm.drop_params = True # Automatically drop unsupported parameters per provider

@dataclass
class GatewayResult:
    """Standardized result from the AI Gateway."""
    engine: str
    analysis: str
    thinking_time: float
    token_count: int = 0
    cost_eur: float = 0.0
    error: Optional[str] = None
    provider: str = "unknown"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# V6.5 AI GATEWAY â€” The Universal Router (Powered by LiteLLM)
# Seamlessly routes to SambaNova, GitHub Models, Mistral, Groq, etc.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AIGateway:
    """
    Unified entrypoint for all LLMs in the DueSight ecosystem.
    Replaces the fragmented multi_model_thinker.py individual API calls.
    Supports over 100+ providers out of the box.
    """

    # Provider mapping to LiteLLM formats
    MODEL_ALIASES = {
        # SambaNova (The Volume King - 20M tokens/day developer tier)
        "sambanova/deepseek-r1": "hosted_vllm/deepseek-r1", # Requires custom base_url usually or explicit Sambanova config
        "sambanova/llama3-70b": "hosted_vllm/llama3.1-70b",

        # GitHub Models (Free Azure Backbone)
        "github/gpt-4o": "github/gpt-4o",
        "github/o1-mini": "github/o1-mini",

        # Mistral
        "mistral/large": "mistral/mistral-large-latest",
        "mistral/lechat": "mistral/pixtral-large-2411",

        # Groq (The Speed King)
        "groq/llama3": "groq/llama3-70b-8192",

        # NVIDIA NIM
        "nvidia/nemotron": "nvidia_nim/meta/llama-3.1-70b-instruct",

        # Default Google
        "google/gemini-flash": "gemini/gemini-2.5-flash",
    }

    @staticmethod
    async def think(
        prompt: str,
        data_context: str = "",
        model_alias: str = "google/gemini-flash",
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> GatewayResult:
        """
        Execute a standard analytical generation.
        """
        t0 = time.time()

        # Resolve internal alias to LiteLLM correct model string
        target_model = AIGateway.MODEL_ALIASES.get(model_alias, model_alias)
        provider_key = model_alias.split("/")[0] if "/" in model_alias else model_alias

        try:
            assert_ai_route_allowed(
                model_alias=model_alias,
                target_model=target_model,
                provider=provider_key,
            )
        except ProductionPolicyError as e:
            return GatewayResult(
                engine=model_alias,
                analysis="",
                thinking_time=time.time() - t0,
                error=f"production AI route blocked: {e}",
                provider=provider_key,
            )

        if not litellm:
            return GatewayResult(
                model_alias,
                "",
                time.time() - t0,
                error="LiteLLM library not installed. Please run: pip install litellm",
                provider=provider_key,
            )

        # Build prompt
        full_text = prompt
        if data_context:
            full_text += f"\n\n[LIVE CONTEXT DATA]\n{data_context}\n[/LIVE CONTEXT DATA]"

        messages = [{"role": "user", "content": full_text}]
        estimated_tokens = max(1, len(full_text) // 4) + max_tokens
        try:
            estimated_cost = float(os.getenv("DUESIGHT_AI_DEFAULT_CALL_EUR", "0.02"))
        except ValueError:
            estimated_cost = 0.02
        reservation = None

        try:
            reservation = reserve_ai_call(
                provider_key,
                model=target_model,
                estimated_cost_eur=estimated_cost,
                estimated_tokens=estimated_tokens,
            )

            # Add specific API keys or bases if needed via custom logic,
            # but LiteLLM picks up OS.environ keys automatically (e.g. GITHUB_API_KEY, MISTRAL_API_KEY)

            # SambaNova workaround for LiteLLM if not native yet:
            api_base = None
            if "sambanova" in model_alias:
                api_base = "https://api.sambanova.ai/v1"
                # For SambaNova API compatibility, we use their openai-compatible endpoint
                target_model = "openai/" + target_model.split("/")[-1]
                os.environ["OPENAI_API_KEY"] = os.getenv("SAMBANOVA_API_KEY", "")

            response = await litellm.acompletion(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_base=api_base,
            )

            # Extract content (handling Reasoning models gracefully)
            text = ""
            if response.choices:
                message = response.choices[0].message
                # Some models put reasoning in a different field
                text = getattr(message, "content", "") or ""

            # Token usage & Cost estimation
            usage = response.usage
            tokens = usage.total_tokens if usage else len(text.split())

            try:
                cost = litellm.cost_calculator.cost_per_token(
                    model=target_model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens
                )
            except Exception:
                cost = 0.0 # Fallback if cost not in litellm DB

            # Convert cost to EUR roughly
            cost_eur = cost * 0.92
            finalize_ai_call(
                reservation,
                actual_cost_eur=cost_eur,
                actual_tokens=tokens,
            )
            reservation = None

            # â”€â”€ Rate Limit Tracking â”€â”€
            if _rate_tracker:
                _provider = model_alias.split("/")[0] if "/" in model_alias else model_alias
                _rate_tracker.track_request(
                    _provider,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                )

            return GatewayResult(
                engine=model_alias,
                analysis=text,
                thinking_time=time.time() - t0,
                token_count=tokens,
                cost_eur=cost_eur,
                provider=response.get("model", "unknown")
            )

        except AIBudgetExceeded as e:
            return GatewayResult(
                engine=model_alias,
                analysis="",
                thinking_time=time.time() - t0,
                error=f"AI budget exceeded: {e}",
            )
        except Exception as e:
            finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
            return GatewayResult(
                engine=model_alias,
                analysis="",
                thinking_time=time.time() - t0,
                error=str(e)
            )

    @staticmethod
    async def run_consensus_panel(prompt: str, data_context: str) -> Dict[str, GatewayResult]:
        """
        Fires an objective prompt across multiple engines to form a consensus.
        The modern replacement for multi_model_thinker consensus loops.
        """
        import asyncio

        # Core analytical targets, balanced for cost and diverse reasoning
        targets = [
            "google/gemini-flash",      # Baseline Fact Checker
            "github/gpt-4o",            # Heavy Reasoning (Free tier)
            "mistral/large",            # EU Sovereign Logic
            "sambanova/deepseek-r1",    # Pure Analytical Logic
        ]

        tasks = [AIGateway.think(prompt, data_context, model) for model in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        panel_results = {}
        for idx, result in enumerate(results):
            engine_name = targets[idx]
            if isinstance(result, Exception):
                panel_results[engine_name] = GatewayResult(engine_name, "", 0, error=str(result))
            else:
                panel_results[engine_name] = result

        return panel_results
