from django.db import models
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


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
    - likes_count aggregates likes on all comments of this ad.
    """

    owner = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ads",
    )
    # Source URL of the listing (may be null for manually created ads)
    source_url = models.URLField(null=True, blank=True, db_index=True)
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


# -----------------------------
# Comments & Likes
# -----------------------------

class Comment(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    text = models.TextField()
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["ad", "created_at"], name="comment_ad_created_idx"),
        ]
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Comment({self.id}) on Ad({self.ad_id}) by Member({self.author_id}): {self.text[:40]}"


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["comment", "member"], name="uniq_comment_member_like"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"CommentLike(comment={self.comment_id}, member={self.member_id})"


# -----------------------------
# Ad Views tracking (unique window 24h)
# -----------------------------

class AdView(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="views")
    member = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="ad_views"
    )
    fingerprint = models.CharField(max_length=64, null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    ua_hash = models.CharField(max_length=64, null=True, blank=True)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=["ad", "member", "fingerprint", "viewed_at"],
                name="adview_unique_window_idx",
            ),
        ]
        ordering = ["-viewed_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"AdView(ad={self.ad_id}, member={self.member_id}, fp={self.fingerprint}, at={self.viewed_at})"


# -----------------------------
# Signals to sync aggregate counters on Ad/Comment
# -----------------------------

@receiver(post_save, sender=Comment)
def _comment_created(sender, instance: Comment, created: bool, **kwargs):
    if created:
        Ad.objects.filter(id=instance.ad_id).update(
            comments_count=F("comments_count") + 1,
            updated_at=timezone.now(),
        )


@receiver(post_delete, sender=Comment)
def _comment_deleted(sender, instance: Comment, **kwargs):
    Ad.objects.filter(id=instance.ad_id).update(
        comments_count=F("comments_count") - 1,
        updated_at=timezone.now(),
    )


@receiver(post_save, sender=CommentLike)
def _comment_like_created(sender, instance: CommentLike, created: bool, **kwargs):
    if created:
        # Update comment likes_count
        Comment.objects.filter(id=instance.comment_id).update(
            likes_count=F("likes_count") + 1,
            updated_at=timezone.now(),
        )
        # Update ad aggregated likes_count
        ad_id = instance.comment.ad_id
        Ad.objects.filter(id=ad_id).update(
            likes_count=F("likes_count") + 1,
            updated_at=timezone.now(),
        )


@receiver(post_delete, sender=CommentLike)
def _comment_like_deleted(sender, instance: CommentLike, **kwargs):
    Comment.objects.filter(id=instance.comment_id).update(
        likes_count=F("likes_count") - 1,
        updated_at=timezone.now(),
    )
    ad_id = instance.comment.ad_id
    Ad.objects.filter(id=ad_id).update(
        likes_count=F("likes_count") - 1,
        updated_at=timezone.now(),
    )


# -----------------------------
# Import pipeline models
# -----------------------------

class ImportQuota(models.Model):
    """Per-domain quota guard to enforce a minimal interval between requests."""

    domain = models.CharField(max_length=255, unique=True)
    last_request_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"ImportQuota({self.domain}) at {self.last_request_at}"


class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "queued"),
        ("processing", "processing"),
        ("done", "done"),
        ("blocked", "blocked"),
        ("error", "error"),
    ]

    member = models.ForeignKey("api.Member", null=True, on_delete=models.SET_NULL)
    url = models.URLField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    retry_after = models.IntegerField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    ad = models.ForeignKey("api.Ad", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"ImportJob({self.id}) {self.status} url={self.url} ad={self.ad_id}"
