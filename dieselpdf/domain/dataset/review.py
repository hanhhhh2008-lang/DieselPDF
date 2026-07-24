from __future__ import annotations

from typing import Dict, FrozenSet

from .models import ActorRole, ReviewStatus

_ALLOWED_TRANSITIONS: Dict[ReviewStatus, FrozenSet[ReviewStatus]] = {
    ReviewStatus.UNREVIEWED: frozenset({ReviewStatus.REVIEWED, ReviewStatus.REJECTED}),
    ReviewStatus.PROPOSED: frozenset({ReviewStatus.REVIEWED, ReviewStatus.REJECTED}),
    ReviewStatus.REVIEWED: frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED}),
    ReviewStatus.APPROVED: frozenset({ReviewStatus.SUPERSEDED}),
    ReviewStatus.REJECTED: frozenset(),
    ReviewStatus.SUPERSEDED: frozenset(),
}

_ROLE_TARGETS: Dict[ActorRole, FrozenSet[ReviewStatus]] = {
    ActorRole.SYSTEM_IMPORTER: frozenset({ReviewStatus.UNREVIEWED}),
    ActorRole.PROPOSER: frozenset({ReviewStatus.PROPOSED}),
    ActorRole.REVIEWER: frozenset({ReviewStatus.REVIEWED, ReviewStatus.REJECTED}),
    ActorRole.APPROVER: frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.SUPERSEDED}),
    ActorRole.ADMIN: frozenset(ReviewStatus),
}


def validate_initial_status(status: ReviewStatus, role: ActorRole) -> None:
    if role is ActorRole.ADMIN:
        return
    if status not in _ROLE_TARGETS[role]:
        raise PermissionError(f"role {role.value} cannot create status {status.value}")


def validate_review_transition(current: ReviewStatus, target: ReviewStatus, role: ActorRole) -> None:
    if current == target:
        return
    if role is not ActorRole.ADMIN and target not in _ROLE_TARGETS[role]:
        raise PermissionError(f"role {role.value} cannot set status {target.value}")
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid review transition {current.value} -> {target.value}")
