"""Resource namespaces composed onto :class:`~hinge.client.HingeClient`."""

from hinge.client.resources.chat import ChatResource
from hinge.client.resources.content import ContentResource
from hinge.client.resources.profile import ProfileResource
from hinge.client.resources.prompts import PromptsResource
from hinge.client.resources.rating import RatingResource
from hinge.client.resources.recommendations import RecommendationsResource

__all__ = [
    "ChatResource",
    "ContentResource",
    "ProfileResource",
    "PromptsResource",
    "RatingResource",
    "RecommendationsResource",
]
