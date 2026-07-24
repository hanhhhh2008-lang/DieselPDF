import hashlib
import json
import os
import sqlite3
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from pydantic import ValidationError

from dieselpdf.adapters.legacy import LegacyProjectImporter
from dieselpdf.app import DatasetService
from dieselpdf.domain.dataset import (
    ActorIdentity,
    ActorRole,
    BoundingBox2D,
    EntityType,
    GeometryEntity,
    GeometryPayload,
    ProjectRecord,
    RelationshipRecord,
    RelationshipType,
    ReviewStatus,
    RevisionRecord,
    SemanticObject,
    SourceTrace,
    deterministic_stable_id,
    new_stable_id,
)
from dieselpdf.exchange import export_jsonl, import_jsonl
from dieselpdf.persistence import CURRENT_SCHEMA_VERSION, ProjectStore, StoreError
from dieselpdf.ui.tkinter import DatasetCanvasRenderer, DatasetTable, EngineeringDatasetWindow


ROOT = Path(__file__).resolve().parents[1]
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "legacy_phase3_project.dieselpdf.json"


def actor(role=ActorRole.ENGINEER, can_approve=True, name="Aaron Han"):
    return ActorIdentity(
        actor_id=deterministic_stable_id("actor", name, role.value),
        display_name=name,
        role=role,
        can_approve_engineering=can_approve,
    )


def make_store(directory, name="Phase 3 test"):
    project_id = new_stable_id("project")
    revision_id = new_stable_id("revision")
    project = ProjectRecord(project_id=project_id, name=name)
    revision = RevisionRecord(
        revision_id=revision_id,
        project_id=project_id,
        sequence=1,
        author=actor(),
        reason="Initial dataset revision",
    )
    path = Path(directory) / "project.diesel.db"
    return ProjectStore.create(path, project, revision)


def line_entity(store, *, status=ReviewStatus.WORKING, coordinates=None):
    coordinates = coordinates or [0, 0, 1000, 0]
    project = store.project()
    revision_id = store.current_revision_id()
    return GeometryEntity(
        entity_id=new_stable_id("entity"),
        project_id=project.project_id,
        revision_id=revision_id,
        version_sequence=1,
        review_status=status,
        entity_type=EntityType.LINE,
        geometry=GeometryPayload(
            entity_type=EntityType.LINE,
            coordinate_system_id="project",
            unit="mm",
            coordinates=coordinates,
        ),
        bounding_box=BoundingBox2D(
            min_x=min(coordinates[0], coordinates[2]),
            min_y=min(coordinates[1], coordinates[3]),
            max_x=max(coordinates[0], coordinates[2]),
            max_y=max(coordinates[1], coordinates[3]),
        ),
        coordinate_system_id="project",
        source=SourceTrace(
            source_method="engineer_created",
            evidence_summary="Created by a deterministic Phase 3 test",
        ),
    )


class IdentityAndSchemaTests(unittest.TestCase):
    def test_deterministic_ids_repeat_and_random_ids_do_not(self):
        first = deterministic_stable_id("entity", "source", 1)
        self.assertEqual(first, deterministic_stable_id("entity", "source", 1))
        self.assertNotEqual(first, deterministic_stable_id("entity", "source", 2))
        self.assertNotEqual(new_stable_id("entity"), new_stable_id("entity"))

    def test_geometry_schema_rejects_mismatched_type_and_shape(self):
        with self.assertRaises(ValidationError):
            GeometryPayload(
                entity_type=EntityType.LINE,
                coordinate_system_id="project",
                coordinates=[0, 0, 1],
            )

    def test_approval_authority_requires_engineer_role(self):
        with self.assertRaises(ValidationError):
            actor(ActorRole.AI, can_approve=True, name="AI assistant")


