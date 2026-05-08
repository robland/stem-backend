from rest_framework import status
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from accounts.serializer import RegisterSerializer


class LoginView(TokenObtainPairView):

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        refresh = response.data.pop("refresh")

        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            secure=True,   # ⚠️ en prod HTTPS
            samesite="Lax"
        )

        return response


class RefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get("refresh_token")

        request.data["refresh"] = refresh
        return super().post(request, *args, **kwargs)


def logout(request):
    response = Response()
    response.delete_cookie("refresh_token")
    return response


class RegisterView(APIView):

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                data=RegisterSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )




