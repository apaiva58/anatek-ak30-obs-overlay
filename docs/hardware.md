# Hardware Notes

This document describes the hardware setup for connecting the Anatec AK30 
controller to a laptop for serial data capture.

---

## Option 1 — USB (recommended, try first)

The Anatec AK30 controller has a USB port (USB-B, the square connector).
Connect it directly to your laptop with a standard USB-A to USB-B cable.

    Anatec AK30 controller (USB-B)
            |
        USB cable
            |
        Laptop (USB-A)

On macOS, open Terminal and run:

    ls /dev/tty.*

If the controller is recognised you will see something like:

    /dev/tty.usbserial-XXXXXX

Use that port name in capture.py.

Note: The USB port on unmodified AK30 units may or may not be active.
Anatec offers a hardware modification to enable USB output for the 
Sportlinked / NBB digital match form integration. If the port shows 
nothing, proceed to Option 2.

---

## Option 2 — DIN 5-pin serial tap

If the USB port is not active, the same serial data can be tapped from 
the DIN 5-pin connector that connects the controller to the display board.

### The connector

The AK30 uses a Lumberg 0137 series locking DIN connector — a standard 
DIN 5-pin with a metal spring latch tab on top for secure connection.

    Lumberg 0137 05 — 5-pin locking DIN

### What you need

- DIN 5-pin male to open-end cable (bare wires)
- FTDI FT232RL USB-to-serial adapter (5V tolerant)
- Multimeter (to identify TX and GND pins)

All available from:
- reichelt.de
- conrad.nl
- amazon.nl

### Signal properties

- Protocol: UART serial, 8N1
- Baud rate: 2400
- Voltage: 5V TTL (confirmed from PIC16F873 datasheet)
- Direction: controller transmits, display receives

Your FTDI adapter must be 5V tolerant. Most FT232RL boards support 
both 3.3V and 5V via a jumper — set it to 5V.

### Identifying the correct pins

The DIN 5-pin 180-degree pinout is:

    Pin layout (looking into the socket):
    
        1   2   3
          4   5
    
    Typical assignment:
    Pin 1 — GND or signal
    Pin 2 — GND
    Pin 3 — TX data
    Pin 4 — RX data  
    Pin 5 — +5V power

Note: Anatec may use a custom pinout. Always verify with a multimeter 
before connecting anything.

### Identifying pins with a multimeter

Set your multimeter to DC voltage.

Step 1 — find GND:
- Black probe on the outer metal collar of the DIN connector
- Touch red probe to each pin one by one
- The pin reading 0V is GND

Step 2 — find TX:
- Keep black probe on the GND pin
- Touch red probe to each remaining pin
- The TX data line will show a fluctuating voltage (roughly 3-5V) 
  while the controller is powered on — it pulses with the data stream
- A steady 5V or 0V pin is not TX

### Wiring to FTDI adapter

Once you have identified TX and GND:

    DIN connector TX pin  ->  FTDI RXD pin
    DIN connector GND pin ->  FTDI GND pin

That is all. You are only listening (not sending), so FTDI TXD 
is not needed.

### Non-destructive tap using a splitter

To keep the display working normally while tapping the data line, 
use a DIN 5-pin splitter:

    Controller (DIN female socket)
            |
    DIN splitter (male plug in)
        |               |
    female out       female out
        |               |
    existing cable   your cable
        |               |
    display board    FTDI adapter -> laptop

The display keeps working normally. The controller does not know 
anything extra is connected.

---

## Connection diagram

    Anatec AK30 controller
            |
        DIN cable (Option 2) or USB cable (Option 1)
            |
        FTDI adapter (Option 2 only)
            |
        USB
            |
        Laptop running capture.py
            |
        /dev/tty.usbserial-XXXX
            |
        Python / pyserial

---

## Tested configuration

- Controller: Anatec AK30-IPF
- Connection: USB-B to USB-A
- Laptop: MacBook (macOS)
- Baud rate: 2400
- Frame length: 23 bytes
- Frame terminator: carriage return (0x0D)

---

## References

- Anatec AK30-IPF manual:
  https://anatec.nl/wp-content/uploads/2019/07/Handleiding_bedieningsunit_met_persoonlijke_fouten_AK30_IPF_v10.1_.0_L_.pdf

- Remco van den Enden — vMixScoreboard:
  https://github.com/remcoenden/vMixScoreboard

- Lumberg 0137 series connector:
  https://www.reichelt.de (search: Lumberg 0137 05)

- FTDI FT232RL adapter:
  https://www.reichelt.de (search: FTDI FT232)
