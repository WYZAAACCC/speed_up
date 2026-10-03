#!/bin/bash
# _t5_verify_fix.sh --- 核实磁盘上的文件语法 + 展示改动 diff + 提交
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 磁盘文件语法检查（**看文件本身，不是内存字符串**）════'
$PY -m py_compile windowB_surface.py && echo '  ✅ py_compile 通过' || { echo '  ❌ 语法错误 ⇒ 回滚'; cp windowB_surface.py.bak_stackfield windowB_surface.py; exit 1; }
echo
echo '════ ② 实际改了什么（diff，只看关键行）════'
diff windowB_surface.py.bak_stackfield windowB_surface.py | grep -E '^[<>]' | grep -vE '^\s*[<>]\s*#' | cut -c1-130 | sed 's/^/  /'
echo
echo '════ ③ 改后那一段的真实缩进（cat -A 看空格）════'
grep -n "self.seed_plate(k_new, cc, nrm, R, t," windowB_surface.py | head -1 | cut -d: -f1 | while read -r L; do
  sed -n "${L},$((L+6))p" windowB_surface.py | cat -A | sed 's/\$$//' | cut -c1-120 | sed 's/^/  /'
done
echo
echo '════ ④ 三处通道的一致性复核 ════'
printf '  fresh : %s 处用新场\n' "$(grep -c "out.append((kk, 'fresh'))" windowB_surface.py)"
printf '  attach: %s 处用新场 k_new\n' "$(grep -c "out.append((k_new, 'attach'))" windowB_surface.py)"
printf '  stack : %s 处用新场 k_new  ← **本次修的**\n' "$(grep -c "out.append((k_new, 'stack'))" windowB_surface.py)"
