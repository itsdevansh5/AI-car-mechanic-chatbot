from django.urls import path
from .views import booking, booking_detail, chat, diagnosis, health, upload

urlpatterns = [
    path("health/", health),
    path("chat/", chat),
    path("upload/", upload),
    path("diagnosis/", diagnosis),
    path("booking/", booking),
    path("booking/<int:booking_id>/", booking_detail),
]
