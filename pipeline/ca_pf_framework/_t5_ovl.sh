#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== nuc_overlap / overlap_nm 的全部出现处 ==="
grep -n 'nuc_overlap\|overlap_nm\|overlap' _bk_exp.py windowB_surface.py _t5_short.py 2>/dev/null | grep -v '^.*#' | head -30 | cut -c1-175
echo
echo "=== 引擎里的硬芯判据 ==="
grep -n 'overlap' windowB_surface.py | head -20 | cut -c1-175
