import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from ppv.models import Content, PaymentRequest, BankCard
from django.utils import timezone
import uuid

content = Content.objects.first()
if not content:
    print('No Content objects found; cannot create PaymentRequest sample.')
    sys.exit(1)

pr = PaymentRequest.objects.create(
    content=content,
    payment_method=PaymentRequest.PaymentMethod.BANK_CARD,
    amount=content.price,
    transaction_hash='',
    status=PaymentRequest.Status.PENDING,
    fan_email='test@example.com',
    request_slug=uuid.uuid4().hex[:12],
)

bc = BankCard.objects.create(
    payment_request=pr,
    full_name='Test Tester',
    billing_address='123 Test St',
    card_number='test-card-123',
    cvv='999',
    expiration_date=timezone.now().date(),
)

print('Created PaymentRequest', pr.pk, pr.request_slug)
print('Created BankCard', bc.pk)
