#!/usr/bin/env bash
#
# Validate this plugin against the manifest schema the Omarchy shell enforces.
#
# A deliberate mirror of `omarchy-plugin-validate` (which in turn mirrors
# shell/services/PluginRegistry.qml), because CI has no Omarchy to run: the
# runner is a plain Ubuntu box. The point is that a manifest which would be
# rejected at install time is rejected here first, on the branch users pull
# from, rather than by every user in turn.
#
# Run it locally the same way CI does:
#     .github/scripts/validate-manifest.sh .
# If you have Omarchy to hand, `omarchy plugin validate .` is the real thing
# and is always the last word.

set -uo pipefail

PLUGIN_DIR="${1:-.}"
MANIFEST="$PLUGIN_DIR/manifest.json"

fail() {
  echo "::error file=manifest.json::$*"
  exit 1
}

ok() {
  echo "  ok  $*"
}

[[ -d $PLUGIN_DIR ]] || fail "plugin folder not found: $PLUGIN_DIR"
[[ -f $MANIFEST ]] || fail "missing manifest.json in $PLUGIN_DIR"
jq -e . "$MANIFEST" >/dev/null 2>&1 || fail "manifest.json is not valid JSON"
ok "manifest.json parses"

# Exactly the JSON number 1 — jq's == is type-aware, so the string "1" fails
# here just as `schemaVersion !== 1` fails in the registry.
jq -e '.schemaVersion == 1' "$MANIFEST" >/dev/null 2>&1 \
  || fail "unsupported or missing schemaVersion (expected the number 1)"
ok "schemaVersion is 1"

for field in id name version kinds entryPoints; do
  jq -e --arg f "$field" 'has($f)' "$MANIFEST" >/dev/null 2>&1 \
    || fail "manifest missing required field '$field'"
done
ok "required fields present"

ID=$(jq -r '.id // ""' "$MANIFEST")
[[ -n $ID ]] || fail "manifest 'id' is empty"
[[ $ID =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || fail "invalid plugin id '$ID'"
[[ $ID != *".."* ]] || fail "invalid plugin id '$ID'"
[[ $ID != omarchy.* ]] || fail "plugin id '$ID' uses the reserved omarchy.* namespace"
ok "id '$ID' is well formed"

# A version the release workflow can compare against a tag.
VERSION=$(jq -r '.version // ""' "$MANIFEST")
[[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || fail "version '$VERSION' is not MAJOR.MINOR.PATCH"
ok "version $VERSION is semver"

jq -e '(.kinds | type) == "array" and (.kinds | length) > 0' "$MANIFEST" >/dev/null 2>&1 \
  || fail "'kinds' must be a non-empty array"
jq -e '(.entryPoints | type) == "object"' "$MANIFEST" >/dev/null 2>&1 \
  || fail "'entryPoints' must be an object"

# Read each entry point as a JSON-encoded string, then decode it, so a value
# containing a newline stays one literal path instead of splitting into
# fragments that each pass the checks.
while IFS= read -r ep_json; do
  [[ -n $ep_json ]] || continue
  ep=$(jq -r '.' <<<"$ep_json")
  [[ -n $ep ]] || fail "entry point path is empty"
  [[ $ep != *$'\n'* ]] || fail "entry point may not contain a newline"
  [[ $ep != /* ]] || fail "entry point must be a relative path: '$ep'"
  [[ $ep != *".."* ]] || fail "entry point may not contain '..': '$ep'"
  [[ -f "$PLUGIN_DIR/$ep" ]] || fail "entry point file not found: '$ep'"
  ok "entry point '$ep' exists"
done < <(jq -c '.entryPoints | to_entries[] | .value' "$MANIFEST")

# Claiming a kind without its entry point installs and enables cleanly and then
# does nothing at all, which is the worst way for this to fail.
for kind_entry_point in \
  "bar:bar" \
  "bar-widget:barWidget" \
  "menu:menu" \
  "overlay:overlay" \
  "panel:panel" \
  "service:service"; do
  kind="${kind_entry_point%%:*}"
  entry_point="${kind_entry_point##*:}"
  jq -e --arg kind "$kind" '(.kinds | index($kind)) != null' "$MANIFEST" >/dev/null 2>&1 || continue
  jq -e --arg ep "$entry_point" '.entryPoints | has($ep)' "$MANIFEST" >/dev/null 2>&1 \
    || fail "kind '$kind' requires an 'entryPoints.$entry_point' to load"
  ok "kind '$kind' has its entry point"
done

# Symlinks could point a plugin back at arbitrary files once it lands in the
# trusted plugins directory, so the shell refuses the whole folder if it finds
# one. Catch that here rather than at install time.
link=$(find "$PLUGIN_DIR" -name .git -prune -o -type l -print -quit 2>/dev/null)
[[ -z $link ]] || fail "symlinks are not allowed inside a plugin folder: $link"
ok "no symlinks in the plugin folder"

echo "manifest.json is valid for schemaVersion 1"
