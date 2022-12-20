"""
Domain entities and value objects
"""
from enum import Enum
from dataclasses import dataclass
import datetime as dt


class SheetType(Enum):
    REGULAR = "regular"
    BLUE = "blue"
    DENS_GLASS = "dens glass"


class SheetLength(Enum):
    EIGHT_FT = 8
    NINE_FT = 9
    TEN_FT = 10
    TWELVE_FT = 12


@dataclass
class Sheet:
    sheet_type = SheetType
    length: SheetLength


@dataclass
class CurrentActivity:
    name: str
    start: str


@dataclass
class Unit:
    number: int
    washrooms_count: int
    closets_count: int
    rooms_count: int
    windows_count: int
    bulkheads_count: int
    is_finished: bool


@dataclass
class Activity:
    name: str
    description: str


@dataclass
class ActivityTime:
    activity: Activity
    date: dt.date
    start: dt.datetime
    end: dt.datetime | None
    duration: dt.timedelta


class Duration:
    def __init__(self, duration: dt.timedelta) -> None:
        self.duration = duration

    def __str__(self) -> str:
        """
        To return string as 00:00:00 instead of 00:00:00.00000
        """
        return str(self.duration).split(".")[0]


@dataclass
class DailyActivityDuration:
    date: dt.date
    duration: Duration
