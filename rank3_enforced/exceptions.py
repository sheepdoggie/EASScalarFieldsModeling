class CertificationBlocked(RuntimeError):
    """Raised when a run attempts downstream certification without passing gates."""


class ManifestError(ValueError):
    """Raised when a model manifest is incomplete or internally inconsistent."""


class RuleAuditError(ValueError):
    """Raised when a supplied rule fails source or metadata audit."""
