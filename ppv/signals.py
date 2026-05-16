from __future__ import annotations

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Content, Creator, PaymentRequest


def _delete_filefield_file(file_field) -> None:
    if not file_field:
        return
    try:
        file_field.delete(save=False)
    except Exception:
        # Best-effort cleanup: never block model deletes/saves due to storage errors.
        return


@receiver(post_delete, sender=Creator)
def creator_cleanup_files(sender, instance: Creator, **kwargs) -> None:
    _delete_filefield_file(instance.profile_picture)


@receiver(pre_save, sender=Creator)
def creator_cleanup_replaced_files(sender, instance: Creator, **kwargs) -> None:
    if not instance.pk:
        return
    try:
        old = Creator.objects.get(pk=instance.pk)
    except Creator.DoesNotExist:
        return
    if old.profile_picture and old.profile_picture != instance.profile_picture:
        _delete_filefield_file(old.profile_picture)


@receiver(post_delete, sender=Content)
def content_cleanup_files(sender, instance: Content, **kwargs) -> None:
    _delete_filefield_file(instance.preview_image)
    _delete_filefield_file(instance.media_file)


@receiver(pre_save, sender=Content)
def content_cleanup_replaced_files(sender, instance: Content, **kwargs) -> None:
    if not instance.pk:
        return
    try:
        old = Content.objects.get(pk=instance.pk)
    except Content.DoesNotExist:
        return
    if old.preview_image and old.preview_image != instance.preview_image:
        _delete_filefield_file(old.preview_image)
    if old.media_file and old.media_file != instance.media_file:
        _delete_filefield_file(old.media_file)


@receiver(post_delete, sender=PaymentRequest)
def payment_request_cleanup_files(sender, instance: PaymentRequest, **kwargs) -> None:
    _delete_filefield_file(instance.evidence_file)


@receiver(pre_save, sender=PaymentRequest)
def payment_request_cleanup_replaced_files(sender, instance: PaymentRequest, **kwargs) -> None:
    if not instance.pk:
        return
    try:
        old = PaymentRequest.objects.get(pk=instance.pk)
    except PaymentRequest.DoesNotExist:
        return
    if old.evidence_file and old.evidence_file != instance.evidence_file:
        _delete_filefield_file(old.evidence_file)

