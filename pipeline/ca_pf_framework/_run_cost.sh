#!/usr/bin/env bash
# _run_cost.sh --- 24 µm 盒下三个分辨率的消耗扫描（串行，避免内存争用；大的放最后）
#
# 目的：把「N=384（24 µm / 62.5 nm）的代价」从**估算**变成**实测**。
# 关键未知项是**弹性求解（FFT）的内存**——它可能比 `self.phi` 还大。
# 串行 + 大的放最后：若 N=384 因内存失败，前两点的数据仍然保住。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
echo "########## 消耗扫描 start=$(date -Is) ##########"
free -g | head -2

for spec in "250:N96:6" "125:N192:6" "62.5:N384:4"; do
  DXN="${spec%%:*}"; rest="${spec#*:}"
  TAG="${rest%%:*}"; ST="${rest#*:}"
  echo ""
  echo "===== Δx=${DXN} nm  (${TAG})  steps=${ST} ====="
  timeout 3600 "$PY" -u _probe_cost.py --L-um 24 --dx-nm "$DXN" \
      --n0 64 --steps "$ST" --tag "24um-${TAG}" \
      > "_w2_cost_${TAG}.log" 2>&1
  RC=$?
  echo "### ${TAG} rc=${RC} @ $(date -Is)"
  if [ "$RC" -ne 0 ]; then
    echo "--- ${TAG} 失败，日志尾部："
    tail -12 "_w2_cost_${TAG}.log"
  else
    grep -e "C-1" -e "C-2" -e "每胞每步" -e "换算到生产" "_w2_cost_${TAG}.log"
  fi
  sleep 3
done

echo ""
echo "########## 结束 end=$(date -Is) ##########"
free -g | head -2
