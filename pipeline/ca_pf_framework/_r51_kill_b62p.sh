#!/bin/bash
# R51: 杀掉方案 B′ 冒烟（引擎精确判据：t=0 两块接触面 = 963）并列出**同惯习面**的变体对。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for P in $(pgrep -f -- '--tag b62p' 2>/dev/null); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P"; kill -9 "$P" ;;
  esac
done
sleep 2
echo "--- 残留"; ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-52
echo
echo "=== 自协调结构表（同惯习面的变体分组）"
ls -la _r30_selfac_struct.json 2>/dev/null || echo "（无该文件）"
/root/miniconda3/envs/ml/bin/python - <<'PY'
import json, os
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
p = '_r30_selfac_struct.json'
if os.path.exists(p):
    d = json.load(open(p))
    print('顶层键:', list(d.keys())[:12])
    for k in list(d.keys())[:3]:
        v = d[k]
        print('  %s: %s' % (k, str(v)[:300]))
else:
    print('（无）')
PY
