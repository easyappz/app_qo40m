from django.db import models


class Member(models.Model):
    """Standalone user entity (not linked to django.contrib.auth.User)."""

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    avatar_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Member({self.id}): {self.username}"


class Ad(models.Model):
    """
    Advertisement imported from external source (e.g., Avito) or created by a Member.

    Notes:
    - price stores value in integer cents (minor currency units).
    - photos is a JSON list of absolute URLs.
    """

    owner = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ads",
    )
    source_url = models.CharField(max_length=1000)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(default=0)  # cents
    photos = models.JSONField(default=list)

    views_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)  # total comment likes

    avg_rating = models.FloatField(default=0.0)
    ratings_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"], name="ad_created_idx"),
            models.Index(fields=["views_count"], name="ad_views_idx"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Ad({self.id}): {self.title[:40]}"


class Favorite(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="favorites")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ad", "member"], name="uniq_favorite_ad_member"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Favorite(member={self.member_id}, ad={self.ad_id})"


class Rating(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="ratings")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="ratings")
    value = models.PositiveSmallIntegerField()  # 1..5
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ad", "member"], name="uniq_rating_ad_member"),
        ]
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Rating(member={self.member_id}, ad={self.ad_id}, value={self.value})"
