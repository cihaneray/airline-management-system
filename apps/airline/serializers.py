from datetime import timedelta, datetime

from django.utils import timezone
from rest_framework import serializers

from models import Airplane, Flight, Reservation
from services import create_reservation


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = [
            'id',
            'tail_number',
            'model',
            'capacity',
            'production_year',
            'status',
        ]

    def validate_production_year(self, value):
        current_year: int = timezone.now().year

        if value > current_year:
            raise serializers.ValidationError(
                'Production year cannot be in the future.'
            )

        return value


class FlightSerializer(serializers.ModelSerializer):
    airplane_detail = AirplaneSerializer(
        source='airplane',
        read_only=True,
    )

    class Meta:
        model = Flight
        fields = [
            'id',
            'flight_number',
            'departure',
            'destination',
            'departure_time',
            'arrival_time',
            'airplane',
            'airplane_detail',
        ]

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        departure: str = attrs.get(
            'departure',
            getattr(instance, 'departure', None)
        )
        destination: str = attrs.get(
            'destination',
            getattr(instance, 'destination', None)
        )
        departure_time: datetime = attrs.get(
            'departure_time',
            getattr(instance, 'departure_time', None)
        )
        arrival_time: datetime = attrs.get(
            'arrival_time',
            getattr(instance, 'arrival_time', None)
        )
        airplane: Airplane = attrs.get(
            'airplane',
            getattr(instance, 'airplane', None)
        )

        if departure.strip().lower() == destination.strip().lower():
            raise serializers.ValidationError(
                {
                    'destination': (
                        'Departure and destination cannot be the same.'
                    )
                }
            )

        if arrival_time <= departure_time:
            raise serializers.ValidationError(
                {
                    'arrival_time': (
                        'Arrival time must be after departure time.'
                    )
                }
            )

        if not airplane.status:
            raise serializers.ValidationError(
                {
                    'airplane': (
                        'An inactive airplane cannot be assigned to a flight.'
                    )
                }
            )

        minimum_gap: timedelta = timedelta(hours=1)

        conflicting_flights = Flight.objects.filter(
            airplane=airplane,
            departure_time__lt=arrival_time + minimum_gap,
            arrival_time__gt=departure_time - minimum_gap,
        )

        if instance:
            conflicting_flights = conflicting_flights.exclude(
                pk=instance.pk
            )

        if conflicting_flights.exists():
            raise serializers.ValidationError(
                {
                    'airplane': (
                        'This airplane has another flight that conflicts '
                        'with the requested time interval or violates the '
                        'minimum one-hour gap.'
                    )
                }
            )

        return attrs


class ReservationSerializer(serializers.ModelSerializer):
    reservation_code: str = serializers.CharField(read_only=True)
    created_at: datetime = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'passenger_name',
            'passenger_email',
            'reservation_code',
            'flight',
            'status',
            'created_at',
        ]
        read_only_fields = [
            'reservation_code',
            'created_at',
        ]

    def validate_flight(self, flight: Flight):
        if flight.departure_time <= timezone.now():
            raise serializers.ValidationError(
                'A reservation cannot be created for a departed flight.'
            )

        return flight

    def validate(self, attrs):
        request = self.context.get('request')

        if request and request.method == 'POST':
            flight: Flight = attrs.get('flight')
            passenger_email: str = attrs.get('passenger_email')

            duplicate_exists = Reservation.objects.filter(
                flight=flight,
                passenger_email__iexact=passenger_email,
                status=True,
            ).exists()

            if duplicate_exists:
                raise serializers.ValidationError(
                    {
                        'passenger_email': (
                            'This passenger already has an active reservation for this flight.'
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        return create_reservation(validated_data=validated_data)
