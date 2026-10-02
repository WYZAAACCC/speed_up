#!/bin/bash
# _t5_meter_where.sh --- 判据④/⑥ 的量具（f_var/r_selfac/blk_*）为什么在 abA 里是空的
cd "$(dirname "$0")" || exit 1
echo '════ ① 这些列名在代码里出现在哪 ════'
for c in f_var r_selfac nblk_sig blk_laths blk_vars n_var_sig n_habit \
         blk_span_nm blk_alen_nm blk_prof; do
  echo "  ── $c ──"
  grep -n "'$c'\|\"$c\"" _bk_exp.py windowB_surface.py windowB_lath.py 2>/dev/null \
    | head -4 | cut -c1-124 | sed 's/^/     /'
done
echo
echo '════ ② 它们被写进 row 的地方（含门控条件）════'
grep -n "row\['f_var'\]\|row\['r_selfac'\]\|row\['nblk_sig'\]\|row\['blk_" _bk_exp.py 2>/dev/null \
  | head -14 | cut -c1-130 | sed 's/^/  /'
echo
echo '════ ③ 上游函数在哪（谁算的）════'
grep -n 'def .*selfac\|def .*blk\|def .*var_sig\|def .*habit' _bk_exp.py windowB_surface.py windowB_lath.py 2>/dev/null \
  | head -14 | cut -c1-124 | sed 's/^/  /'
