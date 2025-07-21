"""API Client for Hinge API.

██╗  ██╗██╗███╗   ██╗ ██████╗ ███████╗
██║  ██║██║████╗  ██║██╔════╝ ██╔════╝
███████║██║██╔██╗ ██║██║  ███╗█████╗
██╔══██║██║██║╚██╗██║██║   ██║██╔══╝
██║  ██║██║██║ ╚████║╚██████╔╝███████╗
╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝

Hinge API Client - Unhinged Edition 💀
For educational and research purposes only.
Don't be a creep. Use your new powers for good (or at least for science).
"""

from datetime import datetime, timezone
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Any
import asyncio
import httpx
import json
import os
import uuid
import websockets

from config import Settings, get_settings
from hinge_error import HingeAuthError
from hinge_models import (
    AnswerContentPayload,
    HingeAuthToken,
    LikeLimit,
    PhotoContent,
    Preferences,
    ProfileContent,
    RecommendationsResponse,
    SelfContentResponse,
    SelfProfileResponse,
    SendbirdAuthToken,
    UserProfile,
)
from logging_config import logger as log


class HingeClient:
    """An unhinged, async, and fully typed client fo the HHinge API.

    This class handles the entire authentication flow and provides methods
    to interact with the core features of the Hinge app, like getting
    recommendations and rating profiles. It's built for research, automation,
    and whatever chaos you have in mind. 💀
    """

    _BASE_HEADERS: dict[str, str]
    client: httpx.AsyncClient
    device_id: str
    hinge_token: str
    identity_id: str
    installed: bool
    install_id: str
    phone_number: str
    sendbird_jwt: str
    session_file: str
    session_id: str
    sendbird_session_key: str
    settings: Settings

    def __init__(
        self,
        phone_number: str,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
        session_file: str = "session.json",
    ) -> None:
        """Initialize the HingeClient with phone number and settings.

        Args:
            phone_number (str): The phone number associated with the Hinge account.
            client (httpx.AsyncClient | None): Optional HTTP client to use.
            settings (Settings | None): Optional settings for the client.
            session_file (str): Name of the file to store session data.

        """
        self.phone_number = phone_number
        self.session_file = session_file

        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                session_data = json.load(f)

            if self.phone_number == session_data.get("phone_number"):
                log.info(
                    "Using existing session data",
                    phone_number=session_data.get("phone_number"),
                )
                self.device_id = session_data.get(
                    "device_id", str(uuid.uuid4()).upper()
                )
                self.installed = session_data.get("installed", False)
                self.install_id = session_data.get(
                    "install_id", str(uuid.uuid4()).upper()
                )
                self.session_id = session_data.get(
                    "session_id", str(uuid.uuid4()).upper()
                )
                self.hinge_token = session_data.get("hinge_token", "")
                self.identity_id = session_data.get("identity_id", "")
                self.sendbird_jwt = session_data.get("sendbird_jwt", "")
                self.sendbird_session_key = session_data.get(
                    "sendbird_session_key", ""
                )
            else:
                log.warning(
                    "Session file exists but phone number does not match",
                    existing_phone=session_data.get("phone_number"),
                    new_phone=phone_number,
                )
                self._create_session()
        else:
            log.info("No existing session file found, creating new session")
            self._create_session()

        self.settings = settings or get_settings()
        self.client = client or httpx.AsyncClient(
            base_url=self.settings.BASE_URL,  # TODO: Change name
            timeout=30.0,  # TODO: Make this configurable in settings
        )
        self._BASE_HEADERS = {
            "X-Device-Platform": "iOS",
            "User-Agent": f"Hinge/{self.settings.HINGE_BUILD_NUMBER} "
            f"CFNetwork/3857.100.1 Darwin/25.0.0",
            "Accept": "*/*",
            "Accept-Language": "en-GB",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "X-Device-Model-Code": "iPhone16,1",
            "X-Device-Model": "unknown",
            "X-Device-Region": "FR",
        }

    def _get_default_headers(self) -> dict[str, str]:
        """Construct the default headers requires for most Hinge API requests.

        Returns:
            dict[str, str]: Default headers for Hinge API requests.

        """
        headers = self._BASE_HEADERS.copy()
        headers.update(
            {
                "X-Session-Id": self.session_id,
                "X-Device-Id": self.device_id,
                "X-Install-Id": self.install_id,
                "X-App-Version": self.settings.HINGE_APP_VERSION,
                "X-Build-Number": self.settings.HINGE_BUILD_NUMBER,
                "X-OS-Version": self.settings.OS_VERSION,
            }
        )

        if self.hinge_token:
            headers["Authorization"] = f"Bearer {self.hinge_token}"

        return headers

    async def initiate_login(self) -> None:
        """Start the SMS OTP login flow.

        Raises:
            HingeAuthError: If the login initiation fails.

        """
        log.info(
            "Initiating login and registering device",
            phone_number=self.phone_number,
            device_id=self.device_id,
            install_id=self.install_id,
            session_id=self.session_id,
        )
        headers = self._get_default_headers()

        install_payload = {"installId": self.install_id}

        try:
            if not self.installed:
                await self.client.post(
                    "/identity/install",
                    json=install_payload,
                    headers=headers,
                )
                self.installed = True
                log.info("Device registered successfully", install_id=self.install_id)
                self._save_session()
            else:
                log.info("Device already registered", install_id=self.install_id)
        except Exception as e:
            log.error("Failed to register device", exc_info=e)
            raise HingeAuthError("Failed to register device") from e

        otp_payload = {
            "deviceId": self.device_id,
            "phoneNumber": self.phone_number,
        }

        try:
            response = await self.client.post(
                "/auth/sms/v2/initiate",
                json=otp_payload,
                headers=headers,
            )
            response.raise_for_status()
            log.info("Login initiated successfully", phone_number=self.phone_number)
        except httpx.HTTPStatusError as e:
            log.error(
                "Failed to initiate login",
                phone_number=self.phone_number,
                status_code=e.response.status_code,
                detail=e.response.text,
            )
            raise HingeAuthError("Failed to initiate login") from e

    async def submit_otp(self, otp_code: str) -> None:
        """Submit the OTP to complete authentication and get API tokens.

        Args:
            otp_code (str): The OTP code received via SMS.

        Raises:
            HingeAuthError: If the OTP is invalid or authentication fails.

        """
        log.info(
            "Submitting OTP",
            phone_number=self.phone_number,
            otp_code=otp_code,
        )
        headers = self._get_default_headers()

        payload = {
            "installId": self.install_id,
            "deviceId": self.device_id,
            "phoneNumber": self.phone_number,
            "otp": otp_code,
        }

        try:
            response = await self.client.post(
                "/auth/sms/v2", json=payload, headers=headers
            )
            log.info(response.text)
            log.info(str(response))
            response.raise_for_status()
            auth_data = HingeAuthToken.model_validate(response.json())
            self.hinge_token = auth_data.token
            self.identity_id = auth_data.identity_id

            log.info(
                "Hinge authentication successful", auth_data=auth_data.model_dump()
            )

            self._save_session()

            await self._authenticate_with_sendbird()
        except (httpx.HTTPStatusError, ValueError) as e:
            error_text = (
                e.response.text if isinstance(e, httpx.HTTPStatusError) else str(e)
            )
            log.error(
                "Failed to submit OTP",
                phone_number=self.phone_number,
                error_text=error_text,
            )
            raise HingeAuthError(f"OTP submission failed: {error_text}") from e

    async def _authenticate_with_sendbird(self) -> None:
        """Use the Hinge token to get a Sendbird JWT and session key.

        Raises:
            HingeAuthError: If fetching Sendbird credentials fails.

        """
        log.info("Authenticating with Sendbird using Hinge token")
        headers = self._get_default_headers()

        try:
            response = await self.client.post(
                "/message/authenticate",
                json={"refresh": False},
                headers=headers,
            )
            response.raise_for_status()
            sendbird_auth = SendbirdAuthToken.model_validate(response.json())
            self.sendbird_jwt = sendbird_auth.token

            log.info(
                "Sendbird authentication successful",
                sendbird_auth=sendbird_auth.model_dump(),
            )

            ws_uri = (
                f"{self.settings.SENDBIRD_WS_URL}/?user_id={self.identity_id}"
                f"&ai={self.settings.SENDBIRD_APP_ID}"
            )
            extra_headers = {"SENDBIRD-WS-TOKEN": self.sendbird_jwt}

            async with websockets.connect(
                ws_uri, extra_headers=extra_headers
            ) as websocket:
                ws_response = await websocket.recv()
                # The first message is a LOGI payload with the session key
                if isinstance(ws_response, str) and ws_response.startswith("LOGI"):
                    logi_data = BaseModel.model_validate_json(ws_response[4:])
                    self.sendbird_session_key = logi_data.key  # type: ignore
                    log.info(
                        "Sendbird session key established",
                        sendbird_session_key=self.sendbird_session_key,
                    )
                else:
                    raise HingeAuthError(
                        "Did not receive LOGI from Sendbird WebSocket"
                    )

            self._save_session()
            log.info("Sendbird Authentication complete.")
        except (
            httpx.HTTPStatusError,
            websockets.exceptions.InvalidHandshake,
            ValueError,
        ) as e:
            log.error(
                "Failed to authenticate with Sendbird",
                error=str(e),
            )
            raise HingeAuthError(f"Failed to authenticate with Sendbird: {e}") from e

    async def get_recommendations(self) -> RecommendationsResponse:
        """Fetch the main feed of recommended profiles.

        Returns:
            RecommendationsResponse: The response containing the recommendations feed.

        """
        payload = {
            "playerId": self.identity_id,
            "newHere": False,
            "activeToday": False,
        }
        response = await self.client.post(
            "/rec/v2", json=payload, headers=self._get_default_headers()
        )
        response.raise_for_status()
        return RecommendationsResponse.model_validate(response.json())

    async def get_self_profile(self) -> SelfProfileResponse:
        """Fetch the authenticated user's own profile data.

        Returns:
            SelfProfileResponse: The response containing the user's profile data.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info("Fetching self profile data", identity_id=self.identity_id)
        response = await self.client.get(
            "/user/v3", headers=self._get_default_headers()
        )
        response.raise_for_status()
        return SelfProfileResponse.model_validate(response.json())

    async def get_self_content(self) -> SelfContentResponse:
        """Fetch the authenticated user's own content (photos, answers, etc.).

        Returns:
            SelfContentResponse: The response containing the user's content data.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info("Fetching self content data", identity_id=self.identity_id)
        response = await self.client.get(
            "/content/v2", headers=self._get_default_headers()
        )
        response.raise_for_status()
        return SelfContentResponse.model_validate(response.json())

    async def get_self_preferences(self) -> Preferences:
        """Fetch the authenticated user's preferences.

        Returns:
            Preferences: The user's preferences.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info("Fetching self preferences", identity_id=self.identity_id)
        response = await self.client.get(
            "/preference/v2/selected", headers=self._get_default_headers()
        )
        response.raise_for_status()
        return Preferences.model_validate(response.json())

    async def update_self_preferences(self, payload: Preferences) -> dict[str, Any]:
        """Update the authenticated user's preferences.

        Args:
            payload (Preferences): The preferences to update.

        Returns:
            dict[str, Any]: The API response from the update
            (usually a confirmation or partial data).

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info(
            "Updating user preferences",
            preferences=payload.model_dump(by_alias=True, exclude_none=True),
        )
        # The payload is an array containing a single preferences object
        _payload = [payload.model_dump(by_alias=True, exclude_none=True)]
        response = await self.client.patch(
            "/preference/v2/selected",
            json=_payload,
            headers=self._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()  # Returns {"genderPreferenceId":1} or something similar

    async def update_self_profile(
        self, profile_updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update the authenticated user's profile with new data.

        Args:
            profile_updates (dict[str, Any]): Dictionary containing the profile fields
            to update.

        Returns:
            dict[str, Any]: The API response from the update (usually a confirmation or partial data).

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info("Updating authenticated user's profile", updates=profile_updates)
        # The payload you sent was an array with a single object containing 'profile'
        # TODO: Write a proper Pydantic model for profile updates
        payload = [{"profile": profile_updates}]
        response = await self.client.patch(
            "/user/v2", json=payload, headers=self._get_default_headers()
        )
        response.raise_for_status()
        return response.json()  # Returns {"genderId":0} based on request

    async def update_answers(
        self, answers: list[AnswerContentPayload]
    ) -> dict[str, Any]:
        """Update the authenticated user's prompt answers.

        Args:
            answers (list[AnswerContentPayload]): List of answers to update.

        Returns:
            dict[str, Any]: The API response from the update (usually empty for 202).

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info(
            "Updating authenticated user's prompt answers",
            answers=[ans.model_dump(exclude_none=True) for ans in answers],
        )
        payload = [
            answer.model_dump(by_alias=True, exclude_none=True) for answer in answers
        ]
        response = await self.client.put(
            "/content/v1/answers", json=payload, headers=self._get_default_headers()
        )
        response.raise_for_status()
        return response.json()  # Returns {} for 202 accepted

    async def get_profiles(self, user_ids: list[str]) -> list[UserProfile]:
        """Fetch the public profile data for a list of user IDs.

        Args:
            user_ids (list[str]): List of user IDs to fetch profiles for.

        Returns:
            list[UserProfile]: List of user profiles.

        """
        params = {"ids": ",".join(user_ids)}
        response = await self.client.get(
            "/user/v3/public", params=params, headers=self._get_default_headers()
        )
        response.raise_for_status()
        return [UserProfile.model_validate(user) for user in response.json()]

    async def get_profile_content(self, user_ids: list[str]) -> list[ProfileContent]:
        """Fetch the content (photos, prompts, etc.) for a list of user IDs.

        Args:
            user_ids (list[str]): List of user IDs to fetch content for.

        Returns:
            list[ProfileContent]: List of profile content objects.

        """
        params = {"ids": ",".join(user_ids)}
        response = await self.client.get(
            "/content/v2/public", params=params, headers=self._get_default_headers()
        )
        response.raise_for_status()
        return [ProfileContent.model_validate(content) for content in response.json()]

    async def get_like_limit(self) -> LikeLimit:
        """Fetch the authenticated user's daily like and superlike limits.

        Returns:
            LikeLimit: The user's like limits including daily likes and superlikes.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        log.info(
            "Fetching like limits for authenticated user", identity_id=self.identity_id
        )
        response = await self.client.get(
            "/likelimit", headers=self._get_default_headers()
        )
        response.raise_for_status()
        return LikeLimit.model_validate(response.json())

    async def like_photo(
        self, subject_id: str, rating_token: str, photo: PhotoContent
    ) -> dict[str, Any]:
        """Like a specific photo on a user's profile.

        Args:
            subject_id (str): The ID of the user whose photo you want to like.
            rating_token (str): The rating token for the user.
            photo (PhotoContent): The photo content object to like.

        Returns:
            dict[str, Any]: The API response, typically the updated like limit.

        """
        payload = {
            "rating": "like",
            "subjectId": subject_id,
            "ratingToken": rating_token,
            "content": {"photo": photo.model_dump(exclude_none=True)},
            "sessionId": self.session_id,
            "ratingId": str(uuid.uuid4()).upper(),
            "created": datetime.now(timezone.utc).isoformat() + "Z",
            "initiatedWith": "standard",
            "origin": "compatibles",
            "hasPairing": False,
        }
        return await self._rate_user(payload)

    async def skip_profile(self, subject_id: str, rating_token: str) -> dict[str, Any]:
        """Skip a user's profile.

        Args:
            subject_id (str): The ID of the user whose profile you want to skip.
            rating_token (str): The rating token for the user.

        Returns:
            dict[str, Any]: The API response.

        """
        payload = {
            "rating": "skip",
            "subjectId": subject_id,
            "ratingToken": rating_token,
            "sessionId": self.session_id,
            "ratingId": str(uuid.uuid4()).upper(),
            "created": datetime.now(timezone.utc).isoformat() + "Z",
            "origin": "compatibles",
            "hasPairing": False,
        }
        return await self._rate_user(payload)

    async def _rate_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a rating (like/skip/note) for a user.

        Args:
            payload (dict[str, Any]): The payload for the rating request.

        Returns:
            dict[str, Any]: The API response, typically the updated like limit.

        """
        response = await self.client.post(
            "/rate/v2/initiate",
            json=payload,
            headers=self._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    def _create_session(self) -> None:
        """Create a session file with the current authentication state."""
        self.phone_number = self.phone_number
        self.device_id = str(uuid.uuid4()).upper()
        self.install_id = str(uuid.uuid4()).upper()
        self.session_id = str(uuid.uuid4()).upper()

        with open(self.session_file, "w") as f:
            json.dump(
                {
                    "phone_number": self.phone_number,
                    "device_id": self.device_id,
                    "install_id": self.install_id,
                    "session_id": self.session_id,
                    "hinge_token": "",
                    "identity_id": "",
                    "sendbird_jwt": "",
                    "sendbird_session_key": "",
                },
                f,
            )

    def _save_session(self) -> None:
        """Save the current session state to a file."""
        session_data = {
            "phone_number": self.phone_number,
            "device_id": self.device_id,
            "installed": self.installed,
            "install_id": self.install_id,
            "session_id": self.session_id,
            "hinge_token": self.hinge_token,
            "identity_id": self.identity_id,
            "sendbird_jwt": self.sendbird_jwt,
            "sendbird_session_key": self.sendbird_session_key,
        }
        with open(self.session_file, "w") as f:
            json.dump(session_data, f)

        log.info("Session saved successfully")


async def main() -> None:
    """Run the (Un)Hinge(d)Client.

    Don't run this without reading the code, you absolute degenerate. 😈
    """
    load_dotenv()
    phone_number = os.getenv("HINGE_PHONE_NUMBER")

    if not phone_number:
        raise ValueError("Please set the HINGE_PHONE_NUMBER environment variable.")

    client = HingeClient(phone_number=phone_number)

    try:
        await client.initiate_login()
        otp = input("Enter the OTP you received via SMS: ")
        await client.submit_otp(otp.strip())

        print("\n--- Successfully Authenticated ---")
        print(f"Hinge Identity ID: {client.identity_id}")
        print(f"Hinge Token: {client.hinge_token[:10]}...")
        print(f"Sendbird Session Key: {client.sendbird_session_key[:10]}...")

        # --- Core App Loop Example ---
        print("\nFetching recommendations...")
        recs = await client.get_recommendations()

        # We only care about the main feed for now
        main_feed = next(
            (feed for feed in recs.feeds if feed.origin == "compatibles"), None
        )

        if not main_feed or not main_feed.subjects:
            print("No recommendations found in the main feed. Sadge. 😔")
            return

        print(f"Found {len(main_feed.subjects)} potential matches.")

        # Take the first recommendation as an example
        first_rec = main_feed.subjects[0]
        subject_id = first_rec.subject_id
        rating_token = first_rec.rating_token  # noqa: F841

        print(f"\nHydrating profile for user: {subject_id}")
        profiles = await client.get_profiles([subject_id])
        contents = await client.get_profile_content([subject_id])

        if not profiles or not contents:
            print("Failed to fetch profile data.")
            return

        profile = profiles[0]
        content = contents[0]  # noqa: F841

        print(f"Profile Name: {profile.profile.first_name}")
    except HingeAuthError as e:
        print(f"\nAuthentication Error: {e}")
    except httpx.HTTPStatusError as e:
        print(f"\nAPI Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        await client.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
