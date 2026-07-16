from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from airline.models import Airplane, Flight, Reservation


class AirlineAPITestCase(APITestCase):
    password = "StrongPassword123!"

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.password,
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def create_airplane(self, **overrides):
        data = {
            "tail_number": "TC-NRT",
            "model": "Airbus A320",
            "capacity": 2,
            "production_year": 2020,
            "status": True,
        }
        data.update(overrides)
        return Airplane.objects.create(**data)

    def create_flight(self, airplane=None, **overrides):
        airplane = airplane or self.create_airplane()
        departure_time = timezone.now() + timedelta(days=5)
        data = {
            "flight_number": "TK100",
            "departure": "Istanbul Airport",
            "destination": "Heathrow Airport",
            "departure_time": departure_time,
            "arrival_time": departure_time + timedelta(hours=4),
            "airplane": airplane,
        }
        data.update(overrides)
        return Flight.objects.create(**data)

    def create_reservation(self, flight=None, **overrides):
        flight = flight or self.create_flight()
        data = {
            "passenger_name": "Ayse Yilmaz",
            "passenger_email": "ayse@example.com",
            "reservation_code": "ABC12345",
            "flight": flight,
            "status": True,
        }
        data.update(overrides)
        return Reservation.objects.create(**data)
