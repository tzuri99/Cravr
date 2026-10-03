from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django import forms
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm

from .models import OTP, Profile, Follow, Block

import base64
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# ==========================================
# Gmail helper
# ==========================================

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send'
]


def send_otp_email(
    email,
    code,
    subject='Your Cravr Verification Code'
):
    credentials = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )

    credentials.refresh(Request())

    service = build(
        'gmail',
        'v1',
        credentials=credentials,
        cache_discovery=False
    )

    message = EmailMessage()

    message.set_content(
        f'''
Welcome to Cravr!

Your OTP verification code is:

{code}

This code will expire in 5 minutes.
'''
    )

    message['To'] = email
    message['From'] = settings.GMAIL_SENDER_EMAIL
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    service.users().messages().send(
        userId='me',
        body={
            'raw': encoded_message
        }
    ).execute()


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
        if User.objects.filter(
            email__iexact=email
        ).exists():
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

        form = CustomUserCreationForm(
            request.POST
        )

        if form.is_valid():

            # Create user
            user = form.save()

            # Generate OTP
            code = OTP.generate_code()

            # Create OTP
            OTP.objects.create(
                user=user,
                code=code
            )

            # Send OTP email using Gmail API
            send_otp_email(
                user.email,
                code
            )

            # Save user ID in session
            request.session[
                'otp_user_id'
            ] = user.id

            return redirect(
                'verify_otp'
            )

    else:
        form = CustomUserCreationForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


# ==========================================
# Login
# ==========================================

def login_view(request):

    if request.method == 'POST':

        username = request.POST.get(
            'username'
        )

        # Check if account exists
        # and whether it is locked
        try:
            existing_user = (
                User.objects.get(
                    username=username
                )
            )

            profile = (
                existing_user.profile
            )

            if (
                profile.locked_until
                and timezone.now()
                < profile.locked_until
            ):
                minutes_left = int(
                    (
                        profile.locked_until
                        - timezone.now()
                    ).total_seconds()
                    / 60
                ) + 1

                return render(
                    request,
                    'accounts/login.html',
                    {
                        'form':
                            AuthenticationForm(),

                        'error':
                            f'Account locked due to too many failed attempts. Try again in {minutes_left} minute(s).'
                    }
                )

        except User.DoesNotExist:
            existing_user = None

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            # Successful login:
            # reset failed attempts
            user.profile.failed_login_attempts = 0
            user.profile.locked_until = None
            user.profile.save()

            # Check email verification
            if (
                not user.profile.is_verified
                and not user.is_superuser
            ):
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
            login(
                request,
                user
            )

            # Remember Me logic
            remember_me = request.POST.get(
                'remember_me'
            )

            if remember_me:
                # 14 days
                request.session.set_expiry(
                    1209600
                )
            else:
                request.session.set_expiry(
                    0
                )

            # Admin → Django Administration
            if user.is_staff:
                return redirect(
                    '/admin/'
                )

            # Normal User → Home
            return redirect(
                'home'
            )

        else:

            # Failed login:
            # increase failed attempts
            if existing_user:

                profile = (
                    existing_user.profile
                )

                profile.failed_login_attempts += 1

                if (
                    profile.failed_login_attempts
                    >= 5
                ):
                    profile.locked_until = (
                        timezone.now()
                        + timedelta(
                            minutes=15
                        )
                    )

                profile.save()

    else:
        form = AuthenticationForm()

    return render(
        request,
        'accounts/login.html',
        {
            'form': form
        }
    )


# ==========================================
# Logout
# ==========================================

def logout_view(request):

    logout(request)

    return redirect(
        'login'
    )


# ==========================================
# Google Login Redirect
# ==========================================

def google_login_redirect(request):

    if request.session.pop(
        'google_new_user',
        False
    ):
        return redirect(
            'set_password'
        )

    return redirect(
        'home'
    )


# ==========================================
# Set Password
# ==========================================

@login_required
def set_password_view(request):

    form = SetPasswordForm(
        request.user,
        request.POST or None
    )

    if request.method == 'POST':

        if form.is_valid():

            form.save()

            update_session_auth_hash(
                request,
                request.user
            )

            return redirect(
                'home'
            )

    return render(
        request,
        'accounts/set_password.html',
        {
            'form': form
        }
    )


# ==========================================
# Verify OTP
# ==========================================

