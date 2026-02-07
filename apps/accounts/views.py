from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = {
            "id": request.user.id,
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "roles": list(request.user.groups.values_list("name", flat=True)),
        }
        return Response(MeSerializer(payload).data)
