#!/bin/bash
# _r421_smoke2.sh —— ★ `§189` 两处新功能的**端到端冒烟**（小盒子、少步数，只为验接线）
#
# ## 为什么要人为把 α_KM 调大
# `§188` 已证：α_KM=0.011 时 400 步内只有 ~0.5 次事件 ⇒ **交错逻辑根本跑不到**。
# 冒烟的目的是**验接线**，不是出物理结果 ⇒ 把 α_KM 与冷速人为调大，
# 让 15 步内触发远超 nv 的事件，把 fresh/stack 两条分支**都走到**。
# ⚠ **本脚本的任何数值都不得当成物理结果**（α_KM 是人为设的）。
#
# ## 判据
#   S-1 `--block-layout random` 的日志里出现"随机布局"与构型自检，
#       且第一主成分方差占比 **< 0.95**（`line` 是 0.9998）。
#   S-2 `--nuc-fresh-every 4` 下，事件日志里**同时**出现模式 `fresh` 与 `stack`。
#   S-3 `nuc_dbg.json` 里有 `n_events_by_requested_mode` 与 `n_fresh_fallback_to_stack`。
#   S-4 无 Traceback。
#   S-5 **惰性对照**：`--nuc-fresh-every 0`（归档行为）下，模式应**只有 fresh**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

# 12 个场 = 3 块 × 4 板条；形核参数人为放大（见文件头记账）
COMMON="--N 64 --dx-nm 62.5 --steps 15 --every 5 --snap-every 15 --pair-every 5 \
--norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
--laths 1,1,1,1,3,3,3,3,5,5,5,5 --multi-block --block-gap-nm 1200 \
--plate-L 1000 --plate-W 500 --plate-T 250 \
--grow-stack --nuc-law athermal --nuc-init 6 \
--alpha-km 2.0 --cool-rate 5e7 --facet-proj 0"

run_one () {
  local tag="$1"; shift
  echo "######## 臂 $tag ：$*"
  timeout 2400 "$PY" -u _bk_exp.py $COMMON "$@" \
      --tag "$tag" --out _exp/_bk_mb > "_r421_${tag}.log" 2>&1
  echo "   退出码=$?  Traceback=$(grep -c Traceback "_r421_${tag}.log" || true)"
}

rm -rf _exp/_bk_mb/dry_smR _exp/_bk_mb/dry_smL
run_one smR --block-layout random --block-seed 20261001 --nuc-fresh-every 4
run_one smL --block-layout line   --nuc-fresh-every 0

echo
echo "================= S-1 随机布局自检 ================="
grep -nE '随机布局|构型自检|主成分|邻居数' _r421_smR.log | head -8
echo "  （对照）line 臂："
grep -nE '布局轴|构型自检|主成分' _r421_smL.log | head -4

echo
echo "================= S-2 fresh/stack 交错 ================="
echo "-- smR（--nuc-fresh-every 4）模式分布："
grep -oE '模式 \*\*[a-z]+\*\*' _r421_smR.log | sort | uniq -c
echo "-- 前 8 条事件："
grep -nE 'athermal 形核' _r421_smR.log | head -8
echo "-- 退回 stack 次数："
grep -c '退回 .stack.' _r421_smR.log || true

echo
echo "================= S-5 惰性对照（smL，K=0） ================="
echo "-- smL 模式分布（应只有 fresh）："
grep -oE '模式 \*\*[a-z]+\*\*' _r421_smL.log | sort | uniq -c

echo
echo "================= S-3 nuc_dbg.json ================="
for t in smR smL; do
  f="_exp/_bk_mb/dry_${t}/nuc_dbg.json"
  if [ -f "$f" ]; then
    echo "-- $t:"
    "$PY" -c "import json,sys; d=json.load(open('$f')); print('   nuc_fresh_every =', d.get('nuc_fresh_every')); print('   by_requested   =', d.get('n_events_by_requested_mode')); print('   fallback       =', d.get('n_fresh_fallback_to_stack')); print('   n_athermal_ev  =', d.get('n_athermal_ev'), ' n_target_final =', d.get('n_target_final'))"
  else
    echo "-- $t: ✗ 无 nuc_dbg.json"
  fi
done

echo
echo "================= S-4 异常 ================="
for t in smR smL; do
  echo -n "  $t: Traceback="; grep -c Traceback "_r421_${t}.log" || true
done
echo
echo "================= smR 尾部 ================="
tail -12 _r421_smR.log
