#!/bin/bash
# _r448_dgpick.sh —— ★★ **`--stack-pick-dg` 的受控实测**（两臂只差这一个开关）
#
# ## 要回答的问题
# `§195` 实测：sympathetic 形核**继承源块的命运**（接到 V7/V9 的块 ⇒ 长；接到 V1 的块 ⇒ 溶）。
# `§200` 把 `dG`（引擎**已经**在算的量）接到"选哪个块"上。
# **问题：接上之后，选块真的变了、结局真的变好了吗？**
#
# ## 配置（与 `_r423` 同款：人为放大的 `α_KM`，只为在 12 步内触发十几个事件）
# ⚠ **本脚本的绝对数值不是物理结果**，只回答"接线生不生效、方向对不对"。
#
# ## 判据
#   D-1 两臂都无 Traceback。
#   D-2 `--stack-pick-dg 1` 的 `dbg` 里出现 `dg_pick`（真的走了 dG 分支）。
#   D-3 **两臂的事件落场不同** ⇒ 选块规则真的变了（否则是死开关）。
#   D-4 方向：`dg_pick=1` 的"长"的场数**不少于** `0`（若更差 ⇒ 方向错，要记账）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 12 --every 4 --snap-every 12 --pair-every 4 \
--norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
--laths 1,1,1,1,3,3,3,3,5,5,5,5 \
--plate-L 1000 --plate-W 500 --plate-T 250 \
--gamma0 0.25 --beta-h 6.477 \
--grow-stack --nuc-law athermal --nuc-init 8 --nuc-fresh-every 4 \
--alpha-km 2.0 --cool-rate 5e7 --facet-proj 0"

run_one () {
  local tag="$1"; shift
  echo "######## 臂 $tag ：$*"
  timeout 2400 "$PY" -u _bk_exp.py $COMMON "$@" \
      --tag "$tag" --out _exp/_bk_mb > "_r448_${tag}.log" 2>&1
  echo "   退出码=$?  Traceback=$(grep -c Traceback "_r448_${tag}.log" || true)"
}

rm -rf _exp/_bk_mb/dry_dp0 _exp/_bk_mb/dry_dp1
run_one dp0 --stack-pick-dg 0
run_one dp1 --stack-pick-dg 1

echo
echo "======== D-2 dbg 对照 ========"
for t in dp0 dp1; do
  f="_exp/_bk_mb/dry_${t}/nuc_dbg.json"
  if [ -f "$f" ]; then
    echo "-- $t:"
    "$PY" -c "import json;d=json.load(open('$f'));g=d.get('dbg',{});print('   dg_pick      =',g.get('dg_pick'));print('   dg_pick_ncand=',g.get('dg_pick_ncand'));print('   by_requested =',d.get('n_events_by_requested_mode'));print('   n_ev         =',d.get('n_athermal_ev'))"
  else
    echo "-- $t: ✗ 无 nuc_dbg.json"
  fi
done

echo
echo "======== D-3 事件落场对比 ========"
"$PY" _r438_logmap.py 2>/dev/null | head -0
for t in dp0 dp1; do
  echo "-- $t:"
  grep -oE '场 [0-9]+（累计 [0-9]+/[0-9]+；模式 \*\*[a-z]+\*\*' "_r448_${t}.log" | head -14
done

echo
echo "======== D-4 块结构 ========"
for t in dp0 dp1; do
  echo "-- $t:"
  grep -E '每块板条数\(定义\)|逐块柱剖面\*\*不同场数\*\*' "_r448_${t}.log" | tail -2
done

echo
echo "======== 异常 ========"
for t in dp0 dp1; do
  echo "  $t: Traceback=$(grep -c Traceback "_r448_${t}.log" || true)"
done
