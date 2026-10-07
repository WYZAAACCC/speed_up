#!/bin/bash
# _t5_tuse.sh --- 追 `_t_use`（attach/stack 传给 seed_plate 的厚度；横幅说"含自动补厚"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `_t_use` 的全部出现处 ════'
grep -n '_t_use' windowB_surface.py | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `_t_use` 的定义处上下文 ════'
L=$(grep -n '_t_use *=' windowB_surface.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L - 16)); E=$((L + 12))
  echo "  （第 ${S}–${E} 行）"
  sed -n "${S},${E}p" windowB_surface.py | nl -ba -v"$S" | cut -c1-155
fi
echo
echo '════ ③ `t` 在 attach/stack 分支里怎么算的（找 `t =` 与 `t=`）════'
grep -nE '^\s+t = |^\s+_t = |overlap.*t|t.*overlap' windowB_surface.py | head -14 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ④ 引擎传给 nucleate 的 t_nuc / 自动补厚（横幅那句的出处）════'
grep -nE '含自动补厚|自动补厚' _bk_exp.py windowB_surface.py 2>/dev/null | cut -c1-170 | sed 's/^/  /'
