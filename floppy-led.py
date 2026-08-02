#!/usr/bin/env python3
import subprocess
from pathlib import Path

import pyudev
from gpiozero import LED

MOUNT_POINT = Path("/mnt/floppy")

LEDS = {
    "red": LED(5),
    "green": LED(16),
    "yellow": LED(12),
}


def set_leds(colour):
    for name, led in LEDS.items():
        led.value = name == colour


def read_colour(devname):
    MOUNT_POINT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["mount", "-o", "ro", devname, str(MOUNT_POINT)], check=True)
    try:
        text = (MOUNT_POINT / "readme.txt").read_text().strip().lower()
    finally:
        subprocess.run(["umount", str(MOUNT_POINT)], check=False)

    for name in LEDS:
        if name in text:
            return name
    return None


def handle_event(device):
    if device.get("ID_DRIVE_FLOPPY") != "1":
        return

    fs_type = device.get("ID_FS_TYPE")
    if not fs_type:
        print("disk removed or unreadable, turning off LEDs")
        set_leds(None)
        return

    devname = device.get("DEVNAME")
    try:
        colour = read_colour(devname)
    except Exception as e:
        print(f"failed to read {devname}: {e}")
        set_leds(None)
        return

    print(f"detected colour on {devname}: {colour}")
    set_leds(colour)


def main():
    set_leds(None)
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")

    for device in iter(monitor.poll, None):
        if device.action not in ("add", "change"):
            continue
        handle_event(device)


if __name__ == "__main__":
    main()
