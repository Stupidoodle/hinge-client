"""Exceptions for the Hinge API Client."""


class HingeError(Exception):
    """Base exception for all Hinge client related errors."""


class HingeAuthError(HingeError):
    """Exception raised for authentication errors."""

    def __init__(
        self,
        message="Authentication failed. Please check your credentials.",
    ):
        """Initialize the HingeAuthError with a custom message.

        Args:
            message (str): Error message to display.

        """
        super().__init__(message)


class HingeSessionExpiredError(HingeError):
    """Exception raised when the Hinge token is expired or invalid (401)."""

    def __init__(self, message: str = "Hinge session expired. Re-authenticate."):
        """Initialize the HingeSessionExpiredError.

        Args:
            message: Error message to display.

        """
        super().__init__(message)


class HingeEmail2FAError(HingeError):
    """Exception raised when email 2FA is required for authentication."""

    def __init__(self, case_id: str, email: str):
        """Initialize the HingeEmail2FAError with case ID and email.

        Args:
            case_id (str): Case ID for the 2FA request.
            email (str): Email address associated with the account.

        """
        self.case_id = case_id
        self.email = email
        msg = f"Email 2FA required. Check email ({email})."
        super().__init__(msg)
