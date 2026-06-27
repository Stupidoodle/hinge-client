"""Core lifecycle, transport, and session management for the Hinge API client."""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from hinge.core.catalog import Catalog, EnumCatalog
from hinge.core.logging import logger as log
from hinge.error import HingeAuthError, HingeEmail2FAError
from hinge.models import (
    HingeAuthToken,
    LikeLimit,
    PromptsResponse,
    RecommendationSubject,
    SendbirdAuthToken,
    StandoutsV3Response,
)
from hinge.prompts_manager import HingePromptsManager

# --- Constants ---

BASE_URL = "https://prod-api.hingeaws.net"
SENDBIRD_APP_ID = "3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9"
HINGE_APP_VERSION = "9.82.0"
HINGE_BUILD_NUMBER = "11616"
OS_VERSION = "26.0"
SESSIONS_DIR = os.environ.get("HINGE_SESSIONS_DIR", "hinge_sessions")


def _derive_auth_state(
    saved_state: str,
    token: str,
    expires_str: str | None,
) -> str:
    """Derive the effective auth state from persisted session data.

    Returns one of: "authenticated", "expired", "pending_otp",
    "pending_email", "unauthenticated".
    """
    # Pending states are trusted as-is (no token to validate)
    if saved_state in ("pending_otp", "pending_email"):
        return saved_state

    # If there's a token, check if it's still valid
    if token and expires_str:
        try:
            expires = datetime.fromisoformat(expires_str)
            if expires > datetime.now(timezone.utc):
                return "authenticated"
            return "expired"
        except ValueError, TypeError:
            pass

    return "unauthenticated"


async def _preflight_refresh_session(
    data: dict[str, Any],
    fpath: str,
    now: datetime,
    threshold: datetime,
) -> str:
    """Attempt to refresh a single session's token if expiring soon.

    Returns one of: "refreshed", "skipped", "failed", "expired".
    """
    import httpx

    token = data.get("hinge_token", "")
    expires_str = data.get("hinge_token_expires")
    saved_state = data.get("auth_state", "")
    phone = data.get("phone_number", "")

    if not token or saved_state not in ("authenticated", ""):
        return "skipped"

    if not isinstance(expires_str, str):
        return "skipped"
    try:
        expires = datetime.fromisoformat(expires_str)
    except ValueError:
        return "skipped"

    if expires <= now:
        return "expired"
    if expires > threshold:
        return "skipped"

    log.info(
        "preflight_refresh_attempting",
        phone=phone,
        expires=expires_str,
    )
    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
        ) as tmp_client:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Device-Platform": "iOS",
                "User-Agent": (
                    f"Hinge/{HINGE_BUILD_NUMBER} CFNetwork/3857.100.1 Darwin/25.0.0"
                ),
                "Accept": "*/*",
                "X-Device-Id": data.get("device_id", ""),
                "X-Install-Id": data.get("install_id", ""),
                "X-Session-Id": data.get("session_id", ""),
                "X-App-Version": HINGE_APP_VERSION,
                "X-Build-Number": HINGE_BUILD_NUMBER,
                "X-OS-Version": OS_VERSION,
            }
            resp = await tmp_client.get(
                "/auth/refresh",
                headers=headers,
            )
        if resp.status_code == 201:
            resp_data = resp.json()
            data["hinge_token"] = resp_data["token"]
            data["identity_id"] = resp_data.get(
                "identityId",
                data.get("identity_id", ""),
            )
            data["hinge_token_expires"] = resp_data["expires"]
            data["auth_state"] = "authenticated"
            with open(fpath, "w") as f:
                json.dump(data, f)
            log.info(
                "preflight_refresh_success",
                phone=phone,
                new_expires=resp_data["expires"],
            )
            return "refreshed"
        log.warning(
            "preflight_refresh_failed",
            phone=phone,
            status=resp.status_code,
        )
        return "failed"
    except Exception:
        log.error(
            "preflight_refresh_error",
            phone=phone,
            exc_info=True,
        )
        return "failed"


