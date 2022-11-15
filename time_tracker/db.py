"""
Database fetching and saving operations.
To avoid using models in views
"""

from .models import ActionTime, Action, Unit
from .domain import CurrentAction


def list_actions() -> list[str]:
    """
    get list of all available actions

    Returns
    -------
    list[str]
        available actions
    """
    actions = Action.objects.all()
    return [action.name for action in actions]


def current_action() -> CurrentAction | None:
    """
    Get current action name if exists. Otherwise None

    Returns
    -------
    str | None
        current action name
    """
    exists_current_action = ActionTime.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action_object = ActionTime.objects.get(is_current=True)
        current_action = CurrentAction(
            name=current_action_object.action.name, start=current_action_object.start
        )
    else:
        current_action = None

    return current_action


def active_units() -> list[int]:
    active_units_obj = Unit.objects.filter(is_finished=False)
    active_units_numbers = [unit.number for unit in active_units_obj]
    return active_units_numbers
