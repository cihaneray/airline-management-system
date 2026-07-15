from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Flight, Reservation
from .utils import generate_unique_reservation_code


@transaction.atomic
def create_reservation(*, validated_data):
    flight_id: str = validated_data['flight'].id

    flight: Flight = (
        Flight.objects
        .select_for_update()
        .select_related('airplane')
        .get(pk=flight_id)
    )

    active_reservation_count: int = (
        Reservation.objects
        .filter(flight=flight, status=True)
        .count()
    )

    if active_reservation_count >= flight.airplane.capacity:
        raise ValidationError(
            {'flight': 'This flight has reached its capacity.'}
        )

    unique_reservation_code: str = generate_unique_reservation_code()

    reservation: Reservation = Reservation.objects.create(
        **validated_data,
        flight=flight,
        reservation_code=unique_reservation_code,
    )

    return reservation
