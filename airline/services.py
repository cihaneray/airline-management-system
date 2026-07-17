from __future__ import annotations

import secrets
import string
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Airplane, Flight, Reservation

MINIMUM_FLIGHT_GAP = timedelta(hours=1)
RESERVATION_CODE_LENGTH = 8
RESERVATION_CODE_ATTEMPTS = 10

RESERVATION_CODE_CHARACTERS = string.ascii_uppercase + string.digits


def normalize_location(value: str) -> str:
    """
    Normalize a location value for comparisons.
    """
    return "".join(value.strip().lower().split())


def generate_reservation_code(length: int = RESERVATION_CODE_LENGTH) -> str:
    """
    Generate a random uppercase alphanumeric reservation code.

    This function does not guarantee the generated value to be unique.
    Use generate_unique_reservation_code() when creating a reservation.
    """
    if length < 5:
        raise ValueError("Reservation code length must be at least 5.")

    return "".join(secrets.choice(RESERVATION_CODE_CHARACTERS) for _ in range(length))


def get_flight_conflicts(
    *,
    airplane: Airplane,
    departure_time,
    arrival_time,
    exclude_flight_id: int | None = None,
) -> QuerySet[Flight]:
    """
    Return flights that conflict with a requested flight interval.

    A conflict exists when:

        existing departure < requested arrival + one hour

    and:

        existing arrival > requested departure - one hour

    This detects direct overlap and violations of the required one-hour gap before or after the requested flight.
    """
    queryset = Flight.objects.filter(
        airplane=airplane,
        departure_time__lt=arrival_time + MINIMUM_FLIGHT_GAP,
        arrival_time__gt=departure_time - MINIMUM_FLIGHT_GAP,
    )

    if exclude_flight_id is not None:
        queryset = queryset.exclude(pk=exclude_flight_id)

    return queryset.order_by("departure_time")


def validate_flight_data(
    *,
    airplane: Airplane,
    departure: str,
    destination: str,
    departure_time,
    arrival_time,
    exclude_flight_id: int | None = None,
) -> None:
    """
    Validate flight business rules.

    :raises rest_framework.exceptions.ValidationError:
    """
    errors: dict[str, Any] = {}

    if not airplane.status:
        errors["airplane"] = "An inactive airplane cannot be assigned to a flight."

    if not departure or not departure.strip():
        errors["departure"] = "Departure is required."

    if not destination or not destination.strip():
        errors["destination"] = "Destination is required."

    if (
        departure
        and destination
        and normalize_location(departure) == normalize_location(destination)
    ):
        errors["destination"] = "Departure and destination cannot be the same."

    if departure_time is None:
        errors["departure_time"] = "Departure time is required."

    if arrival_time is None:
        errors["arrival_time"] = "Arrival time is required."

    if (
        departure_time is not None
        and arrival_time is not None
        and arrival_time <= departure_time
    ):
        errors["arrival_time"] = "Arrival time must be after departure time."

    if errors:
        raise ValidationError(errors)

    conflicts = get_flight_conflicts(
        airplane=airplane,
        departure_time=departure_time,
        arrival_time=arrival_time,
        exclude_flight_id=exclude_flight_id,
    )

    if conflicts.exists():
        first_conflict = conflicts.first()
        raise ValidationError(
            {
                "airplane": (
                    "This airplane has another flight that overlaps the requested interval or "
                    "violates the required one-hour gap."
                ),
                "conflicting_flight": {
                    "id": first_conflict.id,
                    "flight_number": first_conflict.flight_number,
                    "departure_time": first_conflict.departure_time,
                    "arrival_time": first_conflict.arrival_time,
                },
            }
        )


@transaction.atomic
def create_flight(*, validated_data: dict[str, Any]) -> Flight:
    """
    Create a flight after validating airplane availability and conflicts.

    The airplane row is locked, so concurrent flight creation requests for the same airplane cannot both pass the conflict check.
    """
    airplane_value = validated_data.get("airplane")

    if airplane_value is None:
        raise ValidationError({"airplane": "Airplane is required."})

    airplane_id = (
        airplane_value.pk if isinstance(airplane_value, Airplane) else airplane_value
    )

    try:
        airplane = Airplane.objects.select_for_update().get(pk=airplane_id)
    except Airplane.DoesNotExist as exc:
        raise ValidationError({"airplane": "Airplane does not exist."}) from exc

    validate_flight_data(
        airplane=airplane,
        departure=validated_data.get("departure", ""),
        destination=validated_data.get("destination", ""),
        departure_time=validated_data.get("departure_time"),
        arrival_time=validated_data.get("arrival_time"),
    )

    flight_data = {**validated_data, "airplane": airplane}

    try:
        return Flight.objects.create(**flight_data)
    except IntegrityError as exc:
        raise ValidationError(
            {
                "detail": "The flight could not be created because one or more values violate rules."
            }
        ) from exc


