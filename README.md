# MediTrack

MediTrack helps medical professionals track appointments with their clients and the prescriptions issued to them. It comes in two versions with the same features, built on one shared module:

| File | Purpose |
| --- | --- |
| `meditrack_core.py` | Records, rules, validation, algorithms and file storage |
| `main.py` | Text-based version |
| `gui.py` | Tkinter GUI version |
| `tests/test_meditrack.py` | Automated tests |

## Features

- Add and list professionals
- Add clients, and search them by name, phone or ID
- Book, reschedule, complete and cancel appointments, with clashes rejected for both the professional and the client
- Filter appointments by professional, client, date or status
- Find the next free slot for a professional and client
- Issue, view and stop prescriptions, with overlapping courses of the same medication rejected
- See prescriptions ending within a chosen number of days
- Save automatically to `meditrack_data.json` and load on startup

The free-slot finder only offers times from 09:00 to 17:00, Monday to Friday, on 15-minute boundaries. Direct bookings can be made at any future time.

## Install and run

You need Python 3.9 or later. MediTrack has no third-party packages, but the GUI needs Tkinter. To check that it works, run `python3 -m tkinter`, which should open a small window.

Tkinter can be a problem on macOS:

- **Homebrew Python** doesn't include Tkinter, so `gui.py` fails with `No module named '_tkinter'`. `brew install python-tk@3.14` adds it, but on older macOS versions Homebrew may try to compile Python from source, and that can fail.
- **The system Python** at `/usr/bin/python3` can abort when it opens a window, with a `macOS 13 ... required` message.
- **What works without Homebrew:** a Python that bundles its own Tkinter, such as the python.org installer or a [python-build-standalone](https://github.com/astral-sh/python-build-standalone) release.

If `python3` has no Tkinter, the GUI tests are skipped rather than failed, so check the skip count in the test results.

Text version:

```bash
python3 main.py
```

GUI version:

```bash
python3 gui.py
```

Tests:

```bash
python3 -m unittest discover -s tests
```

The two versions share `meditrack_data.json`. Close one before making changes in the other, because each keeps its own copy in memory and overwrites the file when it saves.

## Limitations

- **Not for real patient data:** the data file is plain, unencrypted JSON, and there are no user accounts or audit trail. Use made-up records only.
- **Records can't be deleted:** people can't be edited or removed, and appointments and prescriptions can only be cancelled or stopped.
- **No medication safety checks:** MediTrack doesn't check dose limits, drug interactions or allergies.

