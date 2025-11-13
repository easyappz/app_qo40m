from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Optional, Any, Iterable, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import requests
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Ad, AdView, Member, ImportJob, ImportQuota


class _OGAndLDParser(HTMLParser):
    """Minimal HTML parser to extract Open Graph tags and JSON-LD blobs."""

    def __init__(self) -> None:
        super().__init__()
        self.og: dict[str, str] = {}
        self.images: list[str] = []
        self._in_ld_json: bool = False
        self._ld_chunks: list[str] = []
        self.ld_json_texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, Optional[str]]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "meta":
            prop = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            content = attrs_dict.get("content") or ""
            if not prop or not content:
                return
            if prop in {"og:title", "og:description"}:
                self.og[prop] = content
            # Collect all og:image variants including og:image:secure_url
            if prop.startswith("og:image") and content:
                if content not in self.images:
                    self.images.append(content)
        elif tag.lower() == "script":
            t = (attrs_dict.get("type") or "").lower()
            if t == "application/ld+json":
                self._in_ld_json = True
                self._ld_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_ld_json:
            self._ld_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_ld_json:
            text = "".join(self._ld_chunks).strip()
            if text:
                self.ld_json_texts.append(text)
            self._in_ld_json = False
            self._ld_chunks = []


# -----------------------------
# Price helpers
# -----------------------------

def _parse_price_minor_units(value: Any) -> Optional[int]:
    """Parse price to integer minor currency units (RUB cents).

    Accepts numbers or strings like "1 234 567", "1234567.00", etc.
    Returns None if cannot parse.
    """
    if value is None:
        return None
    # Numeric types
    if isinstance(value, (int, float)):
        try:
            q = Decimal(str(value))
            return int((q * 100).to_integral_value())
        except (InvalidOperation, ValueError):
            return None
    # Strings
    if isinstance(value, str):
        cleaned = []
        for ch in value:
            # Keep digits and decimal separators
            if ch.isdigit() or ch in ",.":
                cleaned.append(ch)
        txt = "".join(cleaned)
        if not txt:
            return None
        # Normalize comma to dot
        txt = txt.replace(",", ".")
        try:
            q = Decimal(txt)
            return int((q * 100).to_integral_value())
        except (InvalidOperation, ValueError):
            return None
    return None


def _extract_price_from_jsonld_texts(texts: list[str]) -> Optional[int]:
    """Attempt to find a price in any JSON-LD blob and return it as minor units (cents)."""
    def candidate_prices(obj: Any) -> Iterable[Any]:
        if isinstance(obj, dict):
            # Typical places
            if "price" in obj:
                yield obj.get("price")
            offers = obj.get("offers")
            if offers is not None:
                if isinstance(offers, list):
                    for it in offers:
                        if isinstance(it, dict) and "price" in it:
                            yield it.get("price")
                elif isinstance(offers, dict):
                    if "price" in offers:
                        yield offers.get("price")
            # Recurse
            for v in obj.values():
                yield from candidate_prices(v)
        elif isinstance(obj, list):
            for it in obj:
                yield from candidate_prices(it)
        # else ignore scalars

    for text in texts:
        try:
            data = json.loads(text)
        except Exception:
            continue
        for raw in candidate_prices(data):
            price_cents = _parse_price_minor_units(raw)
            if isinstance(price_cents, int) and price_cents > 0:
                return price_cents
    return None


def _looks_like_antibot(html_text: str, status_code: int, headers: dict[str, str]) -> bool:
    low = (html_text or "").lower()
    indicators = [
        "captcha",
        "cloudflare",
        "attention required",
        "access denied",
        "доступ ограничен",
        "вы робот",
        "похоже, вы робот",
        "защита от роботов",
    ]
    if any(x in low for x in indicators):
        return True
    if status_code in (403, 429):
        return True
    # Some providers mark anti-bot via special headers
    hlow = {k.lower(): v.lower() for k, v in headers.items()}
    if any(k.startswith("cf-") for k in hlow.keys()):
        return True
    return False


# -----------------------------
# Existing simple fetcher for legacy import endpoint
# -----------------------------

