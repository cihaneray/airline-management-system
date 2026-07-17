from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from airline.models import Airplane, Flight, Reservation
from airline.services import (
    cancel_reservation,
    create_reservation,
    generate_reservation_code,
    get_flight_availability,
    update_flight,
    update_reservation,
)


class ReservationServiceTests(TestCase):
    def setUp(self):
        self.airplane = Airplane.objects.create(
            tail_number="TC-SVC",
            model="Airbus A320",
            capacity=1,
            production_year=2020,
            status=True,
        )
        departure_time = timezone.now() + timedelta(days=3)
        self.flight = Flight.objects.create(
            flight_number="TK-SVC",
            departure="Istanbul",
            destination="London",
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=4),
            airplane=self.airplane,
        )

    def test_generated_code_is_alphanumeric_and_minimum_length(self):
        code = generate_reservation_code()

        self.assertGreaterEqual(len(code), 5)
        self.assertTrue(code.isalnum())
        self.assertEqual(code, code.upper())

    def test_create_reservation_uses_normalized_email(self):
        reservation = create_reservation(
            validated_data={
                "passenger_name": "  Ayse Yilmaz  ",
                "passenger_email": "AYSE@EXAMPLE.COM ",
                "flight": self.flight,
                "status": True,
            }
        )

        self.assertEqual(reservation.passenger_name, "Ayse Yilmaz")
        self.assertEqual(reservation.passenger_email, "ayse@example.com")

    def test_cancel_reservation(self):
        reservation = Reservation.objects.create(
            passenger_name="Active",
            passenger_email="active@example.com",
            reservation_code="ACT12345",
            flight=self.flight,
            status=True,
        )

        cancelled = cancel_reservation(reservation=reservation)

        self.assertFalse(cancelled.status)

    def test_flight_availability(self):
        Reservation.objects.create(
            passenger_name="Active",
            passenger_email="active@example.com",
            reservation_code="ACT12345",
            flight=self.flight,
            status=True,
        )

        data = get_flight_availability(flight=self.flight)

        self.assertEqual(data["capacity"], 1)
        self.assertEqual(data["occupied_seats"], 1)
        self.assertEqual(data["available_seats"], 0)
        self.assertTrue(data["is_full"])

    def test_update_flight_service(self):
        new_destination = "Berlin"
        updated_flight = update_flight(
            flight=self.flight,
            validated_data={"destination": new_destination}
        )
        self.assertEqual(updated_flight.destination, new_destination)

    def test_update_reservation_service(self):
        reservation = Reservation.objects.create(
            passenger_name="Old Name",
            passenger_email="old@example.com",
            reservation_code="OLD12345",
            flight=self.flight,
            status=True,
        )
        new_name = "New Name"
        updated_reservation = update_reservation(
            reservation=reservation,
            validated_data={"passenger_name": new_name}
        )
        self.assertEqual(updated_reservation.passenger_name, new_name)
