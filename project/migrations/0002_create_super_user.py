from django.db import migrations


def generate_superuser(apps, schema_editor):
    from django.contrib.auth.models import User

    User.objects.create_superuser(
        username="admin",
        email="admin@admin.com",
        password="admin"
    )


class Migration(migrations.Migration):
    dependencies = [
        ('project', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(generate_superuser),
    ]
