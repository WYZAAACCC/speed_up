#!/bin/bash
# _r423_smoke3.sh —— ★ **缺陷③的决定性冒烟**：让 `stack` 通道**真的拿到名额**
#
# ## 为什么上一版没测到
# `_r421` 用了 `--multi-block` ⇒ **12 个场在 t=0 全被播满** ⇒ 形核**没有空场可用**
#   （`nuc_dbg.json` 实测 `fresh_blocked: 4`、`nfsv_nofield: 9`）
# ⇒ 交错逻辑虽然走到了（日志里事件 5、9 的模式确实是 `fresh`，符合 `k%4==1`），
#   但 **`stack` 事件全被"没空场"挡掉**，等于没验。
#
# ## 本版怎么改
# **不加 `--multi-block`** ⇒ 归档的引擎路径在 t=0 **只播第 1 片（场 1）**
#   （`_r414` 冒烟日志原话："t=0 只播第 1 片（场 1）"），其余 11 个场**留空**。
# 于是：
#   * `fresh` 事件 ⇒ 随机位点上的**新块**；
#   * `stack` 事件 ⇒ 贴已有块外缘的**块内板条**（`nfsv` 找同变体的空场）。
#
# ## 判据
#   T-1 日志里**同时**出现模式 `fresh` 与 `stack` 的事件（各 ≥1 次）。
#   T-2 实际分配与 `k % K == 1` 规则**逐条吻合**。
#   T-3 末态 `blk_laths` 里出现 **>1**（块内多根板条）**且**块数 **>1**。
#       ⚠ 这是缺陷②③合并后的**核心验收**：既要多块、又要块内多根。
#   T-4 无 Traceback。
#   T-5 **惰性对照**：`--nuc-fresh-every 0` 时模式**只有 fresh**。
#
# ⚠ 形核参数仍是**人为放大**的（α_KM=2.0、q=5e7）—— 只为在 15 步内触发事件。
#   **本脚本的任何数值都不是物理结果。**
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 12 --every 4 --snap-every 12 --pair-every 4 \
--norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
--laths 1,1,1,1,3,3,3,3,5,5,5,5 \
--plate-L 1000 --plate-W 500 --plate-T 250 \
--grow-stack --nuc-law athermal --nuc-init 8 \
--alpha-km 2.0 --cool-rate 5e7 --facet-proj 0"

run_one () {
  local tag="$1"; shift
  echo "######## 臂 $tag ：$*"
  timeout 2400 "$PY" -u _bk_exp.py $COMMON "$@" \
      --tag "$tag" --out _exp/_bk_mb > "_r423_${tag}.log" 2>&1
  echo "   退出码=$?  Traceback=$(grep -c Traceback "_r423_${tag}.log" || true)"
}

rm -rf _exp/_bk_mb/dry_smS _exp/_bk_mb/dry_smT
run_one smS --nuc-fresh-every 4
run_one smT --nuc-fresh-every 0

echo
echo "============ T-1/T-2 事件模式（smS，K=4）============"
grep -oE '累计 [0-9]+/[0-9]+；模式 \*\*[a-z]+\*\*' _r423_smS.log | head -20
echo "  模式计数："
grep -oE '模式 \*\*[a-z]+\*\*' _r423_smS.log | sort | uniq -c
echo "  退回 stack 次数：$(grep -c '退回 .stack.' _r423_smS.log || true)"

echo
echo "============ T-5 惰性对照（smT，K=0）============"
grep -oE '模式 \*\*[a-z]+\*\*' _r423_smT.log | sort | uniq -c

echo
echo "============ nuc_dbg.json ============"
for t in smS smT; do
  f="_exp/_bk_mb/dry_${t}/nuc_dbg.json"
  if [ -f "$f" ]; then
    echo "-- $t:"
    "$PY" -c "import json; d=json.load(open('$f')); print('   nuc_fresh_every=', d.get('nuc_fresh_every')); print('   by_requested  =', d.get('n_events_by_requested_mode')); print('   fallback      =', d.get('n_fresh_fallback_to_stack')); print('   by_mode(all)  =', d.get('n_events_by_mode')); print('   n_athermal_ev =', d.get('n_athermal_ev'))"
  else
    echo "-- $t: ✗ 无 nuc_dbg.json"
  fi
done

echo
echo "============ T-3 末态块结构（最关键的验收）============"
for t in smS smT; do
  echo "-- $t:"
  grep -E '每块板条数\(定义\)|逐块柱剖面\*\*不同场数\*\*|逐块柱剖面\*\*段数\*\*|该块分量覆盖的场数|每块内板条全部可分辨' \
       "_r423_${t}.log" | tail -6
done

echo
echo "============ T-4 异常 ============"
for t in smS smT; do
  echo "  $t: Traceback=$(grep -c Traceback "_r423_${t}.log" || true)"
done
