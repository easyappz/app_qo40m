from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_url", models.CharField(max_length=1000)),
                ("title", models.CharField(max_length=500)),
                ("description", models.TextField(blank=True)),
                ("price", models.PositiveIntegerField(default=0)),
                ("photos", models.JSONField(default=list)),
                ("views_count", models.PositiveIntegerField(default=0)),
                ("comments_count", models.PositiveIntegerField(default=0)),
                ("likes_count", models.PositiveIntegerField(default=0)),
                ("avg_rating", models.FloatField(default=0.0)),
                ("ratings_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ads", to="api.member"),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(fields=["created_at"], name="ad_created_idx"),
        ),
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(fields=["views_count"], name="ad_views_idx"),
        ),
        migrations.CreateModel(
            name="Favorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to="api.ad")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to="api.member")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="favorite",
            constraint=models.UniqueConstraint(fields=("ad", "member"), name="uniq_favorite_ad_member"),
        ),
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="api.ad")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="api.member")),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.UniqueConstraint(fields=("ad", "member"), name="uniq_rating_ad_member"),
        ),
    ]
