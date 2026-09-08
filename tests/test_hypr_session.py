"""Tests for the parts of the engine that run without a compositor.

Everything here is pure: no hyprctl, no live windows. That is not a
limitation so much as where the bugs are — placing a window is one
dispatcher call, but working out *what to relaunch* from a window class is
guesswork about Chromium, and guesswork is worth pinning down.
"""


# --- web app classes ---------------------------------------------------------

def test_class_for_url_flattens_the_path_like_chromium(session):
    assert session.class_for_url("https://app.slack.com/client") == \
        "chrome-app.slack.com__client-Default"


def test_class_for_url_joins_every_path_segment_with_underscores(session):
    assert session.class_for_url("https://example.com/a/b/c") == \
        "chrome-example.com__a_b_c-Default"


def test_class_for_url_leaves_the_path_empty_for_a_bare_host(session):
    assert session.class_for_url("https://example.com") == "chrome-example.com__-Default"


def test_class_for_url_ignores_a_trailing_slash(session):
    assert session.class_for_url("https://example.com/") == session.class_for_url(
        "https://example.com")


def test_class_for_url_rejects_a_non_http_url(session):
    assert session.class_for_url("file:///tmp/index.html") is None
    assert session.class_for_url("not a url") is None


def test_webapp_url_prefers_the_launcher_over_decoding(session):
    """The decode cannot tell a path's '_' from a flattened '/'; the launcher can.

    This is the whole reason .desktop files are read at all.
    """
    cls = session.class_for_url("https://example.com/my_app/inbox")
    launchers = {cls: "https://example.com/my_app/inbox"}
    assert session.webapp_url(cls, launchers) == "https://example.com/my_app/inbox"
    # Without the launcher the underscore is indistinguishable from a separator.
    assert session.webapp_url(cls, {}) == "https://example.com/my/app/inbox"


def test_webapp_url_decodes_when_no_launcher_matches(session):
    assert session.webapp_url("chrome-app.slack.com__client-Default", {}) == \
        "https://app.slack.com/client"


def test_webapp_url_decodes_a_bare_host(session):
    assert session.webapp_url("chrome-example.com__-Default", {}) == "https://example.com"


# --- .desktop scanning -------------------------------------------------------

def write_desktop(directory, name, body):
    (directory / name).write_text(body)


def test_webapp_launchers_reads_the_url_out_of_a_launcher(session, tmp_path, monkeypatch):
    monkeypatch.setattr(session, "DESKTOP_DIRS", [str(tmp_path)])
    write_desktop(tmp_path, "slack.desktop", (
        "[Desktop Entry]\nName=Slack\n"
        "Exec=omarchy-launch-webapp https://app.slack.com/client\n"
    ))

    assert session.webapp_launchers() == {
        "chrome-app.slack.com__client-Default": "https://app.slack.com/client",
    }


def test_webapp_launchers_skips_launchers_that_are_not_web_apps(session, tmp_path, monkeypatch):
    monkeypatch.setattr(session, "DESKTOP_DIRS", [str(tmp_path)])
    write_desktop(tmp_path, "editor.desktop", "[Desktop Entry]\nExec=nvim %F\n")
    write_desktop(tmp_path, "browser.desktop", "[Desktop Entry]\nExec=omarchy-launch-browser\n")

    assert session.webapp_launchers() == {}


def test_webapp_launchers_ignores_a_file_it_cannot_parse(session, tmp_path, monkeypatch):
    """A malformed Exec must not take the whole snapshot down with it."""
    monkeypatch.setattr(session, "DESKTOP_DIRS", [str(tmp_path)])
    write_desktop(tmp_path, "broken.desktop",
                  '[Desktop Entry]\nExec=omarchy-launch-webapp "https://example.com\n')
    write_desktop(tmp_path, "good.desktop",
                  "[Desktop Entry]\nExec=omarchy-launch-webapp https://ok.example/x\n")

    assert session.webapp_launchers() == {
        "chrome-ok.example__x-Default": "https://ok.example/x",
    }


def test_webapp_launchers_ignores_a_missing_directory(session, tmp_path, monkeypatch):
    monkeypatch.setattr(session, "DESKTOP_DIRS", [str(tmp_path / "nope"), str(tmp_path)])
    write_desktop(tmp_path, "a.desktop", "[Desktop Entry]\nExec=omarchy-launch-webapp https://a.io\n")

    assert session.webapp_launchers() == {"chrome-a.io__-Default": "https://a.io"}


