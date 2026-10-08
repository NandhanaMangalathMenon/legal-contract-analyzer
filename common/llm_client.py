# common/llm_client.py

import json
from typing import Any, Dict

import requests

from common.config import Settings


class LLMClient:
    """
    Shared LLM client.

    Expected endpoint:

        POST {LLM_BASE_URL}/chat/completions

    This follows an OpenAI-compatible API format.

    Agent 1, Agent 2 and Agent 3 all use this class.
    """

    def __init__(
        self,
        settings: Settings | None = None
    ):
        self.settings = settings or Settings()

        # Remove trailing slash
        self.base_url = (
            self.settings.llm_base_url.rstrip("/")
        )

        self.endpoint = (
            f"{self.base_url}/chat/completions"
        )

    # ---------------------------------------------------------
    # Generate JSON
    # ---------------------------------------------------------

    def generate_json(
        self,
        system_prompt: str,
        user_payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        # -----------------------------------------------------
        # Convert payload to JSON
        # -----------------------------------------------------

        user_message = json.dumps(
            user_payload,
            ensure_ascii=False,
            indent=2
        )

        # -----------------------------------------------------
        # Request body
        # -----------------------------------------------------

        payload = {
            "model": self.settings.llm_model,

            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],

            "temperature": self.settings.temperature,

            "frequency_penalty": (
                self.settings.frequency_penalty
            ),

            "presence_penalty": (
                self.settings.presence_penalty
            ),

            "response_format": {
                "type": "json_object"
            }
        }

        # -----------------------------------------------------
        # Headers
        # -----------------------------------------------------

        headers = {
            "Content-Type": "application/json"
        }

        if self.settings.llm_api_key:
            headers["Authorization"] = (
                f"Bearer {self.settings.llm_api_key}"
            )

        # -----------------------------------------------------
        # API request
        # -----------------------------------------------------

        try:

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.settings.request_timeout
            )

        except requests.RequestException as e:

            raise RuntimeError(
                f"LLM request failed: {e}"
            ) from e

        # -----------------------------------------------------
        # HTTP errors
        # -----------------------------------------------------

        if response.status_code != 200:

            raise RuntimeError(
                "LLM API returned HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )

        # -----------------------------------------------------
        # Parse API response
        # -----------------------------------------------------

        try:

            api_response = response.json()

        except json.JSONDecodeError as e:

            raise RuntimeError(
                "LLM API returned invalid JSON."
            ) from e

        # -----------------------------------------------------
        # Extract assistant message
        # -----------------------------------------------------

        try:

            content = (
                api_response["choices"][0]
                ["message"]["content"]
            )

        except (
            KeyError,
            IndexError,
            TypeError
        ) as e:

            raise RuntimeError(
                "Unexpected LLM API response format: "
                f"{api_response}"
            ) from e

        # -----------------------------------------------------
        # Content may already be a dictionary
        # -----------------------------------------------------

        if isinstance(content, dict):
            return content

        if not isinstance(content, str):

            raise RuntimeError(
                "LLM returned unsupported content type."
            )

        # -----------------------------------------------------
        # Remove accidental Markdown code fences
        # -----------------------------------------------------

        content = content.strip()

        if content.startswith("```json"):

            content = content[
                len("```json"):
            ].strip()

            if content.endswith("```"):
                content = content[:-3].strip()

        elif content.startswith("```"):

            content = content[
                len("```"):
            ].strip()

            if content.endswith("```"):
                content = content[:-3].strip()

        # -----------------------------------------------------
        # Parse JSON
        # -----------------------------------------------------

        try:

            result = json.loads(content)

        except json.JSONDecodeError as e:

            raise RuntimeError(
                "LLM did not return valid JSON.\n"
                f"Raw response:\n{content}"
            ) from e

        # -----------------------------------------------------
        # Ensure dictionary
        # -----------------------------------------------------

        if not isinstance(result, dict):

            raise RuntimeError(
                "LLM JSON output must be an object."
            )

        return result
