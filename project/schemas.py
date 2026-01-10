from datetime import date
from typing import Literal

from django.contrib.auth.models import User
from ninja import ModelSchema
from ninja.schema import Schema
from pydantic import Field

from project.models import EntryParagraph, JournalEntry, Label


class ChangePasswordSchema(Schema):
    current_password: str
    new_password: str


class RefreshTokenSchema(Schema):
    refresh_token: str


class UserSchemaOut(ModelSchema):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email")


class JournalFiltersSchema(Schema):
    search_query: str = Field(None, alias="search_query")
    is_bookmarked: bool = Field(None, alias="bookmarked")


class LabelSchemaIn(ModelSchema):
    class Meta:
        model = Label
        exclude = ["id", "created_at", "updated_at", "user"]


class LabelSchemaOut(ModelSchema):
    class Meta:
        model = Label
        fields = ["id", "created_at", "updated_at", "name", "description"]


class LabelSchemaOutSimple(ModelSchema):
    class Meta:
        model = Label
        fields = ["id", "name"]


class EntryParagraphSchemaIn(ModelSchema):
    class Meta:
        model = EntryParagraph
        fields = ["order", "content"]


class EntryParagraphSimpleSchemaOut(ModelSchema):
    class Meta:
        model = EntryParagraph
        fields = ["order", "content"]


class EntryParagraphSchemaOut(ModelSchema):
    labels: list[LabelSchemaOutSimple]

    class Meta:
        model = EntryParagraph
        fields = ["order", "content", "labels"]


class JournalEntrySchemaIn(ModelSchema):
    rating: Literal[1, 2, 3, 4, 5] | None
    paragraphs: list[EntryParagraphSchemaIn]
    json_content: dict | None

    class Meta:
        model = JournalEntry
        exclude = ["id", "created_at", "updated_at", "user"]


class AssignLabelSchemaIn(Schema):
    paragraph_orders: list[int]
    label_id: int


class RemoveLabelSchemaIn(Schema):
    paragraph_order: int
    label_id: int


class JournalEntrySchemaOut(ModelSchema):
    paragraphs: list[EntryParagraphSchemaOut]

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "created_at",
            "updated_at",
            "title",
            "date",
            "rating",
            "is_bookmarked",
            "json_content",
        ]


class EntrySimpleSchemaOut(ModelSchema):
    class Meta:
        model = JournalEntry
        fields = ["id", "created_at", "title", "date", "rating", "is_bookmarked"]


class EntrySearchSchemaOut(Schema):
    id: int
    title: str
    date: date
    rating: Literal[1, 2, 3, 4, 5] | None
    is_bookmarked: bool
    matching_paragraphs: list[EntryParagraphSimpleSchemaOut]


class LabelParagraphsCountSchemaOut(Schema):
    id: int
    name: str
    paragraphs_count: int


class EntryStatsOut(Schema):
    entries_this_month: int
    entries_this_year: int
    total_entries: int
    latest_entry: EntrySimpleSchemaOut | None
    total_labels_used: int
    most_used_label: LabelParagraphsCountSchemaOut | None
    labels_paragraphs_count: list[LabelParagraphsCountSchemaOut]
    bookmarked_entries: int


class PeriodTimelineSchemaOut(Schema):
    period: date
    count: int


class TimelineSchemaOut(Schema):
    week: list[PeriodTimelineSchemaOut]
    month: list[PeriodTimelineSchemaOut]
    year: list[PeriodTimelineSchemaOut]


class LabelParagraphSchemaOut(ModelSchema):
    entry: EntrySimpleSchemaOut

    class Meta:
        model = EntryParagraph
        fields = ["id", "content"]
