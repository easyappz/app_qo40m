from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_adview"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportQuota",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(max_length=255, unique=True)),
                ("last_request_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.URLField()),
                ("status", models.CharField(choices=[("queued", "queued"), ("processing", "processing"), ("done", "done"), ("blocked", "blocked"), ("error", "error")], default="queued", max_length=16)),
                ("retry_after", models.IntegerField(blank=True, null=True)),
                ("message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ad", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="api.ad")),
                ("member", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="api.member")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AlterField(
            model_name="ad",
            name="source_url",
            field=models.URLField(blank=True, db_index=True, null=True),
        ),
    ]
