import json
import tempfile
import unittest
from pathlib import Path

from dieselpdf.adapters.exchange import export_project_jsonl, import_project_jsonl
from dieselpdf.adapters.legacy import LegacyProjectImporter
from dieselpdf.domain.dataset import (
    ActorRole,
    LineGeometry,
    ProjectDraft,
    Provenance,
    RawEntityDraft,
)
from dieselpdf.persistence.sqlite import Database, DatasetRepository, ProjectBundle


class JsonlRoundTripTests(unittest.TestCase):
    def test_snapshot_round_trip_preserves_ids_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_db = Database(root / "source.db")
            self.addCleanup(source_db.close)
            source = DatasetRepository(source_db.open())
            project = source.create_project(ProjectDraft(name="House"), actor_id="aaron")
            with source.begin_revision(
                project.project_id,
                actor_id="importer",
                actor_role=ActorRole.SYSTEM_IMPORTER,
                reason="Add geometry",
            ) as revision:
                entity = revision.add_raw_entity(
                    RawEntityDraft(
                        project_id=project.project_id,
                        entity_type="line",
                        geometry=LineGeometry(start=(0, 0), end=(1200, 0)),
                        coordinate_system_id="project",
                        provenance=Provenance(source_method="test"),
                    )
                )
            export = export_project_jsonl(source, project.project_id, root / "project.diesel.jsonl")
            target_db = Database(root / "target.db")
            self.addCleanup(target_db.close)
            target = DatasetRepository(target_db.open())
            imported = import_project_jsonl(target, export.path)
            self.assertEqual(imported.record_count, export.record_count)
            self.assertEqual(target.get_raw_entity(entity.entity_id).entity_id, entity.entity_id)
            self.assertEqual(
                len(target.list_audit_events(project.project_id)),
                len(source.list_audit_events(project.project_id)),
            )


class LegacyImportTests(unittest.TestCase):
    def test_legacy_import_is_immutable_and_preserves_unknown_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "legacy.dieselpdf.json"
            source = {
                "scale_units_per_px": 2.0,
                "scale_unit": "mm",
                "pages": [
                    {
                        "width": 630,
                        "height": 891,
                        "entries": [
                            {
                                "id": 7,
                                "kind": "Markup",
                                "detail": "Test",
                                "layer": "0",
                                "objects": [
                                    {"type": "line", "coords": [60, 937, 160, 937]},
                                    {"type": "future-object", "coords": [70, 900], "custom": 1},
                                ],
                            }
                        ],
                    }
                ],
            }
            source_path.write_text(json.dumps(source), encoding="utf-8")
            original = source_path.read_bytes()
            project_draft = ProjectDraft(name="Legacy")
            bundle = ProjectBundle.create(root / "Legacy.diesel", project_draft)
            database = Database(bundle.database_path)
            self.addCleanup(database.close)
            repository = DatasetRepository(database.open())
            report = LegacyProjectImporter(repository).import_file(source_path, bundle=bundle)
            self.assertEqual(source_path.read_bytes(), original)
            self.assertTrue(report.complete_without_silent_loss)
            self.assertEqual(report.source_object_count, 2)
            self.assertEqual(report.imported_entity_count, 2)
            self.assertEqual(report.preserved_unsupported_count, 1)
            self.assertTrue(report.reconciliation_artifact.exists())
            entities = repository.list_raw_entities(report.project_id)
            self.assertEqual(len(entities), 2)
            line = next(value for value in entities if value.entity_type == "line")
            self.assertEqual(line.geometry.start, (0.0, 0.0))
            self.assertEqual(line.geometry.end, (200.0, 0.0))
            opaque = next(value for value in entities if value.entity_type.startswith("legacy_"))
            self.assertEqual(opaque.provenance.original_payload["object"]["custom"], 1)


if __name__ == "__main__":
    unittest.main()
