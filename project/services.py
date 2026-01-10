from collections import defaultdict
from collections.abc import Iterable
from datetime import date

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from ninja_jwt.tokens import RefreshToken

from project.exceptions import PasswordError
from project.models import EntryParagraph, JournalEntry, Label
from project.types import EntryDataIn


class EntryService:
    @staticmethod
    def create_entry(user: User, entry_data: EntryDataIn):
        paragraphs = entry_data.pop("paragraphs", [])

        entry = user.journal_entries.create(**entry_data)

        EntryParagraph.objects.bulk_create(
            [
                EntryParagraph(entry=entry, order=paragraph.get("order"), content=paragraph.get("content"))
                for paragraph in paragraphs
            ]
        )

        return entry

    @staticmethod
    def update_entry(entry: JournalEntry, new_entry_data: EntryDataIn):
        paragraphs = new_entry_data.pop("paragraphs", None)

        for attr, value in new_entry_data.items():
            if value is not None:
                setattr(entry, attr, value)
        entry.save()

        if paragraphs is not None:
            paragraph_orders_in_request = {p.get("order") for p in paragraphs}
            existing_paragraphs_by_order = {p.order: p for p in entry.paragraphs.all()}
            paragraphs_to_create = []

            # If paragraphs count has changed,
            # we cannot keep the existing labels,
            # as it is unclear to which paragraphs they belong
            should_delete_labels = len(paragraphs) != len(entry.paragraphs.all())

            for paragraph in paragraphs:
                entry_paragraph = existing_paragraphs_by_order.get(paragraph.get("order"))
                if entry_paragraph is None:
                    paragraphs_to_create.append(
                        EntryParagraph(entry=entry, order=paragraph.get("order"), content=paragraph.get("content"))
                    )
                else:
                    entry_paragraph.content = paragraph.get("content")
                    if should_delete_labels:
                        entry_paragraph.labels.clear()
                    entry_paragraph.save()

            # Create new paragraphs
            if paragraphs_to_create:
                EntryParagraph.objects.bulk_create(paragraphs_to_create)

            # Delete paragraphs that are not in the request
            existing_paragraph_orders = set(existing_paragraphs_by_order.keys())
            paragraph_orders_to_delete = existing_paragraph_orders - paragraph_orders_in_request
            if paragraph_orders_to_delete:
                entry.paragraphs.filter(order__in=paragraph_orders_to_delete).delete()

        return entry

    @staticmethod
    def assign_label_to_paragraphs(paragraphs: Iterable[EntryParagraph], label: Label):
        for paragraph in paragraphs:
            paragraph.labels.add(label)

    @staticmethod
    def remove_label_from_paragraph(paragraph: EntryParagraph, label: Label):
        paragraph.labels.remove(label)

    @staticmethod
    def delete_entry(entry: JournalEntry):
        entry.delete()

    @staticmethod
    def toggle_bookmark(entry: JournalEntry):
        entry.is_bookmarked = not entry.is_bookmarked
        entry.save()

    @staticmethod
    def get_stats(user: User):
        labels_paragraphs_count = (
            user.labels.all()
            .annotate(paragraphs_count=Count("paragraphs"))
            .order_by("-paragraphs_count")
            .exclude(paragraphs_count=0)
        )

        first_day_of_month = date.today().replace(day=1)

        entries = user.journal_entries
        entries_this_month = entries.filter(date__gte=first_day_of_month).count()
        entries_this_year = entries.filter(date__year=date.today().year).count()
        bookmarked_entries = entries.filter(is_bookmarked=True).count()

        return {
            "entries_this_month": entries_this_month,
            "entries_this_year": entries_this_year,
            "total_entries": entries.count(),
            "latest_entry": entries.last(),
            "total_labels_used": user.labels.exclude(paragraphs=None).count(),
            "most_used_label": labels_paragraphs_count.first(),
            "labels_paragraphs_count": list(labels_paragraphs_count),
            "bookmarked_entries": bookmarked_entries,
        }

    @staticmethod
    def _get_timeline_for_period(entries, truncate_function):
        return list(
            entries.annotate(period=truncate_function("date")).values("period").annotate(count=Count("id")).order_by("period")
        )

    @staticmethod
    def get_timeline(user: User):
        entries = user.journal_entries.all()

        return {
            "week": EntryService._get_timeline_for_period(entries, TruncWeek),
            "month": EntryService._get_timeline_for_period(entries, TruncMonth),
            "year": EntryService._get_timeline_for_period(entries, TruncYear),
        }

    @staticmethod
    def search_entries(user: User, search_query: str) -> dict[JournalEntry, list[EntryParagraph]]:
        entries_data: dict[JournalEntry, list[EntryParagraph]] = defaultdict(list)
        paragraphs_matching_content = EntryParagraph.objects.filter(content__icontains=search_query).select_related("entry")

        for paragraph in paragraphs_matching_content:
            entries_data[paragraph.entry].append(paragraph)

        entries_matching_title = user.journal_entries.filter(title__icontains=search_query)
        for entry in entries_matching_title:
            if entry not in entries_data:
                entries_data[entry] = []

        return entries_data


class UserService:
    @staticmethod
    def invalidate_refresh_token(refresh_token: str):
        token = RefreshToken(refresh_token)
        token.blacklist()

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str):
        if not user.check_password(current_password):
            raise PasswordError("Current password is incorrect!")

        try:
            validate_password(new_password)
        except ValidationError as e:
            raise PasswordError(" ".join(e.messages))

        user.set_password(new_password)
        user.save()

        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
