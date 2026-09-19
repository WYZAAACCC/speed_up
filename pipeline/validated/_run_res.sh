#!/bin/bash
# runner for run_kc_fix_res.sh（避免 Git Bash 路径转换）
HERE="/mnt/f/speed_up/pipeline/validated"
export ROOT="${ROOT:-/root/work/kc_fix}"
export T_END="${T_END:-1.5e-2}"
export TMO="${TMO:-900}"
export KC_FIX="${KC_FIX:-1e-14}"
export S_LIST="${S_LIST:-0.5 1 2 4}"
export NW_LIST="${NW_LIST:-40 160}"
bash "$HERE/run_kc_fix_res.sh"
