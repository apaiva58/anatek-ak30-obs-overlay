"""
reader.py
=========
Reads 21-byte frames from the Anatec AK30 serial port
and updates match_state continuously.

Can run in two modes:
  - serial: reads from real USB port
  - simulate: uses simulator.py for testing

Usage (from server.py):
    from reader import start_reader
    start_reader(mode="serial", port="/dev/tty.usbserial-1110")
    start_reader(mode="simulate")
"""

import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parser import parse, format_clock
from state import match_state


FRAME_LENGTH = 21


def _update_state(parsed: dict):
    """Update match_state from a parsed Anatec frame."""
    if not parsed:
        return

    match_state["anatec_home_score"]   = parsed["home_score"]
    match_state["anatec_guest_score"]  = parsed["guest_score"]
    match_state["anatec_home_fouls"]   = parsed["home_fouls"]
    match_state["anatec_guest_fouls"]  = parsed["away_fouls"]
    match_state["anatec_home_timeouts"]  = parsed["home_timeouts"]
    match_state["anatec_guest_timeouts"] = parsed["guest_timeouts"]
    match_state["anatec_period"]       = parsed["period"]
    match_state["anatec_clock_min"]    = parsed["clock_min"]
    match_state["anatec_clock_sec"]    = parsed["clock_sec"]
    match_state["anatec_clock"]        = format_clock(parsed)
    match_state["anatec_clock_running"]= parsed["clock_running"]
    match_state["anatec_timeout"]      = parsed["timeout_active"]
    match_state["anatec_service_dot"]  = parsed["service_dot"]
    match_state["anatec_connected"]    = True


def _read_serial(port: str, baud: int = 2400):
    """Read frames from real serial port with auto-reconnect."""
    try:
        import serial
    except ImportError:
        print("pyserial not installed — run: pip3 install pyserial --break-system-packages")
        return

    while True:
        print(f"Connecting to Anatec on {port} @ {baud} baud...")
        try:
            ser = serial.Serial(port, baud, timeout=2)
            print(f"Connected.")
            match_state["anatec_connected"] = True
            buf = bytearray()

            while True:
                data = ser.read(64)
                if data:
                    buf.extend(data)
                    while len(buf) >= FRAME_LENGTH:
                        frame = bytes(buf[:FRAME_LENGTH])
                        buf = buf[FRAME_LENGTH:]
                        parsed = parse(frame)
                        if parsed:
                            _update_state(parsed)

        except Exception as e:
            print(f"Serial error: {e} — retrying in 5 seconds")
            match_state["anatec_connected"] = False
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(5)


def _read_simulate():
    """Feed frames from simulator."""
    from simulator import game_sequence, make_frame
    print("Anatec reader running in SIMULATE mode.")
    match_state["anatec_connected"] = True

    while True:
        for frame, label, pause in game_sequence():
            parsed = parse(frame)
            if parsed:
                _update_state(parsed)
                print(f"[SIM] {label} — {match_state['anatec_clock']}")
            time.sleep(pause)
        # loop indefinitely
        time.sleep(2)


def start_reader(mode: str = "simulate", port: str = None, baud: int = 2400):
    """
    Start the Anatec reader in a background thread.

    mode: "serial" or "simulate"
    port: serial port path (required for serial mode)
    """
    if mode == "serial":
        if not port:
            print("Serial mode requires a port argument.")
            return
        t = threading.Thread(target=_read_serial, args=(port, baud), daemon=True)
    else:
        t = threading.Thread(target=_read_simulate, daemon=True)

    t.start()
    return t