class SQLiteDatasetTests(unittest.TestCase):
    def test_migration_rtree_and_current_entity_query(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store)
                store.add_entity(entity)
                self.assertEqual(CURRENT_SCHEMA_VERSION, 1)
                self.assertEqual(store.integrity_check(), ("ok",))
                self.assertEqual(store.entities_in_bounds(400, -10, 600, 10), (entity,))
                self.assertEqual(store.entities_in_bounds(2000, 2000, 3000, 3000), ())

    def test_revisions_and_versions_are_append_only(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store)
                store.add_entity(entity)
                with self.assertRaises(sqlite3.IntegrityError):
                    store.connection.execute(
                        "UPDATE entity_versions SET review_status = 'engineer_approved'"
                    )
                store.connection.rollback()
                with self.assertRaises(sqlite3.IntegrityError):
                    store.connection.execute("DELETE FROM revisions")
                store.connection.rollback()

    def test_stable_identity_cannot_change_entity_type(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store)
                store.add_entity(entity)
                revision = RevisionRecord(
                    revision_id=new_stable_id("revision"),
                    project_id=store.project().project_id,
                    sequence=2,
                    parent_revision_id=store.current_revision_id(),
                    author=actor(),
                    reason="Attempt identity mutation",
                )
                store.add_revision(revision)
                changed = entity.model_copy(
                    update={
                        "revision_id": revision.revision_id,
                        "version_sequence": 2,
                        "entity_type": EntityType.RECTANGLE,
                        "geometry": GeometryPayload(
                            entity_type=EntityType.RECTANGLE,
                            coordinate_system_id="project",
                            coordinates=[0, 0, 1, 1],
                        ),
                        "content_hash": None,
                    }
                )
                changed = GeometryEntity.model_validate(changed.model_dump())
                with self.assertRaises(StoreError):
                    store.add_entity(changed)

    def test_semantic_objects_and_relationships_trace_to_raw_entities(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store)
                store.add_entity(entity)
                semantic = SemanticObject(
                    object_id=new_stable_id("object"),
                    project_id=store.project().project_id,
                    revision_id=store.current_revision_id(),
                    version_sequence=1,
                    review_status=ReviewStatus.AI_PROPOSED,
                    object_type="wall_candidate",
                    name_or_mark="W1",
                    source_entity_ids=[entity.entity_id],
                    properties={"model": "deterministic-test", "confidence_basis": "line geometry"},
                    confidence=0.75,
                )
                store.add_semantic_object(semantic)
                relationship = RelationshipRecord(
                    relationship_id=new_stable_id("relationship"),
                    project_id=store.project().project_id,
                    revision_id=store.current_revision_id(),
                    version_sequence=1,
                    review_status=ReviewStatus.ENGINEER_REVIEW_REQUIRED,
                    relationship_type=RelationshipType.DERIVED_FROM,
                    source_id=semantic.object_id,
                    target_id=entity.entity_id,
                )
                store.add_relationship(relationship)
                self.assertEqual(store.semantic_object(semantic.object_id), semantic)
                self.assertEqual(store.relationship(relationship.relationship_id), relationship)

    def test_source_document_and_page_links_must_resolve(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store).model_copy(
                    update={
                        "source": SourceTrace(
                            source_document_id=new_stable_id("document"),
                            source_page_id=new_stable_id("page"),
                            source_method="test_import",
                        ),
                        "content_hash": None,
                    }
                )
                entity = GeometryEntity.model_validate(entity.model_dump())
                with self.assertRaises(StoreError):
                    store.add_entity(entity)


class ApprovalGateTests(unittest.TestCase):
    def test_ai_cannot_approve_and_failure_creates_no_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store, status=ReviewStatus.AI_PROPOSED)
                store.add_entity(entity)
                service = DatasetService(store)
                ai = actor(ActorRole.AI, can_approve=False, name="AI proposal service")
                with self.assertRaises(ValueError):
                    service.review(
                        "entity",
                        entity.entity_id,
                        ReviewStatus.ENGINEER_APPROVED,
                        ai,
                        "AI attempted approval",
                    )
                self.assertEqual(len(store.revisions()), 1)
                self.assertEqual(store.entity(entity.entity_id).review_status, ReviewStatus.AI_PROPOSED)

    def test_authorised_engineer_approval_is_atomic_and_auditable(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store, status=ReviewStatus.ENGINEER_REVIEW_REQUIRED)
                store.add_entity(entity)
                updated = DatasetService(store).review(
                    "entity",
                    entity.entity_id,
                    ReviewStatus.ENGINEER_APPROVED,
                    actor(),
                    "Checked against the source dimension and calibration record",
                )
                self.assertEqual(updated.review_status, ReviewStatus.ENGINEER_APPROVED)
                self.assertEqual(updated.version_sequence, 2)
                self.assertEqual(len(store.revisions()), 2)
                decisions = store.review_decisions(entity.entity_id)
                self.assertEqual(len(decisions), 1)
                self.assertEqual(decisions[0].actor.display_name, "Aaron Han")
                self.assertIn("source dimension", decisions[0].comment)


