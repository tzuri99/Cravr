from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount

# =========================
# OTP Verification
# =========================

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))


# =========================
# User Profile
# =========================

class Profile(models.Model):

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends & Family'),
        ('private', 'Private'),
    ]


    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Email verification status
    is_verified = models.BooleanField(default=False)
    # Profile images
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='cover_photos/', null=True, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    # Control who can view the user's profile
    privacy = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
     # Login security
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username

# =========================
# Follow Relationship
# =========================

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
        # Prevent duplicate follow relationships
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


# =========================
# Block Relationship
# =========================

class Block(models.Model):
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking'
    )
    blocked = models.ForeignKey(
      User,
      on_delete=models.CASCADE,
      related_name='blocked_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"
    
# =========================
# Automatically Create Profile
# =========================

@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    print(f"[DEBUG] post_save signal triggered, created={created}, user={instance.username}")
    if created:
        Profile.objects.get_or_create(user=instance)
        print(f"[DEBUG] Profile created for {instance.username}")


# ============================
# Google Account Verification
# ============================


@receiver(post_save, sender=SocialAccount)
def mark_verified_on_social_account_creation(sender, instance, created, **kwargs):
    print(f"[DEBUG] SocialAccount signal triggered, created={created}")
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance.user)
        profile.is_verified = True
        profile.save()
        print(f"[DEBUG] Profile marked as verified for {instance.user.username}")

