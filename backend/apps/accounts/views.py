"""accounts/views.py"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from .models import User, AuditLog
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer, AuditLogSerializer
)
from .permissions import IsSuperAdmin, IsBranchManagerOrAbove, IsLoanOfficerOrAbove



from django.core.cache import cache as _cache

def _login_lockout_check(email: str):
    """Returns (is_locked, attempts_so_far)."""
    key = f'ql_login:{email.lower()}'
    n   = _cache.get(key, 0)
    return n >= 5, n

def _login_record_failure(email: str):
    key = f'ql_login:{email.lower()}'
    n   = _cache.get(key, 0) + 1
    _cache.set(key, n, 900)  # 15-minute window
    return n

def _login_clear(email: str):
    _cache.delete(f'ql_login:{email.lower()}')

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = (request.data.get('email') or '').strip().lower()

        # Check account lockout (5 failures → 15-min block)
        locked, attempts = _login_lockout_check(email)
        if locked:
            return Response(
                {'detail': 'Account locked after 5 failed attempts. Try again in 15 minutes.'},
                status=429,
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            _login_clear(email)          # Reset failure counter on success
            try:
                user = User.objects.get(email__iexact=email)
                AuditLog.objects.create(
                    user=user, action='User Login',
                    model_name='User', object_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
                # 2FA check
                if user.totp_enabled and user.totp_secret:
                    import jwt as pyjwt, time
                    from django.conf import settings as _s
                    try:
                        payload  = {'user_id': user.id, 'exp': int(time.time()) + 300, 'type': 'totp_temp'}
                        temp_jwt = pyjwt.encode(payload, _s.SECRET_KEY, algorithm='HS256')
                        return Response({'requires_2fa': True, 'temp_jwt': temp_jwt})
                    except Exception:
                        pass   # Fall through to normal login if PyJWT fails
            except User.DoesNotExist:
                pass
        else:
            n = _login_record_failure(email)
            remaining = max(5 - n, 0)
            if remaining <= 2 and remaining > 0:
                data = dict(response.data)
                data['detail'] = f"Invalid credentials. {remaining} attempt(s) remaining before lockout."
                response.data = data
            elif remaining == 0:
                response.data = {'detail': 'Account locked after 5 failed attempts. Try again in 15 minutes.'}
                response.status_code = 429

        return response


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Successfully logged out.'})
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AvatarUploadView(APIView):
    """Upload/update user avatar photo"""
    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)

        file = request.FILES['avatar']
        if not file.content_type.startswith('image/'):
            return Response({'detail': 'File must be an image'}, status=400)

        if file.size > 5 * 1024 * 1024:  # 5MB limit
            return Response({'detail': 'File must be less than 5MB'}, status=400)

        user = request.user

        # Save avatar (convert to base64 for simplicity)
        import base64
        file.seek(0)
        image_data = base64.b64encode(file.read()).decode('utf-8')
        user.avatar_url = f'data:{file.content_type};base64,{image_data}'
        user.save(update_fields=['avatar_url'])

        return Response({'avatar_url': user.avatar_url})


class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    filterset_fields  = ['role', 'branch', 'is_active']
    search_fields     = ['full_name', 'email', 'phone', 'staff_id']

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.select_related('branch')
        if user.role == User.Role.BRANCH_MANAGER:
            qs = qs.filter(branch=user.branch)
        # Loan Officer and BDO can only see staff in their branch
        elif user.role == User.Role.LOAN_OFFICER or user.role == User.Role.BDO:
            qs = qs.filter(branch=user.branch)
        return qs

    def perform_create(self, serializer):
        import secrets, string
        user = serializer.save()
        temp_pw = None

        # Only generate temp password if none was provided
        if not user.password:
            alphabet = string.ascii_letters + string.digits + "!@#$"
            temp_pw  = ''.join(secrets.choice(alphabet) for _ in range(12))
            user.set_password(temp_pw)
            user.save()

        # Send welcome email
        try:
            from apps.notifications.tasks import task_email_staff_welcome
            if temp_pw:
                task_email_staff_welcome.delay(user.id, temp_pw)
        except Exception:
            pass


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class  = UserSerializer
    permission_classes = [IsBranchManagerOrAbove]
    queryset = User.objects.select_related('branch')


class ChangePasswordView(APIView):
    def post(self, request):
        old_pw = request.data.get('old_password')
        new_pw = request.data.get('new_password')
        if not request.user.check_password(old_pw):
            return Response({'detail': 'Old password incorrect.'}, status=400)
        request.user.set_password(new_pw)
        request.user.save()
        return Response({'detail': 'Password updated successfully.'})


class AuditLogListView(generics.ListAPIView):
    serializer_class  = AuditLogSerializer
    permission_classes = [IsSuperAdmin]
    queryset = AuditLog.objects.select_related('user').all()
    filterset_fields = ['model_name']
    search_fields    = ['action', 'user__full_name']


class DashboardStatsView(APIView):
    """Returns high-level KPI data for the dashboard."""
    def get(self, request):
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        from apps.customers.models import Customer
        from django.db.models import Sum, Count
        from django.utils import timezone
        import datetime

        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Portfolio totals
        active_loans     = Loan.objects.filter(status='ACTIVE')
        total_portfolio  = float(active_loans.aggregate(t=Sum('principal'))['t'] or 0)
        total_balance    = float(active_loans.aggregate(t=Sum('balance'))['t'] or 0)

        # PAR 30 (balance of loans overdue > 30 days)
        import datetime as _dt
        par30_loans   = Loan.objects.filter(
            status__in=['ACTIVE', 'DEFAULT'],
            due_date__lt=today - _dt.timedelta(days=30)
        )
        par30_balance = float(par30_loans.aggregate(t=Sum('balance'))['t'] or 0)
        par30_ratio   = round(par30_balance / total_balance * 100, 2) if total_balance else 0

        # MTD collections
        mtd_collections = float(Payment.objects.filter(
            paid_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0)

        # Collection rate
        mtd_due = float(Loan.objects.filter(
            due_date__gte=month_start, due_date__lte=today,
            status__in=['ACTIVE', 'DEFAULT']
        ).aggregate(t=Sum('total_amount'))['t'] or 1)
        collection_rate = round(min(mtd_collections / mtd_due * 100, 100), 1)

        stats = {
            'total_customers':      Customer.objects.filter(is_active=True).count(),
            'new_customers_mtd':    Customer.objects.filter(created_at__date__gte=month_start).count(),
            'active_loans':         active_loans.count(),
            'total_loans':          Loan.objects.count(),
            'defaulted_loans':      Loan.objects.filter(status='DEFAULT').count(),
            'pending_applications': Loan.objects.filter(status='PENDING').count(),
            'total_portfolio':      round(total_portfolio, 2),
            'total_balance':        round(total_balance, 2),
            'mtd_disbursements':    float(Loan.objects.filter(
                disbursed_at__date__gte=month_start, status__in=['ACTIVE', 'CLOSED']
            ).aggregate(total=Sum('principal'))['total'] or 0),
            'mtd_loans_count':      Loan.objects.filter(
                disbursed_at__date__gte=month_start, status__in=['ACTIVE', 'CLOSED']
            ).count(),
            'mtd_collections':      round(mtd_collections, 2),
            'collection_rate':      collection_rate,
            'par30_balance':        round(par30_balance, 2),
            'par30_ratio':          par30_ratio,
            'written_off_mtd':      Loan.objects.filter(
                status='WRITTEN_OFF', updated_at__date__gte=month_start
            ).count(),
        }
        return Response(stats)


# ─── 2FA / TOTP VIEWS ─────────────────────────────────────────────────────────

class TOTPSetupView(APIView):
    """
    Step 1: Generate a TOTP secret + QR code for the logged-in user.
    The user scans the QR code with their authenticator app,
    then calls TOTPConfirmView to activate.
    """
    def get(self, request):
        from apps.accounts.totp import generate_totp_secret, get_qr_code_base64, get_totp_uri
        user = request.user
        if user.totp_enabled:
            return Response({'detail': '2FA is already enabled.'}, status=400)
        # Generate new secret (stored temporarily until confirmed)
        secret = generate_totp_secret()
        user.totp_secret = secret
        user.save(update_fields=['totp_secret'])
        return Response({
            'secret':      secret,
            'qr_code':     get_qr_code_base64(user.email, secret),
            'uri':         get_totp_uri(user.email, secret),
            'instruction': 'Scan the QR code with Google Authenticator or Authy, then POST the 6-digit code to /auth/totp/confirm/',
        })


class TOTPConfirmView(APIView):
    """
    Step 2: Verify the first TOTP token to activate 2FA.
    Returns 10 one-time backup codes.
    """
    def post(self, request):
        from apps.accounts.totp import verify_totp, generate_backup_codes
        token = request.data.get('token', '')
        user  = request.user
        if not user.totp_secret:
            return Response({'detail': 'Run GET /auth/totp/setup/ first.'}, status=400)
        if not verify_totp(user.totp_secret, token):
            return Response({'detail': 'Invalid TOTP token — check your authenticator app.'}, status=400)
        backup_codes = generate_backup_codes(10)
        user.totp_enabled      = True
        user.totp_backup_codes = backup_codes
        user.save(update_fields=['totp_enabled', 'totp_backup_codes'])
        return Response({
            'detail':       '2FA enabled successfully.',
            'backup_codes': backup_codes,
            'warning':      'Save these backup codes now — they will not be shown again.',
        })


class TOTPDisableView(APIView):
    """Disable 2FA (requires current password confirmation)."""
    def post(self, request):
        password = request.data.get('password', '')
        user = request.user
        if not user.check_password(password):
            return Response({'detail': 'Incorrect password.'}, status=400)
        user.totp_enabled = False
        user.totp_secret  = None
        user.totp_backup_codes = []
        user.save(update_fields=['totp_enabled', 'totp_secret', 'totp_backup_codes'])
        return Response({'detail': '2FA disabled.'})


class TOTPVerifyView(APIView):
    """
    Called during login when a user has 2FA enabled.
    Expects: { token, temp_jwt } — returns full access + refresh tokens.
    """
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        from rest_framework_simplejwt.tokens import AccessToken
        from apps.accounts.totp import verify_totp
        import json, base64 as b64

        temp_jwt = request.data.get('temp_jwt', '')
        token    = request.data.get('token', '')

        if not temp_jwt or not token:
            return Response({'detail': 'temp_jwt and token required.'}, status=400)

        # Decode temp JWT payload (not verified here — login view set it)
        try:
            payload_b64 = temp_jwt.split('.')[1]
            # Pad base64
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            payload = json.loads(b64.b64decode(payload_b64))
            user_id = payload.get('user_id')
        except Exception:
            return Response({'detail': 'Invalid temp_jwt.'}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=404)

        # Check backup code
        if '-' in str(token) and token.upper() in user.totp_backup_codes:
            codes = [c for c in user.totp_backup_codes if c != token.upper()]
            user.totp_backup_codes = codes
            user.save(update_fields=['totp_backup_codes'])
        elif not verify_totp(user.totp_secret, token):
            return Response({'detail': 'Invalid 2FA token.'}, status=401)

        # Issue real tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        _clear_attempts(email)  # Clear lockout counter on success
        refresh = RefreshToken.for_user(user)
        # If 2FA is enabled, return a temp JWT and require TOTP verification
        if user.totp_enabled and user.totp_secret:
            import jwt as pyjwt
            import time
            try:
                from django.conf import settings as django_settings
                temp_payload = {'user_id': user.id, 'exp': int(time.time()) + 300, 'type': 'totp_temp'}
                temp_jwt = pyjwt.encode(temp_payload, django_settings.SECRET_KEY, algorithm='HS256')
                return Response({'requires_2fa': True, 'temp_jwt': temp_jwt})
            except ImportError:
                pass  # PyJWT not available — fall through to normal login

        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UserSerializer(user).data,
        })


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/
    Sends a password reset email with a time-limited token.
    { email } → sends email with reset link
    """
    authentication_classes = []
    permission_classes     = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'detail': 'Email address is required.'}, status=400)

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Return 200 even if user not found — prevents email enumeration
            return Response({'detail': 'If that email exists, a reset link has been sent.'})

        # Generate a short-lived token (15 minutes)
        import secrets, hashlib
        from django.core.cache import cache
        token    = secrets.token_urlsafe(32)
        cache_key= f'pwd_reset:{hashlib.sha256(token.encode()).hexdigest()}'
        cache.set(cache_key, user.id, timeout=900)  # 15 minutes

        # Send email
        try:
            from django.core.mail import send_mail
            from django.conf import settings as _s
            reset_link = f"{getattr(_s, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
            send_mail(
                subject  = 'QuickLender — Password Reset Request',
                message  = f'Click the link below to reset your password (expires in 15 minutes):\n\n{reset_link}',
                from_email = _s.DEFAULT_FROM_EMAIL,
                recipient_list = [user.email],
                fail_silently  = True,
            )
        except Exception:
            pass

        AuditLog.objects.create(
            user=user, action='Password reset requested',
            model_name='User', object_id=str(user.id),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'If that email exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    { token, new_password } → sets new password
    """
    authentication_classes = []
    permission_classes     = [permissions.AllowAny]

    def post(self, request):
        import hashlib
        from django.core.cache import cache

        token        = (request.data.get('token') or '').strip()
        new_password = (request.data.get('new_password') or '').strip()

        if not token or not new_password:
            return Response({'detail': 'token and new_password are required.'}, status=400)
        if len(new_password) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=400)

        cache_key = f'pwd_reset:{hashlib.sha256(token.encode()).hexdigest()}'
        user_id   = cache.get(cache_key)

        if not user_id:
            return Response({'detail': 'Reset link is invalid or has expired.'}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=404)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        cache.delete(cache_key)

        AuditLog.objects.create(
            user=user, action='Password reset completed',
            model_name='User', object_id=str(user.id),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'detail': 'Password reset successfully. You can now log in.'})
