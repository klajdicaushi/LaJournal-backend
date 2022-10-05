from django.db import models


class TrackedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class Choices:
    @classmethod
    def choices(cls):
        return {label: value for (label, value) in cls.__dict__.items() if not label.startswith('_')}

    @classmethod
    def as_list(cls):
        return [(value, label) for (label, value) in cls.__dict__.items() if not label.startswith('_')]

    @classmethod
    def as_dict(cls):
        return {value: label for (label, value) in cls.__dict__.items() if not label.startswith('_')}
