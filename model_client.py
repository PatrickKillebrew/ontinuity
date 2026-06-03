"""
model_client.py — Ontinuity provider-agnostic model client (session-independent)

A clean primitive for "call a model provider, get text back." Knows nothing
about sessions, sockets, or any particular configuration. Any Ontinuity
configuration — the research loop, the intake guide, a future crawler — can
call this for specialized purposes.

Design principles:
  - Session-independent: never touches active_session or socketio. Errors are
    raised as exceptions for the caller to handle however it wants.
  - Provider-agnostic: auto-detects API format from the endpoint URL, exactly
    like the engine's detect_api_format. Covers Anthropic, Gemini, and any
    OpenAI-compatible provider (Cerebras, Groq, OpenAI, OpenRouter, Together...).
  - Retry-aware: exponential-ish backoff on rate limits (HTTP 429), matching
    the engine's retry posture, with a hard ceiling.

Usage:
    from model_client import call_provider, ModelClientError

    reply = call_provider(
        url="https://api.cerebras.ai/v1/chat/completions",
        api_key="csk-...",
        model="gpt-oss-120b",
        system_prompt="You are ...",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1024,
        temperature=0.7,
    )
"""

import json as _json
import time as _time
import requests as _requests


class ModelClientError(Exception):
    """Raised on any unrecoverable provider error. Carries an optional status code."""
    def __init__(self, message, status=None, detail=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail


def detect_api_format(url):
    """Auto-detect API format from endpoint URL. Mirrors the engine's logic."""
    if "anthropic.com" in url:
        return "anthropic"
    if "generativelanguage.googleapis.com" in url:
        return "gemini"
    return "openai"  # Cerebras, OpenAI, Groq, OpenRouter, Together, Mistral, etc.


def _call_openai_format(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    full_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    body = {
        "model": model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # Backoff schedule for 429s; final None means "give up after this many".
    delays = retries + [None]
    for attempt, delay in enumerate(delays):
        try:
            r = _requests.post(url, headers=headers, data=_json.dumps(body), timeout=120)
            if r.status_code == 429:
                if delay is None:
                    raise ModelClientError("Rate limit — max retries exceeded.", status=429)
                _time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except ModelClientError:
            raise
        except _requests.exceptions.Timeout:
            raise ModelClientError("The model took too long to respond.", status=504)
        except Exception as e:
            raise ModelClientError("Upstream model error.", status=502, detail=str(e)[:300])
    raise ModelClientError("Rate limit — max retries exceeded.", status=429)


def _call_anthropic_format(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
    }
    delays = retries + [None]
    for attempt, delay in enumerate(delays):
        try:
            r = _requests.post(url, headers=headers, data=_json.dumps(body), timeout=120)
            if r.status_code == 429:
                if delay is None:
                    raise ModelClientError("Rate limit — max retries exceeded.", status=429)
                _time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        except ModelClientError:
            raise
        except _requests.exceptions.Timeout:
            raise ModelClientError("The model took too long to respond.", status=504)
        except Exception as e:
            raise ModelClientError("Upstream model error.", status=502, detail=str(e)[:300])
    raise ModelClientError("Rate limit — max retries exceeded.", status=429)


def _call_gemini_native(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries):
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    contents = []
    for msg in messages:
        if msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
    body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    delays = retries + [None]
    for attempt, delay in enumerate(delays):
        try:
            r = _requests.post(endpoint, headers=headers, data=_json.dumps(body), timeout=120)
            if r.status_code == 429:
                if delay is None:
                    raise ModelClientError("Rate limit — max retries exceeded.", status=429)
                _time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except ModelClientError:
            raise
        except _requests.exceptions.Timeout:
            raise ModelClientError("The model took too long to respond.", status=504)
        except Exception as e:
            raise ModelClientError("Upstream model error.", status=502, detail=str(e)[:300])
    raise ModelClientError("Rate limit — max retries exceeded.", status=429)


def call_provider(url, api_key, model, messages, system_prompt="",
                  max_tokens=1024, temperature=0.7, retries=None):
    """Call any supported provider and return the text reply.

    Args:
        url:           provider endpoint (format auto-detected from it)
        api_key:       provider API key
        model:         model identifier string
        messages:      list of {"role": "user"|"assistant", "content": str}
        system_prompt: system instruction (optional)
        max_tokens:    response cap
        temperature:   sampling temperature
        retries:       list of backoff seconds for 429s; default [30, 60, 120]

    Returns:
        str — the model's reply text.

    Raises:
        ModelClientError on any unrecoverable error (carries .status, .detail).
    """
    if not url or not api_key or not model:
        raise ModelClientError("Provider not configured (missing url, key, or model).", status=500)
    if retries is None:
        retries = [30, 60, 120]

    fmt = detect_api_format(url)
    if fmt == "anthropic":
        return _call_anthropic_format(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries)
    if fmt == "gemini":
        return _call_gemini_native(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries)
    return _call_openai_format(url, api_key, model, system_prompt, messages, max_tokens, temperature, retries)