@transaction.atomic
def update_flight(*, flight: Flight, validated_data: dict[str, Any]) -> Flight:
    """
    Update a flight while safely checking schedule conflicts.
    """
    try:
        locked_flight = (
            Flight.objects.select_for_update()
            .select_related("airplane")
            .get(pk=flight.pk)
        )
    except Flight.DoesNotExist as exc:
        raise ValidationError({"flight": "Flight does not exist."}) from exc

    requested_airplane = validated_data.get("airplane", locked_flight.airplane)
    airplane_id = (
        requested_airplane.pk
        if isinstance(requested_airplane, Airplane)
        else requested_airplane
    )

    try:
        locked_airplane = Airplane.objects.select_for_update().get(pk=airplane_id)
    except Airplane.DoesNotExist as exc:
        raise ValidationError(
            {"airplane": "The selected airplane does not exist."}
        ) from exc

    departure = validated_data.get("departure", locked_flight.departure)
    destination = validated_data.get("destination", locked_flight.destination)
    departure_time = validated_data.get("departure_time", locked_flight.departure_time)
    arrival_time = validated_data.get("arrival_time", locked_flight.arrival_time)

    validate_flight_data(
        airplane=locked_airplane,
        departure=departure,
        destination=destination,
        departure_time=departure_time,
        arrival_time=arrival_time,
        exclude_flight_id=locked_flight.pk,
    )

    for field, value in validated_data.items():
        setattr(locked_flight, field, value)

    locked_flight.airplane = locked_airplane

    try:
        locked_flight.save()
    except IntegrityError as exc:
        raise ValidationError(
            {
                "detail": "The flight could not be updated because one or more values violate rules."
            }
        ) from exc

    return locked_flight


def get_active_reservation_count(*, flight: Flight) -> int:
    """
    Return the number of active reservations for a flight.
    """
    return Reservation.objects.filter(flight=flight, status=True).count()


def get_available_seat_count(*, flight: Flight) -> int:
    """
    Return the remaining number of seats for a flight.
    """
    active_count = get_active_reservation_count(flight=flight)

    return max(flight.airplane.capacity - active_count, 0)


def validate_reservation_data(
    *,
    flight: Flight,
    passenger_name: str,
    passenger_email: str,
    status: bool = True,
    exclude_reservation_id: int | None = None,
) -> None:
    """
    Validate reservation business rules.
    """
    errors: dict[str, Any] = {}

    if not passenger_name or not passenger_name.strip():
        errors["passenger_name"] = "Passenger name is required."

    if not passenger_email or not passenger_email.strip():
        errors["passenger_email"] = "Passenger email is required."

    if flight.departure_time <= timezone.now():
        errors["flight"] = "A reservation cannot be created for a departed flight."

    if status:
        duplicate_query = Reservation.objects.filter(
            flight=flight,
            passenger_email__iexact=passenger_email.strip(),
            status=True,
        )

        if exclude_reservation_id is not None:
            duplicate_query = duplicate_query.exclude(pk=exclude_reservation_id)

        if duplicate_query.exists():
            errors["passenger_email"] = (
                "A reservation for this passenger already exists."
            )

        active_count = get_active_reservation_count(flight=flight)

        if exclude_reservation_id is not None:
            existing_active = Reservation.objects.filter(
                pk=exclude_reservation_id, flight=flight, status=True
            ).exists()

            if existing_active:
                active_count -= 1

        if active_count >= flight.airplane.capacity:
            errors["flight"] = "This flight has reached its capacity."

    if errors:
        raise ValidationError(errors)


