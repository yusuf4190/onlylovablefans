import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from ppv.models import Content, PaymentRequest
from ppv.forms import PaymentRequestForm
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from ppv.templatetags.ppv_extras import media_kind
from django.core.files.storage import default_storage
from django.utils import timezone

print('Starting smoke test')
content = Content.objects.first()
if not content:
    print('NO_CONTENT')
    raise SystemExit(1)
print('Using content:', content.pk, content.title, 'price', content.price)

# build form
data = {'payment_method': 'bank_transfer', 'amount': str(content.price), 'fan_email': 'smoke@example.com'}
file = SimpleUploadedFile('evidence.jpg', b'JPEGDATA', content_type='image/jpeg')
form = PaymentRequestForm(data, {'evidence_file': file})
print('form_valid:', form.is_valid())
if not form.is_valid():
    print('errors:', form.errors.as_json())
    raise SystemExit(1)

# save PR
pr = form.save(commit=False)
pr.content = content
pr.amount = content.price
pr.save()
print('created pr', pr.pk, pr.request_slug, pr.status)

print('media_name:', pr.content.media_file.name)
print('media_kind:', media_kind(pr.content.media_file.name))

# confirm protected view before approval
c = Client()
protected_url = f"/protected/{pr.request_slug}/"
resp = c.get(protected_url)
print('before_approve_status', resp.status_code)

# approve
pr.approve()
pr.save()
print('after approve approved_at, expiry_at:', pr.approved_at, pr.expiry_at, 'is_access_active:', pr.is_access_active)

resp2 = c.get(protected_url)
print('after_approve_status', resp2.status_code)
print('content-type', resp2.get('Content-Type'))
print('content-length', len(resp2.content))

# profile pics
from ppv.models import Creator
for cobj in Creator.objects.all():
    name = getattr(cobj.profile_picture, 'name', None)
    url = getattr(cobj.profile_picture, 'url', None)
    exists = default_storage.exists(name) if name else False
    print('creator', cobj.pk, cobj.name, name, url, 'exists?', exists)

print('smoke test done at', timezone.now())
