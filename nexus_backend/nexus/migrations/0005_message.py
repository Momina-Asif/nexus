# Generated by Django 5.1.1 on 2024-11-20 16:35

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nexus', '0004_conversation_delete_message'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField()),
                ('belongs_in', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='belongs_in', to='nexus.conversation')),
                ('consumer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='receiver', to=settings.AUTH_USER_MODEL)),
                ('producer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sender', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
