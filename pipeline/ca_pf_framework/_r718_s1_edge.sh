#!/usr/bin/env bash
# _r718_s1_edge.sh —— S1 计数器的**边界档实测**（判定 `R718 §4` 的待核项）。
#
# 判据（先登记，可 FAIL）：
#   E-1 `CFL_GUARD_MAX` 取**略低于峰值**（0.1545）⇒ `n_steps_over` 必须是**小数**（≈1–3），
#       且 `first_over_step` 必须 ≈ 峰值出现的那个 step（**不是** 1）
#   E-2 `CFL_GUARD_MAX` 取**略高于峰值**（0.16）⇒ `n_steps_over` 必须**恰为 0**、`first_over_step=-1`
#   ⇒ 若 E-1 给 60（与 V3b 同）⇒ 计数器**不随阈值变** ⇒ **是 bug**（每步都在加）
#   ⇒ 若 E-1 给小整数、E-2 给 0 ⇒ 计数器正确，`V3b` 的 60 只是"真的每步都越限"
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY=/root/miniconda3/envs/ml/bin/python
OUT="$HERE/_exp/_s1edge"
rm -rf "$OUT"; mkdir -p "$OUT"

COMMON=(--N 48 --dx-nm 62.5 --steps 60 --every 20 --snap-every 99999
        --pair-every 0 --norm-smooth 0 --nthreads 4 --arm dry
        --laths 1,1,1 --plate-L 125.0 --plate-W 125.0 --plate-T 125.0
        --nuc-shape disc --grow-stack --nuc-every 0 --nuc-init 0
        --nuc-law cadence --nuc-block-target 0 --nuc-mode auto --eng-cadence 30
        --gamma0 0.25 --gamma-film 0.6 --alpha-km 0.041739
        --T-end 298.0 --cool-rate 2352400.0 --qs-clock 1 --qs-max-relax 100
        --beta-h 6.477 --beta-w 2.3 --ed-eta 0.253
        --mob-iform exp2 --mob-ratio 9.0 --mob-dip 4.0 --band-cells 40 --mob-wulff
        --facet-proj 0 --rank1-swap none --var-rule ed --nuc-sites-refill 1
        --out "$OUT")

for spec in "e1_below:0.1545" "e2_above:0.16"; do
  tag="${spec%%:*}"; lim="${spec##*:}"
  echo "==================== $tag（CFL_GUARD_MAX=$lim）===================="
  CFL_GUARD=warn CFL_GUARD_MAX="$lim" bash -c \
    "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py ${COMMON[*]} --tag $tag" \
    > "$OUT/$tag.log" 2>&1
  echo "rc=$?"
  if compgen -G "$OUT/dry_$tag/cfl_guard_*.txt" > /dev/null; then
    sed 's/^/      /' "$OUT"/dry_$tag/cfl_guard_*.txt
  else
    echo "      ⛔ 未落盘"; tail -4 "$OUT/$tag.log"
  fi
  echo
done

echo "==================== 判定 ===================="
A=$(grep -h 'n_steps_over' "$OUT"/dry_e1_below/cfl_guard_*.txt | cut -d= -f2)
B=$(grep -h 'n_steps_over' "$OUT"/dry_e2_above/cfl_guard_*.txt | cut -d= -f2)
FA=$(grep -h 'first_over_step' "$OUT"/dry_e1_below/cfl_guard_*.txt | cut -d= -f2)
echo "  E-1（上限 0.1545，略低于峰值 0.1545551）：n_steps_over=$A  first_over_step=$FA"
echo "  E-2（上限 0.16，略高于峰值）：              n_steps_over=$B"
if [ "$B" = "0" ] && [ "$A" != "60" ] && [ "$A" -ge 1 ] 2>/dev/null; then
  echo "  ✅ 计数器**随阈值变** ⇒ 正确；V3b 的 60 只是'真的每步都越限'（峰值 0.1528 起就 >0.10）"
elif [ "$B" = "0" ] && [ "$A" = "0" ]; then
  echo "  ⚠ E-1 也给 0 ⇒ 峰值可能没被采到（量具有问题），须查"
else
  echo "  ⛔ 计数器**不随阈值变** ⇒ 有 bug（每步都在加）"
fi
