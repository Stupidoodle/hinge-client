"""Hinge rule-based profile scorer."""

from hinge.domain.models.profile import HingeProfile
from hinge.domain.ports.scorer_port import HingeScorerPort


class HingeRuleBasedScorer(HingeScorerPort):
    """Simple rule-based scorer for Hinge profiles."""

    async def score(self, profile: HingeProfile) -> tuple[float, str]:
        """Score a profile based on basic rules.

        Returns:
            Tuple of (score 0-100, reasoning string).

        """
        score = 50.0
        reasons = []

        # Photo count
        photo_count = len(profile.photo_urls)
        if photo_count >= 4:
            score += 10
            reasons.append(f"{photo_count} photos")
        elif photo_count <= 1:
            score -= 10
            reasons.append("few photos")

        # Prompts
        if profile.prompts:
            score += 5 * min(len(profile.prompts), 3)
            reasons.append(f"{len(profile.prompts)} prompts")

        # Selfie verified
        if profile.selfie_verified:
            score += 5
            reasons.append("verified")

        # Bio completeness
        if profile.job_title:
            score += 5
        if profile.hometown:
            score += 3
        if profile.height:
            score += 2

        score = max(0.0, min(100.0, score))
        reasoning = ", ".join(reasons) if reasons else "base score"
        return score, reasoning
