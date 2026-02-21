"""Shared utilities for agent nodes."""

import logging

logger = logging.getLogger(__name__)


def extract_text(result) -> str:
    """
    Normalise an LLM result into a plain string.

    Different models/fallbacks may return:
      - A string directly
      - An AIMessage with .content as str
      - An AIMessage with .content as list[str]
      - An AIMessage with .content as list[{'type':'text','text':'...'}]
      - A dict with a 'content' key
    """
    # 1. Get raw content
    if hasattr(result, "content"):
        content = result.content
    elif isinstance(result, dict):
        content = result.get("content", result.get("text", str(result)))
    else:
        content = result

    # 2. If it's already a string, return it
    if isinstance(content, str):
        return content

    # 3. If it's a list, join the parts
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", str(part)))
            else:
                parts.append(str(part))
        return "\n".join(parts)

    return str(content)
