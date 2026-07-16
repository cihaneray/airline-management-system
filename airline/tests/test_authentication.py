from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class JWTAuthenticationTests(APITestCase):
    password = "StrongPassword123!"

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.password,
        )

    def test_protected_endpoint_rejects_anonymous_user(self):
        response = self.client.get(reverse("airplane-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_obtain_access_and_refresh_tokens(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_access_token_allows_protected_request(self):
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )
        response = self.client.get(reverse("airplane-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_token_returns_new_access_token(self):
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": token_response.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
