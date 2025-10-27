from __future__ import annotations

import hashlib

from django.db import migrations, models


def hash_existing_code_verifiers(apps, schema_editor):
    GoogleOAuthState = apps.get_model('auth_app', 'GoogleOAuthState')
    for state in GoogleOAuthState.objects.all():
        value = state.code_verifier_hash
        if not value:
            continue
        state.code_verifier_hash = hashlib.sha256(value.encode('utf-8')).hexdigest()
        state.save(update_fields=['code_verifier_hash'])


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='googleoauthstate',
            old_name='code_verifier',
            new_name='code_verifier_hash',
        ),
        migrations.AlterField(
            model_name='googleoauthstate',
            name='code_verifier_hash',
            field=models.CharField(
                max_length=128,
                help_text='SHA-256 hash of PKCE code verifier',
            ),
        ),
        migrations.RunPython(hash_existing_code_verifiers, migrations.RunPython.noop),
    ]
