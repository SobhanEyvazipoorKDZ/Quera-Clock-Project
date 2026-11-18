from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.users.models import User


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserSerializer(user, context={"request": request}).data
        data.update(_tokens_for(user))
        return Response(data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        data = UserSerializer(user, context={"request": request}).data
        data.update(_tokens_for(user))
        return Response(data, status=status.HTTP_200_OK)


class RefreshAPIView(TokenRefreshView):
    permission_classes = (AllowAny,)


class LogoutAPIView(APIView):
    def post(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfilePictureAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get("profile_picture")
        if not file:
            return Response(
                {"profile_picture": "This file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.profile_picture = file
        user.save(update_fields=("profile_picture",))
        return Response(UserSerializer(user, context={"request": request}).data)

    def delete(self, request):
        user = request.user
        if user.profile_picture:
            user.profile_picture.delete(save=False)
            user.profile_picture = None
            user.save(update_fields=("profile_picture",))
        return Response(UserSerializer(user, context={"request": request}).data)


class PasswordChangeAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=("password",))
        return Response({"detail": "Password changed."})


class UserSearchAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        mobile = request.query_params.get("mobile")
        if not mobile:
            return Response(
                {"mobile": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return Response("User not found.", status=status.HTTP_404_NOT_FOUND)

        return Response(UserSerializer(user, context={"request": request}).data)