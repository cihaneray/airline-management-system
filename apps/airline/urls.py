from django.urls import include, path
from rest_framework.routers import DefaultRouter

from views import AirplaneViewSet, FlightViewSet, ReservationViewSet

router = DefaultRouter()
router.register('airplanes', AirplaneViewSet, basename='airplane')
router.register('flights', FlightViewSet, basename='flight')
router.register('reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
]
