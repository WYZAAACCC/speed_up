#!/bin/bash
# _r581_L4ab.sh --- L4（`--bbox-mode`）的真实路径 gate 4 包装
set -u
cd "$(dirname "$0")" || exit 1
exec bash _r581_ab2.sh L4 l4a_noop "--norm-smooth 0" l4b_axis "--bbox-mode axis"
