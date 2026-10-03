#!/bin/bash
# _t5_argdiff.sh --- ★★★★★ 逐字对比 t5N276 与 t5NR 的命令行（验证"只差 --var-rule"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for T in t5N276 t5NR; do
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $T" | awk '{print $1}' | head -1)
  if [ -z "$P" ]; then echo "════ $T：（无进程）════"; continue; fi
  echo "════ $T (pid=$P) ════"
  tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | sed 's/^/  /'
  echo
done
echo '════ ★ 逐项差分（归一化后比较）════'
for T in t5N276 t5NR; do
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $T" | awk '{print $1}' | head -1)
  [ -z "$P" ] && continue
  tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | grep '^--' | sort > /tmp/_a_$T.txt
done
if [ -f /tmp/_a_t5N276.txt ] && [ -f /tmp/_a_t5NR.txt ]; then
  diff /tmp/_a_t5N276.txt /tmp/_a_t5NR.txt | sed 's/^/  /'
  echo '  ⇒ 若上面**只有** var-rule 一行 ⇒ 两算例确实只差这一项'
fi
echo
echo '════ 内存 ════'
free -m | sed -n 2p | sed 's/^/  /'
