# Generated by Django 4.2.2 on 2024-01-06 20:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0004_delete_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='journalentry',
            name='is_bookmarked',
            field=models.BooleanField(default=False),
        ),
    ]