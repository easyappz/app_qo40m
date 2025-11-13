from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_comment_commentlike"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(blank=True, max_length=64, null=True)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("ua_hash", models.CharField(blank=True, max_length=64, null=True)),
                ("viewed_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "ad",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="api.ad"),
                ),
                (
                    "member",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ad_views", to="api.member"),
                ),
            ],
            options={
                "ordering": ["-viewed_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="adview",
            index=models.Index(fields=["ad", "member", "fingerprint", "viewed_at"], name="adview_unique_window_idx"),
        ),
    ]
