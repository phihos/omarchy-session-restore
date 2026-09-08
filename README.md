# Session Restore — an Omarchy shell plugin

Reopens the apps you had open, on the workspaces you had them on, after a
reboot. Neither Omarchy nor Hyprland ships this: Hyprland
[declined session restore as out of scope](https://github.com/hyprwm/Hyprland/issues/2475),
and the [Omarchy discussion asking for it](https://github.com/omacom/omarchy/discussions/2123)
has only community workarounds. This is one, built on Omarchy's supported
extension points.

## Install

```bash
omarchy plugin add https://github.com/<you>/omarchy-session-restore.git --enable
```

The plugin runs as a shell `service` (no bar widget). It snapshots your layout
every 60 seconds and replays it at login.

## Usage

It is meant to be invisible, but the engine is a normal CLI:

```bash
./hypr-session show      # what would be restored
./hypr-session save      # snapshot now
./hypr-session restore   # replay the snapshot
```

| Path | What |
|------|------|
| `~/.local/state/omarchy/session.json` | the snapshot |
| `~/.config/omarchy/session-skip.txt`  | window classes to never save or restore |

## How it works

**Snapshot.** Each window's relaunch command comes from `/proc/<pid>/cmdline`,
so arguments survive. Most session tools keep a hand-maintained class→binary map
and lose that.

Terminals get their directory from the shell running inside them rather than
from their own argv, because argv only records where the terminal was *opened* —
`cd` somewhere during the day and argv is stale.

Chromium is the exception: every web app and browser window shares one process,
so a window's cmdline names whichever app started that process, and keying on
the pid would drop all the others. Those windows are identified by class
instead, and the exact URL is recovered by matching the class against the
`omarchy-launch-webapp` entry in your `.desktop` launchers, falling back to
decoding the URL out of the class.

**Restore.** Each app launches with Hyprland's `[workspace N silent]` rule, and
then — once its window actually maps — is placed explicitly by address.

The second step is not redundant. Omarchy ships
`misc:initial_workspace_tracking = 0` so that apps open on your *current*
workspace, which reduces the exec rule to a timing heuristic: a slow starter
like Chromium maps after the rule has expired and lands wherever you happen to
be, and `omarchy-launch-webapp`'s `setsid` hides the process from the rule
altogether. Placing by address afterwards is what makes web apps land reliably.

Omarchy also sets `misc:focus_on_activate = true`, so apps grab focus as they
finish loading; the restore re-asserts your original workspace afterwards.

## Notes and limits

- Snapshots are **periodic, not on shutdown**. That is deliberate: it also
  survives a crash or a power cut, and saving at `SIGTERM` is a race in any
  design. The cost is that windows opened in the last minute may be missed.
- Only window *placement* is restored. Applications restore their own internal
  state (tabs, buffers, unsaved work) as well as they normally do.
- Browsers are relaunched once via `omarchy-launch-browser` and restore their
  own windows and tabs.
- A slow starter may flash briefly on the current workspace before it is moved.
- What the restore did is logged to `~/.local/state/omarchy/session-restore.log`,
  since it runs unattended at login with no terminal to print to. Saves are
  logged only when the layout actually changed, so the log stays a record of
  events rather than a 60-second heartbeat. It rotates once at 256 KB, so it
  costs at most ~512 KB.
- `omarchy restart shell` will not duplicate your windows: the restore is a
  no-op unless the session is empty and nothing has been restored this boot.
- Plugin ids in Omarchy are author-scoped. Fork and change `id` in
  `manifest.json` if you publish your own build.

## Requirements

Omarchy 4.x with Hyprland 0.56+ (the Lua config parser — this uses Lua
dispatchers such as `hl.dsp.window.move`, and `hyprctl keyword` no longer
exists). Python 3, no third-party modules.

⚠️ Plugins run as unsandboxed code inside your long-lived `omarchy-shell`
process. Read the source before enabling this or any other plugin.

## Prior art

[`wbarakat/omarchy-session-restore`](https://github.com/wbarakat/omarchy-session-restore)
arrived at the same core idea independently and earlier: rebuild launch commands
from `/proc/<pid>/cmdline`, restore at shell startup, place windows silently.
Worth using if it fits you.

This one differs in handling Chromium web apps — which that plugin documents as
a known limitation ("windows sharing one process collapse to a single relaunch
entry") and which is most of a browser-heavy work session — and in snapshotting
periodically rather than on the way to a reboot. Reading its source also
improved this one: capturing the terminal's live working directory, and using an
advisory lock the kernel releases on death rather than a lock file a crash can
leave behind.

## License

MIT
