from datetime import datetime, timedelta, time

import django_filters
from django.db.models import F
from django.utils import timezone

from .models import Flight


class FlightFilter(django_filters.FilterSet):
    departure = django_filters.CharFilter(field_name='departure', lookup_expr='icontains')
    destination = django_filters.CharFilter(field_name='destination', lookup_expr='icontains')
    airplane = django_filters.NumberFilter(field_name='airplane_id')

    departure_date = django_filters.DateFilter(method='filter_departure_date')
    departure_date_from = django_filters.DateTimeFilter(field_name='departure_time', lookup_expr='gte')
    departure_date_to = django_filters.DateTimeFilter(field_name='departure_time', lookup_expr='lte')

    upcoming = django_filters.BooleanFilter(method='filter_upcoming')
    past = django_filters.BooleanFilter(method='filter_past')
    available = django_filters.BooleanFilter(method='filter_available')

    class Meta:
        model = Flight
        fields = [
            'departure',
            'destination',
            'departure_date',
            'departure_date_from',
            'departure_date_to',
            'airplane',
            'upcoming',
            'past',
            'available',
        ]

    def filter_departure_date(self, queryset, name, value):
        current_timezone = timezone.get_current_timezone()

        start = timezone.make_aware(
            datetime.combine(value, time.min),
            current_timezone
        )
        end = start + timedelta(days=1)

        return queryset.filter(
            departure_time__gte=start,
            departure_time__lt=end
        )

    def filter_upcoming(self, queryset, name, value):
        if value is True:
            return queryset.filter(departure_time__gte=timezone.now())
        return queryset

    def filter_past(self, queryset, name, value):
        if value is True:
            return queryset.filter(departure_time__lt=timezone.now())
        return queryset

    def filter_available(self, queryset, name, value):
        if value is True:
            return queryset.filter(active_reservation_count__lt=F('airplane__capacity'))
        return queryset
