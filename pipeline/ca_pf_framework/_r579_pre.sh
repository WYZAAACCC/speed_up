#!/bin/bash
# _r579_pre.sh --- 并行批次**开跑前的快检**：语法 + 每个新脚本的"最小可跑"。
# 判据：任一不过就**不要**启动 15 min 的批次（先修）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
bad=0
echo "=== py_compile ==="
for f in _r579_mem160.py _r579_report.py _r579_gpu.py _r579_exp7.py _r578_r3_ab.sh; do
  case "$f" in
    *.py) $PY -m py_compile "$f" && echo "  OK  $f" || { echo "  FAIL $f"; bad=1; } ;;
    *.sh) bash -n "$f" && echo "  OK  $f" || { echo "  FAIL $f"; bad=1; } ;;
  esac
done
echo
echo "=== M 道最小可跑（N=32, f64/nv=4）==="
rm -f _w2_r579_one_f64_nv4.json
R579_ONE=f64,4 R579_N=32 $PY _r579_mem160.py 2>&1 | tail -3 || bad=1
ls -la _w2_r579_one_f64_nv4.json 2>/dev/null || { echo "  ❌ JSON 没生成"; bad=1; }
echo
echo "=== G 道最小可跑（N=24 nv=4, 1 次）==="
R579G_N=24 R579G_NV=4 R579G_REPS=1 R579G_OUT=_w2_r579_gpu_pre.log $PY _r579_gpu.py 2>&1 | tail -12 || bad=1
echo
echo "=== P 道 ② 最小可跑（N=16）==="
R579E_MODE=2 R579E_N=16 R579E_REPS=3 R579E_OUT=_w2_r579_exp7_pre.log $PY _r579_exp7.py 2>&1 | tail -8 || bad=1
echo
echo "=== RESULT: $([ $bad = 0 ] && echo 'ALL PASS —— 可以启动并行批次' || echo 'FAIL —— 先修') ==="
exit $bad
