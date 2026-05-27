from django.urls import path

from . import views

app_name = "ppv"

urlpatterns = [
    path("", views.home, name="home"),
    path("cloudinary/sign-upload/", views.cloudinary_upload_signature, name="cloudinary_upload_signature"),
    path("content/<uuid:content_id>/", views.content_request, name="content_request"),
    path("status/<slug:request_slug>/", views.status_page, name="status"),
    path("protected/<slug:request_slug>/", views.protected_media, name="protected_media"),
    path("setup/<str:token>/", views.setup_superuser, name="setup_superuser"),
]
