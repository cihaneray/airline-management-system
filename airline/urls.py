from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AirplaneViewSet, FlightViewSet, ReservationViewSet

router = DefaultRouter()

router.register(r'airplanes', AirplaneViewSet, basename='airplane')
router.register(r'flights', FlightViewSet, basename='flight')
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
]
