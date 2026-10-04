#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
bash -n _t10_auto.sh && echo "语法 OK"
grep -n 'VmHWM=' _t10_auto.sh | cut -c1-175
# 重启守望（用修好的版本）
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *_t10_auto.sh*) kill -9 "$P" 2>/dev/null; echo "  重启守望，杀掉旧 pid=$P" ;; esac
done
sleep 2
rm -f _w2_t10_seven.done
setsid nohup bash _t10_auto.sh 21600 > /dev/null 2>&1 < /dev/null &
sleep 18
echo "--- 新守望日志 ---"
tail -3 _w2_t10_auto.log
echo "--- 运行中的盯守 ---"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_t10_|bk_exp' | grep -v grep | cut -c1-105
