#!/bin/bash
# _t5_amkill.sh --- ★★★★★ 两臂被**硬杀**的原因（OOM？段错误？看门狗？）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① dmesg 里的 OOM / segfault 记录 ════'
dmesg 2>/dev/null | tail -40 | grep -iE 'oom|killed process|segfault|python' | tail -12 | sed 's/^/  /' \
  || echo '  （dmesg 不可读或无记录）'
echo
echo '════ ② 内核日志（另一路径）════'
if [ -r /var/log/kern.log ]; then tail -30 /var/log/kern.log | grep -iE 'oom|killed' | tail -6 | sed 's/^/  /'
else echo '  （无 kern.log）'; fi
echo
echo '════ ③ 当前内存与 swap（看是不是被 OOM 杀的）════'
free -m | sed 's/^/  /'
echo
echo '════ ④ 两臂日志里**有没有**退出摘要块（有=正常退出，无=被硬杀）════'
for t in t5AM_ell t5AM_combo; do
  L=_w2_t5_short_$t.log
  echo -n "  $t  exit= 出现次数: "; grep -c 'exit=' "$L" 2>/dev/null
  echo -n "         末尾是否有 '====' 摘要: "; tail -20 "$L" 2>/dev/null | grep -c '====='
done
echo
echo '════ ⑤ 启动器里看门狗的逻辑（会不会杀）════'
grep -n "mem-limit-gb\|mem_limit\|VmHWM\|看门狗" _t5_short.py 2>/dev/null | head -8 | cut -c1-140 | sed 's/^/  /'
