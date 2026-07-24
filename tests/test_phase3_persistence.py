import sqlite3
import tempfile
import unittest
from pathlib import Path

from dieselpdf.domain.dataset import (
    ActorRole,
    BoundingBox2D,
    LineGeometry,
    ProjectDraft,
    Provenance,
    RawEntityDraft,
    RecordType,
    ReviewStatus,
    SemanticObjectDraft,
)
from dieselpdf.persistence.sqlite import (
    Database,
    DatasetRepository,
    MigrationManager,
    ProjectBundle,
    UnsupportedSchemaVersion,
)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.database = Database(self.path / "project.db")
        self.connection = self.database.open()
        self.repository = DatasetRepository(self.connection)
        self.project = self.repository.create_project(
            ProjectDraft(name="House"), actor_id="aaron"
        )

    def tearDown(self):
        self.database.close()
        self.temp.cleanup()

    def test_migrations_and_rtree_are_created(self):
        version = MigrationManager.current_version(self.connection)
        self.assertEqual(version, 2)
        names = {
            row["name"]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        self.assertIn("raw_entity_rtree", names)
        self.assertIn("semantic_object_rtree", names)
        self.assertIn("audit_events", names)

    def test_revision_commit_rtree_query_and_audit(self):
        with self.repository.begin_revision(
            self.project.project_id,
            actor_id="importer",
            actor_role=ActorRole.SYSTEM_IMPORTER,
            reason="Import source geometry",
        ) as revision:
            entity = revision.add_raw_entity(
                RawEntityDraft(
                    project_id=self.project.project_id,
                    entity_type="line",
                    geometry=LineGeometry(start=(0, 0), end=(1000, 0)),
                    coordinate_system_id="project",
                    provenance=Provenance(source_method="test"),
                )
            )
        found = self.repository.query_raw_entities(
            self.project.project_id,
            BoundingBox2D(min_x=400, max_x=600, min_y=-10, max_y=10),
        )
        self.assertEqual(tuple(value.entity_id for value in found), (entity.entity_id,))
        current = self.repository.get_project(self.project.project_id)
        self.assertEqual(current.current_revision_id, revision.revision_id)
        actions = [event.action for event in self.repository.list_audit_events(self.project.project_id)]
        self.assertIn("create", actions)

    def test_failed_revision_rolls_back_all_records(self):
        with self.assertRaises(RuntimeError):
            with self.repository.begin_revision(
                self.project.project_id,
                actor_id="importer",
                actor_role=ActorRole.SYSTEM_IMPORTER,
                reason="Rollback test",
            ) as revision:
                revision.add_raw_entity(
                    RawEntityDraft(
                        project_id=self.project.project_id,
                        entity_type="line",
                        geometry=LineGeometry(start=(0, 0), end=(1, 1)),
                        coordinate_system_id="project",
                        provenance=Provenance(source_method="test"),
                    )
                )
                raise RuntimeError("stop")
        self.assertEqual(self.repository.list_raw_entities(self.project.project_id), ())
        reasons = [value.reason for value in self.repository.list_revisions(self.project.project_id)]
        self.assertNotIn("Rollback test", reasons)

    def test_newer_schema_is_not_silently_modified(self):
        self.database.close()
        connection = sqlite3.connect(self.path / "future.db")
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT, checksum TEXT, applied_at TEXT)"
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES (999, 'future', 'future', 'now')"
        )
        connection.commit()
        connection.close()
        future = Database(self.path / "future.db")
        with self.assertRaises(UnsupportedSchemaVersion):
            future.open()

    def test_semantic_links_and_review_transition(self):
        with self.repository.begin_revision(
            self.project.project_id,
            actor_id="proposer",
            actor_role=ActorRole.PROPOSER,
            reason="Create proposal",
        ) as revision:
            entity = revision.add_raw_entity(
                RawEntityDraft(
                    project_id=self.project.project_id,
                    entity_type="line",
                    geometry=LineGeometry(start=(0, 0), end=(100, 0)),
                    coordinate_system_id="project",
                    provenance=Provenance(source_method="engineer"),
                    review_status=ReviewStatus.PROPOSED,
                )
            )
            wall = revision.add_semantic_object(
                SemanticObjectDraft(
                    project_id=self.project.project_id,
                    object_type="wall",
                    name_or_mark="W1",
                    source_entity_ids=(entity.entity_id,),
                )
            )
        self.assertEqual(len(self.repository.list_links(self.project.project_id)), 1)
        with self.repository.begin_revision(
            self.project.project_id,
            actor_id="reviewer",
            actor_role=ActorRole.REVIEWER,
            reason="Review wall proposal",
        ) as revision:
            revision.update_review_status(
                RecordType.SEMANTIC_OBJECT,
                wall.object_id,
                ReviewStatus.REVIEWED,
            )
        self.assertEqual(
            self.repository.get_semantic_object(wall.object_id).review_status,
            ReviewStatus.REVIEWED,
        )


class BundleTests(unittest.TestCase):
    def test_bundle_structure_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            project = ProjectDraft(name="Bundle")
            bundle = ProjectBundle.create(Path(directory) / "Bundle.diesel", project)
            self.assertTrue(bundle.database_path.exists())
            self.assertTrue(bundle.manifest_path.exists())
            self.assertTrue(bundle.sources_path.is_dir())
            self.assertTrue(bundle.artifacts_path.is_dir())
            self.assertTrue(bundle.exports_path.is_dir())
            reopened = ProjectBundle.open(bundle.root)
            self.assertEqual(reopened.database_path, bundle.database_path)
            database = Database(bundle.database_path)
            self.addCleanup(database.close)
            stored = DatasetRepository(database.open()).get_project(project.project_id)
            self.assertEqual(stored.name, "Bundle")


if __name__ == "__main__":
    unittest.main()
