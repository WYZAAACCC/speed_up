#!/bin/bash
# _t5_vfy_s160.sh --- 验证 `_t5_fill.py` 的修（**三个快照，覆盖三种情形**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 语法 ════'
$PY -m py_compile _t5_fill.py && echo '  ✅ SYNTAX_OK'
echo
echo '════ ② 判据：不再出现硬编码编号 ════'
grep -c 'ANOM' _t5_fill.py | sed 's/^/  含 ANOM 的次数 = /'
grep -c 'THR_EXT' _t5_fill.py | sed 's/^/  含 THR_EXT 的次数 = /'
echo
echo '════ ③ t5V2 @ step 400（应报"没有带延伸的场"，不再有假阳性）════'
taskset -c 16-19 $PY _t5_fill.py _exp/_bk_t5/dry_t5V2/snap_00400.npz 62.5 2>&1 | tail -4
echo
echo '════ ④ t5H3 @ step 1000（应有 8 个带延伸，且结论与 §148 一致）════'
taskset -c 16-19 $PY _t5_fill.py _exp/_bk_t5/dry_t5H3/snap_01000.npz 62.5 2>&1 | tail -8