def verify_otp_view(request):

    # Get user ID from session
    user_id = request.session.get(
        'otp_user_id'
    )

    if not user_id:
        return redirect(
            'register'
        )

    # Find user
    try:
        user = User.objects.get(
            id=user_id
        )

    except User.DoesNotExist:
        return redirect(
            'register'
        )

    if request.method == 'POST':

        entered_code = request.POST.get(
            'otp_code'
        )

        try:

            # Get latest unused OTP
            otp = OTP.objects.filter(
                user=user,
                code=entered_code,
                is_used=False
            ).latest(
                'created_at'
            )

            # Check if OTP expired
            if (
                timezone.now()
                > otp.created_at
                + timedelta(minutes=5)
            ):

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
            del request.session[
                'otp_user_id'
            ]

            # Go to login
            return redirect(
                'login'
            )

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
    user_id = request.session.get(
        'otp_user_id'
    )

    if not user_id:
        return redirect(
            'register'
        )

    # Find user
    try:
        user = User.objects.get(
            id=user_id
        )

    except User.DoesNotExist:
        return redirect(
            'register'
        )

    # Check if already verified
    if user.profile.is_verified:
        return redirect(
            'login'
        )

    # Generate new OTP
    code = OTP.generate_code()

    # Create new OTP
    OTP.objects.create(
        user=user,
        code=code
    )

    # Send new OTP using Gmail API
    send_otp_email(
        user.email,
        code,
        subject=(
            'Your New Cravr '
            'Verification Code'
        )
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
# Profile
# ==========================================

@login_required
def profile_view(request):

    profile = request.user.profile

    followers_count = request.user.followers.count()
    following_count = request.user.following.count()

    my_reviews = request.user.reviews.select_related(
        "restaurant"
    ).prefetch_related(
        "photos"
    )

    if request.method == 'POST':

        bio = request.POST.get('bio', '')
        profile.bio = bio

        privacy = request.POST.get(
            'privacy',
            'public'
        )
        profile.privacy = privacy

        if 'profile_picture' in request.FILES:
            profile.profile_picture = (
                request.FILES['profile_picture']
            )

        if 'cover_photo' in request.FILES:
            profile.cover_photo = (
                request.FILES['cover_photo']
            )

        profile.save()

        messages.success(
            request,
            'Your profile has been updated!'
        )

        return redirect('profile')

    return render(
        request,
        'accounts/profile.html',
        {
            'profile': profile,
            'followers_count': followers_count,
            'following_count': following_count,
            'my_reviews': my_reviews,
        }
    )


# ==========================================
# Follow
# ==========================================

@login_required
def follow_view(
    request,
    username
):

    target_user = User.objects.get(
        username=username
    )

    if target_user != request.user:

        Follow.objects.get_or_create(
            follower=request.user,
            following=target_user
        )

    return redirect(
        'user_profile',
        username=username
    )


# ==========================================
# Unfollow
# ==========================================

@login_required
def unfollow_view(
    request,
    username
):

    target_user = User.objects.get(
        username=username
    )

    Follow.objects.filter(
        follower=request.user,
        following=target_user
    ).delete()

    return redirect(
        'user_profile',
        username=username
    )


# ==========================================
# Block
# ==========================================

@login_required
def block_view(
    request,
    username
):

    target_user = User.objects.get(
        username=username
    )

    if target_user != request.user:

        Block.objects.get_or_create(
            blocker=request.user,
            blocked=target_user
        )

        # Remove both follow relationships

        Follow.objects.filter(
            follower=request.user,
            following=target_user
        ).delete()

        Follow.objects.filter(
            follower=target_user,
            following=request.user
        ).delete()

    return redirect(
        'user_profile',
        username=username
    )


# ==========================================
# Unblock
# ==========================================

@login_required
def unblock_view(
    request,
    username
):

    target_user = User.objects.get(
        username=username
    )

    Block.objects.filter(
        blocker=request.user,
        blocked=target_user
    ).delete()

    return redirect(
        'user_profile',
        username=username
    )


# ==========================================
# User Profile
# ==========================================

@login_required
def user_profile_view(
    request,
    username
):

    target_user = User.objects.get(
        username=username
    )

    profile = target_user.profile

    is_own_profile = (
        target_user == request.user
    )

    is_following = (
        Follow.objects.filter(
            follower=request.user,
            following=target_user
        ).exists()
    )

    is_followed_by = (
        Follow.objects.filter(
            follower=target_user,
            following=request.user
        ).exists()
    )

    followers_count = (
        target_user.followers.count()
    )

    following_count = (
        target_user.following.count()
    )

    mutual_friends_count = (
        Follow.objects.filter(
            follower=request.user,
            following__in=(
                Follow.objects.filter(
                    follower=target_user
                ).values(
                    'following'
                )
            )
        ).count()
    )

    # Check blocking status
    is_blocked_by_me = (
        Block.objects.filter(
            blocker=request.user,
            blocked=target_user
        ).exists()
    )

    is_blocking_me = (
        Block.objects.filter(
            blocker=target_user,
            blocked=request.user
        ).exists()
    )

    # Determine whether
    # the profile should be hidden

    blocked = False

    if not is_own_profile:

        # Other user blocked me
        if is_blocking_me:
            blocked = True

        # I blocked them:
        # still show their profile
        # so I can unblock them
        elif is_blocked_by_me:
            blocked = False

        # User privacy settings
        elif (
            profile.privacy
            == 'private'
        ):
            blocked = True

        elif (
            profile.privacy
            == 'friends'
        ):
            if not (
                is_following
                and is_followed_by
            ):
                blocked = True

    return render(
        request,
        'accounts/user_profile.html',
        {
            'profile_user':
                target_user,

            'profile':
                profile,

            'is_own_profile':
                is_own_profile,

            'is_following':
                is_following,

            'is_followed_by':
                is_followed_by,

            'followers_count':
                followers_count,

            'following_count':
                following_count,

            'mutual_friends_count':
                mutual_friends_count,

            'blocked':
                blocked,

            'is_blocked_by_me':
                is_blocked_by_me,

            'is_blocking_me':
                is_blocking_me,
        }
    )


# ==========================================
# Search Users
# ==========================================

@login_required
def search_users_view(request):

    query = request.GET.get(
        'q',
        ''
    )

    results = []

    if query:

        results = (
            User.objects.filter(
                username__icontains=query
            )
            .exclude(
                id=request.user.id
            )
        )

    return render(
        request,
        'accounts/search_users.html',
        {
            'query':
                query,

            'results':
                results,
        }
    )