"""
simulator.py
============
Simulates Anatec AK30 serial output for testing the parser
and overlay without a physical scoreboard.

Generates a sequence of frames representing a game scenario:
  - Clock counts down
  - Home scores 2+2
  - Guest scores 2+2
  - Home scores 3
  - Free throw made
  - Timeout home
  - Fouls up to bonus
  - Multi-digit scores (10, 20, 99, 100, 119)
  - Sub-second clock

Byte positions (confirmed 2026-04-23):
  16+17+18  home score (hundreds, tens, units)
  12+11+10  guest score (hundreds, tens, units)
  2+3       home fouls (tens, units)
  4+5       away fouls (tens, units)
  6         period
  7         timeout flag (T=home, G=guest, space=none)
  8         guest timeouts
  9         home timeouts
  13+14     clock seconds (or space+tenths below 1 min)
  15        service dot (0x07=ON)
  19+20     clock minutes (or seconds below 1 min)

Usage:
    python3 scoreboard/simulator.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parser import parse, format_clock


def make_frame(
    home_score=0,
    guest_score=0,
    home_fouls=0,
    away_fouls=0,
    period=1,
    clock_min=10,
    clock_sec=0,
    clock_tenths=None,
    clock_running=False,
    timeout_active=None,
    home_timeouts=0,
    guest_timeouts=0,
    service_dot=False,
) -> bytes:
    """Build a 21-byte Anatec frame from game state."""

    def a(n):
        """ASCII encode a single digit (0-9)."""
        return 0x30 + max(0, min(9, n))

    def d(n, pos):
        """Extract digit at decimal position (0=units, 1=tens, 2=hundreds)."""
        return (n // (10 ** pos)) % 10

    f = bytearray(21)

    # pos 0+1 — always 0x30 0x30
    f[0] = 0x30
    f[1] = 0x30

    # pos 2+3 — home fouls (tens, units)
    f[2] = a(d(home_fouls, 1)) if home_fouls >= 10 else 0x20
    f[3] = a(d(home_fouls, 0))

    # pos 4+5 — away fouls (tens, units)
    f[4] = a(d(away_fouls, 1)) if away_fouls >= 10 else 0x20
    f[5] = a(d(away_fouls, 0))

    # pos 6 — period
    f[6] = a(period)

    # pos 7 — timeout flag
    f[7] = 0x54 if timeout_active == "home" else (0x47 if timeout_active == "guest" else 0x20)

    # pos 8+9 — guest/home timeout counts
    f[8] = a(guest_timeouts)
    f[9] = a(home_timeouts)

    # pos 10+11+12 — guest score (units, tens, hundreds)
    f[10] = a(d(guest_score, 0))
    f[11] = a(d(guest_score, 1)) if guest_score >= 10 else 0x20
    f[12] = a(d(guest_score, 2)) if guest_score >= 100 else 0x20

    # pos 13+14 — clock seconds / tenths
    # pos 15 — service dot
    # pos 19+20 — clock minutes / seconds (sub-second mode)

    if clock_tenths is not None:
        # sub-second mode: pos 13=space, pos 14=tenths, pos 19+20=seconds
        f[13] = 0x20
        f[14] = a(clock_tenths)
        f[15] = 0x07 if service_dot else 0x20
        f[16] = 0x20
        f[17] = 0x20
        f[18] = a(d(home_score, 0))
        f[19] = a(d(clock_sec, 1)) if clock_sec >= 10 else 0x20
        f[20] = a(d(clock_sec, 0))
    else:
        # normal mode
        f[13] = a(clock_sec // 10)
        f[14] = a(clock_sec % 10)
        f[15] = 0x07 if service_dot else 0x20
        f[16] = a(d(home_score, 2)) if home_score >= 100 else 0x20
        f[17] = a(d(home_score, 1)) if home_score >= 10 else 0x20
        f[18] = a(d(home_score, 0))

        if clock_running:
            f[19] = a(clock_min)
            f[20] = 0x31
        else:
            f[19] = a(clock_min // 10) if clock_min >= 10 else 0x20
            f[20] = a(clock_min % 10)

    return bytes(f)


def game_sequence():
    """
    Yields (frame, label, pause_seconds) tuples simulating a game.
    """
    s = dict(
        home_score=0, guest_score=0,
        home_fouls=0, away_fouls=0,
        period=1, clock_min=10, clock_sec=0,
        clock_tenths=None, clock_running=False,
        timeout_active=None,
        home_timeouts=0, guest_timeouts=0,
        service_dot=False,
    )

    def state(label, pause=1.0, **kwargs):
        s.update(kwargs)
        return make_frame(**s), label, pause

    yield state("Baseline — all zero, clock stopped", pause=2)

    # Clock counts down
    yield state("Clock starts", clock_running=True, clock_min=10, clock_sec=0)
    for sec in range(59, 29, -1):
        yield state(f"Clock 9:{sec:02d}", clock_min=9, clock_sec=sec, pause=0.1)

    # Home scores 2
    yield state("Home +2 (score 2:0)", clock_running=False,
                clock_min=9, clock_sec=30, home_score=2, pause=2)

    # Guest scores 2
    yield state("Guest +2 (score 2:2)", guest_score=2, pause=2)

    # Home scores 3
    yield state("Home +3 (score 5:2)", home_score=5, pause=2)

    # Free throw
    yield state("Home free throw (score 6:2)", home_score=6, pause=2)

    # Home timeout
    yield state("Home timeout", timeout_active="home",
                home_timeouts=1, pause=3)
    yield state("Timeout ends", timeout_active=None, pause=1)

    # Fouls to bonus
    yield state("Home foul 1", home_fouls=1, pause=1)
    yield state("Home foul 2", home_fouls=2, pause=1)
    yield state("Home foul 3", home_fouls=3, pause=1)
    yield state("Home foul 4 — BONUS", home_fouls=4, pause=2)
    yield state("Away foul 1", away_fouls=1, pause=1)
    yield state("Away foul 4 — BONUS", away_fouls=4, pause=2)

    # Multi-digit scores
    yield state("Home score 10", home_score=10, pause=2)
    yield state("Home score 20", home_score=20, pause=2)
    yield state("Home score 99", home_score=99, pause=2)
    yield state("Home score 100", home_score=100, pause=2)
    yield state("Home score 119", home_score=119, pause=2)
    yield state("Guest score 10", guest_score=10, pause=2)
    yield state("Guest score 99", guest_score=99, pause=2)
    yield state("Guest score 100", guest_score=100, pause=2)

    # Sub-second clock
    yield state("Clock below 1 minute", clock_min=0, clock_sec=59,
                clock_tenths=None, clock_running=True, pause=1)
    for sec in range(9, 0, -1):
        for tenth in range(9, -1, -1):
            yield state(f"Clock 0:{sec:02d}.{tenth}",
                       clock_sec=sec, clock_tenths=tenth, pause=0.05)
    yield state("Clock 0:00 — service dot", clock_sec=0, clock_tenths=0,
                service_dot=True, pause=2)
    yield state("Service dot off", service_dot=False, pause=1)

    # Period 2
    yield state("Period 2", period=2, clock_min=10, clock_sec=0,
                clock_tenths=None, home_fouls=0, away_fouls=0,
                clock_running=False, pause=2)

    yield state("End of simulation", pause=1)


def run():
    print("Anatec AK30 Simulator")
    print("=" * 50)
    print()

    for frame, label, pause in game_sequence():
        parsed = parse(frame)
        if not parsed:
            print(f"[PARSE ERROR] {label}")
            continue
        clock = format_clock(parsed)
        print(f"[{clock}] {label}")
        print(f"  Home {parsed['home_score']} — {parsed['guest_score']} Guest"
              f" | Period {parsed['period']}"
              f" | Fouls H:{parsed['home_fouls']} A:{parsed['away_fouls']}"
              f" | TO:{parsed['timeout_active'] or 'none'}"
              f" | dot:{parsed['service_dot']}")
        print(f"  frame: {frame.hex()}")
        print()
        time.sleep(pause)

    print("Done.")


if __name__ == "__main__":
    run()