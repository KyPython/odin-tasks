"""Exceptions used by the synthetic child operation."""


class ChildOperationError(Exception):
    """Base exception raised by the child operation."""


class HandledItemError(ChildOperationError):
    """An item condition that the item boundary is allowed to handle."""


class UnmatchedChildError(ChildOperationError):
    """A child-operation failure that is not handled at the item boundary."""


class SiblingItemError(ChildOperationError):
    """Another unhandled child-operation failure."""


class ItemProcessingError(Exception):
    """Adds item context to a propagated child-operation failure."""