def fetch_avito_metadata(url: str) -> dict:
    """
    Fetch public metadata from an Avito listing page.

    Rules:
    - Validate that URL host belongs to avito.ru (e.g., avito.ru, www.avito.ru, m.avito.ru).
    - Perform a simple requests.get with a desktop-like User-Agent.
    - If the response indicates anti-bot or non-200, return a structured error.
    - Parse Open Graph tags (og:title, og:description, og:image*) and JSON-LD price (if present).

    Returns a dict in one of the following forms:
    - {"ok": True, "data": {"title": str, "description": str, "price": int, "photos": [str,..]}}
      Note: price is integer in minor currency units (RUB cents). The price key may be omitted if not detected.
    - {"ok": False, "code": str, "detail": str}
      Codes: invalid_url, not_avito, request_failed, blocked, parse_failed, empty
    """
    # Validate URL
    try:
        parsed = urlparse(url)
    except Exception:
        return {"ok": False, "code": "invalid_url", "detail": "URL is not parseable."}

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"ok": False, "code": "invalid_url", "detail": "URL must include scheme and host."}

    host = parsed.netloc.lower()
    if not (host == "avito.ru" or host.endswith(".avito.ru")):
        return {"ok": False, "code": "not_avito", "detail": "Only avito.ru URLs are supported."}

    headers = {"User-Agent": "Mozilla/5.0 Easyappz/1.0"}
    try:
        resp = requests.get(url, timeout=6, headers=headers)
    except Exception as exc:  # network or SSL timeout
        return {"ok": False, "code": "request_failed", "detail": f"Network error: {exc}"}

    status = resp.status_code
    text = resp.text if getattr(resp, "text", None) else (resp.content.decode("utf-8", errors="ignore") if hasattr(resp, "content") else "")

    if status != 200:
        # Distinguish potential blocks
        if _looks_like_antibot(text, status, dict(resp.headers)):
            return {"ok": False, "code": "blocked", "detail": f"Request blocked by remote site (HTTP {status})."}
        return {"ok": False, "code": "request_failed", "detail": f"Unexpected HTTP status {status}."}

    if _looks_like_antibot(text, status, dict(resp.headers)):
        return {"ok": False, "code": "blocked", "detail": "Remote site likely presented anti-bot protection."}

    # Parse HTML for OG and JSON-LD
    try:
        parser = _OGAndLDParser()
        parser.feed(text)
    except Exception:
        return {"ok": False, "code": "parse_failed", "detail": "Failed to parse HTML."}

    title = parser.og.get("og:title", "").strip()
    description = parser.og.get("og:description", "").strip()
    images = [u for u in parser.images if isinstance(u, str) and u.strip()]

    price_cents = _extract_price_from_jsonld_texts(parser.ld_json_texts)

    # Build result
    data: dict[str, Any] = {
        "title": title or "",
        "description": description or "",
        "photos": images[:10],
    }
    if isinstance(price_cents, int) and price_cents > 0:
        data["price"] = price_cents

    # If we found absolutely nothing meaningful, hint empty
    if not data["title"] and not data["description"] and not data["photos"] and "price" not in data:
        return {"ok": False, "code": "empty", "detail": "No public metadata found on the page."}

    return {"ok": True, "data": data}


# -----------------------------
# Unique views helpers (existing)
# -----------------------------

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


# -----------------------------
# New compliant import pipeline (no external libs, respectful rate limits)
# -----------------------------

class LocalRateLimitError(Exception):
    def __init__(self, seconds_left: int) -> None:
        super().__init__(f"Local rate limit hit. Retry after {seconds_left}s")
        self.seconds_left = seconds_left


def _enforce_local_rate_limit(domain: str, min_interval_seconds: int = 5) -> None:
    """Enforce a minimal interval between requests to the given domain.

    If the last request was within min_interval_seconds, raise LocalRateLimitError.
    Otherwise update last_request_at to now.
    """
    now = timezone.now()
    quota, _ = ImportQuota.objects.get_or_create(domain=domain)
    if quota.last_request_at is not None:
        delta = (now - quota.last_request_at).total_seconds()
        if delta < float(min_interval_seconds):
            raise LocalRateLimitError(int(min_interval_seconds - delta))
    quota.last_request_at = now
    quota.save(update_fields=["last_request_at"])


