#!/bin/bash
# _t5_readsc.sh --- ★★★★★ 找 `supercrit` 的 CLI 开关名与**覆盖范围**（含不含 attach/stack）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `supercrit` 的全部出现处 ════'
grep -nE 'supercrit|nuc_supercrit' windowB_surface.py _bk_exp.py 2>/dev/null | head -22 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② CLI 参数定义 ════'
grep -nE "add_argument\('--nuc-supercrit" _bk_exp.py | cut -c1-175 | sed 's/^/  /'
echo
echo '════ ③ `_supercrit_probe` 的定义 ════'
L=$(grep -n 'def _supercrit_probe' windowB_surface.py | head -1 | cut -d: -f1)
echo "  （第 $L 行起）"
[ -n "$L" ] && sed -n "${L},$((L+10))p" windowB_surface.py | nl -ba -v"$L" | cut -c1-158
echo
echo '════ ④ ★ 关键：`supercrit` 判据在**哪条通道**里生效（看缩进与所在分支）════'
for LN in $(grep -n "c.get('supercrit'" windowB_surface.py | cut -d: -f1); do
  echo "  ── 第 $LN 行所在的函数与分支（向上找最近的 def 与通道关键字）──"
  awk -v n="$LN" 'NR<=n && /^    def /{f=$0; fl=NR} NR<=n && /# ====.*通道|attach|stack|fresh/{if($0 ~ /attach|stack|fresh/) {k=$0; kl=NR}} END{}' windowB_surface.py >/dev/null
  sed -n "1,${LN}p" windowB_surface.py | grep -nE '^    def |attach|stack|fresh' | tail -4 | cut -c1-140 | sed 's/^/     /'
done
