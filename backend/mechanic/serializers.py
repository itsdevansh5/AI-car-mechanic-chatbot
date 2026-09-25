from rest_framework import serializers
from .models import Booking, Diagnosis, MediaUpload

class MediaUploadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = MediaUpload
        fields = ["id", "media_type", "mime_type", "size_bytes", "url", "created_at"]
    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ["id", "summary", "likely_causes", "confidence", "checks", "recommended_service", "urgency", "safety_notes", "created_at"]

class BookingSerializer(serializers.ModelSerializer):
    diagnosis_id = serializers.IntegerField(source="diagnosis.id", read_only=True)
    class Meta:
        model = Booking
        fields = ["id", "diagnosis_id", "customer_name", "phone", "preferred_date", "preferred_time", "service_type", "status", "created_at"]
