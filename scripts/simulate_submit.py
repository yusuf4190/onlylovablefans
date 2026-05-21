from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

# simulate a POST submission to PaymentRequestForm
from ppv.models import Content
from ppv.forms import PaymentRequestForm

content = Content.objects.first()
if not content:
    print('no content in DB')
else:
    data = {
        'payment_method': 'bank_transfer',
        'amount': str(content.price),
        'fan_email': 'tester@example.com'
    }
    # create a small dummy file
    f = SimpleUploadedFile('evidence.jpg', b'JPEGDATA', content_type='image/jpeg')
    files = {'evidence_file': f}
    form = PaymentRequestForm(data, files)
    print('is_valid', form.is_valid())
    if not form.is_valid():
        print('errors', form.errors.as_json())
    else:
        pr = form.save(commit=False)
        pr.content = content
        pr.amount = content.price
        pr.save()
        print('saved pr', pr.pk, pr.request_slug)
