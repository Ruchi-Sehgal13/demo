import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

LLMProvider = Literal["groq", "google", "offline"]

# Seconds to wait between LLM/API calls to stay under RPM/TPM limits
THROTTLE_SECONDS = 2.0
# Max retries on 429 RESOURCE_EXHAUSTED
MAX_RETRIES = 4


@dataclass
class LLMConfig:
    provider: LLMProvider = "groq"
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.2


@dataclass
class ProjectPaths:
    ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAW_PDF: str = os.path.join(ROOT, "data", "raw", "IPC-to-BNS-Conversion-Guide.pdf")
    PROCESSED_CHUNKS: str = os.path.join(
        ROOT, "data", "processed", "ipcbns_chunks.json"
    )
    SQLITE_DB: str = os.path.join(ROOT, "data", "db", "ipcbns_mapping.db")
    EVAL_LOG: str = os.path.join(ROOT, "data", "eval_log.jsonl")


paths = ProjectPaths()

# Last time we made an LLM/API call; used for throttling
_last_api_call_time: float = 0.0


def throttle_before_api_call() -> None:
    """Sleep if needed so at least THROTTLE_SECONDS have passed since last API call."""
    global _last_api_call_time
    elapsed = time.monotonic() - _last_api_call_time
    if elapsed < THROTTLE_SECONDS and _last_api_call_time > 0:
        time.sleep(THROTTLE_SECONDS - elapsed)
    _last_api_call_time = time.monotonic()


def _invoke_with_retry(fn: Callable[[], Any], max_retries: int = MAX_RETRIES) -> Any:
    """Run fn(); on 429/RESOURCE_EXHAUSTED, parse retry delay and retry up to max_retries."""
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_error = e
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if not is_rate_limit:
                raise
            if attempt >= max_retries - 1:
                raise last_error from e
            # Wait long enough for per-minute quota to reset (API suggests ~22–37s; use 55s+ to be safe)
            wait = 55.0
            match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", msg, re.I)
            if match:
                wait = min(120.0, max(55.0, float(match.group(1)) + 5.0))
            time.sleep(wait)
    raise last_error  # type: ignore[misc]


class _RetryableLLM:
    """Wraps an LLM to retry on 429 / RESOURCE_EXHAUSTED with backoff."""

    def __init__(self, llm: Any, max_retries: int = MAX_RETRIES) -> None:
        self._llm = llm
        self._max_retries = max_retries

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return _invoke_with_retry(
            lambda: self._llm.invoke(input, config=config, **kwargs),
            max_retries=self._max_retries,
        )

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        from langchain_core.runnables import RunnableLambda

        inner = self._llm.with_structured_output(schema, **kwargs)
        max_retries = self._max_retries

        def invoke_with_retry(input: Any, config: Any = None, **kwargs_inner: Any) -> Any:
            return _invoke_with_retry(
                lambda: inner.invoke(input, config=config, **kwargs_inner),
                max_retries=max_retries,
            )

        return RunnableLambda(invoke_with_retry)


def get_llm(config: Optional[LLMConfig] = None):
    """
    Return a LangChain-compatible chat model. Supports groq, google (Gemini), and offline.
    """
    if config is None:
        config = LLMConfig()

    if config.provider == "groq":
        from langchain_groq import ChatGroq  # type: ignore

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Set GROQ_API_KEY in your .env file.")
        return ChatGroq(
            model=config.model or "llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=config.temperature,
        )

    if config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GOOGLE_API_KEY in your .env file.")
        return ChatGoogleGenerativeAI(
            model=config.model or "gemini-2.5-flash",
            google_api_key=api_key,
            temperature=config.temperature,
        )

    if config.provider == "offline":
        from langchain_core.runnables import RunnableLambda  # type: ignore

        def _dummy(messages):
            last = messages[-1].content if messages else ""
            return {"content": f"OFFLINE DUMMY ANSWER (echo): {last[:200]}"}

        return RunnableLambda(_dummy)

    raise ValueError(f"Unknown provider: {config.provider}")
