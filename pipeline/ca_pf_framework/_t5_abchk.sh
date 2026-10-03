#!/bin/bash
# _t5_abchk.sh --- 查 A/B 是否真的起来了
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① A/B 相关进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '[_]t5_ab_elong|[_]bk_exp.py' \
  | sed 's/^/  /' | cut -c1-96
echo
echo '════ ② 四臂的日志是否已建 ════'
for t in A B C D; do
  f=_w2_t5_ab_t5AB_$t.log
  if [ -f "$f" ]; then
    printf '  %-42s %s 字节\n' "$f" "$(stat -c%s "$f")"
  else
    printf '  %-42s （未建）\n' "$f"
  fi
done
echo
echo '════ ③ 总日志 ════'
if [ -f _w2_t5_ab_elong.log ]; then tail -12 _w2_t5_ab_elong.log | sed 's/^/  /'
else echo '  （未建 ⇒ A/B 脚本没跑起来）'; fi
echo
echo '════ ④ 四臂目录 ════'
ls -1d _exp/_bk_t5/dry_t5AB_* 2>/dev/null | sed 's/^/  /' || echo '  （无）'
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
