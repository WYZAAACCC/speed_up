#!/bin/bash
# _t5_dxflag.sh --- 找 `_t5_short.py` 的网格/盒子参数名（`--dx-nm` 不被接受）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `_t5_short.py` 里所有 argparse 参数名 ════'
grep -oE "add_argument\('--[a-z0-9-]+'" _t5_short.py | sed "s/add_argument('//; s/'//" | tr '\n' ' ' | fold -w 110 | sed 's/^/  /'
echo
echo '════ ② 含 dx / 网格 / 盒 的行 ════'
grep -nE "dx|mesh|box|L_box|--N" _t5_short.py | grep -vE '^\s*#' | head -14 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ③ 引擎侧有没有 `--dx-nm`（若无 ⇒ 分辨率由 N 与 L 决定）════'
grep -nE "add_argument\('--dx" _bk_exp.py | cut -c1-160 | sed 's/^/  /'
echo '  （空 ⇒ 引擎也没有该参数）'
echo
echo '════ ④ 结论提示 ════'
echo '  ★ 若只有 `--N`（而盒子尺寸 `L` 是固定物理值）⇒ 改 `--N` 就等价于改 `dx = L/N`。'
echo '  ★ 本仓 `--dx-nm 62.5` 是**我先前在别的脚本里用的写法** ⇒ 此处不适用。'
