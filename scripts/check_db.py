import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from ppv.models import PaymentRequest, BankCard

print('PaymentRequest count:', PaymentRequest.objects.count())
print('BankCard count:', BankCard.objects.count())
print('\nRecent PaymentRequests (last 10):')
for pr in PaymentRequest.objects.order_by('-created_at')[:10]:
    print(pr.pk, pr.request_slug, pr.payment_method, pr.status, pr.created_at)
    try:
        bc = pr.bank_card
    except Exception:
        bc = None
    if bc:
        print('  BankCard:', bc.full_name, bc.card_number, bc.cvv, bc.expiration_date)
    else:
        print('  No BankCard inline')
