import os
import sys
from pathlib import Path

# Ensure project root (containing manage.py and config/) is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
try:
    django.setup()
    from ppv.forms import PaymentRequestForm
    try:
        f = PaymentRequestForm()
        print('OK', list(f.fields.keys()))
    except Exception as e:
        print('FORM_ERROR', type(e).__name__, str(e))
except Exception as e:
    print('SETUP_ERROR', type(e).__name__, str(e))
