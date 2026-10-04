#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== probe 日志 ==="
cat _w2_t5_nvprobe160.log
echo
echo "=== nvp8 的 time -v ==="
grep -E 'Maximum resident|Elapsed' _w2_t5_time_nvp8.txt
echo
echo "=== nvp32 的 time -v（若已有）==="
[ -f _w2_t5_time_nvp32.txt ] && grep -E 'Maximum resident|Elapsed' _w2_t5_time_nvp32.txt || echo "  （还没写出）"
echo
echo "=== 当前内存 ==="
free -m | sed -n 2p
