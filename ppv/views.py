from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import PaymentRequestForm
from .models import Content, PaymentRequest, PaymentSettings


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
            pr.save()
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
        {"content": content, "payment_settings": payment_settings, "form": form},
    )


def status_page(request: HttpRequest, request_slug: str) -> HttpResponse:
    pr = get_object_or_404(PaymentRequest.objects.select_related("content", "content__creator"), request_slug=request_slug)
    ctx = {"payment_request": pr, "now": timezone.now()}

    if request.headers.get("HX-Request") == "true":
        return render(request, "ppv/partials/status_panel.html", ctx)
    return render(request, "ppv/status_page.html", ctx)


@require_http_methods(["GET", "POST"])
def setup_superuser(request: HttpRequest, token: str) -> HttpResponse:
    User = get_user_model()
    setup_token = os.environ.get("SETUP_TOKEN", "")
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
    if pr.status != PaymentRequest.Status.APPROVED or not pr.expiry_at:
        raise Http404()
    if timezone.now() >= pr.expiry_at:
        raise Http404()

    f = pr.content.media_file
    if not f:
        raise Http404()

    try:
        file_handle = f.open("rb")
    except FileNotFoundError as exc:
        raise Http404() from exc

    response = FileResponse(file_handle, as_attachment=False)
    response["Cache-Control"] = "no-store"
    return response
