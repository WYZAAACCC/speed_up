#!/bin/bash
# _t5_readext.sh --- ★★★★★ 读**速度扩展**（`adv.extend`）—— 判它能否在远处改动 φ
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
git add pipeline/ca_pf_framework/_t5_bandself.py pipeline/ca_pf_framework/_t5_f3test.py \
        pipeline/ca_pf_framework/_t5_compchk.sh pipeline/ca_pf_framework/_t5_tuse.sh \
        pipeline/ca_pf_framework/_t5_read_seed.sh pipeline/ca_pf_framework/_t5_read_seednext.sh \
        pipeline/ca_pf_framework/_t5_git_s263.sh pipeline/ca_pf_framework/_t5_1to1.sh 2>/dev/null
git commit -m 'R581-T5R-s264 量具自查通过（多场重叠 0.03%）+ 六条候选否证记录 + 读码工具落盘' 2>&1 | tail -1
echo
echo '════ ① `extend` 的定义与调用点 ════'
grep -nE 'def extend|\.extend\(|adv\.extend|extend_mode|_emode' windowB_surface.py 2>/dev/null | head -14 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ② 若找到 `def extend`，打印其函数体（前 70 行）════'
L=$(grep -n 'def extend' windowB_surface.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  echo "  （第 $L 行起）"
  sed -n "${L},$((L+70))p" windowB_surface.py | nl -ba -v"$L" | cut -c1-150
else
  echo '  ⚠ 没找到 `def extend`'
fi
