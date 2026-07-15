from datetime import datetime

from rest_framework import serializers

from .models import Airplane, Flight, Reservation
from .services import create_flight, create_reservation, update_flight, update_reservation


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


class FlightSerializer(serializers.ModelSerializer):
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
        ]

    def create(self, validated_data):
        return create_flight(validated_data=validated_data)

    def update(self, instance, validated_data):
        return update_flight(flight=instance, validated_data=validated_data)


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

    def create(self, validated_data):
        return create_reservation(validated_data=validated_data)

    def update(self, instance, validated_data):
        return update_reservation(reservation=instance, validated_data=validated_data)
