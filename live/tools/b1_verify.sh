#!/bin/sh
set -eu

# One bounded, network-free verification entrypoint for the B1 candidate.
# Select the project runtime before any suite starts so a missing dependency is
# a preflight refusal, never a surprise halfway through verification.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
PYTHON_BIN=${B1_TEST_PYTHON:-python3}
export PYTHONDONTWRITEBYTECODE=1

cd "$ROOT"

"$PYTHON_BIN" -c 'import flask, flask_socketio, requests' 2>/dev/null || {
    printf '%s\n' \
        'B1_VERIFY_REFUSED=selected Python lacks flask, flask_socketio, or requests' >&2
    printf '%s\n' \
        'Set B1_TEST_PYTHON to the existing project test environment.' >&2
    exit 69
}
printf 'B1_TEST_RUNTIME=%s\n' "$PYTHON_BIN"
sh -n live/tools/ontinuity_https.sh
"$PYTHON_BIN" - <<'PY'
from pathlib import Path

for name in (
    "app.py", "capability_auth.py", "live/control_loop.py",
    "live/bootstrap/gate.py", "live/box/box_ops.py",
    "live/box/file_server.py", "live/box/seat_mailbox.py",
    "live/box/trusted_deploy.py", "live/shepherd_alert.py",
    "live/experiment/burnin_resident.py",
):
    path = Path(name)
    compile(path.read_bytes(), str(path), "exec")
PY

for module in \
    tests.test_trusted_deploy \
    tests.test_capability_admission \
    tests.test_b1_bootstrap_gate \
    tests.test_b1_burnin_restart \
    tests.test_release_baseline \
    tests.test_b1_release_boundaries \
    tests.test_capability_admission_surface \
    tests.test_capability_box_identity \
    tests.test_capability_courier \
    tests.test_research_preservation \
    tests.test_ontinuity_https_client
do
    "$PYTHON_BIN" -W error -m unittest "$module" -v
done

"$PYTHON_BIN" -m json.tool live/B1_INSTALL_MANIFEST.json >/dev/null
"$PYTHON_BIN" -m json.tool live/B1_TRANSPORT_LOCK_MANIFEST.json >/dev/null
git diff --check
printf '%s\n' 'B1_VERIFY=PASS'
