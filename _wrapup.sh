#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== CA 侧回归（我的改动后）:"
for f in verify_ca3d.py verify_ca3d_physics.py verify_ca3d_envelope.py; do
  s=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > /tmp/r_$f.log 2>&1
  echo "$f rc=$? wall=$(( $(date +%s) - s ))s  $(grep -h '汇总' /tmp/r_$f.log | tail -1)"
done
echo "=== 后台跑 solute + wc_cet（较慢）:"
setsid nohup bash -c 'cd /mnt/f/speed_up/pipeline/ca_pf_framework; /root/miniconda3/envs/ml/bin/python verify_ca3d_solute.py > /tmp/r_solute.log 2>&1; /root/miniconda3/envs/ml/bin/python verify_ca3d_wc_cet.py > /tmp/r_wc.log 2>&1' > /dev/null 2>&1 < /dev/null &
echo " 已挂后台"
echo; echo "=== Window B 现有资产:"
ls /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/ | head -20
echo "--- P11_SPEC 行数: $(wc -l < /mnt/f/speed_up/pipeline/ca_pf_framework/P11_SPEC.md 2>/dev/null)"
echo "--- MATH_FRAMEWORK §5 标题行:"; grep -n '^## 5\|^### 5' /mnt/f/speed_up/pipeline/ca_pf_framework/MATH_FRAMEWORK.md | head