from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Query
from ninja_extra import NinjaExtraAPI, api_controller, route
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController

from project.models import Label
from project.schemas import AssignLabelSchemaIn, JournalEntrySchemaIn, JournalEntrySchemaOut, LabelSchemaOut, \
    LabelSchemaIn, RemoveLabelSchemaIn, EntryStatsOut, JournalFiltersSchema, LabelParagraphSchemaOut, \
    ChangePasswordSchema
from project.services import EntryService, UserService

api = NinjaExtraAPI(title="LaJournal API")
api.register_controllers(NinjaJWTDefaultController)


def _get_user(request) -> User:
    return request.auth


def _get_entry(request, entry_id: int):
    return get_object_or_404(_get_user(request).journal_entries.all(), id=entry_id)


def _get_label(request, label_id: int):
    return get_object_or_404(_get_user(request).labels.all(), id=label_id)


@api.put("/change-password", tags=['auth'])
def change_password(request, payload: ChangePasswordSchema):
    user = _get_user(request)
    UserService.change_password(
        user=user,
        new_password=payload.dict().get('new_password')
    )
    return {"success": True}


@api_controller("/entries", tags=["entries"], auth=JWTAuth())
class EntriesController:
    @route.get("/stats", response=EntryStatsOut)
    def get_stats(self):
        return EntryService.get_stats(user=_get_user(self.context.request))

    @route.get("", response=list[JournalEntrySchemaOut])
    def get_journal_entries(self, filters: JournalFiltersSchema = Query(...)):
        entries = _get_user(self.context.request).journal_entries.all().order_by('-date', '-id')
        for key, value in filters.dict().items():
            if value is not None:
                entries = entries.filter(**{key: value})
        return entries.distinct()

    @route.get("/{entry_id}", response=JournalEntrySchemaOut)
    def get_journal_entry(self, entry_id: int):
        return _get_entry(self.context.request, entry_id)

    @route.post("", response=JournalEntrySchemaOut)
    def create_journal_entry(self, payload: JournalEntrySchemaIn):
        entry_data = payload.dict()
        return EntryService.create_entry(
            user=_get_user(self.context.request),
            entry_data=entry_data
        )

    @route.put("/{entry_id}", response=JournalEntrySchemaOut)
    def update_entry(self, entry_id: int, payload: JournalEntrySchemaIn):
        entry = _get_entry(self.context.request, entry_id)
        new_entry_data = payload.dict()
        return EntryService.update_entry(entry, new_entry_data)

    @route.post("/{entry_id}/assign_label", response=JournalEntrySchemaOut)
    def assign_label(self, entry_id: int, payload: AssignLabelSchemaIn):
        entry = _get_entry(self.context.request, entry_id)
        data = payload.dict()

        paragraphs = entry.paragraphs.filter(order__in=data.get('paragraph_orders'))
        if paragraphs.count() != len(data.get('paragraph_orders')):
            raise Http404("One or more paragraphs do not exist!")

        label = _get_label(self.context.request, data.get('label_id'))

        EntryService.assign_label_to_paragraphs(
            paragraphs=paragraphs,
            label=label
        )
        return entry

    @route.post("/{entry_id}/remove_label", response=JournalEntrySchemaOut)
    def remove_label(self, entry_id: int, payload: RemoveLabelSchemaIn):
        entry = _get_entry(self.context.request, entry_id)
        data = payload.dict()

        paragraph = get_object_or_404(entry.paragraphs, order=data.get('paragraph_order'))
        label = _get_label(self.context.request, data.get('label_id'))

        EntryService.remove_label_from_paragraph(
            paragraph=paragraph,
            label=label
        )
        return entry

    @route.delete("/{entry_id}")
    def delete_entry(self, entry_id: int):
        entry = _get_entry(self.context.request, entry_id)
        EntryService.delete_entry(entry)
        return {"success": True}


@api_controller("/labels", tags=["labels"], auth=JWTAuth())
class LabelsController:
    @route.get("", response=list[LabelSchemaOut])
    def get_labels(self):
        return _get_user(self.context.request).labels.all()

    @route.get("/{label_id}", response=LabelSchemaOut)
    def get_label(self, label_id: int):
        return _get_label(self.context.request, label_id)

    @route.get("/labels/{label_id}/paragraphs", response=list[LabelParagraphSchemaOut])
    def get_label_paragraphs(self, label_id: int):
        label = _get_label(self.context.request, label_id)
        return label.paragraphs.all().order_by('-entry__date', 'id').select_related('entry')

    @route.post("", response=LabelSchemaOut)
    def create_label(self, payload: LabelSchemaIn):
        return Label.objects.create(user=_get_user(self.context.request), **payload.dict())

    @route.put("/labels/{label_id}", response=LabelSchemaOut)
    def update_label(self, label_id: int, payload: LabelSchemaIn):
        label = _get_label(self.context.request, label_id)
        for attr, value in payload.dict().items():
            setattr(label, attr, value)
        label.save()
        return label

    @route.delete("/labels/{label_id}")
    def delete_label(self, label_id: int):
        label = _get_label(self.context.request, label_id)
        label.delete()
        return {"success": True}


api.register_controllers(EntriesController)
api.register_controllers(LabelsController)
