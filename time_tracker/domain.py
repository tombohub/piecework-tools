"""
Domain entities and value objects
"""
from enum import Enum
from dataclasses import dataclass


@dataclass
class CurrentAction:
    name: str
    start: str


class Activity(Enum):
    BOARD = "board"
    BREAK = "break"
    TRAVEL = "travel"
    PACK = "pack"
    TRANSFER = "transfer"
    WASHROOM = "washroom"
    TOOLS = "tools"
    ORGANIZATION = "organization"
    MATERIAL = "material"
