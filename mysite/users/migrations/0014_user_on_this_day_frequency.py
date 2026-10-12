from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_user_apple_sign_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='on_this_day_frequency',
            field=models.CharField(choices=[('off', 'Off'), ('less', 'Less often'), ('normal', 'Normal'), ('more', 'More often')], default='normal', help_text='How often "On this day" memories show in the home feed', max_length=10),
        ),
    ]
