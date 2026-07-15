import django_filters

from models import Flight


class FlightFilter(django_filters.FilterSet):
    departure = django_filters.CharFilter(
        field_name='departure',
        lookup_expr='icontains',
    )
    destination = django_filters.CharFilter(
        field_name='destination',
        lookup_expr='icontains',
    )

    departure_date = django_filters.DateFilter(
        field_name='departure_time',
        lookup_expr='date',
    )
    departure_date_from = django_filters.DateFilter(
        field_name='departure_time',
        lookup_expr='date__gte',
    )
    departure_date_to = django_filters.DateFilter(
        field_name='departure_time',
        lookup_expr='date__lte',
    )

    arrival_date = django_filters.DateFilter(
        field_name='arrival_time',
        lookup_expr='date',
    )

    airplane = django_filters.NumberFilter(
        field_name='airplane_id',
    )

    class Meta:
        model = Flight
        fields = [
            'departure',
            'destination',
            'departure_date',
            'departure_date_from',
            'departure_date_to',
            'arrival_date',
            'airplane'
        ]
