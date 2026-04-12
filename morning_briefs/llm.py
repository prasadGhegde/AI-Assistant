from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .config import AppConfig


class OpenAIModelClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._client = None
        self._import_error: Optional[str] = None

    @property
    def available(self) -> bool:
        return bool(self.config.openai_api_key) and self.client is not None

    @property
    def client(self):
        if self._client is not None:
            return self._client
        if not self.config.openai_api_key:
            return None
        try:
            from openai import OpenAI
        except Exception as exc:
            self._import_error = str(exc)
            return None
        kwargs = {"api_key": self.config.openai_api_key}
        if self.config.openai_org_id:
            kwargs["organization"] = self.config.openai_org_id
        if self.config.openai_project_id:
            kwargs["project"] = self.config.openai_project_id
        self._client = OpenAI(**kwargs)
        return self._client

    @property
    def import_error(self) -> Optional[str]:
        return self._import_error

    def json_response(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: Dict[str, Any],
        max_output_tokens: int = 3000,
    ) -> Optional[Dict[str, Any]]:
        client = self.client
        if client is None:
            return None
        try:
            response = client.responses.create(
                model=self.config.openai_model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    }
                },
                max_output_tokens=max_output_tokens,
            )
            text = response_text(response)
            return json.loads(text) if text else None
        except Exception:
            return None

    def text_response(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = 3800,
    ) -> Optional[str]:
        client = self.client
        if client is None:
            return None
        try:
            response = client.responses.create(
                model=self.config.openai_model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_output_tokens=max_output_tokens,
            )
            return response_text(response)
        except Exception:
            return None


def response_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if direct:
        return str(direct)
    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunks).strip()
