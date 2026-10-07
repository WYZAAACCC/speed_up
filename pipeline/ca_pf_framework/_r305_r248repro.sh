#!/bin/bash
# _r305_r248repro.sh —— ★ **复现 + 稳健性检验 `§144` 的核心结论**（本会话最重要的论断）。
#
# ## 要检验的论断（`§144`/`§248`）
# 「**带 `--facet-proj 10` 时，把 γ_F3 改 31.3 倍 ⇒ 所有形态量逐位为零**。」
#
# ## 为什么要做
# 用户硬要求「**一定要注意确保测量工具的正确性**」，
# 而 `§144` 是本会话**最重要的结论**（它支撑 `§151`/`§154`/`§156` 的解释链）。
# **⇒ 必须做①复现 ②换条件稳健性** 两件事。
#
# ## 判据（**先写死**）
# * **V-1 复现**：与 `_r248` 逐字相同的命令 ⇒ 必须得到**同样的结论**
#   （形态列逐位相同）。
# * **V-2 ★ 稳健性（换几何）**：同样 31.3× 对比、同样带投影，但**换 N 与板条表**
#   ⇒ 若**仍然逐位相同** ⇒ 结论稳健；若**出现差异** ⇒ 说明 `§144` 的适用范围比声称的窄。
# * **V-3 负对照**：同一配置跑两次必须逐位相同（确定性）。
# * **V-4** 不带投影的那一组（`_r248` 已测过差异 0.91）**不复现**，只作为对照引用。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
rm -rf _exp/_bk_repro

echo "=== §144 复现+稳健性检验 $(date '+%F %T') ==="

# --- V-1 复现：与 _r248 逐字相同（N=32 / 1,1 / 30 步 / facet-proj 10）---
G1="--arm dry --N 32 --dx-nm 125 --laths 1,1 --gap-nm 0 --facet-proj 10 \
    --steps 30 --every 1 --snap-every 30 --pair-every 0 --nthreads 2 \
    --out _exp/_bk_repro"
$PY -u _bk_exp.py $G1 --omega-mode ladder  --omega-max-deg 5.0  --tag rH  > _w2_r305_rH.log  2>&1 &
A=$!
$PY -u _bk_exp.py $G1 --omega-mode perstep --omega-max-deg 0.05 --tag rC  > _w2_r305_rC.log  2>&1 &
B=$!
$PY -u _bk_exp.py $G1 --omega-mode ladder  --omega-max-deg 5.0  --tag rH2 > _w2_r305_rH2.log 2>&1 &
C=$!
wait $A $B $C
echo "  V-1/V-3 组完成（rc=$?）"

# --- V-2 稳健性：换几何（N=48 / 1,1,3,3 / 40 步），仍带投影、仍 31.3× ---
G2="--arm dry --N 48 --dx-nm 100 --laths 1,1,3,3 --gap-nm 0 --facet-proj 10 \
    --steps 40 --every 1 --snap-every 40 --pair-every 0 --nthreads 2 \
    --out _exp/_bk_repro"
$PY -u _bk_exp.py $G2 --omega-mode ladder  --omega-max-deg 5.0  --tag sH > _w2_r305_sH.log 2>&1 &
D=$!
$PY -u _bk_exp.py $G2 --omega-mode perstep --omega-max-deg 0.05 --tag sC > _w2_r305_sC.log 2>&1 &
E=$!
wait $D $E
echo "  V-2 组完成（rc=$?）"
echo "=== 结束 $(date '+%F %T') ==="
for f in _w2_r305_*.log; do
  printf '  %-24s Traceback=%s\n' "$f" "$(grep -c Traceback "$f" || true)"
done
