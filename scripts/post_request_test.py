from django.test import Client
from ppv.models import Content
from django.core.files.uploadedfile import SimpleUploadedFile

c = Client()
content = Content.objects.first()
if not content:
    print('no content')
else:
    url = f"/content/{content.uuid}/"
    data = {
        'payment_method': 'bank_transfer',
        'amount': str(content.price),
        'fan_email': 'tester@example.com'
    }
    f = SimpleUploadedFile('evidence.jpg', b'JPEGDATA', content_type='image/jpeg')
    resp = c.post(url, data={'payment_method': data['payment_method'], 'amount': data['amount'], 'fan_email': data['fan_email']}, files={'evidence_file': f})
    print('status_code', resp.status_code)
    print('content', resp.content[:1000])
