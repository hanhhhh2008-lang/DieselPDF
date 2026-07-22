from __future__ import annotations

from typing import Dict, FrozenSet

from .models import ActorIdentity, ActorRole, ReviewStatus


class ReviewTransitionError(ValueError):
    pass


_TRANSITIONS: Dict[ReviewStatus, FrozenSet[ReviewStatus]] = {
    ReviewStatus.WORKING: frozenset(
        {
            ReviewStatus.AI_PROPOSED,
            ReviewStatus.ENGINEER_REVIEW_REQUIRED,
            ReviewStatus.REJECTED,
            ReviewStatus.SUPERSEDED,
        }
    ),
    ReviewStatus.AI_PROPOSED: frozenset(
        {
            ReviewStatus.ENGINEER_REVIEW_REQUIRED,
            ReviewStatus.ENGINEER_APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.SUPERSEDED,
        }
    ),
    ReviewStatus.ENGINEER_REVIEW_REQUIRED: frozenset(
        {
            ReviewStatus.ENGINEER_APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.SUPERSEDED,
        }
    ),
    ReviewStatus.ENGINEER_APPROVED: frozenset({ReviewStatus.SUPERSEDED}),
    ReviewStatus.REJECTED: frozenset({ReviewStatus.SUPERSEDED}),
    ReviewStatus.SUPERSEDED: frozenset(),
}


def require_review_transition(
    current: ReviewStatus,
    target: ReviewStatus,
    actor: ActorIdentity,
) -> None:
    """Enforce the human approval boundary before a decision is persisted."""
    current_status = ReviewStatus(current)
    target_status = ReviewStatus(target)
    if target_status not in _TRANSITIONS[current_status]:
        raise ReviewTransitionError(
            f"review transition {current_status.value!r} -> {target_status.value!r} is not allowed"
        )
    if target_status is ReviewStatus.ENGINEER_APPROVED:
        if actor.role is not ActorRole.ENGINEER or not actor.can_approve_engineering:
            raise ReviewTransitionError(
                "only an authorised engineer may create an engineer-approved decision"
            )
    if actor.role in {ActorRole.AI, ActorRole.SYSTEM} and target_status in {
        ReviewStatus.ENGINEER_APPROVED,
        ReviewStatus.REJECTED,
    }:
        raise ReviewTransitionError("AI and system actors cannot make human review decisions")
