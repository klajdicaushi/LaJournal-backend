from datetime import date
from typing import TypedDict, Optional, Literal


class EntryParagraphDataIn(TypedDict):
    order: int
    content: str


class EntryDataIn(TypedDict):
    title: str
    date: date
    rating: Optional[Literal[1, 2, 3, 4, 5]]
    paragraphs: Optional[list[EntryParagraphDataIn]]
