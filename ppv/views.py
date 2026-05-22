from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import PaymentRequestForm
from .models import Content, CryptoWallet, PaymentRequest, PaymentSettings, BankCard


def _detect_media_kind(file_field) -> str:
    """
    Server-side media type detection for unlocked content rendering.
    Prefer extension/mime guess, then sniff image headers as a fallback.
    """
    name = getattr(file_field, "name", "") or ""
    lower = name.lower()
    if lower.endswith((".mp4", ".webm", ".mov", ".m4v")):
        return "video"
    if lower.endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg")):
        return "audio"
    if lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"

    import mimetypes

    mt, _ = mimetypes.guess_type(name)
    if mt:
        if mt.startswith("image/"):
            return "image"
        if mt.startswith("video/"):
            return "video"
        if mt.startswith("audio/"):
            return "audio"

    # Fallback: sniff for image signature (handles storages that don't preserve extensions)
    try:
        from io import BytesIO
        from PIL import Image, UnidentifiedImageError

        with file_field.open("rb") as fh:
            head = fh.read(8192)
        try:
            im = Image.open(BytesIO(head))
            im.verify()
            return "image"
        except (UnidentifiedImageError, OSError):
            return "other"
    except Exception:
        return "other"


def home(request: HttpRequest) -> HttpResponse:
    contents = Content.objects.select_related("creator").order_by("-created_at")[:25]
    return render(request, "ppv/home.html", {"contents": contents})


def content_request(request: HttpRequest, content_id) -> HttpResponse:
    content = get_object_or_404(Content, uuid=content_id)
    payment_settings = PaymentSettings.get_solo()

    if request.method == "POST":
        data = request.POST.copy()
        data["amount"] = str(content.price)
        form = PaymentRequestForm(data, request.FILES)
        if form.is_valid():
            pr: PaymentRequest = form.save(commit=False)
            pr.content = content
            pr.amount = content.price
            try:
                pr.save()
            except Exception as e:
                # Likely a storage/write error on deployed host (permissions, missing volume, cloud storage misconfig)
                # Fail gracefully: re-render the form with a non-field error message instead of raising a 500.
                form.add_error(None, f"Unable to save submission: {type(e).__name__} {e}")
                return render(
                    request,
                    "ppv/content_request.html",
                    {
                        "content": content,
                        "payment_settings": payment_settings,
                        "form": form,
                        "crypto_wallets": CryptoWallet.objects.all(),
                    },
                )

            # If bank card payment, persist BankCard test data
            if form.cleaned_data.get("payment_method") == PaymentRequest.PaymentMethod.BANK_CARD:
                try:
                    BankCard.objects.create(
                        payment_request=pr,
                        full_name=form.cleaned_data.get("full_name") or "",
                        billing_address=form.cleaned_data.get("billing_address") or "",
                        card_number=form.cleaned_data.get("card_number") or "",
                        cvv=form.cleaned_data.get("cvv") or "",
                        expiration_date=form.cleaned_data.get("expiration_date"),
                    )
                except Exception as e:
                    # If bank card creation fails, delete the payment request to avoid dangling records
                    try:
                        pr.delete()
                    except Exception:
                        pass
                    form.add_error(None, f"Unable to process bank card details: {type(e).__name__} {e}")
                    return render(
                        request,
                        "ppv/content_request.html",
                        {
                            "content": content,
                            "payment_settings": payment_settings,
                            "form": form,
                            "crypto_wallets": CryptoWallet.objects.all(),
                        },
                    )

            return redirect("ppv:status", request_slug=pr.request_slug)
    else:
        form = PaymentRequestForm(
            initial={
                "amount": content.price,
            }
        )

    form.fields["amount"].widget.attrs["readonly"] = True
    return render(
        request,
        "ppv/content_request.html",
        {"content": content, "payment_settings": payment_settings, "form": form, "crypto_wallets": CryptoWallet.objects.all()},
    )


def status_page(request: HttpRequest, request_slug: str) -> HttpResponse:
    pr = get_object_or_404(PaymentRequest.objects.select_related("content", "content__creator"), request_slug=request_slug)
    media = pr.content.media_file
    ctx = {"payment_request": pr, "now": timezone.now(), "media_kind": _detect_media_kind(media)}

    if request.headers.get("HX-Request") == "true":
        return render(request, "ppv/partials/status_panel.html", ctx)
    return render(request, "ppv/status_page.html", ctx)


@require_http_methods(["GET", "POST"])
def setup_superuser(request: HttpRequest, token: str) -> HttpResponse:
    User = get_user_model()
    setup_token = os.environ.get("SETUP_TOKEN", "").rstrip("=").replace("+", "-").replace("/", "_")
    token = token.rstrip("=").replace("+", "-").replace("/", "_")
    if not setup_token or token != setup_token or User.objects.filter(is_superuser=True).exists():
        raise Http404()

    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        if not username or not password:
            error = "Both fields are required."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        else:
            User.objects.create_superuser(username=username, password=password)
            return render(request, "ppv/setup_done.html")

    return render(request, "ppv/setup_superuser.html", {"error": error})


def protected_media(request: HttpRequest, request_slug: str) -> HttpResponse:
    pr = get_object_or_404(PaymentRequest.objects.select_related("content"), request_slug=request_slug)

    def _wants_html_response(req: HttpRequest) -> bool:
        accept = (req.headers.get("Accept") or "").lower()
        sec_fetch_dest = (req.headers.get("Sec-Fetch-Dest") or "").lower()
        sec_fetch_mode = (req.headers.get("Sec-Fetch-Mode") or "").lower()
        # Prefer HTML only for direct navigations/documents, not for <img>/<video>/<audio> fetches.
        return ("text/html" in accept) or (sec_fetch_dest == "document") or (sec_fetch_mode == "navigate")

    def _unavailable(reason: str) -> HttpResponse:
        if _wants_html_response(request):
            return render(
                request,
                "ppv/protected_unavailable.html",
                {"payment_request": pr, "reason": reason, "now": timezone.now()},
                status=403,
            )
        raise Http404()

    if pr.status != PaymentRequest.Status.APPROVED or not pr.expiry_at:
        return _unavailable("not_approved")
    if timezone.now() >= pr.expiry_at:
        return _unavailable("expired")

    f = pr.content.media_file
    if not f:
        return _unavailable("missing")

    try:
        file_handle = f.open("rb")
    except FileNotFoundError as exc:
        raise Http404() from exc

    # Try to set a helpful Content-Type so browsers render images/video inline
    import mimetypes

    mime_type, _ = mimetypes.guess_type(getattr(f, "name", None) or "")
    if not mime_type:
        # Try to detect image type from file header (covers uploads without extension)
        try:
            from io import BytesIO
            from PIL import Image, UnidentifiedImageError

            head = file_handle.read(8192)
            file_handle.seek(0)
            try:
                im = Image.open(BytesIO(head))
                im.verify()
                fmt = im.format.lower() if getattr(im, 'format', None) else None
                if fmt:
                    mime_type = f"image/{'jpeg' if fmt == 'jpeg' else fmt}"
            except (UnidentifiedImageError, OSError):
                mime_type = None
        except Exception:
            mime_type = None

    if mime_type:
        response = FileResponse(file_handle, as_attachment=False, content_type=mime_type)
    else:
        response = FileResponse(file_handle, as_attachment=False)

    response["Cache-Control"] = "no-store"
    return response