def _fetch_url(url: str, timeout: int = 12) -> Tuple[int, dict, bytes]:
    """Fetch URL using urllib with honest headers and return (status, headers, body)."""
    headers = {
        "User-Agent": "Avitolog/1.0 (contact: support@example.com)",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "close",
    }
    req = Request(url, method="GET", headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read() if hasattr(resp, "read") else b""
            headers_dict = dict(getattr(resp, "headers", {}))
            return int(status), headers_dict, body
    except HTTPError as e:  # HTTP errors still return headers and body
        try:
            body = e.read() if hasattr(e, "read") else b""
        except Exception:
            body = b""
        headers_dict = dict(getattr(e, "headers", {}) or {})
        return int(getattr(e, "code", 500) or 500), headers_dict, body
    except URLError as e:
        # Network error: return 0 status to indicate failure
        return 0, {}, str(e).encode("utf-8", errors="ignore")


class SimpleMetaParser(HTMLParser):
    """Collect <meta ... content=...> pairs and <title> text."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self._in_title = False
        self.title_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "meta":
            d = {k.lower(): (v or "") for k, v in attrs}
            name = (d.get("property") or d.get("name") or "").strip()
            content = (d.get("content") or "").strip()
            if name and content and name not in self.meta:
                self.meta[name.lower()] = content
        elif tag.lower() == "title":
            self._in_title = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    @property
    def title(self) -> str:
        return ("".join(self.title_text_parts)).strip()


def _parse_listing(html: str) -> dict:
    """Extract title, description, images and price from HTML meta tags.

    Priority:
      - title: og:title or <title>
      - description: og:description
      - images: all og:image*
      - price: any meta value containing 'price' that parses to a positive number
    """
    parser = SimpleMetaParser()
    parser.feed(html or "")

    meta = parser.meta
    title = (meta.get("og:title") or parser.title or "").strip()
    description = (meta.get("og:description") or meta.get("description") or "").strip()

    images = []
    for k, v in meta.items():
        if k.startswith("og:image") and v:
            if v not in images:
                images.append(v)

    price_cents = None
    for k, v in meta.items():
        if "price" in k and v:
            cents = _parse_price_minor_units(v)
            if isinstance(cents, int) and cents > 0:
                price_cents = cents
                break

    result = {"title": title, "description": description, "images": images}
    if isinstance(price_cents, int) and price_cents > 0:
        result["price"] = price_cents
    return result


def import_listing_from_url(url: str, member: Optional[Member]) -> tuple[ImportJob, Optional[Ad]]:
    """Create/update an ImportJob and import listing data respectfully.

    Steps:
      - Validate domain contains 'avito.ru'.
      - Reuse recent Ad by source_url if updated within last 12h.
      - Enforce local rate limit per domain (5s) before network request.
      - Fetch once; on 429 => status 'blocked' with retry_after.
      - On 200 parse minimal meta and create/update Ad; set job done.
      - On other errors => status 'error' with message.
    """
    # Find or create a working job (to cooperate with caller that may pre-create one)
    existing = ImportJob.objects.filter(member=member, url=url).order_by("-created_at").first()
    job = None
    now = timezone.now()
    if existing and existing.status in {"queued", "processing"} and (now - existing.created_at).total_seconds() < 300:
        job = existing
        if job.status != "processing":
            job.status = "processing"
            job.retry_after = None
            job.message = None
            job.save(update_fields=["status", "retry_after", "message", "updated_at"])
    else:
        job = ImportJob.objects.create(member=member, url=url, status="processing")

    # Domain validation
    try:
        parsed = urlparse(url)
    except Exception:
        job.status = "error"
        job.message = "Invalid URL."
        job.save(update_fields=["status", "message", "updated_at"])
        return job, None

    host = (parsed.netloc or "").lower()
    if "avito.ru" not in host:
        job.status = "error"
        job.message = "Only avito.ru URLs are supported."
        job.save(update_fields=["status", "message", "updated_at"])
        return job, None

    # Reuse recent Ad within 12h without fetching (cache)
    cutoff = now - timedelta(hours=12)
    reused = Ad.objects.filter(source_url=url, updated_at__gte=cutoff).order_by("-updated_at").first()
    if reused:
        job.status = "done"
        job.retry_after = None
        job.message = None
        job.ad = reused
        job.save(update_fields=["status", "retry_after", "message", "ad", "updated_at"])
        return job, reused

    # Enforce local per-domain rate limit
    _enforce_local_rate_limit(host, min_interval_seconds=5)

    # Single respectful fetch
    status_code, headers, body = _fetch_url(url, timeout=12)
    text = body.decode("utf-8", errors="ignore") if isinstance(body, (bytes, bytearray)) else str(body)

    # Handle rate limiting from remote
    if status_code == 429:
        retry_after_raw = headers.get("Retry-After") if isinstance(headers, dict) else None
        try:
            retry_after = int(retry_after_raw) if retry_after_raw is not None else 60
        except Exception:
            retry_after = 60
        job.status = "blocked"
        job.retry_after = retry_after
        job.message = f"Request blocked by remote site (HTTP 429). Please retry after {retry_after} seconds."
        job.save(update_fields=["status", "retry_after", "message", "updated_at"])
        return job, None

    if status_code != 200 or _looks_like_antibot(text, status_code, headers or {}):
        job.status = "error"
        http_info = f"HTTP {status_code}" if status_code else "Network error"
        job.message = f"Failed to import: {http_info}."
        job.save(update_fields=["status", "message", "updated_at"])
        return job, None

    # Parse listing
    payload = _parse_listing(text)
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    images = list(payload.get("images") or [])
    price = int(payload.get("price") or 0)

    # Create a new Ad (or update existing by exact match of source_url)
    ad = Ad.objects.filter(source_url=url).first()
    if ad:
        ad.title = title or ad.title
        ad.description = description or ad.description
        if price > 0:
            ad.price = price
        if images:
            ad.photos = images
        ad.owner = ad.owner or member
        ad.save(update_fields=["title", "description", "price", "photos", "updated_at", "owner"])
    else:
        ad = Ad.objects.create(
            owner=member,
            source_url=url,
            title=title or "",
            description=description or "",
            price=price if price > 0 else 0,
            photos=images,
        )

    job.status = "done"
    job.retry_after = None
    job.message = None
    job.ad = ad
    job.save(update_fields=["status", "retry_after", "message", "ad", "updated_at"])

    return job, ad