class LegacyMigrationAndExchangeTests(unittest.TestCase):
    def test_legacy_import_is_complete_deterministic_and_non_destructive(self):
        source_bytes = LEGACY_FIXTURE.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.diesel.db"
            second_path = Path(directory) / "second.diesel.db"
            first_report = LegacyProjectImporter().import_file(str(LEGACY_FIXTURE), str(first_path))
            second_report = LegacyProjectImporter().import_file(str(LEGACY_FIXTURE), str(second_path))
            self.assertEqual(first_report.object_count, 5)
            self.assertEqual(first_report.entity_count, 5)
            self.assertTrue(first_report.original_preserved)
            self.assertEqual(hashlib.sha256(LEGACY_FIXTURE.read_bytes()).hexdigest(), source_hash)
            self.assertIn("project.legacy_project_note", first_report.unmapped_fields)
            with ProjectStore.open(first_path) as first, ProjectStore.open(second_path) as second:
                self.assertEqual(
                    [item.entity_id for item in first.entities()],
                    [item.entity_id for item in second.entities()],
                )
                self.assertTrue(
                    all(
                        item.review_status is ReviewStatus.ENGINEER_REVIEW_REQUIRED
                        for item in first.entities()
                    )
                )
                stored_payload = json.loads(first.import_runs()[0]["source_payload_json"])
                self.assertEqual(stored_payload, json.loads(source_bytes))
                self.assertEqual(len(first.legacy_id_map()), 5)
                self.assertEqual(len(first.documents()), 1)
                self.assertEqual(len(first.pages()), 1)
                for item in first.entities():
                    self.assertEqual(
                        first.page(item.source.source_page_id).document_id,
                        item.source.source_document_id,
                    )

    def test_jsonl_round_trip_preserves_versions_review_and_import_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source_db = Path(directory) / "source.diesel.db"
            exchange = Path(directory) / "project.diesel.jsonl"
            target_db = Path(directory) / "target.diesel.db"
            LegacyProjectImporter().import_file(str(LEGACY_FIXTURE), str(source_db))
            with ProjectStore.open(source_db) as source:
                first = source.entities()[0]
                DatasetService(source).review(
                    "entity",
                    first.entity_id,
                    ReviewStatus.ENGINEER_APPROVED,
                    actor(),
                    "Verified imported geometry",
                )
                export_jsonl(source, str(exchange))
                expected_entity_json = [item.model_dump(mode="json") for item in source.entities()]
                expected_revisions = [item.model_dump(mode="json") for item in source.revisions()]
            with import_jsonl(str(exchange), str(target_db)) as target:
                self.assertEqual(
                    [item.model_dump(mode="json") for item in target.entities()],
                    expected_entity_json,
                )
                self.assertEqual(
                    [item.model_dump(mode="json") for item in target.revisions()],
                    expected_revisions,
                )
                self.assertEqual(len(target.review_decisions()), 1)
                self.assertEqual(len(target.import_runs()), 1)
                self.assertEqual(len(target.legacy_id_map()), 5)
                self.assertEqual(len(target.documents()), 1)
                self.assertEqual(len(target.pages()), 1)
                self.assertEqual(target.integrity_check(), ("ok",))


class FakeCanvas:
    def __init__(self):
        self.next_item = 1
        self.items = {}

    def winfo_width(self):
        return 800

    def winfo_height(self):
        return 600

    def delete(self, tag):
        if tag == "diesel_dataset":
            self.items.clear()

    def _create(self, kind, coordinates, options):
        item = self.next_item
        self.next_item += 1
        self.items[item] = {"type": kind, "coordinates": coordinates, "options": dict(options)}
        return item

    def create_line(self, *coordinates, **options):
        return self._create("line", coordinates, options)

    def create_oval(self, *coordinates, **options):
        return self._create("oval", coordinates, options)

    def create_rectangle(self, *coordinates, **options):
        return self._create("rectangle", coordinates, options)

    def create_polygon(self, *coordinates, **options):
        return self._create("polygon", coordinates, options)

    def create_text(self, *coordinates, **options):
        return self._create("text", coordinates, options)

    def type(self, item):
        return self.items[item]["type"]

    def itemconfigure(self, item, **options):
        self.items[item]["options"].update(options)


class DatasetProjectionTests(unittest.TestCase):
    def test_canvas_is_rendered_from_current_database_entities_and_cross_selects(self):
        with tempfile.TemporaryDirectory() as directory:
            with make_store(directory) as store:
                entity = line_entity(store, status=ReviewStatus.ENGINEER_REVIEW_REQUIRED)
                store.add_entity(entity)
                canvas = FakeCanvas()
                renderer = DatasetCanvasRenderer(canvas)
                projection = renderer.render(store.entities())
                items = projection.items_for_entity(entity.entity_id)
                self.assertEqual(len(items), 1)
                self.assertEqual(projection.entity_for_item(items[0]), entity.entity_id)
                renderer.select(entity.entity_id)
                self.assertEqual(canvas.items[items[0]]["options"]["width"], 3)


class DatasetTableTests(unittest.TestCase):
    def test_dataset_table_lists_stable_records_and_reports_selection(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as directory:
                with make_store(directory) as store:
                    entity = line_entity(store)
                    store.add_entity(entity)
                    selected = []
                    table = DatasetTable(root, store, lambda kind, stable_id: selected.append((kind, stable_id)))
                    table.pack()
                    table.select_item(entity.entity_id)
                    root.update()
                    self.assertTrue(table.tree.exists(entity.entity_id))
                    self.assertEqual(table.selected_item(), ("entity", entity.entity_id))
                    self.assertIn(("entity", entity.entity_id), selected)
        finally:
            root.destroy()

    def test_engineering_dataset_window_loads_database_owned_records(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as directory:
                database = Path(directory) / "legacy.diesel.db"
                LegacyProjectImporter().import_file(str(LEGACY_FIXTURE), str(database))
                window = EngineeringDatasetWindow(root, str(database))
                window.withdraw()
                root.update()
                window.refresh()
                root.update()
                self.assertEqual(len(window.table.tree.get_children()), 5)
                self.assertEqual(len(window.projection), 5)
                first_entity_id = window.store.entities()[0].entity_id
                first_item_id = window.projection.items_for_entity(first_entity_id)[0]
                self.assertEqual(window.projection.entity_for_item(first_item_id), first_entity_id)
                window._close()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
