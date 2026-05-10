from __future__ import annotations

from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ppv.models import Content, Creator, PaymentRequest, PaymentSettings


class Command(BaseCommand):
    help = "Seed demo Creator/Content/PaymentSettings (and an optional pending PaymentRequest)."

    def add_arguments(self, parser):
        parser.add_argument("--with-request", action="store_true", help="Create a pending PaymentRequest as well.")

    def handle(self, *args, **options):
        settings = PaymentSettings.get_solo()
        if not settings.bank_details:
            settings.bank_details = "Bank: Demo Bank\nAcct Name: Demo Name\nAcct No: 0000000000"
        if not settings.paypal_email:
            settings.paypal_email = "demo@example.com"
        if not settings.crypto_address:
            settings.crypto_address = "0xDEMOCRYPTOADDRESS"
        settings.save()

        creator, _ = Creator.objects.get_or_create(slug="demo-creator", defaults={"name": "Demo Creator"})

        content, created = Content.objects.get_or_create(
            creator=creator,
            title="Demo Content (text file)",
            defaults={
                "description": "This is a seeded demo asset stored in private storage.",
                "price": Decimal("1000.00"),
            },
        )

        if created or not content.media_file:
            content.media_file.save("demo.txt", ContentFile(b"Demo paid content.\n"), save=True)

        pr = None
        if options["with_request"]:
            pr = PaymentRequest.objects.create(
                content=content,
                payment_method=PaymentRequest.PaymentMethod.BANK_TRANSFER,
                amount=content.price,
            )
            pr.evidence_file.save("evidence.txt", ContentFile(b"Demo evidence file.\n"), save=True)

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
        self.stdout.write(f"Content UUID: {content.uuid}")
        self.stdout.write(f"Public content URL: /content/{content.uuid}/")
        if pr:
            self.stdout.write(f"PaymentRequest slug: {pr.request_slug}")
            self.stdout.write(f"Status URL: /status/{pr.request_slug}/")
