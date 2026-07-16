from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from airline.models import Flight
from airline.tests.base import AirlineAPITestCase


class FlightAPITests(AirlineAPITestCase):
    def valid_payload(self, airplane, **overrides):
        departure_time = timezone.now() + timedelta(days=10)
        payload = {
            "flight_number": "TK200",
            "departure": "Istanbul Airport",
            "destination": "Heathrow Airport",
            "departure_time": departure_time.isoformat(),
            "arrival_time": (
                departure_time + timedelta(hours=4)
            ).isoformat(),
            "airplane": airplane.pk,
        }
        payload.update(overrides)
        return payload

    def test_create_flight(self):
        airplane = self.create_airplane()

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(airplane),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Flight.objects.filter(flight_number="TK200").exists()
        )

    def test_arrival_before_departure_is_rejected(self):
        airplane = self.create_airplane()
        departure_time = timezone.now() + timedelta(days=10)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane,
                departure_time=departure_time.isoformat(),
                arrival_time=(
                    departure_time - timedelta(hours=1)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("arrival_time", response.data)

    def test_same_departure_and_destination_is_rejected(self):
        airplane = self.create_airplane()

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane,
                departure="Istanbul Airport",
                destination="  istanbul airport ",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destination", response.data)

    def test_inactive_airplane_is_rejected(self):
        airplane = self.create_airplane(status=False)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(airplane),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("airplane", response.data)

    def test_overlapping_flight_is_rejected(self):
        airplane = self.create_airplane()
        existing = self.create_flight(airplane=airplane)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane,
                flight_number="TK201",
                departure_time=(
                    existing.departure_time + timedelta(hours=1)
                ).isoformat(),
                arrival_time=(
                    existing.arrival_time + timedelta(hours=1)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("airplane", response.data)

    def test_less_than_one_hour_gap_is_rejected(self):
        airplane = self.create_airplane()
        existing = self.create_flight(airplane=airplane)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane,
                flight_number="TK202",
                departure_time=(
                    existing.arrival_time + timedelta(minutes=59)
                ).isoformat(),
                arrival_time=(
                    existing.arrival_time + timedelta(hours=3)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exactly_one_hour_gap_is_accepted(self):
        airplane = self.create_airplane()
        existing = self.create_flight(airplane=airplane)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane,
                flight_number="TK203",
                departure="Heathrow Airport",
                destination="Paris Charles de Gaulle",
                departure_time=(
                    existing.arrival_time + timedelta(hours=1)
                ).isoformat(),
                arrival_time=(
                    existing.arrival_time + timedelta(hours=3)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_same_time_is_allowed_for_different_airplanes(self):
        airplane_one = self.create_airplane(tail_number="TC-ONE")
        airplane_two = self.create_airplane(tail_number="TC-TWO")
        existing = self.create_flight(airplane=airplane_one)

        response = self.client.post(
            reverse("flight-list"),
            self.valid_payload(
                airplane_two,
                flight_number="TK204",
                departure_time=existing.departure_time.isoformat(),
                arrival_time=existing.arrival_time.isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_patch_does_not_conflict_with_itself(self):
        flight = self.create_flight()

        response = self.client.patch(
            reverse("flight-detail", args=[flight.pk]),
            {"destination": "Berlin Brandenburg Airport"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_flight_reservations_action(self):
        flight = self.create_flight()
        self.create_reservation(flight=flight)

        response = self.client.get(
            reverse("flight-reservations", args=[flight.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_availability_action(self):
        flight = self.create_flight()
        self.create_reservation(flight=flight)

        response = self.client.get(
            reverse("flight-availability", args=[flight.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["capacity"], 2)
        self.assertEqual(response.data["occupied_seats"], 1)
        self.assertEqual(response.data["available_seats"], 1)
        self.assertFalse(response.data["is_full"])

    def test_filter_by_departure(self):
        self.create_flight(
            flight_number="TK300",
            departure="Istanbul Airport",
        )
        self.create_flight(
            airplane=self.create_airplane(tail_number="TC-TWO"),
            flight_number="TK301",
            departure="Berlin Brandenburg Airport",
        )

        response = self.client.get(
            reverse("flight-list"),
            {"departure": "istanbul"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["flight_number"], "TK300")
