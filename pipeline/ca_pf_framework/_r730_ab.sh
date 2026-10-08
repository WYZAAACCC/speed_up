#!/usr/bin/env bash
# _r730_ab.sh —— R730 的 A/B：`NDIR_LSQ` 关 / 开（**单变量：只切这一个环境变量**）。
#
# 判据（`R727 §3`）：
#   J-5  `beta_h^eff` 兑现率上升（基线 0.953 -> 靶 >= 0.98）
#   J-9  `f_flat` 不劣化
#   J-10 步数比 ∈ [0.8, 1.25]
#   ★ 开关生效的**独有成功串**：`ndir_` 变了 ⇒ `beta_h^eff` 或 PCA 该变
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY=/root/miniconda3/envs/ml/bin/python
OUT="$HERE/_exp/_ndirlsq"
rm -rf "$OUT"; mkdir -p "$OUT"

COMMON=(--N 96 --dx-nm 62.5 --steps 100 --every 25 --snap-every 25
        --pair-every 25 --norm-smooth 0 --nthreads 4 --arm dry
        --laths 1,1,1,1,1,1
        --plate-L 125.0 --plate-W 125.0 --plate-T 125.0
        --nuc-shape disc --grow-stack --nuc-every 0 --nuc-init 0
        --nuc-law cadence --nuc-block-target 0 --nuc-mode auto --eng-cadence 30
        --gamma0 0.25 --gamma-film 0.6 --alpha-km 0.041739
        --T-end 298.0 --cool-rate 2352400.0 --qs-clock 1 --qs-max-relax 100
        --beta-h 6.477 --beta-w 2.3 --ed-eta 0.253
        --mob-iform exp2 --mob-ratio 9.0 --mob-dip 4.0
        --facet-proj 0 --rank1-swap none --var-rule ed --nuc-sites-refill 1
        --band-cells 40 --mob-wulff --out "$OUT")

echo "==================== 臂 A：NDIR_LSQ 关（默认档）===================="
env -u NDIR_LSQ bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py ${COMMON[*]} --tag nlsq_off" \
  > "$OUT/nlsq_off.log" 2>&1
echo "rc=$?"

echo
echo "==================== 臂 B：NDIR_LSQ=1 ===================="
NDIR_LSQ=1 bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py ${COMMON[*]} --tag nlsq_on" \
  > "$OUT/nlsq_on.log" 2>&1
echo "rc=$?"

echo
echo "==================== 判据 ===================="
"$PY" "$HERE/_r730_abread.py" "$OUT" nlsq_off nlsq_on
