import unittest
from uuid import uuid4

from pydantic import ValidationError

from dieselpdf.domain.dataset import (
    ActorRole,
    BoundingBox2D,
    LineGeometry,
    ProjectDraft,
    Provenance,
    RawEntityDraft,
    RelationshipDraft,
    RelationshipType,
    ReviewStatus,
    validate_initial_status,
    validate_review_transition,
)


class SchemaTests(unittest.TestCase):
    def test_geometry_is_discriminated_and_bounded(self):
        project = ProjectDraft(name="House")
        entity = RawEntityDraft(
            project_id=project.project_id,
            entity_type="line",
            geometry=LineGeometry(start=(10, 20), end=(-5, 30)),
            coordinate_system_id="project",
            provenance=Provenance(source_method="manual"),
            review_status=ReviewStatus.PROPOSED,
        )
        self.assertEqual(
            entity.bounding_box,
            BoundingBox2D(min_x=-5, max_x=10, min_y=20, max_y=30),
        )
        restored = RawEntityDraft.model_validate(entity.model_dump(mode="json"))
        self.assertIsInstance(restored.geometry, LineGeometry)

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            RawEntityDraft(
                project_id=uuid4(),
                entity_type="line",
                geometry=LineGeometry(start=(0, 0), end=(1, 1)),
                coordinate_system_id="project",
                provenance=Provenance(source_method="manual"),
                confidence=1.1,
            )

    def test_relationship_cannot_target_itself(self):
        identity = uuid4()
        with self.assertRaises(ValidationError):
            RelationshipDraft(
                project_id=uuid4(),
                relationship_type=RelationshipType.CONNECTED_TO,
                source_id=identity,
                target_id=identity,
            )


class ReviewPolicyTests(unittest.TestCase):
    def test_role_and_transition_policy(self):
        validate_initial_status(ReviewStatus.PROPOSED, ActorRole.PROPOSER)
        validate_review_transition(
            ReviewStatus.PROPOSED,
            ReviewStatus.REVIEWED,
            ActorRole.REVIEWER,
        )
        validate_review_transition(
            ReviewStatus.REVIEWED,
            ReviewStatus.APPROVED,
            ActorRole.APPROVER,
        )
        validate_review_transition(
            ReviewStatus.APPROVED,
            ReviewStatus.SUPERSEDED,
            ActorRole.APPROVER,
        )

    def test_proposer_cannot_approve(self):
        with self.assertRaises(PermissionError):
            validate_review_transition(
                ReviewStatus.REVIEWED,
                ReviewStatus.APPROVED,
                ActorRole.PROPOSER,
            )

    def test_approved_cannot_return_to_reviewed(self):
        with self.assertRaises(ValueError):
            validate_review_transition(
                ReviewStatus.APPROVED,
                ReviewStatus.REVIEWED,
                ActorRole.ADMIN,
            )


if __name__ == "__main__":
    unittest.main()
