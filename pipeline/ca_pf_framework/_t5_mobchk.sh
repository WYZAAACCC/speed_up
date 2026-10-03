#!/bin/bash
# _t5_mobchk.sh --- ★★★★★ 先验：`--mob-iform ellipse` 到底有没有进到引擎
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 两臂的**实际命令行**（ps 里看有没有 --mob-iform）════'
ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -oE 'dry_t5[A-Za-z0-9_]+|--mob-iform [a-z]+|--mob-ratio [0-9.]+|--eng-elong [0-9.]+' \
  | paste - - - - 2>/dev/null | sed 's/^/  /'
echo '  ── 若上面没列出 --mob-iform ⇒ 参数没传进去 ──'
echo
echo '════ ② 直接查进程的完整参数（只取 t5AM_*）════'
for P in $(ps -eo pid,args --no-headers | grep '[_]bk_exp.py' | grep 't5AM' | awk '{print $1}'); do
  printf '  pid=%s\n' "$P"
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | tr ' ' '\n' | grep -A1 -E '^--(mob-iform|mob-ratio|eng-elong|tag)$' | paste - - | sed 's/^/     /'
done
echo
echo '════ ③ 启动器是否支持这些参数（直接问它）════'
/root/miniconda3/envs/ml/bin/python _t5_short.py --help 2>&1 | grep -E 'mob-iform|mob-ratio|mob-wulff|mob-dip' | sed 's/^/  /'
echo
echo '════ ④ 两臂日志里有没有**报错**（未知参数会立刻退出）════'
for t in t5AM_ell t5AM_combo; do
  echo "  ── $t ──"
  tail -3 _w2_t5_am_$t.log 2>/dev/null | cut -c1-140 | sed 's/^/     /'
done
