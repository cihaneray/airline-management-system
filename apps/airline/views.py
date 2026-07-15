from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from filters import FlightFilter
from models import Airplane, Flight, Reservation
from serializers import AirplaneSerializer, FlightSerializer, ReservationSerializer


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def flights(self, request, pk=None):
        airplane = self.get_object()

        queryset = airplane.flights.select_related(
            'airplane',
        ).all()

        serializer = FlightSerializer(
            queryset,
            many=True,
            context={'request': request},
        )

        return Response(serializer.data)


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.select_related('airplane').all()
    serializer_class = FlightSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    ]
    ordering_fields = [
        'departure_time',
        'arrival_time',
        'flight_number',
    ]
    ordering = ['departure_time']

    @action(detail=True, methods=['get'])
    def reservations(self, request, pk=None):
        flight = self.get_object()

        queryset = flight.reservations.all()

        serializer = ReservationSerializer(
            queryset,
            many=True,
            context={'request': request},
        )

        return Response(serializer.data)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Reservation.objects
        .select_related('flight', 'flight__airplane')
        .all()
    )
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
