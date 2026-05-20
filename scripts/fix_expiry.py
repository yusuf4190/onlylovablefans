#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ppv.models import PaymentRequest
from django.utils import timezone

qs = PaymentRequest.objects.filter(status='approved', expiry_at__isnull=True)
print('to_fix', qs.count())
fixed = []
now = timezone.now()
for pr in list(qs):
    if not pr.approved_at:
        pr.approved_at = now
    pr.expiry_at = now + timedelta(hours=24)
    pr.save(update_fields=['approved_at', 'expiry_at'])
    fixed.append(pr.request_slug)
print('fixed', len(fixed))
if fixed:
    print('examples_fixed', fixed[:10])
else:
    print('no_rows_fixed')
