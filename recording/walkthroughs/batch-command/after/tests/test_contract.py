from itertools import permutations

import pytest

import batch_command.command as command
from batch_command import BatchReport, ItemSpec, run_batch
from batch_command.errors import ItemProcessingError, SiblingItemError, UnmatchedChildError


@pytest.mark.parametrize("mode", ["unmatched", "sibling"])
def test_failed_item_is_reported_once_and_never_processed(mode):
    assert run_batch((ItemSpec("failed", mode),)) == BatchReport(
        (), ("failed",),
        ("open:failed", "execute:failed", "cleanup:failed", "failed:failed"),
    )


def test_original_deterministic_fixture(deterministic_failure_set):
    assert run_batch(deterministic_failure_set) == BatchReport(
        ("alpha",), ("bravo", "charlie"),
        (
            "open:alpha", "execute:alpha", "cleanup:alpha", "processed:alpha",
            "open:bravo", "execute:bravo", "cleanup:bravo", "failed:bravo",
            "open:charlie", "execute:charlie", "cleanup:charlie", "failed:charlie",
        ),
    )


@pytest.mark.parametrize("order", list(permutations(("alpha", "bravo", "charlie"))))
def test_failure_semantics_do_not_depend_on_input_order(order):
    items = {
        "alpha": ItemSpec("alpha", "ok"),
        "bravo": ItemSpec("bravo", "unmatched"),
        "charlie": ItemSpec("charlie", "sibling"),
    }
    expected_events = {
        "alpha": ("open:alpha", "execute:alpha", "cleanup:alpha", "processed:alpha"),
        "bravo": ("open:bravo", "execute:bravo", "cleanup:bravo", "failed:bravo"),
        "charlie": ("open:charlie", "execute:charlie", "cleanup:charlie", "failed:charlie"),
    }
    assert run_batch(tuple(items[name] for name in order)) == BatchReport(
        ("alpha",), tuple(name for name in order if name != "alpha"),
        tuple(event for name in order for event in expected_events[name]),
    )


def test_other_child_exception_fails_item_and_batch_continues(monkeypatch):
    original = command._child_operation

    def child(item, events):
        if item.name == "unexpected":
            events.append("execute:unexpected")
            raise RuntimeError("synthetic child failure")
        original(item, events)

    monkeypatch.setattr(command, "_child_operation", child)
    assert run_batch((ItemSpec("unexpected", "ok"), ItemSpec("next", "handled"))) == BatchReport(
        ("next",), ("unexpected",),
        (
            "open:unexpected", "execute:unexpected", "cleanup:unexpected", "failed:unexpected",
            "open:next", "execute:next", "handled:next", "cleanup:next", "processed:next",
        ),
    )


@pytest.mark.parametrize("error_type", [UnmatchedChildError, SiblingItemError, RuntimeError])
def test_wrapped_exception_keeps_cause_cleans_up_and_skips_after_call(monkeypatch, error_type):
    failure = error_type("synthetic child failure")
    events = []

    def child(item, observed):
        observed.append("execute:item")
        raise failure

    monkeypatch.setattr(command, "_child_operation", child)
    with pytest.raises(ItemProcessingError) as raised:
        command._process_item(ItemSpec("item", "ok"), events)
        events.append("after-call")
    assert raised.value.__cause__ is failure
    assert events == ["open:item", "execute:item", "cleanup:item"]


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_process_control_signal_is_not_swallowed(monkeypatch, error_type):
    failure = error_type("synthetic stop")
    events = []

    def child(item, observed):
        observed.append("execute:item")
        raise failure

    monkeypatch.setattr(command, "_child_operation", child)
    with pytest.raises(error_type) as raised:
        command._process_item(ItemSpec("item", "ok"), events)
        events.append("after-call")
    assert raised.value is failure
    assert events == ["open:item", "execute:item", "cleanup:item"]


def test_empty_batch():
    assert run_batch(()) == BatchReport((), (), ())


def test_repeated_mixed_reports_are_identical():
    items = (ItemSpec("a", "unmatched"), ItemSpec("b", "handled"), ItemSpec("c", "sibling"))
    expected = BatchReport(
        ("b",), ("a", "c"),
        (
            "open:a", "execute:a", "cleanup:a", "failed:a",
            "open:b", "execute:b", "handled:b", "cleanup:b", "processed:b",
            "open:c", "execute:c", "cleanup:c", "failed:c",
        ),
    )
    assert [run_batch(items) for _ in range(3)] == [expected, expected, expected]
