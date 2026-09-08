# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version is
the one in `manifest.json` — CI refuses a release whose tag and manifest
disagree.

## [Unreleased]

## [0.1.1] - 2026-09-08

Fixes for the restore's closing steps, found while checking whether apps in
Omarchy's Meta+S scratchpad survive a restore. They do — and the snapshot side
already handled special workspaces correctly — but the restore left the desktop
in the wrong state afterwards.

### Fixed

- The restore never returned you to the workspace you started on. It called
  `hl.dsp.workspace(N)`, and `hl.dsp.workspace` is a namespace table rather
  than a dispatcher, so Hyprland answered "attempt to call a table value" every
  time. Switching workspace is `hl.dsp.focus`. Because the error was discarded,
  the log still reported a clean finish, and you simply ended up wherever the
  last app to load had grabbed focus.
- A failing dispatcher is now logged instead of being dropped. That silence is
  the only reason the bug above survived this long.
- Restoring an app into the scratchpad left the scratchpad pulled up over your
  desktop, because placing a window there by address reveals it. Any special
  workspace the restore reveals is now put away again, while one you already
  had open is left alone.

### Changed

- When one class was launched more than once — a terminal on a workspace and a
  second one in the scratchpad — the window that maps first no longer simply
  claims the first matching entry. It prefers the entry that wants the
  workspace the window actually reached, so two same-class windows cannot swap
  places, and falls back to launch order as before.

## [0.1.0] - 2026-09-08

First release. Reopens the apps you had open, on the workspaces you had them
on, after a reboot.

### Added

- A shell `service` that snapshots the window layout every 60 seconds and
  replays it once at login, guarded by `--if-empty` so `omarchy restart shell`
  cannot duplicate a live session.
- Relaunch commands rebuilt from `/proc/<pid>/cmdline`, so arguments survive
  without a hand-maintained class-to-binary map.
- Chromium web apps identified by window class rather than pid — every web app
  and browser window shares one process — with the exact URL recovered from the
  `omarchy-launch-webapp` entry in the matching `.desktop` launcher, falling
  back to decoding the URL out of the class.
- Terminals restored in the directory their shell was actually in, not the one
  they were opened with.
- Explicit placement by window address after launch, because Omarchy's
  `misc:initial_workspace_tracking = 0` reduces Hyprland's `[workspace N
  silent]` exec rule to a timing heuristic that slow starters lose.
- Floating windows restored to their size and position.
- A skip list at `~/.config/omarchy/session-skip.txt`, with desktop-owned
  windows skipped unconditionally.
- A log at `~/.local/state/omarchy/session-restore.log` recording what a
  restore did, written only when the layout changed so it stays a record of
  events rather than a 60-second heartbeat. It rotates once at 256 KB.

[Unreleased]: https://github.com/phihos/omarchy-session-restore/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/phihos/omarchy-session-restore/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/phihos/omarchy-session-restore/releases/tag/v0.1.0
