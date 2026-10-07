# Dispatch label behavior

The dispatch label must contain the calendar date at the dispatch location at
the instant the label is created. A date must not change merely because the
machine running the application uses a different local timezone.

Dates around local midnight and daylight-saving transitions are part of this
contract.
