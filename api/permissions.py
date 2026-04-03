from django.conf import settings
from rest_framework.permissions import BasePermission


class ApiKeyPermission(BasePermission):
    message = "Missing or invalid API key."

    def has_permission(self, request, view):
        expected_key = getattr(settings, "API_AUTH_KEY", "")
        if not expected_key:
            return False

        header_key = request.META.get("HTTP_X_API_KEY", "").strip()
        if header_key and header_key == expected_key:
            return True

        auth_header = request.META.get("HTTP_AUTHORIZATION", "").strip()
        if auth_header.lower().startswith("apikey "):
            token = auth_header.split(" ", 1)[1].strip()
            return token == expected_key

        return False
