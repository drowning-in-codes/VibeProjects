"""Shared helpers for Anthropic and OpenAI-compatible model providers."""
from typing import Any, Optional
from urllib.parse import urlsplit

from anthropic import Anthropic
from openai import OpenAI


def create_chat_client(api_key: str, base_url: Optional[str] = None,
                       http_client=None, provider: str = "openai") -> Any:
    """Create a client for an Anthropic or OpenAI-compatible endpoint."""
    if provider == "anthropic":
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")
        if http_client:
            client_kwargs["http_client"] = http_client
        return Anthropic(**client_kwargs)

    if provider != "openai":
        raise ValueError(f"Unsupported chat provider: {provider}")

    client_kwargs = {"api_key": api_key}
    if base_url:
        normalized_url = base_url.rstrip("/")
        if not urlsplit(normalized_url).path.rstrip("/").endswith("/v1"):
            normalized_url += "/v1"
        client_kwargs["base_url"] = normalized_url
    if http_client:
        client_kwargs["http_client"] = http_client
    return OpenAI(**client_kwargs)


def complete_chat(client: Any, model: str, prompt: str, max_tokens: int,
                  system_prompt: str = "", provider: str = "openai") -> str:
    """Call the configured provider and return the assistant's text."""
    if provider == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt or None,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        )

    if provider != "openai":
        raise ValueError(f"Unsupported chat provider: {provider}")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    if not response.choices:
        return ""
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.text for part in content if getattr(part, "text", None)
        )
    return ""
