#!/usr/bin/env bash
set -euo pipefail

# One-command demo: provision subscriber profiles, attach the selected virtual
# UE, and drive the kpm-load-watch state machine with bounded traffic.

PROFILE="${1:-ue2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/provision-ue-lab-profiles.sh"
"${SCRIPT_DIR}/select-ue-lab-profile.sh" "${PROFILE}"
"${SCRIPT_DIR}/refresh-kpm-xapps.sh"
"${SCRIPT_DIR}/demo-load-watch.sh"

echo "UE_LAB_DEMO_OK profile=${PROFILE}"
