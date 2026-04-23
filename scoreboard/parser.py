"""
parser.py
=========
Parses 21-byte Anatec AK30 serial frames into a readable dict.

Frame format: ASCII encoded, space-separated values.
All values transmitted as ASCII: '0'=0x30, '1'=0x31, etc.
Spaces (0x20) represent zero or empty at that position.

Byte positions (confirmed from capture sessions 2026-04-20 and 2026-04-23):

  HOME SCORE
  16      hundreds
  17      tens
  18      units

  GUEST SCORE
  12      hundreds
  11      tens
  10      units

  HOME FOULS
  2       tens (activates at 10)
  3       units

  AWAY FOULS
  4       tens (activates at 10)
  5       units

  PERIOD
  6       period number (1=Q1, 2=Q2, 3=Q3, 4=Q4)

  CLOCK (above 1 minute)
  19      minutes tens
  20      minutes units / running flag (0x31 = running)
  13      seconds tens
  14      seconds units

  CLOCK (below 1 minute — tenths of second mode)
  19      seconds tens
  20      seconds units
  13      space (0x20)
  14      tenths of second

  SERVICE DOT / SHOT CLOCK ZERO
  15      0x07 = service dot ON, 0x20 = OFF

  TIMEOUT
  7       0x54 ('T') = home timeout active
          0x47 ('G') = guest timeout active
          0x20 = none

  HOME TIMEOUTS TAKEN
  9       count

  GUEST TIMEOUTS TAKEN
  8       count

  UNKNOWN
  0+1     always 0x30 0x30 — purpose unknown
"""

FRAME_LENGTH = 21


def _digit(frame: bytes, pos: int) -> int:
    """Read ASCII digit at position. Returns 0 for space or non-digit."""
    v = frame[pos]
    if 0x30 <= v <= 0x39:
        return v - 0x30
    return 0


def _number(frame: bytes, *positions) -> int:
    """Read multi-digit number from multiple positions (hundreds, tens, units)."""
    result = 0
    for pos in positions:
        result = result * 10 + _digit(frame, pos)
    return result


def parse(frame: bytes) -> dict | None:
    """
    Parse a 21-byte Anatec AK30 frame.
    Returns a dict or None if frame is invalid.
    """
    if len(frame) != FRAME_LENGTH:
        return None

    # Clock — detect sub-second mode
    # Above 1 minute: pos 13 = seconds tens, pos 14 = seconds units
    # Below 1 minute: pos 13 = space, pos 14 = tenths, pos 19+20 = seconds
    sub_second = frame[13] == 0x20

    if sub_second:
        # Below 1 minute — pos 19+20 = seconds, pos 14 = tenths
        seconds = _number(frame, 19, 20)
        tenths = _digit(frame, 14)
        minutes = 0
        clock_running = False  # sub-second is always near end, stopped
    else:
        # Above 1 minute
        tenths = None
        seconds = _number(frame, 13, 14)

        # Clock running — pos 20 = 0x31 when running
        if frame[20] == 0x31:
            minutes = _digit(frame, 19)
            clock_running = True
        else:
            min_tens = _digit(frame, 19) if frame[19] != 0x20 else 0
            min_units = _digit(frame, 20)
            minutes = min_tens * 10 + min_units
            clock_running = False

    # Timeout
    timeout_flag = frame[7]
    if timeout_flag == 0x54:
        timeout_active = "home"
    elif timeout_flag == 0x47:
        timeout_active = "guest"
    else:
        timeout_active = None

    return {
        "home_score":      _number(frame, 16, 17, 18),
        "guest_score":     _number(frame, 12, 11, 10),
        "home_fouls":      _number(frame, 2, 3),
        "away_fouls":      _number(frame, 4, 5),
        "period":          _digit(frame, 6),
        "clock_min":       minutes,
        "clock_sec":       seconds,
        "clock_tenths":    tenths,
        "clock_running":   clock_running,
        "sub_second":      sub_second,
        "timeout_active":  timeout_active,
        "home_timeouts":   _digit(frame, 9),
        "guest_timeouts":  _digit(frame, 8),
        "service_dot":     frame[15] == 0x07,
    }


def format_clock(parsed: dict) -> str:
    """Format clock as MM:SS or 0:SS.t string."""
    if parsed["sub_second"]:
        t = parsed["clock_tenths"] if parsed["clock_tenths"] is not None else 0
        return f"0:{parsed['clock_sec']:02d}.{t}"
    return f"{parsed['clock_min']:02d}:{parsed['clock_sec']:02d}"