"""Explicit Archive and Corpus failure types."""


class ObservatoryError(Exception):
    """Base class for operator-visible Observatory failures."""


class ArchiveWriteError(ObservatoryError):
    """An object or event could not be durably written."""


class InvalidEventError(ObservatoryError):
    """An Archive event is malformed or conflicts with another event."""


class RecordIdentityConflictError(InvalidEventError):
    """One logical record ID was assigned incompatible titles."""


class IntegrityError(ObservatoryError):
    """Archived bytes do not match their recorded identity."""
