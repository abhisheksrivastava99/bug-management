import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from .env_utils import load_dotenv_file


LOGGER = logging.getLogger(__name__)
load_dotenv_file()


class OpenAIChatClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        self.model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "25"))
        self.debug = os.getenv("BM_LLM_DEBUG", "").lower() in {"1", "true", "yes", "on"}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        response_format: str = "json_object",
        debug_label: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.debug:  # pragma: no cover - debug-only behavior
            LOGGER.info("llm request label=%s model=%s", debug_label or "unknown", self.model)
            LOGGER.info("llm system prompt:\n%s", system_prompt)
            LOGGER.info("llm user prompt:\n%s", user_prompt)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            message = response.json()["choices"][0]["message"]["content"]
            if isinstance(message, list):
                message = "".join(
                    item.get("text", "") for item in message if isinstance(item, dict)
                )
            return _extract_json(message)
        except Exception as exc:  # pragma: no cover - best effort only
            LOGGER.warning("llm request failed: %s", exc)
            return None


def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    content = content.strip()
    if not content:
        return None
    if content.startswith("```"):
        parts = [part for part in content.split("```") if part.strip()]
        content = parts[0]
        if content.lower().startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
