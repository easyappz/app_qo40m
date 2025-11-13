from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Ad, Member


class SmokeFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _register(self, username: str = "alice", email: str = "alice@example.com", password: str = "secret123"):
        url = "/api/auth/register/"
        payload = {"username": username, "email": email, "password": password}
        resp = self.client.post(url, payload, format="json")
        self.assertIn(resp.status_code, (201, 400))
        return resp

    def _login(self, username: str = "alice", email: str = "alice@example.com", password: str = "secret123") -> str:
        # Backend currently supports either username or email; use email for reliability
        url = "/api/auth/login/"
        payload = {"email": email, "password": password}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access", data)
        return data["access"]

    def test_hello(self):
        resp = self.client.get("/api/hello/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("message", resp.json())

    def test_auth_and_me(self):
        self._register()
        token = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("username"), "alice")

    def test_ads_popular_empty(self):
        resp = self.client.get("/api/ads/popular/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)

    def test_ad_detail_and_views_and_comments_favorites_rating_history(self):
        # Create member and token
        self._register("bob", "bob@example.com")
        token = self._login("bob", "bob@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Create an ad directly
        member = Member.objects.get(username="bob")
        ad = Ad.objects.create(
            owner=member,
            source_url="https://www.avito.ru/some/slug",
            title="Test Ad",
            description="Desc",
            price=12345,
            photos=["https://example.com/p1.jpg", "https://example.com/p2.jpg"],
        )

        # Detail
        resp = self.client.get(f"/api/ads/{ad.id}/")
        self.assertEqual(resp.status_code, 200)

        # Views (public endpoint)
        self.client.credentials()  # clear auth for guest view
        resp = self.client.post(f"/api/ads/{ad.id}/views/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("views_count", resp.json())

        # Auth again
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Comment create
        resp = self.client.post(f"/api/ads/{ad.id}/comments/", {"text": "Nice ad!"}, format="json")
        self.assertEqual(resp.status_code, 201)
        comment_id = resp.json().get("id")
        self.assertIsNotNone(comment_id)

        # Comment like toggle
        resp = self.client.post(f"/api/comments/{comment_id}/like/")
        self.assertEqual(resp.status_code, 200)

        # Favorite toggle
        resp = self.client.post(f"/api/ads/{ad.id}/favorite/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("is_favorite", resp.json())

        # Rate ad
        resp = self.client.post(f"/api/ads/{ad.id}/ratings/", {"value": 5}, format="json")
        self.assertEqual(resp.status_code, 200)

        # History (should succeed even if empty for member)
        resp = self.client.get("/api/me/history/?limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("items", resp.json())
