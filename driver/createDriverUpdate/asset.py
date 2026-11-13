"""The engine's front door: everything fed to the engine arrives as one Asset, a whole document or any part of one."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Unit:
    """A piece of text and its place in one file of the document."""
    text: str
    file: str
    start: int
    end: int

    def __post_init__(self):
        if not (isinstance(self.text, str) and self.text): raise ValueError('unit has no text')
        if not (isinstance(self.file, str) and self.file): raise ValueError('unit has no file')
        if not (type(self.start) is int and type(self.end) is int and 0 <= self.start < self.end):
            raise ValueError('unit has no span')


@dataclass(frozen=True)
class Asset:
    source_id: str           # the document's id in the database
    source_type: str         # its kind: 8-K, 10-Q, transcript, news
    date: datetime           # when it became public
    units: tuple[Unit, ...]  # in reading order

    def __post_init__(self):
        object.__setattr__(self, 'units', tuple(self.units or ()))  # a fixed copy: it cannot change or run out later
        if not (isinstance(self.source_id, str) and self.source_id): raise ValueError('asset has no source_id')
        if not (isinstance(self.source_type, str) and self.source_type): raise ValueError('asset has no source_type')
        if not (isinstance(self.date, datetime) and self.date.utcoffset() is not None):
            raise ValueError('asset has no date with a time zone')
        if not (self.units and all(isinstance(unit, Unit) for unit in self.units)):
            raise ValueError('asset has no units')
