from whitenoise.storage import CompressedManifestStaticFilesStorage

class IgnoreMissingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            return name