@transaction.atomic
def create_reservation(*, validated_data: dict[str, Any]) -> Reservation:
    """
    Safely create a reservation.
    """
    flight_value = validated_data.get("flight")

    if flight_value is None:
        raise ValidationError({"flight": "A flight is required."})

    flight_id = flight_value.pk if isinstance(flight_value, Flight) else flight_value

    try:
        flight = (
            Flight.objects.select_for_update()
            .select_related("airplane")
            .get(pk=flight_id)
        )
    except Flight.DoesNotExist as exc:
        raise ValidationError({"flight": "Flight does not exist."}) from exc

    passenger_name = validated_data.get("passenger_name", "").strip()
    passenger_email = validated_data.get("passenger_email", "").strip().lower()
    reservation_status = validated_data.get("status", True)

    validate_reservation_data(
        flight=flight,
        passenger_name=passenger_name,
        passenger_email=passenger_email,
        status=reservation_status,
    )

    reservation_data = {
        **validated_data,
        "flight": flight,
        "passenger_name": passenger_name,
        "passenger_email": passenger_email,
    }

    reservation_data.pop("reservation_code", None)
    reservation_data.pop("created_at", None)

    last_error = None
    for _ in range(RESERVATION_CODE_ATTEMPTS):
        try:
            # Atomic block to create a savepoint.
            with transaction.atomic():
                return Reservation.objects.create(
                    **reservation_data,
                    reservation_code=generate_reservation_code(
                        length=RESERVATION_CODE_LENGTH
                    ),
                )
        except IntegrityError as exc:
            last_error = exc

    raise ValidationError(
        {
            "reservation_code": "A unique reservation code could not be generated. Please try again."
        }
    ) from last_error


@transaction.atomic
def update_reservation(
    *, reservation: Reservation, validated_data: dict[str, Any]
) -> Reservation:
    """
    Update a reservation safely.
    """
    try:
        locked_reservation = (
            Reservation.objects.select_for_update()
            .select_related("flight", "flight__airplane")
            .get(pk=reservation.pk)
        )
    except Reservation.DoesNotExist as exc:
        raise ValidationError({"reservation": "Reservation does not exist."}) from exc

    requested_flight = validated_data.get("flight", locked_reservation.flight)
    target_flight_id = (
        requested_flight.pk
        if isinstance(requested_flight, Flight)
        else requested_flight
    )

    flight_ids = sorted(
        {
            locked_reservation.flight_id,
            target_flight_id,
        }
    )

    locked_flights = {
        flight.pk: flight
        for flight in (
            Flight.objects.select_for_update()
            .select_related("airplane")
            .filter(pk__in=flight_ids)
            .order_by("pk")
        )
    }

    target_flight = locked_flights.get(target_flight_id)

    if target_flight is None:
        raise ValidationError({"flight": "The selected flight does not exist."})

    passenger_name = validated_data.get(
        "passenger_name", locked_reservation.passenger_name
    ).strip()
    passenger_email = (
        validated_data.get("passenger_email", locked_reservation.passenger_email)
        .strip()
        .lower()
    )
    new_status = validated_data.get("status", locked_reservation.status)

    validate_reservation_data(
        flight=target_flight,
        passenger_name=passenger_name,
        passenger_email=passenger_email,
        status=new_status,
        exclude_reservation_id=locked_reservation.pk,
    )

    protected_fields = {
        "reservation_code",
        "created_at",
    }

    for field, value in validated_data.items():
        if field not in protected_fields:
            setattr(locked_reservation, field, value)

    locked_reservation.flight = target_flight
    locked_reservation.passenger_name = passenger_name
    locked_reservation.passenger_email = passenger_email

    try:
        locked_reservation.save()
    except IntegrityError as exc:
        raise ValidationError(
            {
                "detail": "The reservation could not be updated because one or more values violate rules."
            }
        ) from exc

    return locked_reservation


@transaction.atomic
def cancel_reservation(*, reservation: Reservation) -> Reservation:
    """
    Cancel a reservation without deleting it.
    """
    try:
        locked_reservation = Reservation.objects.select_for_update().get(
            pk=reservation.pk
        )
    except Reservation.DoesNotExist as exc:
        raise ValidationError({"reservation": "Reservation does not exist."}) from exc

    if not locked_reservation.status:
        raise ValidationError(
            {"reservation": "This reservation has already been cancelled."}
        )

    locked_reservation.status = False
    locked_reservation.save(update_fields=["status"])

    return locked_reservation


def get_flight_availability(*, flight: Flight) -> dict[str, Any]:
    """
    Return a serializable availability summary for a flight.
    """
    active_reservations = get_active_reservation_count(flight=flight)

    capacity = flight.airplane.capacity
    available_seats = max(capacity - active_reservations, 0)

    return {
        "flight_id": flight.id,
        "flight_number": flight.flight_number,
        "airplane_id": flight.airplane_id,
        "airplane_tail_number": flight.airplane.tail_number,
        "capacity": capacity,
        "occupied_seats": active_reservations,
        "available_seats": available_seats,
        "is_full": available_seats == 0,
    }
