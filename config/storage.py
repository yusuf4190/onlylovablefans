from __future__ import annotations

import logging

from whitenoise.storage import CompressedManifestStaticFilesStorage, MissingFileError

logger = logging.getLogger(__name__)


class IgnoreMissingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """A staticfiles storage that tolerates missing files referenced by other files.

    Whitenoise's manifest post-processing raises a MissingFileError when a collected
    file references another file that isn't present (e.g. a JS file referencing a
    .map file). For deployments where source maps are not required, it's better
    to warn and continue rather than fail the whole `collectstatic` step.
    """

    def stored_name(self, name: str) -> str:  # keep original tolerant behavior
        try:
            return super().stored_name(name)
        except ValueError:
            return name

    def post_process(self, *args, **kwargs):
        gen = super().post_process(*args, **kwargs)
        while True:
            try:
                item = next(gen)
            except StopIteration:
                break
            except MissingFileError as exc:
                logger.warning("Ignoring missing static file during collectstatic: %s", exc)
                continue
            except Exception:
                raise
            else:
                yield item