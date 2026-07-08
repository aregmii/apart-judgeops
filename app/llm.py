"""ONLY module that touches the Anthropic API.

MODE=cached (default): never touch the network. Steps replay committed artifacts
from runs/<id>/ or fall back to data/seeds/. MODE=live makes real calls.
"""

import json
import os
import sys
import time

from pydantic import BaseModel, ValidationError

from app import ROOT

PROMPTS = ROOT / "prompts"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 8}
# Web search server tool costs $10 / 1k searches on top of tokens:
# https://docs.claude.com/en/docs/agents-and-tools/tool-use/web-search-tool


class CachedModeError(RuntimeError):
    pass


def mode() -> str:
    return os.environ.get("MODE", "cached")


def is_live() -> bool:
    return mode() == "live"


def render(prompt_id: str, ctx: dict) -> str:
    """Trivial {placeholder} templating; only known keys are substituted so JSON
    braces inside prompt files survive untouched."""
    text = (PROMPTS / f"{prompt_id}.md").read_text()
    for key, value in ctx.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object found in model output: {text[:200]}")
    return text[start : end + 1]


def call(
    prompt_id: str,
    ctx: dict,
    schema: type[BaseModel] | None = None,
    use_web_search: bool = False,
    temperature: float = 0.0,
) -> BaseModel | str:
    if not is_live():
        raise CachedModeError(
            f"MODE=cached: refusing network call for prompt '{prompt_id}'. "
            "Set MODE=live and ANTHROPIC_API_KEY to regenerate artifacts."
        )
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("MODEL", "claude-sonnet-4-6")
    prompt = render(prompt_id, ctx)
    if schema is not None:
        prompt += "\n\nRespond with a single JSON object only. No prose, no markdown fences."

    kwargs: dict = {
        "model": model,
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if use_web_search:
        kwargs["tools"] = [WEB_SEARCH_TOOL]

    text = _request_with_retries(client, kwargs, prompt_id)
    if schema is None:
        return text
    try:
        return schema.model_validate(json.loads(_extract_json(text)))
    except (ValidationError, ValueError, json.JSONDecodeError) as err:
        # One repair retry that feeds back the validation error, then raise.
        kwargs["messages"].append({"role": "assistant", "content": text})
        kwargs["messages"].append(
            {
                "role": "user",
                "content": f"Your JSON failed validation: {err}\n"
                "Return the corrected JSON object only.",
            }
        )
        repaired = _request_with_retries(client, kwargs, f"{prompt_id}:repair")
        return schema.model_validate(json.loads(_extract_json(repaired)))


def _request_with_retries(client, kwargs: dict, prompt_id: str) -> str:
    import anthropic

    delay = 1.0
    for attempt in range(3):
        try:
            response = client.messages.create(**kwargs)
            usage = response.usage
            print(
                f"[llm] prompt_id={prompt_id} model={kwargs['model']} "
                f"in_tokens={usage.input_tokens} out_tokens={usage.output_tokens}",
                file=sys.stderr,
            )
            return "".join(b.text for b in response.content if b.type == "text")
        except anthropic.APIStatusError as err:
            if err.status_code == 429 or err.status_code >= 500:
                if attempt == 2:
                    raise
                time.sleep(delay)
                delay *= 2
            else:
                raise
        except anthropic.APIConnectionError:
            if attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")
