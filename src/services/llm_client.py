"""Groq API adapter for chat completions."""

import logging
import time
from typing import Any

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from src.config import settings

logger = logging.getLogger(__name__)

MAX_RATE_LIMIT_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


class LLMClientError(Exception):
    """Raised when the Groq client cannot complete a request."""


class LLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        client: Groq | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._model = model or settings.groq_model
        self._default_temperature = (
            temperature if temperature is not None else settings.groq_temperature
        )
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> str:
        if not self._api_key:
            raise LLMClientError("Groq API key not configured")

        temp = self._default_temperature if temperature is None else temperature
        return self._complete_with_retries(system_prompt, user_prompt, temperature=temp)

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
        return self._client

    def _complete_with_retries(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
    ) -> str:
        last_error: Exception | None = None

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                start = time.perf_counter()
                response = self._get_client().chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                elapsed_ms = (time.perf_counter() - start) * 1000
                usage = getattr(response, "usage", None)
                logger.info(
                    "Groq completion model=%s latency_ms=%.0f usage=%s",
                    self._model,
                    elapsed_ms,
                    usage,
                )

                content = self._extract_content(response)
                if not content.strip():
                    raise LLMClientError("Groq returned an empty response")
                return content

            except RateLimitError as exc:
                last_error = exc
                if attempt >= MAX_RATE_LIMIT_RETRIES:
                    break
                backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "Groq rate limit (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES,
                    backoff,
                )
                time.sleep(backoff)

            except APIConnectionError as exc:
                last_error = exc
                if attempt >= 1:
                    break
                logger.warning("Groq connection error, retrying once: %s", exc)
                time.sleep(INITIAL_BACKOFF_SECONDS)

            except APIStatusError as exc:
                if exc.status_code == 429:
                    last_error = exc
                    if attempt >= MAX_RATE_LIMIT_RETRIES:
                        break
                    backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Groq HTTP 429 (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        MAX_RATE_LIMIT_RETRIES,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                raise LLMClientError(str(exc)) from exc

        raise LLMClientError(
            f"Groq request failed after retries: {last_error}"
        ) from last_error

    @staticmethod
    def _extract_content(response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        return getattr(message, "content", None) or ""
