#!/bin/bash
# _r581_L6ab.sh --- L6（`--ufv-c`）的真实路径 gate 4 包装
set -u
cd "$(dirname "$0")" || exit 1
exec bash _r581_ab2.sh L6 l6a_noop "--norm-smooth 0" l6b_c "--ufv-c 1"
