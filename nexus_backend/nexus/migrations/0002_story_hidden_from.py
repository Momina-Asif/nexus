# Generated by Django 5.1.1 on 2024-11-15 17:43

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nexus', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='hidden_from',
            field=models.ManyToManyField(blank=True, related_name='hidden_from', to=settings.AUTH_USER_MODEL),
        ),
    ]
