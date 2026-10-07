#!/bin/bash
# _r565_wslrun.sh --- **统一的基准跑法**：一律在生产宿主（WSL + conda `ml`）上量。
#
# 为什么必须固化这一步（本轮实测的教训 R564）：
#   同一份 `eps0_fields`，Windows Anaconda(numpy 2.1.3) = 0.103 s，
#   WSL conda `ml`(numpy 2.5.3) = **0.048 s** ⇒ **差 2.1×**。
#   而我先前两次基准都跑在 Windows 上 ⇒ 绝对值全部偏高、结论差点下错。
#   归档 `_r559` 的 0.048 s/次 与 WSL `ml` **逐位吻合** ⇒ 生产就在这条路上。
#
# 用法： bash _r565_wslrun.sh <脚本名.py> [更多脚本...]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

PY=/root/miniconda3/envs/ml/bin/python
[ -x "$PY" ] || { echo "找不到 $PY"; exit 1; }

echo "############################################################"
echo "# 宿主指纹（每次基准都留档，防"量在哪个解释器上"再出错）"
echo "############################################################"
"$PY" - <<'PYEOF'
import sys, platform, numpy, scipy
print('  host   :', platform.platform())
print('  python :', sys.version.split()[0], sys.executable)
print('  numpy  :', numpy.__version__, '| scipy:', scipy.__version__)
PYEOF

for S in "$@"; do
  echo ""
  echo "########## RUN $S ##########"
  "$PY" "$S" 2>&1
  echo "########## EXIT($S) = $? ##########"
done
