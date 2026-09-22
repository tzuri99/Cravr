from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))

class Profile(models.Model):

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends & Family'),
        ('private', 'Private'),
    ]


    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='cover_photos/', null=True, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    privacy = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )

    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


    
@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    print(f"[DEBUG] post_save signal triggered, created={created}, user={instance.username}")
    if created:
        Profile.objects.get_or_create(user=instance)
        print(f"[DEBUG] Profile created for {instance.username}")


from allauth.socialaccount.models import SocialAccount

@receiver(post_save, sender=SocialAccount)
def mark_verified_on_social_account_creation(sender, instance, created, **kwargs):
    print(f"[DEBUG] SocialAccount signal triggered, created={created}")
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance.user)
        profile.is_verified = True
        profile.save()
        print(f"[DEBUG] Profile marked as verified for {instance.user.username}")