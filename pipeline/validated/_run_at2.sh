#!/bin/bash
# runner for run_antitrap2.sh
HERE="/mnt/f/speed_up/pipeline/validated"
export ROOT="${ROOT:-/root/work/at2b}"
export NX="${NX:-160}"
export T_END="${T_END:-1.5e-2}"
export TMO="${TMO:-900}"
export KC_FIX="${KC_FIX:-1e-14}"
export S_LIST="${S_LIST:-0.5 4}"
export ALPHA_LIST="${ALPHA_LIST:-0 1.5 2 2.5 3}"
bash "$HERE/run_antitrap2.sh"
