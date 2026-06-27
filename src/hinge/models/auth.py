"""Authentication token schemas for Hinge and Sendbird."""

from datetime import datetime

from hinge.models.base import BaseHingeModel


class HingeAuthToken(BaseHingeModel):
    """Schema for the main Hinge Bearer token."""

    identity_id: str
    token: str
    expires: datetime


class SendbirdAuthToken(BaseHingeModel):
    """Schema for the Sendbird Bearer token."""

    token: str
    expires: datetime
