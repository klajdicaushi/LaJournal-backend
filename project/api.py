from django.contrib.auth.models import User
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Query, Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import TokenError
from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.tokens import RefreshToken

from project.exceptions import PasswordError
from project.models import Label
from project.schemas import (
    AssignLabelSchemaIn,
    ChangePasswordSchema,
    EntrySearchSchemaOut,
    EntrySimpleSchemaOut,
    EntryStatsOut,
    JournalEntrySchemaIn,
    JournalEntrySchemaOut,
    JournalFiltersSchema,
    LabelParagraphSchemaOut,
    LabelSchemaIn,
    LabelSchemaOut,
    RefreshTokenSchema,
    RemoveLabelSchemaIn,
    TimelineSchemaOut,
    UserSchemaOut,
)
from project.services import EntryService, UserService

api = NinjaAPI(title="LaJournal API", auth=JWTAuth(), version="1.0.0")
api.add_router("/token", obtain_pair_router)


def _get_user(request) -> User:
    return request.auth


def _get_entry(request, entry_id: int):
    return get_object_or_404(_get_user(request).journal_entries.all(), id=entry_id)


def _get_label(request, label_id: int):
    return get_object_or_404(_get_user(request).labels.all(), id=label_id)


@api.get("/me", response=UserSchemaOut, tags=["auth"])
def me(request):
    return _get_user(request)


@api.put("/change-password", tags=["auth"])
def change_password(request, payload: ChangePasswordSchema):
    user = _get_user(request)

    try:
        UserService.change_password(
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except PasswordError as e:
        raise HttpError(400, str(e))

    return {"success": True}


@api.post("/token/refresh-tokens", tags=["token"], auth=None)
def refresh_tokens(request, payload: RefreshTokenSchema):
    """
    Refresh both tokens (access and refresh) using refresh token.
    """

    try:
        refresh_token = RefreshToken(payload.refresh_token)
    except TokenError as e:
        raise HttpError(400, str(e))

    user_id = refresh_token.payload.get("user_id")
    user = User.objects.get(id=user_id)

    new_refresh_token = RefreshToken.for_user(user)

    return {
        "refresh": str(new_refresh_token),
        "access": str(new_refresh_token.access_token),
    }


@api.post("/token/invalidate", tags=["token"])
def invalidate_token(request, payload: RefreshTokenSchema):
    try:
        UserService.invalidate_refresh_token(payload.refresh_token)
        return {"success": True}
    except TokenError as e:
        raise HttpError(400, str(e))


entries_router = Router(tags=["entries"])


@entries_router.get("/stats", response=EntryStatsOut)
def get_stats(request):
    return EntryService.get_stats(user=_get_user(request))


@entries_router.get("/timeline", response=TimelineSchemaOut)
def get_timeline(request):
    return EntryService.get_timeline(user=_get_user(request))


@entries_router.get("", response=list[EntrySimpleSchemaOut])
def get_journal_entries(request, filters: JournalFiltersSchema = Query(...)):
    entries = _get_user(request).journal_entries.all().order_by("-date", "-id")
    for key, value in filters.dict().items():
        if value is None:
            continue

        if key == "search_query":
            entries = entries.filter(Q(title__icontains=value) | Q(paragraphs__content__icontains=value))
        else:
            entries = entries.filter(**{key: value})

    return entries.distinct()


@entries_router.get("/search", response=list[EntrySearchSchemaOut])
def search_journal_entries(request, search_query: str):
    user = _get_user(request)

    entries_data = EntryService.search_entries(user=user, search_query=search_query)

    return [
        {
            "id": entry.id,
            "title": entry.title,
            "date": entry.date,
            "rating": entry.rating,
            "is_bookmarked": entry.is_bookmarked,
            "matching_paragraphs": [
                {
                    "order": paragraph.order,
                    "content": paragraph.content,
                }
                for paragraph in sorted(paragraphs, key=lambda x: x.order)
            ],
        }
        for entry, paragraphs in sorted(entries_data.items(), key=lambda x: x[0].date, reverse=True)
    ]


@entries_router.get("/{entry_id}", response=JournalEntrySchemaOut)
def get_journal_entry(request, entry_id: int):
    return _get_entry(request, entry_id)


@entries_router.post("", response=JournalEntrySchemaOut)
def create_journal_entry(request, payload: JournalEntrySchemaIn):
    entry_data = payload.dict()
    return EntryService.create_entry(user=_get_user(request), entry_data=entry_data)


@entries_router.put("/{entry_id}", response=JournalEntrySchemaOut)
def update_entry(request, entry_id: int, payload: JournalEntrySchemaIn):
    entry = _get_entry(request, entry_id)
    new_entry_data = payload.dict()
    return EntryService.update_entry(entry, new_entry_data)


@entries_router.post("/{entry_id}/assign_label", response=JournalEntrySchemaOut)
def assign_label(request, entry_id: int, payload: AssignLabelSchemaIn):
    entry = _get_entry(request, entry_id)
    data = payload.dict()

    paragraphs = entry.paragraphs.filter(order__in=data.get("paragraph_orders"))
    if paragraphs.count() != len(data.get("paragraph_orders")):
        raise Http404("One or more paragraphs do not exist!")

    label = _get_label(request, data.get("label_id"))

    EntryService.assign_label_to_paragraphs(paragraphs=paragraphs, label=label)
    return entry


@entries_router.post("/{entry_id}/remove_label", response=JournalEntrySchemaOut)
def remove_label(request, entry_id: int, payload: RemoveLabelSchemaIn):
    entry = _get_entry(request, entry_id)
    data = payload.dict()

    paragraph = get_object_or_404(entry.paragraphs, order=data.get("paragraph_order"))
    label = _get_label(request, data.get("label_id"))
    EntryService.remove_label_from_paragraph(paragraph=paragraph, label=label)
    return entry


@entries_router.post("/{entry_id}/toggle_bookmark", response=JournalEntrySchemaOut)
def toggle_bookmark(request, entry_id: int):
    entry = _get_entry(request, entry_id)
    EntryService.toggle_bookmark(entry)
    return entry


@entries_router.delete("/{entry_id}")
def delete_entry(request, entry_id: int):
    entry = _get_entry(request, entry_id)
    EntryService.delete_entry(entry)
    return {"success": True}


labels_router = Router(tags=["labels"])


@labels_router.get("", response=list[LabelSchemaOut])
def get_labels(request):
    return _get_user(request).labels.all()


@labels_router.get("/{label_id}", response=LabelSchemaOut)
def get_label(request, label_id: int):
    return _get_label(request, label_id)


@labels_router.get("/{label_id}/paragraphs", response=list[LabelParagraphSchemaOut])
def get_label_paragraphs(request, label_id: int):
    label = _get_label(request, label_id)
    return label.paragraphs.all().order_by("-entry__date", "id").select_related("entry")


@labels_router.post("", response=LabelSchemaOut)
def create_label(request, payload: LabelSchemaIn):
    return Label.objects.create(user=_get_user(request), **payload.dict())


@labels_router.put("/{label_id}", response=LabelSchemaOut)
def update_label(request, label_id: int, payload: LabelSchemaIn):
    label = _get_label(request, label_id)
    for attr, value in payload.dict().items():
        setattr(label, attr, value)
    label.save()
    return label


@labels_router.delete("/{label_id}")
def delete_label(request, label_id: int):
    label = _get_label(request, label_id)
    label.delete()
    return {"success": True}


api.add_router("/entries", entries_router)
api.add_router("/labels", labels_router)
