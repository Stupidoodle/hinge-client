"""Exceptions for the Hinge API Client."""


class HingeError(Exception):
    """Base exception for all Hinge client related errors."""


class HingeAuthError(HingeError):
    """Exception raised for authentication errors."""

    def __init__(
        self, message="Authentication failed. Please check your credentials."
    ):
        """Initialize the HingeAuthError with a custom message.

        Args:
            message (str): Error message to display.

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
        super().__init__(
            f"Email 2FA required. Check your email ({email}) for the verification code."
        )
