"""Content settings, prompt evaluation, fresh start, and account info resource."""

from typing import Any

from hinge.client.resources._base import BaseResource
from hinge.models import ContentSettings, PromptEvaluation


class ContentResource(BaseResource):
    """Content settings, AI prompt evaluation, fresh start, and config."""

    async def settings(self) -> ContentSettings:
        """Fetch content settings (GET /content/v1/settings)."""
        response = await self._client.client.get(
            "/content/v1/settings",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return ContentSettings.model_validate(response.json())

    async def update_settings(
        self,
        settings: ContentSettings,
    ) -> ContentSettings:
        """Update content settings (PATCH /content/v1/settings)."""
        response = await self._client.client.patch(
            "/content/v1/settings",
            json=settings.model_dump(by_alias=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return ContentSettings.model_validate(response.json())

    async def evaluate_prompt(
        self,
        prompt_id: str,
        answer: str,
    ) -> PromptEvaluation:
        """AI evaluation of a prompt answer (POST /content/v1/answer/evaluate)."""
        response = await self._client.client.post(
            "/content/v1/answer/evaluate",
            json={"promptId": prompt_id, "answer": answer},
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return PromptEvaluation.model_validate(response.json())

    async def fresh_start_eligible(self) -> bool:
        """Check if eligible for fresh start (GET /freshstart/eligible)."""
        response = await self._client.client.get(
            "/freshstart/eligible",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json().get("eligible", False)

    async def fresh_start(self) -> bool:
        """Execute a fresh start (POST /freshstart)."""
        response = await self._client.client.post(
            "/freshstart",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return True

    async def store_account(self) -> dict[str, Any]:
        """Fetch store/account info (GET /store/v2/account)."""
        response = await self._client.client.get(
            "/store/v2/account",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def config(self) -> dict[str, Any]:
        """Fetch server-side enum config (GET /config/v3)."""
        response = await self._client.client.get(
            "/config/v3",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def boost_status(self) -> dict[str, Any]:
        """Fetch boost status (GET /boost/status)."""
        response = await self._client.client.get(
            "/boost/status",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()
