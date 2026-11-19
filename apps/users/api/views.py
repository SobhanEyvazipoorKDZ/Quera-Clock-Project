from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.api.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.users.models import User
from apps.users.api.throttles import AuthRateThrottle


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        data = UserSerializer(user, context={"request": request}).data
        data.update({"access": str(refresh.access_token), "refresh": str(refresh)})
        return Response(data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken.for_user(serializer.validated_data["user"])
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class RefreshAPIView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutAPIView(APIView):
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            RefreshToken(refresh).blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfilePictureAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile_picture = request.FILES.get("profile_picture")
        if not profile_picture:
            return Response(
                {"profile_picture": "This file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.profile_picture = profile_picture
        request.user.save(update_fields=["profile_picture"])
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def delete(self, request):
        if request.user.profile_picture:
            request.user.profile_picture.delete(save=False)
        request.user.profile_picture = None
        request.user.save(update_fields=["profile_picture"])
        return Response(UserSerializer(request.user, context={"request": request}).data)


class PasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed."})


class UserSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mobile = (request.query_params.get("mobile") or "").strip()
        if not mobile:
            return Response(
                {"mobile": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(mobile=mobile).first()
        if not user:
            raise NotFound("User not found.")
        return Response(UserSerializer(user, context={"request": request}).data)
