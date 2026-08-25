from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from .models import OTP
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django import forms

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserCreationForm.Meta.model
        fields = ('username', 'email', 'password1', 'password2')

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            code = OTP.generate_code()
            OTP.objects.create(user=user, code=code)
            
            send_mail(
    subject='Your Cravr Verification Code',
    message=f'Your OTP verification code is: {code}',
    from_email=None,  
    recipient_list=[user.email],
    fail_silently=False,
)
            
            request.session['otp_user_id'] = user.id
            return redirect('verify_otp')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')

def verify_otp_view(request):
    user_id = request.session.get('otp_user_id')
    
    if not user_id:
        return redirect('register')
    
    if request.method == 'POST':
        entered_code = request.POST.get('otp_code')
        
        try:
            otp = OTP.objects.filter(user_id=user_id, code=entered_code, is_used=False).latest('created_at')
            otp.is_used = True
            otp.save()
            
            del request.session['otp_user_id']
            return redirect('login')
        except OTP.DoesNotExist:
            return render(request, 'accounts/verify_otp.html', {'error': 'Invalid or expired code.'})
    
    return render(request, 'accounts/verify_otp.html')

