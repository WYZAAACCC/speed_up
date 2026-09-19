#!/bin/bash
# runner for run_prod_1d.sh
HERE="/mnt/f/speed_up/pipeline/validated"
export ROOT="${ROOT:-/root/work/prod1d}"
export NX="${NX:-160}"
export T_END="${T_END:-5.0e-5}"
export TMO="${TMO:-900}"
export KC_FIX="${KC_FIX:-1e-14}"
export V_LIST="${V_LIST:-0.6}"
bash "$HERE/run_prod_1d.sh"
