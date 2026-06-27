"""Sendbird chat and Hinge messaging resource."""

import uuid
from typing import Any

from hinge.client.resources._base import BaseResource


class ChatResource(BaseResource):
    """Sendbird channels and messages plus Hinge-side message sending."""

    async def conversations(
        self,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List match channels from Sendbird."""
        url = (
            f"{self._client._SENDBIRD_REST_BASE}"
            f"/v3/users/{self._client.identity_id}/my_group_channels"
        )
        params = {
            "show_member": "true",
            "show_read_receipt": "true",
            "show_delivery_receipt": "true",
            "show_metadata": "true",
            "limit": str(limit),
            "order": "latest_last_message",
        }
        resp = await self._client.client.get(
            url,
            params=params,
            headers=self._client._sendbird_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def messages(
        self,
        channel_url: str,
        *,
        next_limit: int = 30,
        message_ts: int = 0,
        prev_limit: int = 0,
    ) -> dict[str, Any]:
        """Fetch message history from a Sendbird channel."""
        url = (
            f"{self._client._SENDBIRD_REST_BASE}"
            f"/v3/group_channels/{channel_url}/messages"
        )
        params = {
            "message_ts": str(message_ts),
            "prev_limit": str(prev_limit),
            "next_limit": str(next_limit),
            "include": "true",
            "with_sorted_meta_array": "true",
        }
        resp = await self._client.client.get(
            url,
            params=params,
            headers=self._client._sendbird_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def mark_read(
        self,
        channel_url: str,
    ) -> dict[str, Any]:
        """Mark all messages as read in a Sendbird channel."""
        url = (
            f"{self._client._SENDBIRD_REST_BASE}"
            f"/v3/group_channels/{channel_url}/messages/mark_as_read"
        )
        resp = await self._client.client.put(
            url,
            json={"user_id": self._client.identity_id},
            headers=self._client._sendbird_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def unread_count(self) -> dict[str, Any]:
        """Get unread channel count from Sendbird."""
        url = (
            f"{self._client._SENDBIRD_REST_BASE}"
            f"/v3/users/{self._client.identity_id}/unread_channel_count"
        )
        resp = await self._client.client.get(
            url,
            headers=self._client._sendbird_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def send(
        self,
        subject_id: str,
        message: str,
        *,
        match_message: bool = False,
        dedup_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a message via Hinge API (server-side harassment check)."""
        payload: dict[str, Any] = {
            "subjectId": subject_id,
            "matchMessage": match_message,
            "origin": "chat",
            "dedupId": dedup_id or str(uuid.uuid4()),
            "messageData": {
                "message": message,
                "fileUrl": None,
                "fileMetadata": None,
            },
            "ays": False,
        }
        resp = await self._client.client.post(
            "/message/send",
            json=payload,
            headers=self._client._get_default_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def react(
        self,
        channel_url: str,
        message_id: int,
        reaction: str = "like",
    ) -> dict[str, Any]:
        """Add a reaction (sorted_metaarray) to a Sendbird message.

        Hinge uses sorted_metaarray for likes, NOT the standard
        Sendbird reactions API.  Must use ``"value"`` (singular).
        """
        url = (
            f"{self._client._SENDBIRD_REST_BASE}"
            f"/v3/group_channels/{channel_url}"
            f"/messages/{message_id}/sorted_metaarray"
        )
        resp = await self._client.client.put(
            url,
            json={
                "sorted_metaarray": [
                    {"key": self._client.identity_id, "value": [reaction]},
                ],
                "upsert": True,
                "mode": "add",
            },
            headers=self._client._sendbird_headers(),
        )
        resp.raise_for_status()
        return resp.json()
