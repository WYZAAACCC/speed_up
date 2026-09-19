#!/bin/bash
# runner：在 WSL 内执行，避免 Git Bash 的路径转换把 /root/... 变成 Files/Git/root/...
HERE="/mnt/f/speed_up/pipeline/validated"
export ROOT="${ROOT:-/root/work/kc_keff}"
export NX="${NX:-160}"
export T_END="${T_END:-8e-3}"
export TMO="${TMO:-900}"
export KC_LIST="${KC_LIST:-1e-15 1e-14 1e-13 1e-12 1.125e-11}"
bash "$HERE/run_kc_vs_keff.sh"
