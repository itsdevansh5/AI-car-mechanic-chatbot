from django.contrib import admin
from .models import Booking, Conversation, Diagnosis, MediaUpload, Message

admin.site.register([Conversation, Message, MediaUpload, Diagnosis, Booking])
