import unittest

from cursor_client import FixtureTransport, ProtocolError


class FixtureTransportTests(unittest.TestCase):
    def test_rejects_a_cursor_that_does_not_match_the_transcript(self) -> None:
        transport = FixtureTransport(
            [
                {
                    "request_cursor": None,
                    "response": {"records": [], "next_cursor": None},
                }
            ]
        )

        with self.assertRaisesRegex(ProtocolError, "expected cursor"):
            transport("unexpected")

    def test_rejects_requests_after_the_transcript_is_exhausted(self) -> None:
        transport = FixtureTransport([])

        with self.assertRaisesRegex(ProtocolError, "no fixture response"):
            transport(None)


if __name__ == "__main__":
    unittest.main()
