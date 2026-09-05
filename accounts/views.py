from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import OTP, Profile
from django.contrib.admin.views.decorators import staff_member_required



# ==========================================
# Custom Registration Form
# ==========================================

class CustomUserCreationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="Email"
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password1',
            'password2'
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'This email is already registered.'
            )

        # Store email in lowercase
        return email.lower()


# ==========================================
# Register
# ==========================================

def register_view(request):

    if request.method == 'POST':

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            # Create user
            user = form.save()

            # Create profile
            Profile.objects.create(
                user=user,
                is_verified=False
            )

            # Generate OTP
            code = OTP.generate_code()

            # Create OTP
            OTP.objects.create(
                user=user,
                code=code
            )

            # Send OTP email
            send_mail(
                subject='Your Cravr Verification Code',
                message=f'Your OTP verification code is: {code}',
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )

            # Save user ID in session
            request.session['otp_user_id'] = user.id

            return redirect('verify_otp')

    else:
        form = CustomUserCreationForm()

    return render(
        request,
        'accounts/register.html',
        {'form': form}
    )


# ==========================================
# Login
# ==========================================

def login_view(request):

    if request.method == 'POST':

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            # Check email verification
            if not user.profile.is_verified:

                return render(
                    request,
                    'accounts/login.html',
                    {
                        'form': form,
                        'error':
                            'Please verify your email before logging in.'
                    }
                )

            # Login
            login(request, user)
#help system to differentiate whether the acc is user acc or admin acc
            if user.is_staff:

              return redirect('admin_dashboard')

            return redirect('home')

    else:
        form = AuthenticationForm()

    return render(
        request,
        'accounts/login.html',
        {'form': form}
    )


# ==========================================
# Logout
# ==========================================

def logout_view(request):

    logout(request)

    return redirect('login')


# ==========================================
# Verify OTP
# ==========================================

def verify_otp_view(request):

    # Get user ID from session
    user_id = request.session.get('otp_user_id')

    if not user_id:
        return redirect('register')

    # Find user
    try:
        user = User.objects.get(id=user_id)

    except User.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':

        entered_code = request.POST.get('otp_code')

        try:

            # Get latest unused OTP
            otp = OTP.objects.filter(
                user=user,
                code=entered_code,
                is_used=False
            ).latest('created_at')

            # Check if OTP expired
            if timezone.now() > otp.created_at + timedelta(minutes=5):

                return render(
                    request,
                    'accounts/verify_otp.html',
                    {
                        'error':
                            'Code expired. Please request a new one.'
                    }
                )

            # Mark OTP as used
            otp.is_used = True
            otp.save()

            # Verify user
            user.profile.is_verified = True
            user.profile.save()

            # Remove session
            del request.session['otp_user_id']

            # Go to login
            return redirect('login')

        except OTP.DoesNotExist:

            return render(
                request,
                'accounts/verify_otp.html',
                {
                    'error':
                        'Invalid or expired code.'
                }
            )

    return render(
        request,
        'accounts/verify_otp.html'
    )


# ==========================================
# Resend OTP
# ==========================================

def resend_otp_view(request):

    # Get user ID from session
    user_id = request.session.get('otp_user_id')

    if not user_id:
        return redirect('register')

    # Find user
    try:
        user = User.objects.get(id=user_id)

    except User.DoesNotExist:
        return redirect('register')

    # Check if already verified
    if user.profile.is_verified:
        return redirect('login')

    # Generate new OTP
    code = OTP.generate_code()

    # Create new OTP
    OTP.objects.create(
        user=user,
        code=code
    )

    # Send new OTP
    send_mail(
        subject='Your New Cravr Verification Code',
        message=f'Your new OTP verification code is: {code}',
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return render(
        request,
        'accounts/verify_otp.html',
        {
            'success':
                'A new verification code has been sent to your email.'
        }
    )



# ==========================================
# Admin Dashboard (Review Restaurant Submissions)
# ==========================================

@staff_member_required
def admin_dashboard_view(request):

    # TODO: 等 restaurants app 的 Restaurant model 完成后，
    # 取消注释下面这段，改去用真实数据

    # from restaurants.models import Restaurant
    # pending_submissions = Restaurant.objects.filter(status='pending')

    # if request.method == 'POST':
    #     submission_id = request.POST.get('submission_id')
    #     action = request.POST.get('action')  # 'approve' 或 'reject'
    #     submission = Restaurant.objects.get(id=submission_id)
    #     if action == 'approve':
    #         submission.status = 'approved'
    #     elif action == 'reject':
    #         submission.status = 'rejected'
    #     submission.save()
    #     return redirect('admin_dashboard')

    return render(
        request,
        'accounts/admin_dashboard.html',
        {'submissions': []}  # 暂时给空列表，避免报错
    )

