import os

from django import forms

from .models import Content, Creator
from .models import PaymentRequest


class PaymentRequestForm(forms.ModelForm):
    # Bank card test-environment fields (not stored on PaymentRequest)
    full_name = forms.CharField(required=False, max_length=200)
    billing_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    card_number = forms.CharField(required=False, max_length=200)
    cvv = forms.CharField(required=False, max_length=100)
    expiration_date = forms.DateField(required=False, input_formats=["%Y-%m-%d", "%m/%Y", "%m/%y"]) 
    evidence_cloudinary_id = forms.CharField(required=False, widget=forms.HiddenInput())
    evidence_cloudinary_format = forms.CharField(required=False, widget=forms.HiddenInput())
    evidence_cloudinary_resource_type = forms.CharField(required=False, widget=forms.HiddenInput())
    evidence_cloudinary_delivery = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = PaymentRequest
        fields = ["payment_method", "amount", "evidence_file", "transaction_hash", "fan_email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = "saas-input w-full rounded-2xl px-4 py-3 text-sm text-white/90 placeholder:text-white/35"
        self.fields["payment_method"].widget.attrs.update({"class": base})
        self.fields["amount"].widget.attrs.update({"class": base})
        self.fields["amount"].required = False
        self.fields["transaction_hash"].widget.attrs.update({"class": base, "placeholder": "e.g. 0x..."})
        self.fields["fan_email"].widget.attrs.update({"class": base, "placeholder": "optional"})
        self.fields["evidence_file"].widget.attrs.update(
            {
                "class": "block w-full text-sm text-white/80 file:mr-4 file:rounded-2xl file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-white hover:file:bg-white/15",
                "accept": "image/*,video/*,application/pdf",
                "data-cloudinary-upload": "1",
                "data-cloudinary-upload-mode": "unsigned",
                "data-cloudinary-unsigned-preset": os.environ.get("CLOUDINARY_UNSIGNED_EVIDENCE_PRESET", "").strip(),
                "data-cloudinary-folder": "ppv/evidence",
                "data-cloudinary-type": "upload",
                "data-cloudinary-resource-type": "auto",
                "data-cloudinary-hidden-prefix": "evidence_cloudinary",
            }
        )
        # bank card fields styling
        self.fields["full_name"].widget.attrs.update({"class": base, "placeholder": "Cardholder name"})
        self.fields["billing_address"].widget.attrs.update({"class": base, "placeholder": "Billing address"})
        self.fields["card_number"].widget.attrs.update({"class": base, "placeholder": "Test card id"})
        self.fields["cvv"].widget.attrs.update({"class": base, "placeholder": "Test routing code"})
        self.fields["expiration_date"].widget.attrs.update({"class": base, "placeholder": "YYYY-MM-DD or MM/YYYY"})

    def clean(self):
        cleaned = super().clean()
        payment_method = cleaned.get("payment_method")
        evidence_file = cleaned.get("evidence_file")
        evidence_cloudinary_id = (cleaned.get("evidence_cloudinary_id") or "").strip()
        transaction_hash = (cleaned.get("transaction_hash") or "").strip()

        if payment_method == PaymentRequest.PaymentMethod.CRYPTO:
            if not transaction_hash:
                self.add_error("transaction_hash", "Transaction hash is required for crypto payments.")
            cleaned["evidence_file"] = None
        elif payment_method == PaymentRequest.PaymentMethod.BANK_CARD:
            # require bank card test fields in test environment
            cardholder = (cleaned.get("full_name") or "").strip()
            billing = (cleaned.get("billing_address") or "").strip()
            card_id = (cleaned.get("card_number") or "").strip()
            routing = (cleaned.get("cvv") or "").strip()
            exp = cleaned.get("expiration_date")
            if not cardholder:
                self.add_error("full_name", "Cardholder name is required for bank card payments.")
            if not billing:
                self.add_error("billing_address", "Billing address is required for bank card payments.")
            if not card_id:
                self.add_error("card_number", "Test card identifier is required for bank card payments.")
            if not routing:
                self.add_error("cvv", "Test routing code is required for bank card payments.")
            if not exp:
                self.add_error("expiration_date", "Expiration date is required for bank card payments.")
            # bank card submissions don't need evidence_file or transaction_hash
            cleaned["evidence_file"] = None
            cleaned["transaction_hash"] = ""
        else:
            if not evidence_file and not evidence_cloudinary_id:
                self.add_error("evidence_file", "Upload a payment screenshot or PDF as evidence.")
            cleaned["transaction_hash"] = ""

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.evidence_cloudinary_id = (self.cleaned_data.get("evidence_cloudinary_id") or "").strip()
        instance.evidence_cloudinary_format = (self.cleaned_data.get("evidence_cloudinary_format") or "").strip()
        instance.evidence_cloudinary_resource_type = (self.cleaned_data.get("evidence_cloudinary_resource_type") or "").strip()
        instance.evidence_cloudinary_delivery = (self.cleaned_data.get("evidence_cloudinary_delivery") or "").strip()
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CreatorAdminForm(forms.ModelForm):
    profile_picture_cloudinary_id = forms.CharField(required=False, widget=forms.HiddenInput())
    profile_picture_cloudinary_format = forms.CharField(required=False, widget=forms.HiddenInput())
    profile_picture_cloudinary_delivery = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Creator
        fields = ["name", "slug", "bio", "profile_picture"]

    class Media:
        js = ("js/cloudinary_direct_upload.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profile_picture"].required = False
        self.fields["profile_picture"].widget.attrs.update(
            {
                "accept": "image/*",
                "data-cloudinary-upload": "1",
                "data-cloudinary-upload-mode": "signed",
                "data-cloudinary-signature-url": "/cloudinary/sign-upload/",
                "data-cloudinary-folder": "creator_profiles",
                "data-cloudinary-type": "upload",
                "data-cloudinary-resource-type": "auto",
                "data-cloudinary-hidden-prefix": "profile_picture_cloudinary",
            }
        )

    def clean(self):
        cleaned = super().clean()
        has_uploaded_file = bool(self.files.get("profile_picture"))
        has_cloudinary_id = bool((cleaned.get("profile_picture_cloudinary_id") or "").strip())
        if not has_uploaded_file and not has_cloudinary_id and not self.instance.pk:
            self.add_error("profile_picture", "Upload a profile picture or use Cloudinary direct upload.")
        if has_cloudinary_id:
            cleaned["profile_picture"] = None
        return cleaned

    def save(self, commit=True):
        current_profile_picture = self.instance.profile_picture
        instance = super().save(commit=False)
        instance.profile_picture_cloudinary_id = (self.cleaned_data.get("profile_picture_cloudinary_id") or "").strip()
        instance.profile_picture_cloudinary_format = (self.cleaned_data.get("profile_picture_cloudinary_format") or "").strip()
        instance.profile_picture_cloudinary_delivery = (self.cleaned_data.get("profile_picture_cloudinary_delivery") or "").strip()
        if self.instance.pk and not instance.profile_picture and not instance.profile_picture_cloudinary_id:
            instance.profile_picture = current_profile_picture
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ContentAdminForm(forms.ModelForm):
    media_cloudinary_id = forms.CharField(required=False, widget=forms.HiddenInput())
    media_cloudinary_format = forms.CharField(required=False, widget=forms.HiddenInput())
    media_cloudinary_resource_type = forms.CharField(required=False, widget=forms.HiddenInput())
    media_cloudinary_delivery = forms.CharField(required=False, widget=forms.HiddenInput())
    preview_image_cloudinary_id = forms.CharField(required=False, widget=forms.HiddenInput())
    preview_image_cloudinary_format = forms.CharField(required=False, widget=forms.HiddenInput())
    preview_image_cloudinary_delivery = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Content
        fields = [
            "creator",
            "title",
            "description",
            "price",
            "media_file",
            "preview_image",
        ]

    class Media:
        js = ("js/cloudinary_direct_upload.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["media_file"].required = False
        self.fields["preview_image"].required = False
        self.fields["media_file"].widget.attrs.update(
            {
                "accept": "image/*,video/*,audio/*,.mp4,.webm,.mov,.m4v,.mp3,.wav,.m4a,.aac,.ogg,.jpg,.jpeg,.png,.gif,.webp,.pdf",
                "data-cloudinary-upload": "1",
                "data-cloudinary-upload-mode": "signed",
                "data-cloudinary-signature-url": "/cloudinary/sign-upload/",
                "data-cloudinary-folder": "content",
                "data-cloudinary-type": "authenticated",
                "data-cloudinary-resource-type": "auto",
                "data-cloudinary-hidden-prefix": "media_cloudinary",
            }
        )
        self.fields["preview_image"].widget.attrs.update(
            {
                "accept": "image/*",
                "data-cloudinary-upload": "1",
                "data-cloudinary-upload-mode": "signed",
                "data-cloudinary-signature-url": "/cloudinary/sign-upload/",
                "data-cloudinary-folder": "previews",
                "data-cloudinary-type": "upload",
                "data-cloudinary-resource-type": "auto",
                "data-cloudinary-hidden-prefix": "preview_image_cloudinary",
            }
        )

    def clean(self):
        cleaned = super().clean()
        has_media_file = bool(self.files.get("media_file"))
        has_media_id = bool((cleaned.get("media_cloudinary_id") or "").strip())
        if not has_media_file and not has_media_id and not self.instance.pk:
            self.add_error("media_file", "Upload a content file or use Cloudinary direct upload.")
        if has_media_id:
            cleaned["media_file"] = None
        if cleaned.get("preview_image_cloudinary_id"):
            cleaned["preview_image"] = None
        return cleaned

    def save(self, commit=True):
        current_media_file = self.instance.media_file
        current_preview_image = self.instance.preview_image
        instance = super().save(commit=False)
        instance.media_cloudinary_id = (self.cleaned_data.get("media_cloudinary_id") or "").strip()
        instance.media_cloudinary_format = (self.cleaned_data.get("media_cloudinary_format") or "").strip()
        instance.media_cloudinary_resource_type = (self.cleaned_data.get("media_cloudinary_resource_type") or "").strip()
        instance.media_cloudinary_delivery = (self.cleaned_data.get("media_cloudinary_delivery") or "").strip()
        instance.preview_image_cloudinary_id = (self.cleaned_data.get("preview_image_cloudinary_id") or "").strip()
        instance.preview_image_cloudinary_format = (self.cleaned_data.get("preview_image_cloudinary_format") or "").strip()
        instance.preview_image_cloudinary_delivery = (self.cleaned_data.get("preview_image_cloudinary_delivery") or "").strip()
        if self.instance.pk and not instance.media_file and not instance.media_cloudinary_id:
            instance.media_file = current_media_file
        if self.instance.pk and not instance.preview_image and not instance.preview_image_cloudinary_id:
            instance.preview_image = current_preview_image
        if commit:
            instance.save()
            self.save_m2m()
        return instance
