from typing import Literal, Optional

from django.contrib.auth.models import User
from ninja import ModelSchema
from ninja.schema import Schema
from pydantic import Field

from project.models import JournalEntry, Label, EntryParagraph


class ChangePasswordSchema(Schema):
    current_password: str
    new_password: str


class RefreshTokenSchema(Schema):
    refresh_token: str


class UserSchemaOut(ModelSchema):
    class Config:
        model = User
        model_fields = ("id", "username", "first_name", "last_name", "email")


class JournalFiltersSchema(Schema):
    paragraphs__labels__id__in: list[int] = Field(None, alias="labels")


class LabelSchemaIn(ModelSchema):
    class Config:
        model = Label
        model_exclude = ['id', 'created_at', 'updated_at', 'user']


class LabelSchemaOut(ModelSchema):
    class Config:
        model = Label
        model_fields = ['id', 'created_at', 'updated_at', 'name', 'description']


class LabelSchemaOutSimple(ModelSchema):
    class Config:
        model = Label
        model_fields = ['id', 'name']


class EntryParagraphSchemaIn(ModelSchema):
    class Config:
        model = EntryParagraph
        model_fields = ['order', 'content']


class EntryParagraphSchemaOut(ModelSchema):
    labels: list[LabelSchemaOutSimple]

    class Config:
        model = EntryParagraph
        model_fields = ['order', 'content', 'labels']


class JournalEntrySchemaIn(ModelSchema):
    rating: Optional[Literal[1, 2, 3, 4, 5]]
    paragraphs: list[EntryParagraphSchemaIn]

    class Config:
        model = JournalEntry
        model_exclude = ['id', 'created_at', 'updated_at', 'user']
        

class AssignLabelSchemaIn(Schema):
    paragraph_orders: list[int]
    label_id: int


class RemoveLabelSchemaIn(Schema):
    paragraph_order: int
    label_id: int


class JournalEntrySchemaOut(ModelSchema):
    paragraphs: list[EntryParagraphSchemaOut]

    class Config:
        model = JournalEntry
        model_fields = ['id', 'created_at', 'updated_at', 'title', 'date', 'rating', 'is_bookmarked']


class EntrySimpleSchemaOut(ModelSchema):
    class Config:
        model = JournalEntry
        model_fields = ['id', 'created_at', 'title', 'date', 'rating']


class LabelParagraphsCountSchemaOut(Schema):
    id: int
    name: str
    paragraphs_count: int


class EntryStatsOut(Schema):
    entries_this_month: int
    entries_this_year: int
    total_entries: int
    latest_entry: Optional[EntrySimpleSchemaOut]
    total_labels_used: int
    most_used_label: Optional[LabelParagraphsCountSchemaOut]
    labels_paragraphs_count: list[LabelParagraphsCountSchemaOut]


class LabelParagraphSchemaOut(ModelSchema):
    entry: EntrySimpleSchemaOut

    class Config:
        model = EntryParagraph
        model_fields = ['id', 'content']
