from __future__ import annotations

from dieselpdf.domain.dataset import (
    ActorIdentity,
    ReviewDecision,
    ReviewStatus,
    RevisionRecord,
    new_stable_id,
)
from dieselpdf.persistence import ProjectStore


class DatasetService:
    """Application commands over the engineering dataset transaction boundary."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def review(
        self,
        item_kind: str,
        item_id: str,
        decision: ReviewStatus,
        actor: ActorIdentity,
        comment: str,
    ):
        revisions = self.store.revisions()
        current_revision = revisions[-1]
        current_item = self.store.item(item_kind, item_id)
        revision_id = new_stable_id("revision")
        revision = RevisionRecord(
            revision_id=revision_id,
            project_id=current_revision.project_id,
            sequence=current_revision.sequence + 1,
            parent_revision_id=current_revision.revision_id,
            author=actor,
            reason=f"Review {item_kind} {item_id}: {decision.value}",
        )
        review_decision = ReviewDecision(
            decision_id=new_stable_id("decision"),
            project_id=current_revision.project_id,
            revision_id=revision_id,
            item_kind=item_kind,
            item_id=item_id,
            previous_status=current_item.review_status,
            decision=decision,
            actor=actor,
            comment=comment,
        )
        return self.store.apply_review_revision(revision, review_decision)
