"""Provider-neutral reasoners used by role executors."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Protocol

from agent_framework.exceptions import ChatClientException
from openai import RateLimitError


class Reasoner(Protocol):
    async def respond(self, role_id: str, instructions: str, prompt: str) -> str: ...


class ScriptedReasoner:
    """Deterministic model substitute for workflow and policy tests."""

    def __init__(self, responses: Mapping[str, str] | None = None) -> None:
        self.responses = dict(responses or {})

    async def respond(self, role_id: str, instructions: str, prompt: str) -> str:
        return self.responses.get(
            role_id,
            f"{role_id} completed deterministic review of the supplied evidence.",
        )


class AgentFrameworkReasoner:
    def __init__(
        self,
        client: object,
        *,
        run_options: dict[str, object] | None = None,
    ) -> None:
        from agent_framework import Agent

        self._agent_type = Agent
        self._client = client
        self._agents: dict[str, object] = {}
        self._run_options = run_options

    async def respond(self, role_id: str, instructions: str, prompt: str) -> str:
        agent = self._agents.get(role_id)
        if agent is None:
            agent = self._agent_type(
                client=self._client,
                name=role_id,
                instructions=instructions,
            )
            self._agents[role_id] = agent
        for attempt in range(3):
            try:
                result = await agent.run(prompt, options=self._run_options)
                return result.text if hasattr(result, "text") else str(result)
            except ChatClientException as error:
                cause = error.__cause__
                if (
                    not isinstance(cause, RateLimitError)
                    or attempt == 2
                ):
                    raise
                retry_after = float(
                    cause.response.headers.get("retry-after", 2 ** (attempt + 1))
                )
                await asyncio.sleep(min(max(retry_after, 1), 60))
        raise RuntimeError("Model retry loop ended without a response")


def provider_identity(provider: str) -> dict[str, str | None]:
    if provider == "scripted":
        return {
            "provider": "scripted",
            "model": None,
            "label": "Scripted evidence mode (no LLM)",
        }
    if provider == "ollama":
        model = os.environ.get("OLLAMA_MODEL")
        return {
            "provider": "ollama",
            "model": model,
            "label": f"Ollama · {model}" if model else "Ollama · default model",
        }
    if provider == "foundry":
        model = os.environ.get("FOUNDRY_MODEL")
        return {
            "provider": "foundry",
            "model": model,
            "label": (
                f"Microsoft Foundry · {model}"
                if model
                else "Microsoft Foundry · model not configured"
            ),
        }
    raise ValueError(f"Unsupported model provider: {provider}")


def create_reasoner(provider: str) -> Reasoner:
    if provider == "scripted":
        return ScriptedReasoner()
    if provider == "ollama":
        try:
            from agent_framework.ollama import OllamaChatClient
        except ImportError as error:
            raise RuntimeError(
                "Ollama provider dependencies are not installed"
            ) from error
        return AgentFrameworkReasoner(OllamaChatClient())
    if provider == "foundry":
        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise RuntimeError(
                "Foundry provider dependencies are not installed"
            ) from error
        endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        openai_base_url = os.environ.get("FOUNDRY_OPENAI_BASE_URL")
        model = os.environ.get("FOUNDRY_MODEL")
        if not model or not (endpoint or openai_base_url):
            raise RuntimeError(
                "FOUNDRY_MODEL and either FOUNDRY_PROJECT_ENDPOINT or "
                "FOUNDRY_OPENAI_BASE_URL are required"
            )
        credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=True
        )
        if openai_base_url:
            try:
                from agent_framework_openai import OpenAIChatClient
            except ImportError as error:
                raise RuntimeError(
                    "Azure OpenAI provider dependencies are not installed"
                ) from error
            return AgentFrameworkReasoner(
                OpenAIChatClient(
                    model=model,
                    base_url=openai_base_url,
                    credential=credential,
                ),
                run_options={
                    "reasoning": {
                        "effort": os.environ.get(
                            "FOUNDRY_REASONING_EFFORT", "low"
                        )
                    },
                    "verbosity": os.environ.get("FOUNDRY_VERBOSITY", "low"),
                    "max_tokens": int(
                        os.environ.get("FOUNDRY_MAX_OUTPUT_TOKENS", "4000")
                    ),
                },
            )
        from agent_framework.foundry import FoundryChatClient

        return AgentFrameworkReasoner(
            FoundryChatClient(
                project_endpoint=endpoint,
                model=model,
                credential=credential,
            ),
            run_options={
                "max_tokens": int(
                    os.environ.get("FOUNDRY_MAX_OUTPUT_TOKENS", "4000")
                )
            },
        )
    raise ValueError(f"Unsupported model provider: {provider}")
