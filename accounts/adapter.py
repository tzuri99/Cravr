from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """
        If a Google account uses an email that already belongs
        to an existing Cravr user, connect Google to that user.
        """
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('email')

        if not email:
            return

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # Mark brand-new Google users so they can set a password
        request.session['google_new_user'] = True

        return user