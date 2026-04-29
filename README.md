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
