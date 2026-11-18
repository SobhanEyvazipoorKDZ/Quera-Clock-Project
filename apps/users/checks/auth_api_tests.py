from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User


class RegisterTests(APITestCase):
    def test_register_success(self):
        url = reverse("users_api:register")
        response = self.client.post(url, {
            "mobile": "09120000001",
            "password": "strongpass123",
            "first_name": "Ali",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_duplicate_mobile(self):
        User.objects.create_user(mobile="09120000002", password="pass12345")
        url = reverse("users_api:register")
        response = self.client.post(url, {
            "mobile": "09120000002",
            "password": "strongpass123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mobile", response.data)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09120000003", password="pass12345")

    def test_login_success(self):
        url = reverse("users_api:login")
        response = self.client.post(url, {
            "mobile": "09120000003",
            "password": "pass12345",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_invalid_credentials(self):
        url = reverse("users_api:login")
        response = self.client.post(url, {
            "mobile": "09120000003",
            "password": "wrongpass",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09120000004", password="pass12345")

    def test_me_requires_authentication(self):
        url = reverse("users_api:me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_update_profile(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("users_api:me")
        response = self.client.patch(url, {"first_name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")


class UserSearchTests(APITestCase):
    def setUp(self):
        self.searcher = User.objects.create_user(mobile="09120000005", password="pass12345")
        self.target = User.objects.create_user(mobile="09120000006", password="pass12345")
        self.client.force_authenticate(user=self.searcher)

    def test_search_missing_mobile(self):
        url = reverse("users_api:search")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_found(self):
        url = reverse("users_api:search")
        response = self.client.get(url, {"mobile": "09120000006"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["mobile"], "09120000006")

    def test_search_not_found(self):
        url = reverse("users_api:search")
        response = self.client.get(url, {"mobile": "09120099999"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)