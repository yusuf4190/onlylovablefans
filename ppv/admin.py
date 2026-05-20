from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Content, Creator, CryptoWallet, PaymentRequest, PaymentSettings, BankCard

admin.site.site_header = "Onlylovablefans"
admin.site.site_title = "Onlylovablefans Admin"
admin.site.index_title = "Admin"


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    search_fields = ["name", "slug"]
    list_display = ["name", "slug", "has_profile_picture"]

    @admin.display(boolean=True, description="Profile pic")
    def has_profile_picture(self, obj: Creator) -> bool:
        return bool(obj.profile_picture)


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    search_fields = ["title", "creator__name"]
    list_filter = ["creator"]
    list_display = ["title", "creator", "price", "uuid", "created_at"]
    readonly_fields = ["uuid", "created_at"]


class PaymentSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: HttpRequest) -> bool:
        return not PaymentSettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


admin.site.register(PaymentSettings, PaymentSettingsAdmin)


@admin.register(CryptoWallet)
class CryptoWalletAdmin(admin.ModelAdmin):
    list_display = ["label", "address", "order"]
    ordering = ["order", "label"]


class RejectNoteForm(forms.Form):
    note = forms.CharField(
        label="Rejection note",
        widget=forms.Textarea(attrs={"rows": 4, "cols": 60}),
        required=True,
    )


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    class BankCardInline(admin.StackedInline):
        model = BankCard
        can_delete = False
        fk_name = "payment_request"
        verbose_name = "Bank card (test)"
        verbose_name_plural = "Bank card (test)"

    inlines = [BankCardInline]
    change_form_template = "admin/ppv/paymentrequest/change_form.html"
    list_display = ["request_slug", "creator_name", "content", "payment_method", "amount", "status", "created_at"]
    list_filter = ["status", "payment_method", "content__creator"]
    search_fields = ["request_slug", "content__title", "content__creator__name", "transaction_hash", "fan_email"]
    readonly_fields = [
        "request_slug",
        "created_at",
        "approved_at",
        "expiry_at",
        "evidence_download",
    ]
    fields = [
        "content",
        "payment_method",
        "amount",
        "status",
        "full_name",
        "billing_address",
        "card_number",
        "cvv",
        "expiration_date",
        "admin_note",
        "transaction_hash",
        "evidence_file",
        "evidence_download",
        "fan_email",
        "request_slug",
        "created_at",
        "approved_at",
        "expiry_at",
    ]

    actions = ["approve_selected", "reject_selected"]

    @admin.display(ordering="content__creator__name", description="Creator")
    def creator_name(self, obj: PaymentRequest) -> str:
        return obj.content.creator.name

    @admin.display(description="Evidence")
    def evidence_download(self, obj: PaymentRequest) -> str:
        if not obj.evidence_file:
            return "-"
        url = reverse("admin:ppv_paymentrequest_evidence", args=[obj.pk])
        return format_html('<a href="{}">Download evidence</a>', url)

    @admin.action(description="Approve selected requests")
    def approve_selected(self, request: HttpRequest, queryset):
        changed = 0
        for pr in queryset:
            if pr.status != PaymentRequest.Status.APPROVED:
                pr.approve()
                pr.save(update_fields=["status", "approved_at", "expiry_at", "admin_note"])
                changed += 1
        self.message_user(request, f"Approved {changed} request(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected requests (add note)")
    def reject_selected(self, request: HttpRequest, queryset):
        ids = ",".join(str(pk) for pk in queryset.values_list("pk", flat=True))
        return redirect(f"reject/?ids={ids}")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("reject/", self.admin_site.admin_view(self.reject_view), name="ppv_paymentrequest_reject"),
            path(
                "<int:pk>/evidence/",
                self.admin_site.admin_view(self.evidence_view),
                name="ppv_paymentrequest_evidence",
            ),
        ]
        return custom + urls

    def reject_view(self, request: HttpRequest) -> HttpResponse:
        raw_ids = (request.GET.get("ids") or "").strip()
        ids = [int(x) for x in raw_ids.split(",") if x.strip().isdigit()]
        qs = PaymentRequest.objects.filter(pk__in=ids)

        if request.method == "POST":
            form = RejectNoteForm(request.POST)
            if form.is_valid():
                note = form.cleaned_data["note"]
                count = 0
                for pr in qs:
                    pr.reject(note)
                    pr.save(update_fields=["status", "admin_note", "approved_at", "expiry_at"])
                    count += 1
                self.message_user(request, f"Rejected {count} request(s).", level=messages.SUCCESS)
                return redirect("..")
        else:
            form = RejectNoteForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "requests": qs.select_related("content", "content__creator"),
            "title": "Reject payment requests",
        }
        return render(request, "admin/ppv/reject_requests.html", context)

    def evidence_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        pr = get_object_or_404(PaymentRequest, pk=pk)
        if not pr.evidence_file:
            raise Http404()
        try:
            fh = pr.evidence_file.open("rb")
        except FileNotFoundError as exc:
            raise Http404() from exc
        resp = FileResponse(fh, as_attachment=True, filename=pr.evidence_file.name.rsplit("/", 1)[-1])
        resp["Cache-Control"] = "no-store"
        return resp

    def response_change(self, request: HttpRequest, obj: PaymentRequest):
        if "_approve" in request.POST:
            obj.approve()
            obj.save(update_fields=["status", "approved_at", "expiry_at", "admin_note"])
            self.message_user(request, "Payment request approved.", level=messages.SUCCESS)
            return redirect(request.path)
        if "_reject" in request.POST:
            return redirect(f"../reject/?ids={obj.pk}")
        return super().response_change(request, obj)
