from datetime import timedelta

from django.db.models.deletion import ProtectedError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from airline.models import Airplane, Flight
from airline.tests.base import AirlineAPITestCase


class AirplaneAPITests(AirlineAPITestCase):
    def test_list_airplanes(self):
        self.create_airplane()

        response = self.client.get(reverse("airplane-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_create_airplane(self):
        payload = {
            "tail_number": "TC-ABC",
            "model": "Boeing 737-800",
            "capacity": 189,
            "production_year": 2018,
            "status": True,
        }

        response = self.client.post(
            reverse("airplane-list"),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Airplane.objects.filter(tail_number="TC-ABC").exists()
        )

    def test_duplicate_tail_number_is_rejected(self):
        self.create_airplane(tail_number="TC-ABC")

        response = self.client.post(
            reverse("airplane-list"),
            {
                "tail_number": "TC-ABC",
                "model": "Airbus A321",
                "capacity": 220,
                "production_year": 2021,
                "status": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tail_number", response.data)

    def test_patch_airplane(self):
        airplane = self.create_airplane()

        response = self.client.patch(
            reverse("airplane-detail", args=[airplane.pk]),
            {"status": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        airplane.refresh_from_db()
        self.assertFalse(airplane.status)

    def test_airplane_flights_action(self):
        airplane = self.create_airplane()
        self.create_flight(airplane=airplane)

        response = self.client.get(
            reverse("airplane-flights", args=[airplane.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["flight_number"], "TK100")

    def test_airplane_with_flights_cannot_be_deleted(self):
        airplane = self.create_airplane()
        self.create_flight(airplane=airplane)

        response = self.client.delete(
            reverse("airplane-detail", args=[airplane.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Airplane.objects.filter(pk=airplane.pk).exists())

    def test_filter_airplanes_by_status(self):
        self.create_airplane(tail_number="TC-ONE", status=True)
        self.create_airplane(tail_number="TC-TWO", status=False)

        response = self.client.get(
            reverse("airplane-list"),
            {"status": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tail_number"], "TC-ONE")
