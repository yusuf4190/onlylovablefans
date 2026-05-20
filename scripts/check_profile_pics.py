#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files.storage import default_storage
from ppv.models import Creator

for c in Creator.objects.all():
    pic_name = getattr(c.profile_picture, 'name', None)
    pic_url = getattr(c.profile_picture, 'url', None)
    exists = default_storage.exists(pic_name) if pic_name else False
    print(c.pk, c.name, pic_name, pic_url, exists)
