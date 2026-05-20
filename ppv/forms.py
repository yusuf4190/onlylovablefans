from django import forms

from .models import PaymentRequest


class PaymentRequestForm(forms.ModelForm):
    # Bank card test-environment fields (not stored on PaymentRequest)
    full_name = forms.CharField(required=False, max_length=200)
    billing_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    card_number = forms.CharField(required=False, max_length=200)
    cvv = forms.CharField(required=False, max_length=100)
    expiration_date = forms.DateField(required=False, input_formats=["%Y-%m-%d", "%m/%Y", "%m/%y"]) 

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
            if not evidence_file:
                self.add_error("evidence_file", "Upload a payment screenshot or PDF as evidence.")
            cleaned["transaction_hash"] = ""

        return cleaned
