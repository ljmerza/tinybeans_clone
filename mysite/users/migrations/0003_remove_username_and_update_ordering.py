from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_backfill_archived_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='circlemembership',
            options={'ordering': ['circle__name', 'user__email']},
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'ordering': ['email']},
        ),
        migrations.RemoveField(
            model_name='user',
            name='username',
        ),
    ]
