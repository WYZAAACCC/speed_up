#!/bin/bash
# _r30_mb2b.sh —— R37：**P-SA-1 的重复种子**（判据跑之前就写好，与 R36 同一套）
#
# 为什么必须做：R36 的 P-SA-1 是**单次实现**（`--eng-seed` 默认值），
#   差异只有 10–26% ⇒ **不换种子就不知道它是分布结论还是这一次的运气**。
#
# 装置与 R36 **逐项相同**，只差 `--eng-seed`：
#   seed 23 → mb2b(ed) / mb3b(random)
#   seed 37 → mb2c(ed) / mb3c(random)   ← 跑完第一对自动接上
#
# 判据（与 R36 完全相同，不得改）：
#   P-SA-1a  ed 的 r_selfac 更低（共同 f 逐点配对）
#   P-SA-1b  ed 的 E_el 更低
#   P-SA-1c  ed 的变体数不多于 random
#   ★ **汇总判据（新登记）**：3 个种子 × 3 条 ⇒ 至少 7/9 通过才算"可重复"；
#     若只有 1 个种子通过 ⇒ 写成"未复现"。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--arm eng --N 96 --dx-nm 125 \
  --laths 1,1,2,2,3,3,4,4,5,5,6,6 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --eng-r-nm 320 --eng-t-nm 510 --eng-elong 3.0 --nuc-overlap-nm 0 \
  --eng-cadence 60 --nuc-init 30 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 900 --every 20 --snap-every 100 --pair-every 20 --nthreads 3"

for S in 23 37; do
  case "$S" in
    23) TA=mb2b; TB=mb3b ;;
    37) TA=mb2c; TB=mb3c ;;
  esac
  echo "=== seed=$S : $TA(ed) / $TB(random)  $(date '+%F %T') ==="
  "$PY" -u _bk_exp.py $COMMON --var-rule ed --eng-seed "$S" \
      --tag "$TA" --out _exp/_bk_mb > "_w2_r37_${TA}.log" 2>&1 &
  P1=$!
  "$PY" -u _bk_exp.py $COMMON --var-rule random --eng-seed "$S" \
      --tag "$TB" --out _exp/_bk_mb > "_w2_r37_${TB}.log" 2>&1 &
  P2=$!
  wait $P1; echo "$TA 结束 rc=$?"
  wait $P2; echo "$TB 结束 rc=$?"
done
echo "=== R37 重复种子 DONE $(date '+%F %T') ==="
