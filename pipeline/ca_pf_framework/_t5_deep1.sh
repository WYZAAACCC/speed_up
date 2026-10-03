#!/bin/bash
# _t5_deep1.sh --- ★★★★★ 深度彻查①：nfsv 接线 · n_target/burst 节奏 · hardened 条件
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════════ A. `_bk_exp.py` 里 `nfsv` 传的是什么 ════════'
grep -n "nfsv" _bk_exp.py 2>/dev/null | cut -c1-170 | sed 's/^/  /'
echo
echo '════════ B. `n_target` 是怎么算的（burst 节奏的源头）════════'
grep -n "n_target" _bk_exp.py windowB_surface.py 2>/dev/null | cut -c1-170 | sed 's/^/  /'
echo
echo '════════ C. `cap` / `nuc_max_per_step` / cadence（每档放几个核）════════'
grep -nE "max_per_step|nuc_every|nuc_cadence|eng_cadence|cap *=|cap=" _bk_exp.py 2>/dev/null | head -22 | cut -c1-165 | sed 's/^/  /'
echo
echo '════════ D. `hardened` 是什么（决定 nfsv 是否生效）════════'
grep -n "hardened" windowB_surface.py _bk_exp.py 2>/dev/null | head -14 | cut -c1-170 | sed 's/^/  /'
