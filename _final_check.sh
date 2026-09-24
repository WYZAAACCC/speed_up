#!/bin/bash
echo "=== CA 回归（后台那两个）:"
tail -2 /tmp/r_solute.log 2>/dev/null || echo "  solute 日志无"
tail -3 /tmp/r_wc.log 2>/dev/null || echo "  wc_cet 日志无（可能仍在跑）"
ps -eo etime,args | grep -E '[_]verify_ca3d_wc' | head -1
echo; echo "=== 今晚新增/改动的文件:"
cd /mnt/f/speed_up
ls -lat pipeline/ca_pf_framework/*.py pipeline/ca_pf_framework/*.md bench/exaca/*.md 2>/dev/null | head -14