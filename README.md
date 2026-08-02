# floppy-led

Insert a floppy disk into a USB floppy drive on a Raspberry Pi; a `readme.txt`
file on the disk containing "red", "green", or "yellow" lights the matching
LED via `gpiozero`. Removing the disk (or inserting an unreadable one) turns
the LEDs off.

## Hardware

- Raspberry Pi with a USB floppy drive attached
- Three LEDs (with appropriate current-limiting resistors) wired to:
  - Red &rarr; GPIO5
  - Green &rarr; GPIO16
  - Yellow &rarr; GPIO12

## How it works

`floppy-led.py` runs as a persistent daemon (not a one-shot udev `RUN+=`
script). It uses `pyudev` to listen for `block` subsystem uevents and reacts
whenever a device tagged `ID_DRIVE_FLOPPY=1` reports a filesystem
(`ID_FS_TYPE`). It mounts that device read-only, reads `readme.txt` from the
root of the disk, and sets the LEDs to match.

Two things make this trickier than a typical udev rule:

- **No native media-change signalling.** USB floppy bridges don't tell Linux
  when a disk is swapped, so detection relies on `udisks2`'s periodic polling
  of removable drives (it re-probes every couple of seconds and fires a fresh
  `change` uevent when the state changes). No installation is needed for
  this &mdash; `udisks2` polls any device udev tags as removable/floppy
  automatically.
- **Inconsistent device naming.** Some floppy disks mount directly as
  `/dev/sda` (a "superfloppy" with no partition table). Others get a spurious
  `/dev/sda1` partition device, because a standard FAT boot sector's trailing
  `0x55AA` signature happens to look like a valid MBR to the kernel's
  partition scanner. The daemon doesn't hardcode a device path &mdash; it
  reads `DEVNAME` from whichever uevent fired.

A one-shot script triggered directly via udev's `RUN+=` was deliberately
avoided: udev `RUN+=` handlers must return quickly and shouldn't block, and
using `gpiozero` in a short-lived process is also awkward because gpiozero
releases (and effectively turns off) GPIO pins on process exit, which would
undo the very LED state we just set. Running as a long-lived systemd service
sidesteps both problems.

## Install

Run on the Raspberry Pi (requires `python3-gpiozero` and `python3-pyudev`,
both available via `apt` on Raspberry Pi OS / Debian):

```
sudo install -m 755 floppy-led.py /usr/local/bin/floppy-led.py
sudo install -m 644 floppy-led.service /etc/systemd/system/floppy-led.service
sudo systemctl daemon-reload
sudo systemctl enable --now floppy-led.service
```

## Usage

Format a floppy disk with a plain FAT filesystem and add a `readme.txt` file
at its root containing `red`, `green`, or `yellow`:

```
sudo mount /dev/sda /mnt/floppy   # or /dev/sda1, depending on the disk
echo "red" | sudo tee /mnt/floppy/readme.txt
sudo umount /mnt/floppy
```

Insert the disk into the drive. Within a few seconds the matching LED lights
up. Check progress with:

```
sudo journalctl -u floppy-led.service -f
```

## Troubleshooting a "won't read" disk

If a disk fails to mount with a kernel message like:

```
sd 0:0:0:0: [sda] Unit Not Ready
sd 0:0:0:0: [sda] Sense Key : 0x3 [current]
sd 0:0:0:0: [sda] ASC=0x30 ASCQ=0x1
```

that's `CANNOT READ MEDIUM - UNKNOWN FORMAT` &mdash; the drive detects media
but can't sync to it. This is a physical drive/media issue, not a missing
package. Try cleaning the read head with an isopropyl alcohol swab, or test
with a different disk to tell drive faults apart from disk faults.