def test_webapp_launchers_dedupes_two_launchers_for_one_url(session, tmp_path, monkeypatch):
    """Two launchers for one URL is a user's duplicate, not two different apps."""
    monkeypatch.setattr(session, "DESKTOP_DIRS", [str(tmp_path)])
    write_desktop(tmp_path, "a-first.desktop",
                  "[Desktop Entry]\nExec=omarchy-launch-webapp https://example.com/x\n")
    write_desktop(tmp_path, "b-second.desktop",
                  "[Desktop Entry]\nExec=omarchy-launch-webapp https://example.com/x\n")

    assert session.webapp_launchers() == {
        "chrome-example.com__x-Default": "https://example.com/x",
    }


# --- relaunch commands -------------------------------------------------------

def test_normalize_collapses_a_web_app_to_the_omarchy_launcher(session):
    argv = [
        "/usr/lib/chromium/chromium", "--ozone-platform=wayland",
        "--app=https://app.slack.com/client", "--user-data-dir=/home/u/.config/chromium",
    ]
    assert session.normalize(argv) == ["omarchy-launch-webapp", "https://app.slack.com/client"]


def test_normalize_finds_the_app_flag_in_a_rewritten_cmdline(session):
    """Chromium rewrites argv into one space-joined blob for its process title."""
    blob = ["/usr/lib/chromium/chromium --type=renderer --app=https://example.com/x --foo"]
    assert session.normalize(blob) == ["omarchy-launch-webapp", "https://example.com/x"]


def test_normalize_strips_quotes_from_the_app_url(session):
    assert session.normalize(['chromium --app="https://example.com/x"']) == \
        ["omarchy-launch-webapp", "https://example.com/x"]


def test_normalize_splits_a_single_token_blob(session):
    assert session.normalize(["alacritty --title 'my term'"]) == \
        ["alacritty", "--title", "my term"]


def test_normalize_leaves_an_ordinary_argv_alone(session):
    argv = ["nvim", "--cmd", "set number", "/tmp/a b.txt"]
    assert session.normalize(argv) == argv


# --- terminal working directories --------------------------------------------

def test_strip_cwd_flags_drops_a_flag_and_its_value(session):
    assert session.strip_cwd_flags(
        ["alacritty", "--working-directory", "/home/u/src", "-e", "nvim"]) == \
        ["alacritty", "-e", "nvim"]


def test_strip_cwd_flags_drops_the_equals_spelling(session):
    assert session.strip_cwd_flags(["kitty", "--directory=/home/u/src", "top"]) == \
        ["kitty", "top"]


def test_strip_cwd_flags_drops_the_short_spelling(session):
    assert session.strip_cwd_flags(["kitty", "-d", "/home/u/src"]) == ["kitty"]


def test_strip_cwd_flags_keeps_everything_else(session):
    argv = ["ghostty", "--title=work", "-e", "btop"]
    assert session.strip_cwd_flags(argv) == argv


def test_strip_cwd_flags_survives_a_trailing_flag_with_no_value(session):
    assert session.strip_cwd_flags(["foot", "--working-dir"]) == ["foot"]


# --- routing a window to a relaunch strategy ----------------------------------

def test_resolve_keys_a_web_app_on_its_class_not_its_pid(session):
    """Every Chromium window shares one pid, so the pid identifies the wrong app."""
    client = {"class": "chrome-app.slack.com__client-Default", "pid": 4242}
    key, command = session.resolve(client, {})
    assert key == "class:chrome-app.slack.com__client-Default"
    assert command == ["omarchy-launch-webapp", "https://app.slack.com/client"]


def test_resolve_uses_the_launcher_url_for_a_web_app(session):
    cls = "chrome-example.com__my_app-Default"
    key, command = session.resolve({"class": cls, "pid": 1},
                                   {cls: "https://example.com/my_app"})
    assert command == ["omarchy-launch-webapp", "https://example.com/my_app"]


def test_resolve_relaunches_a_browser_once_by_class(session):
    key, command = session.resolve({"class": "Brave-browser", "pid": 99}, {})
    assert key == "class:Brave-browser"
    assert command == ["omarchy-launch-browser"]


def test_resolve_reads_the_cmdline_for_an_ordinary_window(session, monkeypatch):
    monkeypatch.setattr(session, "cmdline_for", lambda pid: ["nvim", "/tmp/x"])
    assert session.resolve({"class": "nvim", "pid": 7}, {}) == ("pid:7", ["nvim", "/tmp/x"])


def test_resolve_falls_back_to_the_initial_class(session, monkeypatch):
    monkeypatch.setattr(session, "cmdline_for", lambda pid: ["chromium"])
    key, _ = session.resolve({"initialClass": "chromium", "pid": 7}, {})
    assert key == "class:chromium"


def test_resolve_skips_a_window_with_no_pid(session):
    assert session.resolve({"class": "weird", "pid": 0}, {}) is None


