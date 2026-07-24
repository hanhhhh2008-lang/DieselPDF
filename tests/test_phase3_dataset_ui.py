import tempfile
import unittest
from pathlib import Path

from dieselpdf.app import DatasetFilter, DatasetService
from dieselpdf.domain.dataset import (
    ActorRole,
    LineGeometry,
    ProjectDraft,
    Provenance,
    RawEntityDraft,
    RecordType,
    SemanticObjectDraft,
)
from dieselpdf.domain.geometry import Point2D
from dieselpdf.persistence.sqlite import Database, DatasetRepository
from dieselpdf.ui.tkinter import (
    CanvasProjectionMap,
    DatasetCanvasRenderer,
    DatasetTreeController,
)


class FakeCanvas:
    def __init__(self):
        self.next_id = 1
        self.created = {}
        self.deleted = []

    def _create(self, kind, coords, kwargs):
        item_id = self.next_id
        self.next_id += 1
        self.created[item_id] = (kind, tuple(coords), dict(kwargs))
        return item_id

    def create_line(self, *coords, **kwargs): return self._create("line", coords, kwargs)
    def create_rectangle(self, *coords, **kwargs): return self._create("rectangle", coords, kwargs)
    def create_oval(self, *coords, **kwargs): return self._create("oval", coords, kwargs)
    def create_polygon(self, *coords, **kwargs): return self._create("polygon", coords, kwargs)
    def create_text(self, *coords, **kwargs): return self._create("text", coords, kwargs)
    def delete(self, item_id): self.deleted.append(item_id); self.created.pop(item_id, None)


class FakeTree:
    def __init__(self):
        self.rows = {}
        self._selection = ()

    def get_children(self):
        return tuple(self.rows)

    def delete(self, item):
        self.rows.pop(item, None)

    def insert(self, parent, position, *, iid, values):
        self.rows[iid] = tuple(values)

    def selection(self):
        return self._selection

    def selection_set(self, values):
        self._selection = tuple(values)


class DatasetUiTests(unittest.TestCase):
    def test_database_owned_render_and_cross_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "project.db")
            self.addCleanup(database.close)
            repository = DatasetRepository(database.open())
            project = repository.create_project(ProjectDraft(name="House"), actor_id="aaron")
            with repository.begin_revision(
                project.project_id,
                actor_id="importer",
                actor_role=ActorRole.SYSTEM_IMPORTER,
                reason="Import",
            ) as revision:
                entity = revision.add_raw_entity(
                    RawEntityDraft(
                        project_id=project.project_id,
                        entity_type="line",
                        geometry=LineGeometry(start=(0, 0), end=(100, 0)),
                        coordinate_system_id="project",
                        provenance=Provenance(source_method="test"),
                        properties={"name_or_mark": "L1", "style": {"fill": "red"}},
                    )
                )
            canvas = FakeCanvas()
            projection = CanvasProjectionMap()
            renderer = DatasetCanvasRenderer(
                repository,
                canvas,
                projection,
                project_to_canvas=lambda point: Point2D(point.x + 10, 200 - point.y, "px", "canvas"),
            )
            item_ids = renderer.render_entity(entity.entity_id)
            self.assertEqual(len(item_ids), 1)
            self.assertEqual(canvas.created[item_ids[0]][0], "line")
            self.assertEqual(canvas.created[item_ids[0]][1], (10.0, 200.0, 110.0, 200.0))
            service = DatasetService(repository, project.project_id, projection)
            rows = service.rows(DatasetFilter(text="L1"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].record_type, RecordType.RAW_ENTITY)
            self.assertEqual(service.canvas_items_for_dataset_ids([entity.entity_id]), item_ids)
            self.assertEqual(service.dataset_ids_for_canvas_items(item_ids), (entity.entity_id,))
            renderer.clear_entity(entity.entity_id)
            self.assertEqual(service.canvas_items_for_dataset_ids([entity.entity_id]), ())

    def test_semantic_cross_selection_and_treeview_stable_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "project.db")
            self.addCleanup(database.close)
            repository = DatasetRepository(database.open())
            project = repository.create_project(ProjectDraft(name="House"), actor_id="aaron")
            with repository.begin_revision(
                project.project_id,
                actor_id="importer",
                actor_role=ActorRole.SYSTEM_IMPORTER,
                reason="Import",
            ) as revision:
                entity = revision.add_raw_entity(
                    RawEntityDraft(
                        project_id=project.project_id,
                        entity_type="line",
                        geometry=LineGeometry(start=(0, 0), end=(100, 0)),
                        coordinate_system_id="project",
                        provenance=Provenance(source_method="test"),
                    )
                )
            with repository.begin_revision(
                project.project_id,
                actor_id="designer",
                actor_role=ActorRole.PROPOSER,
                reason="Classify wall",
            ) as revision:
                semantic = revision.add_semantic_object(
                    SemanticObjectDraft(
                        project_id=project.project_id,
                        object_type="wall",
                        name_or_mark="W1",
                        source_entity_ids=(entity.entity_id,),
                        bounding_box=entity.bounding_box,
                    )
                )

            projection = CanvasProjectionMap()
            projection.bind(str(entity.entity_id), [101])
            service = DatasetService(repository, project.project_id, projection)
            self.assertEqual(
                service.canvas_items_for_dataset_ids([semantic.object_id]),
                (101,),
            )
            self.assertEqual(
                service.dataset_ids_for_canvas_items([101]),
                tuple(sorted((entity.entity_id, semantic.object_id), key=str)),
            )

            tree = FakeTree()
            controller = DatasetTreeController(tree)
            rows = service.rows()
            controller.refresh(rows)
            self.assertIn(str(entity.entity_id), tree.rows)
            self.assertIn(str(semantic.object_id), tree.rows)
            controller.select_records([semantic.object_id])
            self.assertEqual(controller.selected_record_ids(), (semantic.object_id,))


if __name__ == "__main__":
    unittest.main()
