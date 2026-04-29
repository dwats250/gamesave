# gamesave

`gamesave` is a manifest-based sync tool for retro gaming save files and save
states. It is designed for Android retro handhelds such as the Anbernic RG476H
and Retroid Pocket 4 Pro, with Syncthing handling transport and `gamesave`
handling manifests, backups, naming audits, and conflict recovery.

## Quick Start

Create a config file:

```toml
device_name = "steamdeck"
sync_dir = "/home/deck/RetroSaveSync"
stability_seconds = 10

[[paths]]
system = "gba"
kind = "save"
path = "/home/deck/Emulation/saves/gba"
patterns = ["*.sav", "*.srm"]

[[paths]]
system = "gba"
kind = "state"
path = "/home/deck/Emulation/states/gba"
patterns = ["*.state", "*.ss*"]
```

Then run:

```bash
python3 -m gamesave status --config config.toml
python3 -m gamesave sync --config config.toml --dry-run
python3 -m gamesave sync --config config.toml
```

For Android handhelds, start from a preset:

```bash
python3 -m gamesave presets list
python3 -m gamesave init-device --profile rg476h --config gamesave.toml
python3 -m gamesave init-device --profile retroid-pocket-4-pro --config gamesave.toml
```

Or use the guided setup flow:

```bash
python3 -m gamesave walkthrough
python3 -m gamesave self-test --reset
```

`self-test` creates only synthetic files under:

```text
/storage/emulated/0/GamesaveTest
/storage/emulated/0/RetroSaveSyncTest
```

Use that test sync folder in Syncthing-Fork first. Only move to real emulator
folders after the self-test and test-folder Syncthing pass both work.

## Detailed Walkthrough

This walkthrough is meant to prove each risky part in isolation before real
emulator saves are touched. Run the same stages on both handhelds.

### Stage 1: Install And Clone

Install Termux and Syncthing-Fork on the handheld.

In Termux:

```bash
pkg update
pkg install python git
cd ~
git clone https://github.com/dwats250/gamesave.git
cd gamesave
```

Confirm the CLI works:

```bash
python3 -m unittest discover -s tests -v
python3 -m gamesave --help
python3 -m gamesave presets list
```

Stop here if Python, Git, or the test suite fails.

### Stage 2: Run The Synthetic Pipeline

Run:

```bash
python3 -m gamesave self-test --reset
```

Expected output should end with:

```text
doctor=WARN
scan=1
plan=UPLOAD
copy=ok
second_status=skip
result PASS
```

This creates:

```text
/storage/emulated/0/GamesaveTest/local/gba/TestGame.sav
/storage/emulated/0/RetroSaveSyncTest/saves/gba/save/TestGame.sav
gamesave-test.toml
```

This confirms `gamesave` can scan, plan, copy, write a manifest, and detect that
a second run is already synchronized.

### Stage 3: Test Syncthing With Synthetic Data

In Syncthing-Fork, share only this folder between handhelds:

```text
/storage/emulated/0/RetroSaveSyncTest
```

Do not add real emulator save folders yet.

On device A:

```bash
cd ~/gamesave
printf "from-device-a" > /storage/emulated/0/GamesaveTest/local/gba/TestGame.sav
python3 -m gamesave sync --config gamesave-test.toml
```

Wait until Syncthing-Fork says the test folder is synchronized.

On device B:

```bash
cd ~/gamesave
python3 -m gamesave sync --config gamesave-test.toml
cat /storage/emulated/0/GamesaveTest/local/gba/TestGame.sav
```

Expected:

```text
from-device-a
```

Then reverse the test from device B back to device A. Only continue after both
directions work.

### Stage 4: Create The Real Device Config

On the RG476H:

```bash
python3 -m gamesave init-device --profile rg476h --config gamesave.toml
```

On the Retroid Pocket 4 Pro:

```bash
python3 -m gamesave init-device --profile retroid-pocket-4-pro --config gamesave.toml
```

Open `gamesave.toml` and remove or edit emulator path entries you do not use.
Android emulator paths vary by app version and storage permissions, so treat the
preset as a starting point, not a guarantee.

### Stage 5: Real-Save Safety Gate

Run:

```bash
python3 -m gamesave doctor --config gamesave.toml
python3 -m gamesave backup --config gamesave.toml
python3 -m gamesave names audit --config gamesave.toml
python3 -m gamesave sync --config gamesave.toml --dry-run
```

Review the dry run before doing a real sync:

```text
UPLOAD    means local file would be copied into the sync folder
DOWNLOAD  means sync-folder file would be copied into the local emulator folder
CONFLICT  means both sides differ and gamesave will preserve a conflict copy
SKIP      means no file copy is needed
```

Do not continue if the dry run wants to download into the wrong emulator folder
or upload files you do not recognize.

### Stage 6: First Real Sync

After the dry run looks right:

```bash
python3 -m gamesave sync --config gamesave.toml
```

Wait for Syncthing-Fork to finish syncing the real `RetroSaveSync` folder before
starting the game on the other device.

On the other device:

```bash
python3 -m gamesave sync --config gamesave.toml --dry-run
python3 -m gamesave sync --config gamesave.toml
```

### Stage 7: Normal Use

Before switching devices:

```bash
python3 -m gamesave sync --config gamesave.toml
```

Wait for Syncthing-Fork to finish.

Before launching the game on the next device:

```bash
python3 -m gamesave sync --config gamesave.toml
```

For the lowest risk, quit the emulator before syncing. Save states are more
fragile than normal in-game saves, especially when emulator cores differ.

The shared directory layout is:

```text
RetroSaveSync/
  manifest.json
  backups/
  conflicts/
  reports/
  saves/
    gba/save/...
    gba/state/...
```

## Conflict Behavior

When the same save changed locally and in the sync directory, `gamesave` keeps
the sync copy in place and writes the local copy as a conflict file:

```text
RetroSaveSync/conflicts/gba/save/Pokemon Emerald.conflict.rg476h.20260428-120455.sav
```

Resolve conflicts after deciding which save should win:

```bash
python3 -m gamesave conflicts --config gamesave.toml
python3 -m gamesave resolve gba/save/Pokemon\ Emerald.sav --use sync --config gamesave.toml
python3 -m gamesave resolve gba/save/Pokemon\ Emerald.sav --use local --config gamesave.toml
python3 -m gamesave resolve gba/save/Pokemon\ Emerald.sav --use file --file winner.sav --config gamesave.toml
```

## Contingency Tools

Run setup checks:

```bash
python3 -m gamesave doctor --config gamesave.toml
```

Create an explicit backup snapshot:

```bash
python3 -m gamesave backup --config gamesave.toml
```

Audit save naming issues:

```bash
python3 -m gamesave names audit --config gamesave.toml
```

`doctor` writes `reports/doctor-latest.json`, and `names audit` writes
`reports/name-audit-latest.json` under the sync root.

## Android Notes

Both the RG476H and Retroid Pocket 4 Pro are Android handhelds. The intended v1
setup is:

1. Install Python through Termux or equivalent.
2. Install Syncthing-Fork or another compatible Syncthing client.
3. Sync a shared `RetroSaveSync` folder between devices.
4. Run `gamesave` locally on each handheld before and after play sessions.

Save states are treated as high-risk because they are often tied to emulator,
core, and version. Prefer in-game saves when possible, and keep RetroArch core
and save settings consistent across devices.
