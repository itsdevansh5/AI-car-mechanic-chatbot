import uuid
from django.db import models

class Conversation(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Message(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class MediaUpload(models.Model):
    TYPE_CHOICES = [("image", "Image"), ("audio", "Audio"), ("video", "Video")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    media_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class Diagnosis(models.Model):
    URGENCY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="diagnoses")
    summary = models.TextField()
    likely_causes = models.JSONField(default=list)
    confidence = models.PositiveSmallIntegerField(default=50)
    checks = models.JSONField(default=list)
    recommended_service = models.CharField(max_length=255)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default="medium")
    safety_notes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class Booking(models.Model):
    STATUS_CHOICES = [("requested", "Requested"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="bookings")
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    service_type = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)
