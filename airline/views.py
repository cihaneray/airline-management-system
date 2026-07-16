from django.db.models import Count, Q, Model
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import FlightFilter
from .models import Airplane, Reservation, Flight
from .serializers import AirplaneSerializer, FlightSerializer, ReservationSerializer
from .services import cancel_reservation


class AirplaneViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing airplanes.

    Endpoints:
        GET     /api/airplanes
        POST    /api/airplanes
        GET     /api/airplanes/{id}
        GET     /api/airplanes/{id}/flights
        DELETE  /api/airplanes/{id}
        PATCH   /api/airplanes/{id}
    """

    serializer_class = AirplaneSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = {
        'status': ['exact'],
        'model': ['exact', 'icontains'],
        'production_year': ['exact', 'gte', 'lte'],
        'capacity': ['exact', 'gte', 'lte'],
    }

    search_fields = [
        'model',
        'tail_number',
    ]

    ordering_fields = [
        'id',
        'tail_number',
        'model',
        'capacity',
        'production_year',
        'status',
    ]

    ordering = ['tail_number']

    def get_queryset(self):
        """
        Return airplanes and include useful calculated values.

        flight_count:
            Total number of flights assigned to the airplane.

        active_reservation_count:
            Total active reservations across the airplane's flights.
        """
        return (
            Airplane.objects
            .annotate(
                flight_count=Count('flights', distinct=True),
                active_reservation_count=Count(
                    'flights__reservations',
                    filter=Q(flights__reservations__status=True),
                    distinct=True,
                ),
            )
            .order_by('tail_number')
        )

    @action(detail=True, methods=['get'], url_path='flights')
    def flights(self, request, pk=None):
        """
        Return all flights assigned to a specific airplane.

        Optional query parameters:
            upcoming=true
            past=true
            ordering=departure_time
            ordering=-departure_time
        """
        airplane = self.get_object()

        queryset = (
            airplane.flights.select_related(
                'airplane',
            ).annotate(
                active_reservation_count=Count(
                    'reservations',
                    filter=Q(reservations__status=True),
                )
            )
        )

        upcoming = request.query_params.get('upcoming')
        past = request.query_params.get('past')

        if upcoming and upcoming.lower() == 'true':
            queryset = queryset.filter(
                departure_time__gte=timezone.now()
            )

        if past and past.lower() == 'true':
            queryset = queryset.filter(
                departure_time__lt=timezone.now()
            )

        ordering = request.query_params.get('ordering', 'departure_time')

        allowed_ordering = {
            'departure_time',
            '-departure_time',
            'arrival_time',
            '-arrival_time',
            'flight_number',
            '-flight_number',
        }

        if ordering not in allowed_ordering:
            ordering = 'departure_time'

        queryset = queryset.order_by(ordering)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = FlightSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        serializer = FlightSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deletion when the airplane is protected by related flights.
        TODO:
        This is relevant when Flight.airplane uses on_delete=PROTECT.
        """
        airplane = self.get_object()

        try:
            airplane.delete()
        except ProtectedError:
            return Response(
                {
                    'detail': 'This airplane cannot be deleted because it is assigned to one or more flights.'
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class FlightViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing flights.

    Endpoints:
        GET     /api/flights/
        POST    /api/flights/
        GET     /api/flights/{id}/
        PATCH   /api/flights/{id}/
        DELETE  /api/flights/{id}/
        GET     /api/flights/{id}/reservations/
    """

    serializer_class = FlightSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]

    filterset_class = FlightFilter

    search_fields = [
        'flight_number',
        'departure',
        'destination',
        'airplane__tail_number',
        'airplane__model',
    ]

    ordering_fields = [
        'id',
        'flight_number',
        'departure',
        'destination',
        'departure_time',
        'arrival_time',
    ]

    ordering = ['departure_time']

    def get_queryset(self):
        """
        Return flights with their airplane and active reservation count.
        """
        return (
            Flight.objects
            .select_related('airplane')
            .annotate(
                active_reservation_count=Count(
                    'reservations',
                    filter=Q(reservations__status=True),
                )
            )
            .order_by('departure_time')
        )

    @action(detail=True, methods=['get'], url_path='reservations')
    def reservations(self, request, pk=None):
        """
        Return reservations for a particular flight.

        Optional parameters:
            status=true
            status=false
            search=passenger
            ordering=created_at
            ordering=-created_at
        """
        flight = self.get_object()

        queryset = flight.reservations.select_related(
            'flight',
            'flight__airplane',
        )

        reservation_status = request.query_params.get('status')

        if reservation_status is not None:
            normalized_status = reservation_status.lower()

            if normalized_status == 'true':
                queryset = queryset.filter(status=True)
            elif normalized_status == 'false':
                queryset = queryset.filter(status=False)

        search_value = request.query_params.get('search')

        if search_value:
            queryset = queryset.filter(
                Q(passenger_name__icontains=search_value)
                | Q(passenger_email__icontains=search_value)
                | Q(reservation_code__icontains=search_value)
            )

        ordering = request.query_params.get('ordering', '-created_at')

        allowed_ordering = {
            'created_at',
            '-created_at',
            'passenger_name',
            '-passenger_name',
            'reservation_code',
            '-reservation_code',
        }

        if ordering not in allowed_ordering:
            ordering = '-created_at'

        queryset = queryset.order_by(ordering)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ReservationSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        serializer = ReservationSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='availability')
    def availability(self, request, pk=None):
        """
        Return the current capacity information for a flight.

        Endpoint:
            GET /api/flights/{id}/availability
        """
        flight = self.get_object()

        capacity = flight.airplane.capacity
        occupied_seats = flight.active_reservation_count
        available_seats = max(capacity - occupied_seats, 0)

        return Response({
            'flight_id': flight.id,
            'flight_number': flight.flight_number,
            'airplane': flight.airplane.tail_number,
            'capacity': capacity,
            'occupied_seats': occupied_seats,
            'available_seats': available_seats,
            'is_full': available_seats == 0
        },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deletion when the flight has protected reservations.
        """
        flight = self.get_object()

        try:
            flight.delete()
        except ProtectedError:
            return Response(
                {
                    'detail': 'This flight cannot be deleted because it has active reservations.'
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoints for managing reservations.

    Endpoints:
        GET     /api/reservations/
        POST    /api/reservations/
        GET     /api/reservations/{id}/
        PATCH   /api/reservations/{id}/
    """

    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]

    filterset_fields = {
        'flight': ['exact'],
        'status': ['exact'],
        'created_at': ['exact', 'date', 'gte', 'lte'],
    }

    search_fields = [
        'passenger_name',
        'passenger_email',
        'reservation_code',
        'flight__flight_number',
    ]

    ordering_fields = [
        'id',
        'passenger_name',
        'passenger_email',
        'reservation_code',
        'created_at',
        'status'
    ]

    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Reservation.objects
            .select_related('flight', 'flight__airplane')
            .order_by('-created_at')
        )

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel a reservation without deleting it.

        Endpoint:
            PATCH /api/reservations/{id}/cancel
        """
        reservation = cancel_reservation(
            reservation=self.get_object()
        )

        serializer = self.get_serializer(reservation)

        return Response(serializer.data, status=status.HTTP_200_OK)