def test_resolve_skips_a_window_whose_process_is_gone(session, monkeypatch):
    monkeypatch.setattr(session, "cmdline_for", lambda pid: None)
    assert session.resolve({"class": "nvim", "pid": 7}, {}) is None


# --- what counts as a change --------------------------------------------------

def entry(**overrides):
    base = {
        "class": "alacritty", "cwd": "/home/u", "title": "term", "workspace": "2",
        "workspace_id": 2, "floating": False, "at": [10, 20], "size": [800, 600],
        "command": ["alacritty"],
    }
    return {**base, **overrides}


def test_layout_signature_ignores_geometry(session):
    """Retiling moves windows constantly; that is not an event worth logging."""
    assert session.layout_signature([entry()]) == \
        session.layout_signature([entry(at=[500, 500], size=[1, 1], title="other")])


def test_layout_signature_notices_a_workspace_change(session):
    assert session.layout_signature([entry()]) != \
        session.layout_signature([entry(workspace="5")])


def test_layout_signature_notices_a_new_working_directory(session):
    assert session.layout_signature([entry()]) != \
        session.layout_signature([entry(cwd="/home/u/src")])


def test_layout_signature_notices_a_window_appearing(session):
    assert session.layout_signature([entry()]) != \
        session.layout_signature([entry(), entry(**{"class": "nvim"})])


def test_layout_signature_notices_a_changed_relaunch_command(session):
    assert session.layout_signature([entry()]) != \
        session.layout_signature([entry(command=["alacritty", "-e", "btop"])])


# --- skip rules ---------------------------------------------------------------

def test_skip_classes_always_covers_the_desktop_itself(session, tmp_path, monkeypatch):
    monkeypatch.setattr(session, "SKIP_FILE", str(tmp_path / "absent.txt"))
    classes = session.skip_classes()
    assert {"omarchy-shell", "hyprlock", "walker"} <= classes


def test_skip_classes_reads_the_user_file(session, tmp_path, monkeypatch):
    skip_file = tmp_path / "session-skip.txt"
    skip_file.write_text(
        "# a comment\n"
        "\n"
        "Spotify\n"
        "   signal   # trailing comment\n"
    )
    monkeypatch.setattr(session, "SKIP_FILE", str(skip_file))

    classes = session.skip_classes()
    assert "Spotify" in classes
    assert "signal" in classes
    assert "# a comment" not in classes


# --- how a workspace is recorded ----------------------------------------------

def test_workspace_target_uses_the_number_for_a_normal_workspace(session):
    assert session.workspace_target({"id": 3, "name": "3"}) == "3"


def test_workspace_target_uses_the_name_for_a_special_workspace(session):
    """Special workspaces have negative, unstable ids, so they go by name.

    This is what makes Omarchy's Meta+S scratchpad survive a restore.
    """
    assert session.workspace_target({"id": -98, "name": "special:scratchpad"}) == \
        "special:scratchpad"


def test_workspace_target_handles_an_unnamed_special_workspace(session):
    assert session.workspace_target({"id": -99, "name": "special"}) == "special:special"


def test_workspace_target_skips_a_window_with_no_workspace(session):
    assert session.workspace_target({}) is None


# --- matching a mapped window to the entry that asked for it ------------------

def pending_entry(cls, workspace):
    return {"class": cls, "workspace": workspace, "command": [cls]}


def test_match_entry_picks_the_only_candidate(session):
    pending = [pending_entry("foot", "3")]
    assert session.match_entry(pending, "foot", "3") is pending[0]


def test_match_entry_ignores_other_classes(session):
    pending = [pending_entry("chromium", "1"), pending_entry("foot", "3")]
    assert session.match_entry(pending, "foot", "3") is pending[1]


def test_match_entry_returns_none_for_a_window_we_did_not_ask_for(session):
    assert session.match_entry([pending_entry("foot", "3")], "spotify", "2") is None


def test_match_entry_prefers_the_entry_whose_workspace_the_window_reached(session):
    """Two terminals, one in the scratchpad: the exec rule usually landed each
    one correctly, so believe it rather than claiming entries in launch order."""
    scratch = pending_entry("foot", "special:scratchpad")
    normal = pending_entry("foot", "3")
    pending = [scratch, normal]
    assert session.match_entry(pending, "foot", "3") is normal
    assert session.match_entry(pending, "foot", "special:scratchpad") is scratch


def test_match_entry_falls_back_to_launch_order_when_the_window_landed_wrong(session):
    """A window that ignored its rule matches the oldest pending entry, which is
    the earliest launched -- the behaviour this had before the tiebreak."""
    first = pending_entry("foot", "3")
    second = pending_entry("foot", "4")
    assert session.match_entry([first, second], "foot", "9") is first
