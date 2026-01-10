from datetime import date

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from project.utils import TrackedModel


class JournalEntry(TrackedModel):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="journal_entries")
    title = models.CharField(max_length=200, null=True)
    date = models.DateField(default=date.today)
    rating = models.FloatField(null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_bookmarked = models.BooleanField(default=False)
    json_content = models.JSONField(null=True)

    def __hash__(self):
        return hash(self.id)


class Label(TrackedModel):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=50)
    description = models.TextField(null=True)

    class Meta:
        ordering = ["-id"]


class EntryParagraph(models.Model):
    entry = models.ForeignKey(to=JournalEntry, related_name="paragraphs", on_delete=models.CASCADE)
    order = models.IntegerField()
    content = models.TextField()
    labels = models.ManyToManyField(to=Label, related_name="paragraphs")

    class Meta:
        ordering = ["order"]
