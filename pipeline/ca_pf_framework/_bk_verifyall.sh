#!/bin/bash
# _bk_verifyall.sh —— 阶段 1/2 的全部自检一次性跑完，落盘日志
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
FAILS=0
for s in _bk_verify.py windowB_lath.py _bk_measure.py _bk_engine_identity.py; do
  log="_w2_chk_${s%.py}.log"
  echo "=================== $s -> $log"
  "$PY" -u "$s" > "$log" 2>&1
  rc=$?
  n=$(grep -ac 'FAIL' "$log" || true)
  echo "   exit=$rc  含FAIL行=$n"
  grep -a 'FAIL' "$log" | grep -av 'FAIL = 0' | tail -4
  [ "$rc" != "0" ] && FAILS=$((FAILS+1))
done
echo "=================== 汇总：非零退出的脚本数 = $FAILS"
