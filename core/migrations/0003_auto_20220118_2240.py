# Generated by Django 2.2 on 2022-01-18 22:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_profile_subscription_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="subscription_mode",
            field=models.CharField(
                choices=[
                    (None, "No subscription"),
                    ("FULL", "Full"),
                    ("TRIAL", "Trial"),
                ],
                default=None,
                max_length=5,
                null=True,
            ),
        ),
    ]
