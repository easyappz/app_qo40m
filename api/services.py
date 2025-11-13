from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Ad, AdView, Member


def _get_client_ip(request) -> Optional[str]:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # first IP in the list is the original client
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record_unique_view(request, ad: Ad) -> int:
    """
    Record a unique view for the given ad with a 24h uniqueness window.

    - Authenticated users: unique by (ad, member) within last 24h.
    - Guests: approximate uniqueness by fingerprint sha256("{ip}|{user_agent}").

    Returns the current ad.views_count after a potential increment.
    """
    now = timezone.now()
    cutoff = now - timedelta(hours=24)

    ip = _get_client_ip(request)
    ua = _get_user_agent(request)
    ua_hash = _sha256(ua) if ua else None

    is_auth = bool(getattr(request.user, "is_authenticated", False))

    if is_auth:
        member: Member = getattr(request.user, "member", request.user)
        exists = AdView.objects.filter(ad=ad, member=member, viewed_at__gte=cutoff).exists()
        if not exists:
            with transaction.atomic():
                AdView.objects.create(
                    ad=ad,
                    member=member,
                    ip=ip,
                    ua_hash=ua_hash,
                    viewed_at=now,
                )
                Ad.objects.filter(id=ad.id).update(views_count=F("views_count") + 1, updated_at=now)
        ad.refresh_from_db(fields=["views_count"])
        return ad.views_count

    # Guest path: fingerprint by ip + UA
    base = f"{ip or ''}|{ua or ''}"
    fingerprint = _sha256(base)

    exists = AdView.objects.filter(
        ad=ad,
        member__isnull=True,
        fingerprint=fingerprint,
        viewed_at__gte=cutoff,
    ).exists()

    if not exists:
        with transaction.atomic():
            AdView.objects.create(
                ad=ad,
                member=None,
                fingerprint=fingerprint,
                ip=ip,
                ua_hash=ua_hash,
                viewed_at=now,
            )
            Ad.objects.filter(id=ad.id).update(views_count=F("views_count") + 1, updated_at=now)

    ad.refresh_from_db(fields=["views_count"])
    return ad.views_count
