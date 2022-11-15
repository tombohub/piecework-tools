"""
Domain entities and value objects
"""

from dataclasses import dataclass


@dataclass
class CurrentAction:
    name: str
    start: str
