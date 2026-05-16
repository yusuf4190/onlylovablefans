from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('private/', include('private_storage.urls')),
    path('', include('ppv.urls')),
]

# Only serve uploaded media files from Django in local/dev when using filesystem storage.
# In production (and/or with Cloudinary), media URLs should resolve to the external storage.
if settings.DEBUG and not getattr(settings, "USE_CLOUDINARY", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
