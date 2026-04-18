# anatek-ak30-obs-overlay
ython bridge between Anatec AK30 scoreboard controller and OBS Studio for live basketball overlay. Reads serial data via USB, serves a web overlay, feeds into OBS Browser Source. Developed by Almere Pioneers basketball club.

# Almere Pioneers Scoreboard Bridge

A Python-based bridge between the Anatec AK30 scoreboard controller 
and OBS Studio, enabling live scoreboard overlays for basketball 
livestreams without manual score input.

## What it does

Reads live scoreboard data directly from the Anatec AK30 controller 
via USB, serves it as a web overlay, and feeds it into OBS Studio as 
a Browser Source. One person operates the scoreboard as normal — 
the overlay updates automatically.

## Background

This project was developed by Almere Pioneers basketball club 
(Almere, Netherlands) to automate scoreboard overlays for 
livestreamed matches.

The serial protocol was reverse-engineered from the Anatec AK30-IPF 
controller. Credit to Remco van den Enden 
(github.com/remcoenden/vMixScoreboard) whose work on the AnatecIndor 
serial reader provided the foundation.

## Hardware

- Anatec AK30-IPF scoreboard controller
- USB cable (USB-A to USB-B) from controller to Mac/PC
- MacBook or laptop running OBS Studio

If USB is not available on your controller model, see 
`docs/hardware.md` for the DIN 5-pin serial tap approach using an 
FTDI adapter.

## Project Status

| Milestone | Status |
|---|---|
| Protocol discovery | 🔄 In progress |
| Technical version (terminal) | ⏳ Planned |
| Packaged macOS app | ⏳ Planned |
| Extended features (fouls, timeouts) | ⏳ Planned |
| Community / other clubs | ⏳ Planned |

## Roadmap

See [Milestones](../../milestones) for the full development plan.

### Milestone 1 — Protocol Discovery
- [ ] USB connection test
- [ ] Capture session with capture.py
- [ ] Document all byte positions
- [ ] Publish protocol documentation

### Milestone 2 — Technical Version
- [ ] Serial reader module
- [ ] Frame parser module  
- [ ] Flask server + JSON endpoint
- [ ] HTML/CSS overlay
- [ ] OBS integration test

### Milestone 3 — Packaged macOS App
- [ ] Simple GUI (auto-detect USB, status display)
- [ ] Bundle as .app with PyInstaller
- [ ] Volunteer setup guide

### Milestone 4 — Extended Features
- [ ] Period display
- [ ] Team fouls display
- [ ] Timeouts display
- [ ] Pioneers branding

### Milestone 5 — Community
- [ ] Contact Remco van den Enden
- [ ] Publish protocol documentation for Dutch basketball community
- [ ] README for other clubs using Anatec scoreboards

## Supported Hardware

Developed and tested with:
- Anatec AK30-IPF (with personal foul panels)

Likely compatible with:
- Anatec AK30-I (without personal foul panels)
- Other Anatec AK30 variants

## Requirements

- Python 3.8+
- pyserial
- Flask
- OBS Studio with Browser Source support

## Quick Start

```bash
# Install dependencies
pip3 install pyserial flask

# Discover your serial port
ls /dev/tty.*

# Run protocol capture (first time)
python3 capture.py

# Run the bridge (once protocol is confirmed)
python3 scoreboard/server.py --port /dev/tty.usbserial-XXXX
```

## Repository Structure
