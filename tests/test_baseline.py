from batch_command import ItemSpec, run_batch


def test_processes_an_ordinary_item() -> None:
    report = run_batch((ItemSpec("alpha", "ok"),))

    assert report.processed == ("alpha",)
    assert report.failures == ()
    assert report.events == (
        "open:alpha",
        "execute:alpha",
        "cleanup:alpha",
        "processed:alpha",
    )


def test_handles_the_documented_recoverable_condition() -> None:
    report = run_batch((ItemSpec("bravo", "handled"),))

    assert report.processed == ("bravo",)
    assert report.failures == ()
    assert report.events == (
        "open:bravo",
        "execute:bravo",
        "handled:bravo",
        "cleanup:bravo",
        "processed:bravo",
    )
