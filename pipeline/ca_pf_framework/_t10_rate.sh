#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10N160.log
echo "size=$(stat -c%s "$L" 2>/dev/null) bytes"
echo "--- 【 N] 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | cut -c1-70
echo "--- 含 s/步 的行 ---"
grep -aoE '[0-9.]+s/步' "$L" 2>/dev/null | tail -5
echo "--- 异常扫描 ---"
grep -aiE 'error|traceback|exception|killed|MemoryError|OOM' "$L" 2>/dev/null | tail -6 | cut -c1-170
echo "--- 末 3 行 ---"
tail -3 "$L" 2>/dev/null | cut -c1-170
echo "--- 形核/事件计数 ---"
echo "  athermal 事件行 = $(grep -ac 'athermal' "$L" 2>/dev/null)"
echo "  s292 补投轮    = $(grep -ac 's292 补投轮' "$L" 2>/dev/null)"
echo "  s295 分诊      = $(grep -ac 's295 形核分诊' "$L" 2>/dev/null)"
echo "--- 进程 CPU 时间（判是否真在算）---"
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) ps -o pid,etime,time,pcpu,pmem --no-headers -p $P ;; esac
done
