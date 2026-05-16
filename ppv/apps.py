from django.apps import AppConfig


class PpvConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ppv'

    def ready(self) -> None:
        from . import signals  # noqa: F401
