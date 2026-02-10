"""Initial migration for device_areas app."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Initial migration for device_areas app."""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Device Area',
                'verbose_name_plural': 'Device Areas',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DeviceAreaAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_assignments', to='device_areas.devicearea')),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='device_assignments_made', to=settings.AUTH_USER_MODEL)),
                ('device', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='area_assignment', to='auth.trusteddevice')),
            ],
            options={
                'verbose_name': 'Device Area Assignment',
                'verbose_name_plural': 'Device Area Assignments',
                'ordering': ['-assigned_at'],
            },
        ),
    ]
