#!/bin/bash
# _r433_fcritsmoke.sh —— ★ **`--nuc-fcrit` 的受控实测**：它到底拦不拦得住事件？
#
# ## 为什么用"人为放大 α_KM"的冒烟配置
# 要回答的问题是「`(df + max_k ed_k) > fcrit` 这条判据会不会拒掉位点」——
# 这个比较**与 α_KM 无关**（`df` 来自温度、`ed` 来自应变场、`fcrit = 4γ/t` 是常数）。
# 而真实 α_KM 下 200 步才几个事件，实测一次要 20 min/臂。
# ⇒ 用 `_r423` 的放大配置（12 步内触发十几个事件），**2 min/臂**。
# ⚠ **本脚本的绝对数值不是物理结果**，只回答"拦不拦"。
#
# ## 判据
#   F-1 两臂都无 Traceback。
#   F-2 `--nuc-fcrit 1` 的 `dbg['fcrit']`（被拒位点数）**是多少**。
#   F-3 两臂的事件数是否相同。**相同 + `fcrit=0` ⇒ 判据在当前量级下无效**（负面结论，要记账）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 12 --every 4 --snap-every 12 --pair-every 4 \
--norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
--laths 1,1,1,1,3,3,3,3,5,5,5,5 \
--plate-L 1000 --plate-W 500 --plate-T 250 \
--grow-stack --nuc-law athermal --nuc-init 8 --nuc-fresh-every 4 \
--alpha-km 2.0 --cool-rate 5e7 --facet-proj 0"

run_one () {
  local tag="$1"; shift
  echo "######## 臂 $tag ：$*"
  timeout 2400 "$PY" -u _bk_exp.py $COMMON "$@" \
      --tag "$tag" --out _exp/_bk_mb > "_r433_${tag}.log" 2>&1
  echo "   退出码=$?  Traceback=$(grep -c Traceback "_r433_${tag}.log" || true)"
}

rm -rf _exp/_bk_mb/dry_fc0 _exp/_bk_mb/dry_fc1
run_one fc0 --nuc-fcrit 0
run_one fc1 --nuc-fcrit 1

echo
echo "======== F-2/F-3 nuc_dbg.json 对照 ========"
for t in fc0 fc1; do
  f="_exp/_bk_mb/dry_${t}/nuc_dbg.json"
  if [ -f "$f" ]; then
    echo "-- $t:"
    "$PY" -c "import json;d=json.load(open('$f'));print('   n_athermal_ev =',d.get('n_athermal_ev'));print('   by_requested  =',d.get('n_events_by_requested_mode'));print('   dbg           =',d.get('dbg'))"
  else
    echo "-- $t: ✗ 无 nuc_dbg.json"
  fi
done

echo
echo "======== 事件对比 ========"
for t in fc0 fc1; do
  echo -n "  $t 事件数 = "; grep -c 'athermal 形核' "_r433_${t}.log" || true
done
echo
echo "======== 尾部判决对比 ========"
for t in fc0 fc1; do
  echo "-- $t:"
  grep -E '逐块柱剖面\*\*不同场数\*\*|每块板条数\(定义\)' "_r433_${t}.log" | tail -2
done
