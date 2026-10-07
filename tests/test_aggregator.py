import unittest

from cursor_client import FixtureTransport, collect_records


class CollectRecordsTests(unittest.TestCase):
    def test_collects_a_single_page(self) -> None:
        transport = FixtureTransport(
            [
                {
                    "request_cursor": None,
                    "response": {
                        "records": [{"id": "rec-001", "label": "one"}],
                        "next_cursor": None,
                    },
                }
            ]
        )

        self.assertEqual(
            collect_records(transport),
            [{"id": "rec-001", "label": "one"}],
        )
        self.assertEqual(transport.requested_cursors, [None])

    def test_collects_ordinary_pages_in_server_order(self) -> None:
        transport = FixtureTransport.from_path("fixtures/ordinary.json")

        records = collect_records(transport)

        self.assertEqual(
            [record["id"] for record in records],
            ["rec-101", "rec-102", "rec-103"],
        )
        self.assertEqual(transport.requested_cursors, [None, "page-2"])


if __name__ == "__main__":
    unittest.main()
