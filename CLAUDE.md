# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Local macOS water-reminder for a weekday work schedule (Mon–Fri, 09:30–18:00). The user carries a 0.5 L thermos and refills at a water dispenser; the app nudges them to drink and refill toward a daily goal (default 2.5 L). The user communicates in Turkish, and all UI strings are Turkish.

No build step, no dependencies. Tests use stdlib `unittest`. macOS-only: it relies on `osascript` and system `/usr/bin/python3` (3.9, so avoid newer syntax).

## Commands

```
python3 su_hatirlatici.py                      # run the reminder loop (foreground)
python3 su_hatirlatici.py --test               # show one reminder immediately, then exit
python3 su_hatirlatici.py --ayarla             # user settings: --hedef-litre --baslangic --bitis --kap-ml (no flags = interactive)
python3 su_hatirlatici.py --install-autostart  # write + load a launchd agent (local.su-hatirlatici)
python3 su_hatirlatici.py --uninstall-autostart
python3 -m unittest discover -s tests -v       # run all tests
python3 -m unittest tests.test_su_hatirlatici.RemindTests.test_snooze_changes_nothing  # single test
rm ~/.su_hatirlatici.json                      # reset today's state (--test records a real 150 ml sip)
```

Popup alone: `osascript -l JavaScript popup.js <theme su|doldur|ozet> "<message>" <timeout_s> <button1> [button2 ...]` prints the pressed button's title to stdout, and nothing on timeout.

## Architecture

Two files that must stay side by side:

- `su_hatirlatici.py` — scheduler and state. Constants at the top are defaults; user choices (hours, goal, vessel size) live in `~/.su_hatirlatici_ayar.json`, written by `--ayarla` and applied to the globals by `apply_settings()` on every loop turn (interval is derived: span / ceil(goal/sip), clamped 10–60). Sip size and snooze remain constants. `run()` polls every 20 s; `in_hours()` gates on weekday and time; `remind()` decides between a "drink" prompt and a "thermos empty, refill" prompt from the tracked `thermos` level. State (`date`, `drunk`, `thermos`) lives in `~/.su_hatirlatici.json` and resets when the date changes; the thermos is assumed empty at the start of each day. An end-of-day summary popup fires once after `END` on workdays.
- `popup.js` — a JXA (AppKit via `osascript -l JavaScript`) borderless, colored floating `NSPanel` anchored bottom-right of the main screen's `visibleFrame`. Message convention: first line = title, a line starting with `Bugün:` containing `X / Y` drives the progress bar, remaining lines = body; keep titles short (one line, no wrapping). Theme picks color/icon. `ask()` in the Python file shells out to it and treats empty stdout as "ignored/snoozed". Window size is the `W`/`H` constants. JXA doesn't expose `NSAttributedString` initializers and offscreen render skips layer-backed subviews, so bars/button backgrounds are `NSBox` and button text color uses `contentTintColor`.

## First-run setup

`--install-autostart` on a fresh install (no `~/.su_hatirlatici_ayar.json`) calls `first_run_setup()`: four `popup.js` cards (theme `kurulum`, mouse-only choice buttons, progress via an `Adım: X / Y` line; the last button, prefixed `✓`, is the current default) ask goal, start, end and vessel size, then a summary card. Answers are saved, `skip_today()` is set so reminders begin the next workday, and only then is the launchd agent loaded. Unanswered (5 min timeout) = defaults, no skip. It works from non-interactive shells (Claude Code) since it only needs the screen. Custom values outside the offered choices go through `--ayarla`.

## Tests

`tests/test_su_hatirlatici.py` covers scheduling (`in_hours`, `next_start`), state persistence, and `remind()` branches. It mocks `ask` and `save_state`/`STATE_FILE`, so no popup appears and the real `~/.su_hatirlatici.json` is untouched. `popup.js` has no automated tests; verify it manually with `--test`.

## Gotchas

- The popup must never take keyboard focus (`becomesKeyOnlyIfNeeded`, no `makeKeyAndOrderFront`, no Enter key equivalent). If it becomes the key window, the user's typing goes to it and macOS beeps. It is mouse-only by design.

- Tkinter is not usable here: system Tk crashes on this macOS version ("macOS 14 (1408) or later required"). That's why the popup is JXA rather than Python GUI.
- The native `display dialog` was rejected because it can't be positioned; keep the custom panel.
- The popup process exits via `$.exit(0)` from the button handler or a timeout timer; button identity is passed back only through stdout, so keep button titles in sync with the string comparisons in `remind()` ("İçtim", "Ertele", "Doldurdum, içtim").
