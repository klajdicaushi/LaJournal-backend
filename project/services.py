from datetime import date
from typing import Iterable

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Count
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from ninja_jwt.tokens import RefreshToken

from project.exceptions import PasswordError
from project.models import JournalEntry, EntryParagraph, Label
from project.types import EntryDataIn


class EntryService:
    @staticmethod
    def create_entry(user: User, entry_data: EntryDataIn):
        paragraphs = entry_data.pop('paragraphs', [])

        entry = user.journal_entries.create(**entry_data)

        EntryParagraph.objects.bulk_create([EntryParagraph(
            entry=entry,
            order=paragraph.get('order'),
            content=paragraph.get('content')
        ) for paragraph in paragraphs])

        return entry

    @staticmethod
    def update_entry(entry: JournalEntry, new_entry_data: EntryDataIn):
        paragraphs = new_entry_data.pop('paragraphs', None)

        for attr, value in new_entry_data.items():
            if value is not None:
                setattr(entry, attr, value)
        entry.save()

        if paragraphs is not None:
            # If paragraphs count has changed,
            # we cannot keep the existing labels,
            # as it is unclear to which paragraphs they belong
            if len(paragraphs) != entry.paragraphs.count():
                # Delete all existing paragraphs
                entry.paragraphs.all().delete()

                # Create new paragraphs
                EntryParagraph.objects.bulk_create([EntryParagraph(
                    entry=entry,
                    order=paragraph.get('order'),
                    content=paragraph.get('content')
                ) for paragraph in paragraphs])
            else:
                # Update existing paragraphs
                for paragraph in paragraphs:
                    entry_paragraph = entry.paragraphs.get(order=paragraph.get('order'))
                    entry_paragraph.content = paragraph.get('content')
                    entry_paragraph.save()

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
    def get_stats(user: User):
        labels_paragraphs_count = user.labels.all().annotate(
            paragraphs_count=Count('paragraphs')
        ).order_by('-paragraphs_count').exclude(paragraphs_count=0)

        first_day_of_month = date.today().replace(day=1)

        entries = user.journal_entries
        entries_this_month = entries.filter(created_at__date__gte=first_day_of_month).count()
        entries_this_year = entries.filter(created_at__date__year=date.today().year).count()

        return {
            'entries_this_month': entries_this_month,
            'entries_this_year': entries_this_year,
            'total_entries': user.journal_entries.count(),
            'latest_entry': user.journal_entries.last(),
            'total_labels_used': user.labels.exclude(paragraphs=None).count(),
            'most_used_label': labels_paragraphs_count.first(),
            'labels_paragraphs_count': list(labels_paragraphs_count),
        }


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
