#!/bin/bash
# 核查：GPU 情况 + MOOSE 里是否有凝固/液相/热场能力

echo "===== 1. GPU ====="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv 2>/dev/null || echo "  无 nvidia-smi"
python3 -c "import torch;print('  torch', torch.__version__, 'cuda可用:', torch.cuda.is_available())" 2>/dev/null || \
    (source /root/miniconda3/etc/profile.d/conda.sh; conda activate ml 2>/dev/null; \
     python3 -c "import torch;print('  torch', torch.__version__, 'cuda可用:', torch.cuda.is_available())")

echo
echo "===== 2. MOOSE 里与凝固/热场相关的示例与源码 ====="
cd /root/moose || exit 1
echo "--- 含 solidification / melting / latent 的输入文件 ---"
find modules -name '*.i' \( -iname '*solidif*' -o -iname '*melt*' -o -iname '*latent*' -o -iname '*cast*' \) 2>/dev/null | head -20
echo "--- phase_field 模块里含 'liquid' 的输入文件 ---"
grep -rl 'liquid' modules/phase_field --include='*.i' 2>/dev/null | head -15
echo "--- 含温度变量的相场输入文件（temperature / temp） ---"
grep -rl 'temperature\|\[temp\]\|T = ' modules/phase_field/examples --include='*.i' 2>/dev/null | head -15

echo
echo "===== 3. 关键：GrainTracker 是否只能用于固态晶粒长大？ ====="
grep -n 'class GrainTracker' -A5 modules/phase_field/include/postprocessors/GrainTracker.h 2>/dev/null | head -20
echo "--- GrainGrowthAction 支持的参数 ---"
grep -n 'addParam' modules/phase_field/src/actions/GrainGrowthAction.C 2>/dev/null | head -25

echo
echo "===== 4. 有没有 KKS / 凝固相关的相场 kernel ====="
ls modules/phase_field/src/kernels/ 2>/dev/null | head -40

echo
echo "===== 5. 各 app 的可用性 ====="
ls -la /root/moose/modules/*/  2>/dev/null | grep -E '^\-.*-opt$' | awk '{print $NF}' | head -20
