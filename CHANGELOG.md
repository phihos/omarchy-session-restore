# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version is
the one in `manifest.json` — CI refuses a release whose tag and manifest
disagree.

## [Unreleased]

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

[Unreleased]: https://github.com/phihos/omarchy-session-restore/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/phihos/omarchy-session-restore/releases/tag/v0.1.0
