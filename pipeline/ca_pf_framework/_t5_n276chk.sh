#!/bin/bash
# _t5_n276chk.sh --- ★★★★★ 确认 nv=276 的构造是否通过（N8 自洽 / 约束 / 进度）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
L=_w2_t5_n276.log
echo '════ ① 是否活着 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5N276' | cut -c1-64 | sed 's/^/  /'
echo -n '  进程数 = '; ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5N276'
echo
echo '════ ② 构造关键行（约束 / N8 / 根数 / 是否有❌）════'
grep -nE '总根数|导出板条数|B_max|几何上界|不自洽|❌|✗|Traceback|约束|nvar|m *= *23|nv *= *276' "$L" 2>/dev/null \
  | head -14 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ③ 日志末尾 8 行（看跑到哪了）════'
tail -8 "$L" 2>/dev/null | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ④ 末步 / 快照 / 检查点 ════'
printf '  末步 = %s   快照数 = %s   ckpt 数 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/snap_*.npz 2>/dev/null | wc -l)" \
  "$(ls -1 _exp/_bk_t5/dry_t5N276/ckpt/*.npz 2>/dev/null | wc -l)"
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
