from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Optional, Set, Tuple

from dieselpdf.domain.common import non_empty_identifier


class CanvasProjectionMap:
    """Ephemeral mapping between stable domain IDs and Tk Canvas item IDs."""
    def __init__(self)->None:
        self._entity_to_items:Dict[str,Set[int]]=defaultdict(set); self._item_to_entity:Dict[int,str]={}
    def bind(self,entity_id:str,canvas_item_ids:Iterable[int])->None:
        entity=non_empty_identifier(entity_id,"entity_id"); items=tuple(canvas_item_ids)
        if not items: raise ValueError("at least one Canvas item ID is required")
        for item in items:
            if isinstance(item,bool) or not isinstance(item,int) or item<=0: raise ValueError("Canvas item IDs must be positive integers")
            previous=self._item_to_entity.get(item)
            if previous is not None and previous!=entity:
                self._entity_to_items[previous].discard(item)
                if not self._entity_to_items[previous]: del self._entity_to_items[previous]
            self._item_to_entity[item]=entity; self._entity_to_items[entity].add(item)
    def entity_for_item(self,canvas_item_id:int)->Optional[str]: return self._item_to_entity.get(canvas_item_id)
    def items_for_entity(self,entity_id:str)->Tuple[int,...]: return tuple(sorted(self._entity_to_items.get(non_empty_identifier(entity_id,"entity_id"),())))
    def entities_for_items(self,canvas_item_ids:Iterable[int])->Tuple[str,...]: return tuple(sorted({self._item_to_entity[item] for item in canvas_item_ids if item in self._item_to_entity}))
    def unbind_item(self,canvas_item_id:int)->None:
        entity=self._item_to_entity.pop(canvas_item_id,None)
        if entity is None:return
        self._entity_to_items[entity].discard(canvas_item_id)
        if not self._entity_to_items[entity]:del self._entity_to_items[entity]
    def unbind_entity(self,entity_id:str)->None:
        entity=non_empty_identifier(entity_id,"entity_id")
        for item in tuple(self._entity_to_items.pop(entity,())): self._item_to_entity.pop(item,None)
    def clear(self)->None: self._entity_to_items.clear(); self._item_to_entity.clear()
    def __len__(self)->int:return len(self._item_to_entity)
