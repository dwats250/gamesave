# gamesave

`gamesave` is a manifest-based sync tool for retro gaming save files and save
states. It compares emulator folders against a shared sync directory, plans safe
uploads/downloads, and preserves conflicts instead of overwriting them.

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

The shared directory layout is:

```text
RetroSaveSync/
  manifest.json
  saves/
    gba/save/...
    gba/state/...
```

## Conflict Behavior

When the same save changed locally and in the sync directory, `gamesave` keeps
the sync copy in place and writes the local copy as a conflict file:

```text
Pokemon Emerald.conflict.steamdeck.20260428-120455.sav
```

Resolve conflicts manually after deciding which save should win.
