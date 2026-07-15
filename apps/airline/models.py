from datetime import datetime

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Airplane(models.Model):
    tail_number: str = models.CharField(max_length=20, unique=True)
    model: str = models.CharField(max_length=100)
    capacity: int = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    production_year: int = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(timezone.now().year)
        ]
    )
    status: bool = models.BooleanField(default=True)

    class Meta:
        ordering: list[str] = ['tail_number']

    def __str__(self) -> str:
        return f'{self.tail_number} - {self.model}'


class Flight(models.Model):
    flight_number: str = models.CharField(max_length=20, unique=True)  # Check after wrote the function of flight number
    departure: str = models.CharField(max_length=150)
    destination: str = models.CharField(max_length=150)
    departure_time: datetime = models.DateTimeField()
    arrival_time: datetime = models.DateTimeField()

    airplane: Airplane = models.ForeignKey(
        Airplane,
        on_delete=models.PROTECT,
        related_name='flights',
    )

    class Meta:
        ordering: list[str] = ['departure_time']
        indexes: list[models.Index] = [
            models.Index(fields=['departure']),
            models.Index(fields=['destination']),
            models.Index(fields=['departure_time']),
            models.Index(fields=['airplane', 'departure_time']),
        ]

    def __str__(self) -> str:
        return self.flight_number


class Reservation(models.Model):
    passenger_name: str = models.CharField(max_length=150)
    passenger_email: str = models.EmailField()
    reservation_code: str = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
    )

    flight: Flight = models.ForeignKey(
        Flight,
        on_delete=models.PROTECT,
        related_name='reservations',
    )

    status: bool = models.BooleanField(default=True)
    created_at: datetime = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering: list[str] = ['-created_at']
        indexes: list[models.Index] = [
            models.Index(fields=['reservation_code']),
            models.Index(fields=['flight', 'status']),
            models.Index(fields=['passenger_email']),
        ]

    def __str__(self) -> str:
        return self.reservation_code
