"""
Creating contexts for views
"""
from dataclasses import dataclass, asdict
from . import db
from .domain import CurrentAction


@dataclass
class IndexContext:
    actions: list[str]
    current_action: CurrentAction | None
    active_units: list[int]


def index_context() -> dict:
    actions = db.list_actions()
    current_action = db.current_action()
    active_units = db.active_units()
    index_context = IndexContext(
        actions=actions, current_action=current_action, active_units=active_units
    )
    return asdict(index_context)
