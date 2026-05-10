import uuid
from datetime import timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from private_storage.fields import PrivateFileField


class Creator(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="creator_profiles/", blank=True)

    def __str__(self) -> str:
        return self.name


class Content(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.PROTECT, related_name="contents")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    media_file = PrivateFileField(upload_to="content/")
    preview_image = models.ImageField(upload_to="previews/", blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.creator})"


class PaymentSettings(models.Model):
    bank_details = models.TextField(blank=True)
    paypal_email = models.EmailField(blank=True)
    crypto_address = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Payment settings"
        verbose_name_plural = "Payment settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "PaymentSettings":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "Payment settings"


class PaymentRequest(models.Model):
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        PAYPAL = "paypal", "PayPal"
        CRYPTO = "crypto", "Crypto"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    content = models.ForeignKey(Content, on_delete=models.PROTECT, related_name="payment_requests")
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    evidence_file = PrivateFileField(upload_to="evidence/", blank=True, null=True)
    transaction_hash = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)
    request_slug = models.SlugField(unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expiry_at = models.DateTimeField(null=True, blank=True)
    fan_email = models.EmailField(blank=True)

    def save(self, *args, **kwargs):
        if not self.request_slug:
            self.request_slug = uuid.uuid4().hex[:12]
        return super().save(*args, **kwargs)

    def approve(self):
        now = timezone.now()
        self.status = self.Status.APPROVED
        self.approved_at = now
        self.expiry_at = now + timedelta(hours=24)
        self.admin_note = ""

    def reject(self, note: str):
        self.status = self.Status.REJECTED
        self.admin_note = note or ""
        self.approved_at = None
        self.expiry_at = None

    @property
    def is_access_active(self) -> bool:
        if self.status != self.Status.APPROVED or not self.expiry_at:
            return False
        return timezone.now() < self.expiry_at

    def __str__(self) -> str:
        return f"{self.request_slug} - {self.content} ({self.status})"