class HingeClient:
    """Async client for the Hinge API.

    Handles authentication, recommendation fetching, rating, profile
    management, and all core Hinge API interactions.
    """

    client: httpx.AsyncClient
    device_id: str
    hinge_token: str
    hinge_token_expires: datetime
    identity_id: str
    installed: bool
    install_id: str
    phone_number: str
    prompts_manager: HingePromptsManager | None
    _enum_catalog: EnumCatalog | None
    _rec_cache: dict[str, RecommendationSubject]
    sendbird_jwt: str
    sendbird_jwt_expires: datetime
    session_file: str
    session_id: str
    sendbird_session_key: str

    # Auth state constants
    AUTH_UNAUTHENTICATED = "unauthenticated"
    AUTH_PENDING_OTP = "pending_otp"
    AUTH_PENDING_EMAIL = "pending_email"
    AUTH_AUTHENTICATED = "authenticated"

    def __init__(
        self,
        phone_number: str,
        client: httpx.AsyncClient | None = None,
        prompts_cache_file: str = "prompts_cache.json",
    ) -> None:
        """Initialize the HingeClient with phone number.

        Args:
            phone_number: The phone number associated with the Hinge account.
            client: Optional HTTP client to use.
            prompts_cache_file: Name of the file to cache prompts data.

        """
        self.phone_number = phone_number
        self.prompts_cache_file = prompts_cache_file
        self.auth_state: str = self.AUTH_UNAUTHENTICATED
        self._pending_email_2fa: dict[str, str] | None = None  # {case_id, email}
        self.feed_exhausted: bool = False
        self._standouts_etag: str | None = None
        self._standouts_cache: StandoutsV3Response | None = None
        self._enum_catalog: EnumCatalog | None = None

        # Ensure sessions directory exists
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        # Session file is per-phone-number
        self.session_file = self._session_file_for(phone_number)
        self._load_or_create_session()
        self._load_recommendations()

        self.client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
        )
        self._BASE_HEADERS = {
            "X-Device-Platform": "iOS",
            "User-Agent": (
                f"Hinge/{HINGE_BUILD_NUMBER} CFNetwork/3857.100.1 Darwin/25.0.0"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-GB",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "X-Device-Model-Code": "iPhone16,1",
            "X-Device-Model": "unknown",
            "X-Device-Region": "FR",
        }
        self.prompts_manager = self._load_prompts_from_cache()

        from hinge.client.resources import (
            ChatResource,
            ContentResource,
            ProfileResource,
            PromptsResource,
            RatingResource,
            RecommendationsResource,
        )

        self.recommendations = RecommendationsResource(self)
        self.profile = ProfileResource(self)
        self.rating = RatingResource(self)
        self.content = ContentResource(self)
        self.prompts = PromptsResource(self)
        self.chat = ChatResource(self)

    def _get_default_headers(self) -> dict[str, str]:
        """Construct the default headers for most Hinge API requests."""
        headers = self._BASE_HEADERS.copy()
        headers.update(
            {
                "X-Session-Id": self.session_id,
                "X-Device-Id": self.device_id,
                "X-Install-Id": self.install_id,
                "X-App-Version": HINGE_APP_VERSION,
                "X-Build-Number": HINGE_BUILD_NUMBER,
                "X-OS-Version": OS_VERSION,
            },
        )
        if self.hinge_token:
            headers["Authorization"] = f"Bearer {self.hinge_token}"
        return headers

    # --- Token Refresh ---

    def _token_expires_within(self, days: int = 7) -> bool:
        """Check if the Hinge token expires within the given number of days."""
        if not self.hinge_token or not self.hinge_token_expires:
            return False
        from datetime import timedelta

        threshold = datetime.now(timezone.utc) + timedelta(days=days)
        return self.hinge_token_expires < threshold

    async def ensure_fresh_token(self) -> None:
        """Proactively refresh the Hinge token if it expires within 7 days.

        CRITICAL: ``GET /auth/refresh`` instantly invalidates the old token.
        The new token MUST be persisted before any subsequent request, or the
        session is permanently dead (requires full SMS OTP re-auth).
        """
        if not self.hinge_token or self.auth_state != self.AUTH_AUTHENTICATED:
            return
        if not self._token_expires_within(days=7):
            return

        log.info(
            "hinge_token_refresh_starting",
            expires=self.hinge_token_expires.isoformat(),
        )
        headers = self._get_default_headers()
        try:
            response = await self.client.get(
                "/auth/refresh",
                headers=headers,
            )
            if response.status_code == 201:
                data = response.json()
                self.hinge_token = data["token"]
                self.identity_id = data.get("identityId", self.identity_id)
                self.hinge_token_expires = datetime.fromisoformat(data["expires"])
                # MUST save immediately — old token is already dead
                self._save_session()
                log.info(
                    "hinge_token_refreshed",
                    new_expires=self.hinge_token_expires.isoformat(),
                )
            else:
                log.warning(
                    "hinge_token_refresh_failed",
                    status=response.status_code,
                    body=response.text[:200],
                )
        except Exception:
            log.error("hinge_token_refresh_error", exc_info=True)

    # --- Auth Flow ---

    async def initiate_login(self) -> None:
        """Start the SMS OTP login flow."""
        headers = self._get_default_headers()

        if not self.installed:
            await self.client.post(
                "/identity/install",
                json={"installId": self.install_id},
                headers=headers,
            )
            self.installed = True
            self._save_session()

        response = await self.client.post(
            "/auth/sms/v2/initiate",
            json={
                "deviceId": self.device_id,
                "phoneNumber": self.phone_number,
            },
            headers=headers,
        )
        response.raise_for_status()
        self.auth_state = self.AUTH_PENDING_OTP
        log.info("hinge_login_initiated", phone=self.phone_number)

    async def submit_otp(self, otp_code: str) -> None:
        """Submit OTP to complete authentication.

        Args:
            otp_code: The OTP code received via SMS.

        Raises:
            HingeEmail2FAError: If email 2FA is required.
            HingeAuthError: If authentication fails.

        """
        headers = self._get_default_headers()
        payload = {
            "installId": self.install_id,
            "deviceId": self.device_id,
            "phoneNumber": self.phone_number,
            "otp": otp_code,
        }

        response = await self.client.post(
            "/auth/sms/v2",
            json=payload,
            headers=headers,
        )

        if response.status_code == 412:
            error_data = response.json()
            case_id = error_data.get("caseId")
            email = error_data.get("email")
            if case_id and email:
                self.auth_state = self.AUTH_PENDING_EMAIL
                self._pending_email_2fa = {"case_id": case_id, "email": email}
                self._save_session()
                raise HingeEmail2FAError(case_id=case_id, email=email)
            raise HingeAuthError(f"Unexpected 412 response: {response.text}")

        response.raise_for_status()
        auth_data = HingeAuthToken.model_validate(response.json())
        self.hinge_token = auth_data.token
        self.identity_id = auth_data.identity_id
        self.hinge_token_expires = auth_data.expires
        self.auth_state = self.AUTH_AUTHENTICATED
        self._save_session()

        await self._authenticate_with_sendbird()

    async def submit_email_code(self, email_code: str, case_id: str) -> None:
        """Submit email 2FA verification code.

        Args:
            email_code: The verification code received via email.
            case_id: The case ID from the initial 412 response.

        """
        headers = self._get_default_headers()
        payload = {
            "installId": self.install_id,
            "code": email_code,
            "caseId": case_id,
            "deviceId": self.device_id,
        }

        response = await self.client.post(
            "/auth/device/validate",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        auth_data = HingeAuthToken.model_validate(response.json())
        self.hinge_token = auth_data.token
        self.identity_id = auth_data.identity_id
        self.hinge_token_expires = auth_data.expires
        self.auth_state = self.AUTH_AUTHENTICATED
        self._pending_email_2fa = None
        self._save_session()

        await self._authenticate_with_sendbird()

    async def _authenticate_with_sendbird(self) -> None:
        """Use the Hinge token to get a Sendbird JWT and session key."""
        headers = self._get_default_headers()

        response = await self.client.post(
            "/message/authenticate",
            json={"refresh": False},
            headers=headers,
        )
        response.raise_for_status()
        sendbird_auth = SendbirdAuthToken.model_validate(response.json())
        self.sendbird_jwt = sendbird_auth.token
        self.sendbird_jwt_expires = sendbird_auth.expires

        try:
            import websockets

            ws_uri = (
                f"wss://ws-{SENDBIRD_APP_ID.lower()}.sendbird.com"
                f"/?user_id={self.identity_id}"
                f"&ai={SENDBIRD_APP_ID}"
            )
            extra_headers = {"SENDBIRD-WS-TOKEN": self.sendbird_jwt}

            async with websockets.connect(
                ws_uri,
                additional_headers=extra_headers,
            ) as websocket:
                ws_response = await websocket.recv()
                if isinstance(ws_response, str) and ws_response.startswith("LOGI"):
                    logi_data = json.loads(ws_response[4:])
                    self.sendbird_session_key = logi_data["key"]
                else:
                    raise HingeAuthError(
                        "Did not receive LOGI from Sendbird WebSocket",
                    )
        except ImportError:
            log.warning("websockets_not_installed")
            self.sendbird_session_key = ""

        self._save_session()

    async def check_session_health(self) -> LikeLimit | None:
        """Ping ``/likelimit`` to verify the session is truly alive.

        Returns the ``LikeLimit`` on success, or ``None`` if the session
        is dead (confirmed by two consecutive 401s).  A single 401 may be
        transient (rate limit masquerading as auth error), so we retry
        once after a short delay before declaring the session dead.
        """
        if not self.hinge_token:
            return None

        for attempt in range(2):
            try:
                return await self.rating.limit()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    if attempt == 0:
                        log.info("session_health_retry")
                        await asyncio.sleep(3)
                        continue
                    # Second 401 — session is genuinely dead
                    log.warning("session_health_dead")
                    self.auth_state = self.AUTH_UNAUTHENTICATED
                    self._save_session()
                    return None
                raise
        return None  # pragma: no cover - unreachable; loop always returns or raises

    async def is_session_valid(self) -> bool:
        """Check if the current session is still valid via /likelimit.

        Also proactively refreshes the token if it expires within 7 days.
        """
        if not self.hinge_token:
            return False

        # Proactive token refresh (non-destructive check first)
        await self.ensure_fresh_token()

        # Authoritative check: /likelimit
        limit = await self.check_session_health()
        if limit is None:
            return False

        # Sendbird refresh if needed
        now_utc = datetime.now(timezone.utc)
        sendbird_valid = (
            self.sendbird_jwt_expires > now_utc if self.sendbird_jwt_expires else False
        )
        if not sendbird_valid and self.sendbird_jwt:
            await self._authenticate_with_sendbird()

        return True

    # --- Prompts ---

    @property
    def catalog(self) -> Catalog:
        """In-memory catalog: enum labels (static) + the live prompt library."""
        if self._enum_catalog is None:
            self._enum_catalog = EnumCatalog.load()
        return Catalog(self._enum_catalog, self.prompts_manager)

    def _resolve_prompt_text(self, question_id: str) -> str:
        """Resolve a prompt question id to its display text (best-effort)."""
        if self.prompts_manager is not None:
            return self.prompts_manager.get_prompt_display_text(question_id)
        return ""

    # --- Sendbird Chat ---

    _SENDBIRD_REST_BASE = (
        "https://api-3cdad91c-1e0d-4a0d-bbee-9671988bf9e9.sendbird.com"
    )

    def _sendbird_headers(self) -> dict[str, str]:
        """Headers for Sendbird REST API calls."""
        return {
            "Session-Key": self.sendbird_session_key,
            "Content-Type": "application/json",
        }

    # --- Session Persistence ---

    @staticmethod
    def _session_file_for(phone: str) -> str:
        """Return the session file path for a given phone number.

        Strips spaces and dashes but preserves the leading ``+`` so that
        the filename matches the canonical phone format stored in the
        session data.
        """
        safe = phone.replace(" ", "").replace("-", "")
        return os.path.join(SESSIONS_DIR, f"{safe}.json")

    @staticmethod
    def list_sessions() -> list[dict[str, Any]]:
        """List all saved Hinge sessions.

        Returns:
            List of session metadata dicts with phone, identity_id,
            token_expires, auth_state, and needs_reauth.

        """
        sessions: list[dict[str, Any]] = []
        if not os.path.isdir(SESSIONS_DIR):
            return sessions
        for fname in os.listdir(SESSIONS_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(SESSIONS_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                token = data.get("hinge_token", "")
                expires_str = data.get("hinge_token_expires")
                saved_state = data.get("auth_state", "")

                # Derive effective auth_state
                auth_state = _derive_auth_state(
                    saved_state,
                    token,
                    expires_str,
                )
                needs_reauth = auth_state in (
                    "unauthenticated",
                    "expired",
                )

                sessions.append(
                    {
                        "phone_number": data.get("phone_number", ""),
                        "identity_id": data.get("identity_id", ""),
                        "token_expires": expires_str,
                        "auth_state": auth_state,
                        "needs_reauth": needs_reauth,
                    },
                )
            except json.JSONDecodeError, OSError:
                continue
        return sessions

    @staticmethod
    async def refresh_all_sessions(
        *,
        threshold_days: int = 14,
    ) -> dict[str, str]:
        """Refresh tokens for all stored sessions expiring soon.

        Returns:
            Mapping of phone_number → result ("refreshed", "skipped",
            "failed", "expired").

        """
        results: dict[str, str] = {}
        if not os.path.isdir(SESSIONS_DIR):
            return results

        from datetime import timedelta

        now = datetime.now(timezone.utc)
        threshold = now + timedelta(days=threshold_days)

        for fname in os.listdir(SESSIONS_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(SESSIONS_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
            except json.JSONDecodeError, OSError:
                continue

            result = await _preflight_refresh_session(
                data,
                fpath,
                now,
                threshold,
            )
            phone = data.get("phone_number", fname)
            results[phone] = result

        return results

    def switch_session(self, phone_number: str) -> None:
        """Switch the active session to a different phone number.

        Loads the session file for the given phone number, or creates
        a new session if none exists.
        """
        self.phone_number = phone_number
        self.session_file = self._session_file_for(phone_number)
        self._load_or_create_session()
        log.info("hinge_session_switched", phone=phone_number)

    def _load_or_create_session(self) -> None:
        """Load an existing session or create a fresh one.

        Checks the canonical filename first, then falls back to the legacy
        format (without leading ``+``) and migrates it.  When no phone
        number is configured, scans the sessions directory for any valid
        session file.
        """
        for path in self._candidate_session_paths():
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    self._apply_session_data(data)
                    # Migrate legacy file to canonical path
                    if path != self.session_file:
                        self._save_session()
                        os.remove(path)
                        log.info(
                            "hinge_session_migrated",
                            old=path,
                            new=self.session_file,
                        )
                    return
                except json.JSONDecodeError, OSError:
                    log.warning("hinge_session_corrupt", file=path)

        # No phone-specific session found — scan for any valid session
        if not self.phone_number and os.path.isdir(SESSIONS_DIR):
            for fname in sorted(os.listdir(SESSIONS_DIR)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(path) as f:
                        data = json.load(f)
                    if data.get("auth_state") == self.AUTH_AUTHENTICATED:
                        self._apply_session_data(data)
                        self.phone_number = data.get(
                            "phone_number",
                            "",
                        )
                        self.session_file = path
                        log.info(
                            "hinge_session_auto_detected",
                            phone=self.phone_number,
                        )
                        return
                except json.JSONDecodeError, OSError:
                    continue

        self._create_session()

    def _candidate_session_paths(self) -> list[str]:
        """Return candidate session file paths (canonical first, legacy second)."""
        canonical = self.session_file
        legacy = os.path.join(
            SESSIONS_DIR,
            f"{self.phone_number.replace('+', '').replace(' ', '').replace('-', '')}"
            ".json",
        )
        paths = [canonical]
        if legacy != canonical:
            paths.append(legacy)
        return paths

    def _apply_session_data(self, data: dict[str, Any]) -> None:
        """Apply loaded session data to the client state."""
        log.info("hinge_session_loaded", phone=data.get("phone_number"))
        self.device_id = data.get("device_id", str(uuid.uuid4()).upper())
        self.installed = data.get("installed", False)
        self.install_id = data.get("install_id", str(uuid.uuid4()).upper())
        self.session_id = data.get("session_id", str(uuid.uuid4()).upper())
        self.hinge_token = data.get("hinge_token", "")
        self.identity_id = data.get("identity_id", "")
        self.sendbird_jwt = data.get("sendbird_jwt", "")
        self.sendbird_session_key = data.get("sendbird_session_key", "")
        if data.get("hinge_token_expires"):
            self.hinge_token_expires = datetime.fromisoformat(
                data["hinge_token_expires"],
            )
        else:
            self.hinge_token_expires = datetime.now(timezone.utc)
        if data.get("sendbird_jwt_expires"):
            self.sendbird_jwt_expires = datetime.fromisoformat(
                data["sendbird_jwt_expires"],
            )
        else:
            self.sendbird_jwt_expires = datetime.now(timezone.utc)
        # Restore auth state — trust the file if it has one, otherwise derive
        saved_state = data.get("auth_state")
        if saved_state in (
            self.AUTH_UNAUTHENTICATED,
            self.AUTH_PENDING_OTP,
            self.AUTH_PENDING_EMAIL,
            self.AUTH_AUTHENTICATED,
        ):
            # Validate: if file says authenticated, confirm token is actually valid
            if saved_state == self.AUTH_AUTHENTICATED and (
                not self.hinge_token
                or self.hinge_token_expires <= datetime.now(timezone.utc)
            ):
                self.auth_state = self.AUTH_UNAUTHENTICATED
            else:
                self.auth_state = saved_state
        elif self.hinge_token and self.hinge_token_expires > datetime.now(timezone.utc):
            self.auth_state = self.AUTH_AUTHENTICATED
        else:
            self.auth_state = self.AUTH_UNAUTHENTICATED

    def _create_session(self) -> None:
        """Create a new session with fresh UUIDs."""
        self.device_id = str(uuid.uuid4()).upper()
        self.installed = False
        self.install_id = str(uuid.uuid4()).upper()
        self.session_id = str(uuid.uuid4()).upper()
        self.hinge_token = ""
        self.identity_id = ""
        self.sendbird_jwt = ""
        self.sendbird_session_key = ""
        self.hinge_token_expires = datetime.now(timezone.utc)
        self.sendbird_jwt_expires = datetime.now(timezone.utc)
        self.auth_state = self.AUTH_UNAUTHENTICATED
        self._save_session()

    def _save_session(self) -> None:
        """Save the current session state to a file."""
        if not self.phone_number or not self.phone_number.strip():
            return
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        session_data = {
            "phone_number": self.phone_number,
            "device_id": self.device_id,
            "installed": self.installed,
            "install_id": self.install_id,
            "session_id": self.session_id,
            "hinge_token": self.hinge_token,
            "hinge_token_expires": self.hinge_token_expires.isoformat(),
            "identity_id": self.identity_id,
            "sendbird_jwt": self.sendbird_jwt,
            "sendbird_session_key": self.sendbird_session_key,
            "sendbird_jwt_expires": self.sendbird_jwt_expires.isoformat(),
            "auth_state": self.auth_state,
        }
        with open(self.session_file, "w") as f:
            json.dump(session_data, f)

    def _load_recommendations(self) -> None:
        """Load recommendations from file if available."""
        self._rec_cache = {}
        recs_file = f"recommendations_{self.session_id}.json"

        if not os.path.exists(recs_file):
            return

        try:
            with open(recs_file) as f:
                recs_data = json.load(f)
                for subject_id, subject_data in recs_data.items():
                    self._rec_cache[subject_id] = RecommendationSubject.model_validate(
                        subject_data
                    )
        except json.JSONDecodeError, KeyError:
            self._rec_cache = {}

    def _save_recommendations(self) -> None:
        """Save current recommendations to file."""
        with open(f"recommendations_{self.session_id}.json", "w") as f:
            serializable = {sid: s.model_dump() for sid, s in self._rec_cache.items()}
            json.dump(serializable, f, indent=2)

    def _load_prompts_from_cache(self) -> HingePromptsManager | None:
        """Load prompts from cached JSON file."""
        if not os.path.exists(self.prompts_cache_file):
            return None
        try:
            with open(self.prompts_cache_file) as f:
                cache_data = json.load(f)
            prompts_data = PromptsResponse.model_validate(cache_data)
            return HingePromptsManager(prompts_data)
        except Exception:
            return None

    def _save_prompts_to_cache(self, prompts_data: PromptsResponse) -> None:
        """Save prompts data to cache file."""
        try:
            with open(self.prompts_cache_file, "w") as f:
                json.dump(prompts_data.model_dump(by_alias=True), f, indent=2)
        except Exception:
            log.warning("hinge_prompts_cache_save_failed", exc_info=True)
