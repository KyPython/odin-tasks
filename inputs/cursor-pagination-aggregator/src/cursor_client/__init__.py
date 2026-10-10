"""Synthetic cursor pagination client."""

from .aggregator import collect_records
from .fixture_transport import FixtureTransport, ProtocolError

__all__ = ["FixtureTransport", "ProtocolError", "collect_records"]
