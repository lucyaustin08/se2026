#!/usr/bin/env bash
# Run a CI command. If it fails, publish its last lines as a GitHub error annotation
# so the failure is readable from the pull request's checks, not only the raw log.
# Usage: annotate.sh "<step title>" <command> [args...]
set -uo pipefail

title="$1"
shift
log="$(mktemp)"

"$@" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}

if [ "$status" -ne 0 ]; then
  # Annotation messages are single-line; GitHub decodes %0A back into newlines.
  message="$(tail -n 40 "$log" | sed -e 's/%/%25/g' -e 's/\r//g' | sed -e ':a;N;$!ba;s/\n/%0A/g')"
  echo "::error title=${title}::${message}"
fi
exit "$status"
