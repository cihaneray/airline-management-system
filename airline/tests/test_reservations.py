from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from airline.tests.base import AirlineAPITestCase


class ReservationAPITests(AirlineAPITestCase):
    def reservation_payload(self, flight, **overrides):
        payload = {
            "passenger_name": "Mehmet Demir",
            "passenger_email": "mehmet@example.com",
            "flight": flight.pk,
            "status": True,
        }
        payload.update(overrides)
        return payload

    def test_create_reservation_generates_code(self):
        flight = self.create_flight()

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(flight),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        code = response.data["reservation_code"]
        self.assertGreaterEqual(len(code), 5)
        self.assertRegex(code, r"^[A-Z0-9]+$")

    def test_client_cannot_set_reservation_code(self):
        flight = self.create_flight()

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(
                flight,
                reservation_code="CLIENT1",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(
            response.data["reservation_code"],
            "CLIENT1",
        )

    def test_duplicate_active_reservation_is_rejected(self):
        flight = self.create_flight()
        self.create_reservation(
            flight=flight,
            passenger_email="same@example.com",
        )

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(
                flight,
                passenger_email="SAME@example.com",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("passenger_email", response.data)

    def test_full_flight_is_rejected(self):
        airplane = self.create_airplane(capacity=1)
        flight = self.create_flight(airplane=airplane)
        self.create_reservation(flight=flight)

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(
                flight,
                passenger_email="second@example.com",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("flight", response.data)

    def test_cancelled_reservation_does_not_consume_capacity(self):
        airplane = self.create_airplane(capacity=1)
        flight = self.create_flight(airplane=airplane)
        self.create_reservation(flight=flight, status=False)

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(
                flight,
                passenger_email="active@example.com",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reservation_for_departed_flight_is_rejected(self):
        airplane = self.create_airplane()
        departure_time = timezone.now() - timedelta(hours=5)
        flight = self.create_flight(
            airplane=airplane,
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=2),
        )

        response = self.client.post(
            reverse("reservation-list"),
            self.reservation_payload(flight),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("flight", response.data)

    def test_cancel_action_sets_status_false(self):
        reservation = self.create_reservation()

        response = self.client.patch(
            reverse("reservation-cancel", args=[reservation.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertFalse(reservation.status)

    def test_cancel_action_rejects_already_cancelled_reservation(self):
        reservation = self.create_reservation(status=False)

        response = self.client.patch(
            reverse("reservation-cancel", args=[reservation.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reservation_delete_route_is_not_available(self):
        reservation = self.create_reservation()

        response = self.client.delete(
            reverse("reservation-detail", args=[reservation.pk])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_patch_cannot_change_reservation_code_or_created_at(self):
        reservation = self.create_reservation()
        original_code = reservation.reservation_code
        original_created_at = reservation.created_at

        response = self.client.patch(
            reverse("reservation-detail", args=[reservation.pk]),
            {
                "reservation_code": "CHANGED1",
                "created_at": "2030-01-01T00:00:00Z",
                "passenger_name": "Updated Passenger",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.reservation_code, original_code)
        self.assertEqual(reservation.created_at, original_created_at)
        self.assertEqual(
            reservation.passenger_name,
            "Updated Passenger",
        )

    def test_list_reservations(self):
        self.create_reservation()

        response = self.client.get(reverse("reservation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_retrieve_reservation(self):
        reservation = self.create_reservation()

        response = self.client.get(
            reverse("reservation-detail", args=[reservation.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reservation_code"], reservation.reservation_code)

    def test_update_reservation_flight(self):
        reservation = self.create_reservation()
        new_airplane = self.create_airplane(tail_number="TC-NEW")
        new_flight = self.create_flight(airplane=new_airplane, flight_number="TK999")

        response = self.client.patch(
            reverse("reservation-detail", args=[reservation.pk]),
            {"flight": new_flight.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.flight.pk, new_flight.pk)
