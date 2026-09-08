#!/usr/bin/env bash
#
# Print the CHANGELOG.md section for one version, so the release notes on
# GitHub are the notes that were written by hand rather than a list of commit
# subjects. Exits non-zero when there is no section for that version, which the
# release workflow treats as "fall back to generated notes".
#
#     .github/scripts/changelog-section.sh 0.1.0

set -uo pipefail

version="${1:?usage: changelog-section.sh <version>}"
changelog="${2:-CHANGELOG.md}"

[[ -f $changelog ]] || exit 1

section=$(awk -v want="$version" '
  # Section heads look like: ## [0.1.0] - 2026-09-08
  /^## / {
    inside = ($0 ~ "^## \\[" want "\\]")
    next
  }
  # The link-reference block at the foot of the file belongs to no section.
  /^\[[^]]+\]: / { inside = 0 }
  inside { print }
' "$changelog")

# Trim leading and trailing blank lines.
section=$(printf '%s\n' "$section" | sed -e '/./,$!d' | tac | sed -e '/./,$!d' | tac)

[[ -n $section ]] || exit 1
printf '%s\n' "$section"
