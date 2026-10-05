#!/bin/bash
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R601_TRIP_THEORY.md \
        pipeline/ca_pf_framework/_t10_vis2.sh \
        pipeline/ca_pf_framework/_w2_t5_split3d_t10CL2_f111_en.png \
        pipeline/ca_pf_framework/_w2_t5_split3d_t10CL2_f10_en.png
git commit -q -m '④ σ_y(873K) 出处完整登记（R601 §5）：两轮检索只得到文献标题、无可直接引用数值 ⇒ 不编数字，登记 4 个候选出处(含 SCI 原文与 NASA NTRS 数据表)待逐篇提取；并写明待补的是出处不是结论（η 只由静水占比决定，σ_y∈0.1–2 GPa 结论不变）。另附修复后三维视觉验证图（pieces=1 main=100%）'
git log --oneline -1
echo "--- swap ---"
awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/9409/status 2>/dev/null
free -m | sed -n '2,3p' | sed 's/^/  /'
