# Cursor pagination aggregator starter

This synthetic Python service models a client that collects records from a
cursor-paginated REST endpoint. Everything in this directory is fabricated and
uses deterministic local JSON fixtures; it makes no network requests.

## Setup

Python 3.11 or newer is sufficient. The starter has no third-party runtime or
test dependencies.

```bash
cd cursor-pagination-aggregator
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Baseline exploration

Run the client against any included fixture:

```bash
PYTHONPATH=src python -m cursor_client.cli fixtures/ordinary.json
PYTHONPATH=src python -m cursor_client.cli fixtures/repeated-cursor.json
PYTHONPATH=src python -m cursor_client.cli fixtures/empty-page.json
PYTHONPATH=src python -m cursor_client.cli fixtures/duplicate-records.json
```

The CLI prints JSON on success and reports fixture/protocol errors on stderr.
The ordinary fixture is covered by starter tests. The other fixtures preserve
deterministic boundary cases for the exercise; their final behavioral tests
and the production repair are intentionally not part of this starter.

## Contract

`collect_records(transport)` should return the endpoint's logical record set in
server order. Pagination metadata is server-controlled. A robust client must
finish deterministically when cursors repeat, continue across an empty page
when another cursor is supplied, and emit each record identifier only once
while retaining its first server position.

The exercise is to inspect the current behavior, diagnose contract violations,
implement a focused repair, and add decisive tests for the supplied boundary
fixtures. Do not replace the fixture transport with network access.
