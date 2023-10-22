from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Query
from ninja.errors import HttpError
from ninja_extra import NinjaExtraAPI, api_controller, route
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.exceptions import TokenError
from ninja_jwt.tokens import RefreshToken

from project.exceptions import PasswordError
from project.models import Label
from project.schemas import AssignLabelSchemaIn, JournalEntrySchemaIn, JournalEntrySchemaOut, LabelSchemaOut, \
    LabelSchemaIn, RemoveLabelSchemaIn, EntryStatsOut, JournalFiltersSchema, LabelParagraphSchemaOut, \
    ChangePasswordSchema, UserSchemaOut, RefreshTokenSchema, EntrySimpleSchemaOut
from project.services import EntryService, UserService

api = NinjaExtraAPI(title="LaJournal API")
api.register_controllers(NinjaJWTDefaultController)


def _get_user(request) -> User:
    return request.auth


def _get_entry(request, entry_id: int):
    return get_object_or_404(_get_user(request).journal_entries.all(), id=entry_id)


def _get_label(request, label_id: int):
    return get_object_or_404(_get_user(request).labels.all(), id=label_id)


@api.get("/me", response=UserSchemaOut, tags=['auth'], auth=JWTAuth())
def me(request):
    return _get_user(request)


@api.put("/change-password", tags=['auth'], auth=JWTAuth())
def change_password(request, payload: ChangePasswordSchema):
    user = _get_user(request)

    try:
        UserService.change_password(
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password
        )
    except PasswordError as e:
        raise HttpError(400, str(e))

    return {"success": True}


@api.post("/token/refresh-tokens", tags=['token'], auth=None)
def refresh_tokens(request, payload: RefreshTokenSchema):
    """
    Refresh both tokens (access and refresh) using refresh token.
    """

    try:
        refresh_token = RefreshToken(payload.refresh_token)
    except TokenError as e:
        raise HttpError(400, str(e))

    user_id = refresh_token.payload.get('user_id')
    user = User.objects.get(id=user_id)

    new_refresh_token = RefreshToken.for_user(user)

    return {
        "refresh": str(new_refresh_token),
        "access": str(new_refresh_token.access_token)
    }


@api.post("/token/invalidate", tags=['token'], auth=JWTAuth())
def invalidate_token(request, payload: RefreshTokenSchema):
    try:
        UserService.invalidate_refresh_token(payload.refresh_token)
        return {"success": True}
    except TokenError as e:
        raise HttpError(400, str(e))


@api_controller("/entries", tags=["entries"], auth=JWTAuth())
class EntriesController:
    @route.get("/stats", response=EntryStatsOut)
    def get_stats(self):
        return EntryService.get_stats(user=_get_user(self.context.request))

    @route.get("", response=list[EntrySimpleSchemaOut])
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

    @route.get("/{label_id}/paragraphs", response=list[LabelParagraphSchemaOut])
    def get_label_paragraphs(self, label_id: int):
        label = _get_label(self.context.request, label_id)
        return label.paragraphs.all().order_by('-entry__date', 'id').select_related('entry')

    @route.post("", response=LabelSchemaOut)
    def create_label(self, payload: LabelSchemaIn):
        return Label.objects.create(user=_get_user(self.context.request), **payload.dict())

    @route.put("/{label_id}", response=LabelSchemaOut)
    def update_label(self, label_id: int, payload: LabelSchemaIn):
        label = _get_label(self.context.request, label_id)
        for attr, value in payload.dict().items():
            setattr(label, attr, value)
        label.save()
        return label

    @route.delete("/{label_id}")
    def delete_label(self, label_id: int):
        label = _get_label(self.context.request, label_id)
        label.delete()
        return {"success": True}


api.register_controllers(EntriesController)
api.register_controllers(LabelsController)
