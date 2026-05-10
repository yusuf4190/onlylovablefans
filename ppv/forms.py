from django import forms

from .models import PaymentRequest


class PaymentRequestForm(forms.ModelForm):
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
        self.fields["evidence_file"].widget.attrs.update({"class": "block w-full text-sm text-white/80 file:mr-4 file:rounded-2xl file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-white hover:file:bg-white/15"})

    def clean(self):
        cleaned = super().clean()
        payment_method = cleaned.get("payment_method")
        evidence_file = cleaned.get("evidence_file")
        transaction_hash = (cleaned.get("transaction_hash") or "").strip()

        if payment_method == PaymentRequest.PaymentMethod.CRYPTO:
            if not transaction_hash:
                self.add_error("transaction_hash", "Transaction hash is required for crypto payments.")
            cleaned["evidence_file"] = None
        else:
            if not evidence_file:
                self.add_error("evidence_file", "Upload a payment screenshot or PDF as evidence.")
            cleaned["transaction_hash"] = ""

        return cleaned
