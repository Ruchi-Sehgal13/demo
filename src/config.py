import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LLMProvider = Literal["google", "offline", "openai", "anthropic"]

# Ordered list of Google models to try when the primary model's quota is exhausted.
GOOGLE_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
]


@dataclass
class LLMConfig:
    provider: LLMProvider = "google"
    model: str = "gemini-2.5-flash"
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


def get_llm(config: Optional[LLMConfig] = None):
    """
    Return a LangChain-compatible chat model.

    For the Google provider, the returned model is wrapped with fallbacks so
    that if the primary model's quota is exhausted (429 RESOURCE_EXHAUSTED),
    the next model in GOOGLE_FALLBACK_MODELS is tried automatically.
    """
    from langchain_core.language_models import BaseChatModel  # type: ignore

    if config is None:
        config = LLMConfig()

    if config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GOOGLE_API_KEY or GEMINI_API_KEY in environment.")

        def _make_google_llm(model_name: str) -> ChatGoogleGenerativeAI:
            return ChatGoogleGenerativeAI(
                model=model_name,
                api_key=api_key,
                temperature=config.temperature,
                max_retries=1,  # fail fast → let fallback handle it
            )

        primary: BaseChatModel = _make_google_llm(config.model)

        # Build fallback LLMs from every model in the list except the primary.
        fallbacks = [
            _make_google_llm(m)
            for m in GOOGLE_FALLBACK_MODELS
            if m != config.model
        ]

        if fallbacks:
            logger.info(
                "Google LLM: primary=%s, fallbacks=%s",
                config.model,
                [m for m in GOOGLE_FALLBACK_MODELS if m != config.model],
            )
            return primary.with_fallbacks(fallbacks)

        return primary

    if config.provider == "offline":
        from langchain_core.runnables import RunnableLambda  # type: ignore

        def _dummy(messages):
            last = messages[-1].content if messages else ""
            return {"content": f"OFFLINE DUMMY ANSWER (echo): {last[:200]}"}

        return RunnableLambda(_dummy)

    if config.provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore

        return ChatOpenAI(
            model=config.model or "gpt-4o-mini",
            temperature=config.temperature,
        )

    if config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # type: ignore

        return ChatAnthropic(
            model=config.model or "claude-3-haiku-20240307",
            temperature=config.temperature,
        )

    raise ValueError(f"Unknown provider: {config.provider}")
