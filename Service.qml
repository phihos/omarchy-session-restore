import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  // Injected by omarchy-shell (the service loader).
  property var shell: null

  // The snapshot engine ships with the plugin, so resolve it relative to this
  // file rather than expecting it on PATH: the restore fires early at login,
  // before a PATH imported from the session environment can be relied on, and
  // a published plugin cannot assume anything about the user's ~/.local/bin.
  readonly property string bin: String(Qt.resolvedUrl("hypr-session")).replace(/^file:\/\//, "")

  // How often the layout is snapshotted. Periodic beats save-on-shutdown: it
  // also survives a crash, a power cut, or a hard reset, and saving at SIGTERM
  // is a race in any design.
  readonly property int saveIntervalMs: 60000

  // Give Hyprland and the shell a moment to settle before replaying a session.
  readonly property int restoreDelayMs: 2500

  function save() {
    if (saveProcess.running) return
    saveProcess.command = [root.bin, "save"]
    saveProcess.running = true
  }

  function restore() {
    if (restoreProcess.running) return
    // --if-empty makes this a no-op unless the session is genuinely bare and
    // nothing has been restored since this boot, so `omarchy restart shell`
    // never duplicates your windows.
    restoreProcess.command = [root.bin, "restore", "--if-empty"]
    restoreProcess.running = true
  }

  Process {
    id: saveProcess
  }

  Process {
    id: restoreProcess
    // Only start snapshotting once the restore has settled, so a half-replayed
    // session is never written over a good snapshot.
    onExited: saveTimer.start()
  }

  Timer {
    id: restoreTimer
    interval: root.restoreDelayMs
    repeat: false
    running: true
    onTriggered: root.restore()
  }

  Timer {
    id: saveTimer
    interval: root.saveIntervalMs
    repeat: true
    onTriggered: root.save()
  }
}
