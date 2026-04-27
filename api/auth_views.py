from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from merchants.models import Merchant

class CSRFView(APIView):
    authentication_classes = []
    permission_classes = []
    
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({'message': 'CSRF cookie set'})

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Please provide email and password'}, status=status.HTTP_400_BAD_REQUEST)

        # Allow login by email by finding the username first
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            try:
                merchant = user.merchant
                return Response({
                    'merchant_id': merchant.id,
                    'merchant_name': merchant.name,
                    'email': user.email
                })
            except Merchant.DoesNotExist:
                return Response({'error': 'User has no linked merchant account'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Successfully logged out'})

class MeView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            merchant = request.user.merchant
            return Response({
                'merchant_id': merchant.id,
                'merchant_name': merchant.name,
                'email': request.user.email
            })
        except Merchant.DoesNotExist:
            return Response({'error': 'No linked merchant account'}, status=status.HTTP_403_FORBIDDEN)
