#!/bin/bash
# _t5_edsign.sh --- ★★★★★★ 找 `ed`（弹性能项）的**带符号**数值
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 引擎日志里所有与 ed / 弹性能 有关的带符号输出 ════'
grep -nE 'sc_last_ed|ed_k|Δed *=|ed *=|弹性|E_el' _w2_t5_short_t5B4D.log 2>/dev/null | head -16 | cut -c1-200 | sed 's/^/  /'
echo
echo '════ ② 形核判据里 `ed` 的用法（`_bk_exp.py` 2620–2640）════'
sed -n '2618,2642p' _bk_exp.py | nl -ba -v2618 | cut -c1-155
echo
echo '════ ③ `ed` 的定义（`windowB_surface.py` 里 `ed =` 的赋值）════'
grep -nE '^\s+ed *=|self\.ed *=|ed_by_face' windowB_surface.py | head -12 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ④ `edk` / `edl` 的取法（`dG_cell` 前几行）════'
sed -n '4290,4320p' windowB_surface.py | grep -nE 'edk|edl|ed\[|karr|larr' | cut -c1-150 | sed 's/^/  /'
