import mimetypes
from django.db import transaction
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Booking, Message
from .serializers import BookingSerializer, DiagnosisSerializer, MediaUploadSerializer
from .services import deterministic_reply, enough_for_diagnosis, get_conversation, save_diagnosis

MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED = {
    "image": {"image/jpeg", "image/png", "image/webp"},
    "audio": {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"},
    "video": {"video/mp4", "video/webm", "video/quicktime"},
}


def health(request):
    return JsonResponse({"status": "ok", "service": "ai-car-mechanic"})

@api_view(["POST"])
def chat(request):
    message = str(request.data.get("message", "")).strip()
    if not message:
        return Response({"detail": "message is required"}, status=400)
    conversation = get_conversation(request.data.get("session_id"))
    Message.objects.create(conversation=conversation, role="user", content=message)
    reply = deterministic_reply(message, conversation)
    if reply is None:
        reply = "I understand the car issue. Before I diagnose it, tell me the vehicle make/model/year and exactly when the symptom occurs (for example: cold start, idle, acceleration, braking, turning, or at a particular speed)."
    Message.objects.create(conversation=conversation, role="assistant", content=reply)
    return Response({
        "session_id": str(conversation.session_id),
        "reply": reply,
        "ready_for_diagnosis": enough_for_diagnosis(conversation),
        "history": list(conversation.messages.values("role", "content", "created_at")),
    })

@api_view(["POST"])
def upload(request):
    conversation = get_conversation(request.data.get("session_id"))
    file = request.FILES.get("file")
    if not file:
        return Response({"detail": "file is required"}, status=400)
    if file.size > MAX_FILE_SIZE:
        return Response({"detail": "Maximum file size is 20 MB."}, status=400)
    mime = file.content_type or mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    media_type = next((kind for kind, mimes in ALLOWED.items() if mime in mimes), None)
    if not media_type:
        return Response({"detail": "Unsupported file type. Use JPEG/PNG/WebP, MP3/WAV/OGG/MP4 audio, or MP4/WebM/MOV video."}, status=400)
    media = conversation.media.create(file=file, media_type=media_type, mime_type=mime, size_bytes=file.size)
    return Response({"session_id": str(conversation.session_id), "media": MediaUploadSerializer(media, context={"request": request}).data}, status=201)

@api_view(["POST"])
def diagnosis(request):
    conversation = get_conversation(request.data.get("session_id"))
    if not conversation.messages.filter(role="user").exists():
        return Response({"detail": "Start a troubleshooting conversation first."}, status=400)
    with transaction.atomic():
        result = save_diagnosis(conversation)
    return Response({"diagnosis": DiagnosisSerializer(result).data})

@api_view(["POST"])
def booking(request):
    conversation = get_conversation(request.data.get("session_id"))
    diagnosis_id = request.data.get("diagnosis_id")
    diagnosis = conversation.diagnoses.filter(id=diagnosis_id).first() if diagnosis_id else conversation.diagnoses.order_by("-created_at").first()
    required = ["customer_name", "phone", "preferred_date", "preferred_time", "service_type"]
    missing = [x for x in required if not request.data.get(x)]
    if missing:
        return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
    serializer = BookingSerializer(data={
        "customer_name": request.data["customer_name"],
        "phone": request.data["phone"],
        "preferred_date": request.data["preferred_date"],
        "preferred_time": request.data["preferred_time"],
        "service_type": request.data["service_type"],
    })
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    booking_obj = Booking.objects.create(conversation=conversation, diagnosis=diagnosis, **serializer.validated_data)
    return Response({"booking": BookingSerializer(booking_obj).data, "message": "Mechanic booking request created."}, status=201)

@api_view(["GET"])
def booking_detail(request, booking_id):
    try:
        booking_obj = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"detail": "Booking not found."}, status=404)
    return Response(BookingSerializer(booking_obj).data)
