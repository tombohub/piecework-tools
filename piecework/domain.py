"""
Domain entities and value objects
"""
from enum import Enum
from dataclasses import dataclass
import datetime as dt

PRICE_PER_SQUARE_FOOT = 0.352

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
    end: "dt.datetime | None"
    duration: dt.timedelta


@dataclass
class DailyDuration:
    date: dt.date
    activity_name: str
    duration: dt.timedelta


