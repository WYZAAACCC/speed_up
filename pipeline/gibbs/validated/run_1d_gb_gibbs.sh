#!/bin/bash
# =============================================================================
# 1D 晶界 Gibbs 模型 —— 物理闭合验证
# =============================================================================
# 核心判据：整个 PDE 求解出来的**峰** c_GB 是否等于精确 McLean 解析值
#   c_GB/(1-c_GB) = (c0/(1-c0))*exp(-dG_seg/(R*T))
# 这是"物理闭合"的判决：模型复现了 Cahn 1962 的等温线，且带温度依赖。
#
# 扫两类： kappa_c（梯度项的抹平）与 dx（分辨率）—— 峰应收敛到解析值。
# ⚠ 结果写 /mnt/f（WSL 会不定期自动重启）
# =============================================================================
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_1d_gb_gibbs.py" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results}"
ROOT="${ROOT:-/root/work/g1d}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
DELTA="${DELTA:-0.5e-9}"

rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"
[ -f "$SAVE/ALL.txt" ] && rm -f "$SAVE/ALL.txt"

# tag  T(K)  kappa_c  dx/wgb  ldom/wgb  t_end
DEFAULT_CASES=(
  "kc1e-9_T1950    1950  1e-9    0.125  533  1.0e-4"
  "kc1e-10_T1950   1950  1e-10   0.125  533  1.0e-4"
  "kc1e-11_T1950   1950  1e-11   0.125  533  1.0e-4"
  "kc1e-12_T1950   1950  1e-12   0.125  533  1.0e-4"
  "kc1e-13_T1950   1950  1e-13   0.125  533  1.0e-4"
  "kc1e-10_T923     923  1e-10   0.125  533  1.0e-4"
  "kc1e-11_T923     923  1e-11   0.125  533  1.0e-4"
  "kc1e-12_T923     923  1e-12   0.125  533  1.0e-4"
  "kc1e-13_T923     923  1e-13   0.125  533  1.0e-4"
  "kc1e-13_T1500   1500  1e-13   0.125  533  1.0e-4"
)
if [ -n "${CASES_OVERRIDE:-}" ]; then
  IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"
else
  CASES=("${DEFAULT_CASES[@]}")
fi

echo "=============================================================="
echo " 1D 晶界 Gibbs —— 物理闭合验证（峰 vs 精确 McLean）"
echo " 结果目录: $SAVE"
echo "=============================================================="

for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; T=$2; kc=$3; dxr=$4; nr=$5; tend=$6
  D="$ROOT/$tag"; mkdir -p "$D"; cd "$D"
  WGB=$(python3 -c "print(0.75*$DELTA)")
  DX=$(python3 -c  "print($WGB*$dxr)")
  LDOM=$(python3 -c "print($WGB*$nr)")

  timeout 600 python3 "$HERE/make_1d_gb_gibbs.py" --out gb.i \
      --temp "$T" --kc "$kc" --delta-gb "$DELTA" \
      --dx "$DX" --ldom "$LDOM" --n-steps 2000 --t-end "$tend" \
      > gen.log 2>&1 || { echo "$tag 生成失败"; tail -3 gen.log; continue; }

  timeout 3600 "$MOOSE" -i gb.i > run.log 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A4 -m1 '\*\*\* ERROR' | head -5
    continue
  fi
  mkdir -p "$SAVE/$tag"
  cp -f gb.i run.log gb_out.csv gen.log params.json "$SAVE/$tag/" 2>/dev/null
  sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'JIT compile failed' > "$SAVE/$tag/jit.txt"
  sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'Solve Did NOT Converge' > "$SAVE/$tag/nconv.txt"
  cd "$ROOT"
done

echo
echo "=== 逐档验证 ==="
python3 - "$SAVE" <<'PY'
import csv, json, os, sys
root = sys.argv[1]
rows = []
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        continue
    try:
        m = json.load(open(os.path.join(p, "params.json"), encoding="utf-8"))
        r = list(csv.DictReader(open(os.path.join(p, "gb_out.csv"))))
    except Exception as e:
        print("  %-16s 读失败 %s" % (d, e)); continue
    if not r:
        continue
    last, first = r[-1], r[0]
    cmax = float(last["c_max"]); cmin = float(last["c_min"])
    cedge = float(last["c_edge"]); ctot = float(last["total_c"])
    hmax = float(last["hgb_max"]); dmin = float(last["D_min"]); dmax = float(last["D_max"])
    jit = int(open(os.path.join(p, "jit.txt")).read().strip() or 1)
    ncv = int(open(os.path.join(p, "nconv.txt")).read().strip() or 1)
    c_ana = m["c_GB_analytic"]
    s_ana = m["s_analytic"]
    Glen = ctot - cedge * m["ldom"]
    Gmodel = m["rho_mol"] * Glen
    Gtarget = m["Gamma_phys_target"]
    drift = (ctot - float(first["total_c"])) / float(first["total_c"])
    wc = (m["kappa_c"] / (8.314462618 * m["T"] / (9.873e-6 * m["c0"] * (1 - m["c0"])))) ** 0.5
    rows.append((m["T"], m["kappa_c"], m["dx"], m["wgb"], wc, wc / m["dx"], cmax, c_ana,
                 (cmax - c_ana) / c_ana, cmax / cedge, s_ana, Gmodel, Gtarget,
                 Gmodel / Gtarget, drift, cmin, hmax, dmin, dmax, jit, ncv, d))

# 按 T 分组打印
for T in sorted({r[0] for r in rows}, reverse=True):
    grp = sorted([r for r in rows if r[0] == T], key=lambda x: -x[1])
    print()
    print("=== T = %.0f K ===" % T)
    print("  %-9s %-8s %-7s %10s %10s %10s %9s %10s %9s %-9s %s" %
          ("kappa_c", "w_c/dx", "dx", "c_max", "McLean", "偏差", "s_实测", "s_解析",
           "Γ比", "守恒漂移", "c_min | JIT/未收敛"))
    print("  " + "-" * 118)
    for r in grp:
        (T_, kc, dx, wgb, wc, wcdx, cmax, cana, err, s, sana, Gm, Gt, gr, dr,
         cmin, hmax, dmin, dmax, jit, ncv, tag) = r
        print("  %-9.0e %-8.2f %-7.3g %10.7f %10.7f %9.2f%% %9.4f %10.4f %9.3f %-9.2e %.5f | %d/%d"
              % (kc, wcdx, dx, cmax, cana, err * 100, s, sana, gr, dr, cmin, jit, ncv))
    best = min(grp, key=lambda x: abs(x[8]))
    print("  ⇒ 最接近解析值: kappa_c=%.0e  偏差 %+.2f%%  (w_c/dx=%.2f)" %
          (best[1], best[8] * 100, best[5]))
    print("  ⇒ 收敛趋势: 随 kappa_c 减小，|偏差| 应单调减小 ⇒ 见上表")
PY