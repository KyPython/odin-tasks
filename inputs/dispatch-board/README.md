# Dispatch board

This small Python project models the date label shown on a dispatch board. It
uses only the Python standard library.

## Run the starter test

```bash
python -m unittest discover -s tests -v
```

## Reproduce timezone sensitivity

```bash
python scripts/show_timezone_variation.py
```

You can also run the test in individual process timezones:

```bash
TZ=Pacific/Kiritimati python -m unittest discover -s tests -v
TZ=Etc/GMT+12 python -m unittest discover -s tests -v
```
