import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keeps', '0002_initial'),
        ('users', '0002_add_circle_owner_field'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TinybeansImportRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_type', models.CharField(choices=[('journal', 'Journal'), ('child', 'Child'), ('user', 'User'), ('entry', 'Entry'), ('comment', 'Comment'), ('emotion', 'Emotion')], max_length=20)),
                ('tinybeans_id', models.CharField(max_length=64)),
                ('payload', models.JSONField(blank=True, default=dict, help_text='Raw remote object snapshot for debugging')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('circle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to='users.circle')),
                ('child', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to='users.childprofile')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to=settings.AUTH_USER_MODEL)),
                ('keep', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to='keeps.keep')),
                ('comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to='keeps.keepcomment')),
                ('reaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tinybeans_import_records', to='keeps.keepreaction')),
            ],
            options={
                'unique_together': {('object_type', 'tinybeans_id')},
            },
        ),
        migrations.AddIndex(
            model_name='tinybeansimportrecord',
            index=models.Index(fields=['object_type', 'tinybeans_id'], name='keeps_tinyb_object__idx'),
        ),
    ]
