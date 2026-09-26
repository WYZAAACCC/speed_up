#!/bin/bash
# =============================================================================
# 1D Gibbs 面模型（低维 Γ）验证
# =============================================================================
# 核心判据（这是弥散表示**做不到**的）：
#   C1  Γ 与 wgb 无关  —— 固定域长，只改 wgb（2/5/10/20 nm），Γ 应不变
#   C2  Γ 收敛到 A_s*c_far（Henry 等温线），且与完整 Langmuir 值差 <15%
#   C3  温度依赖：Γ/K(T) 应不随 T 变（Γ ∝ K(T)）
#   C4  守恒：∫c dx + Γ 的漂移 ~ 机器精度
#   C5  JIT=0、未收敛=0、c_min>0
# =============================================================================
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_1d_gb_gam.py" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_gam}"
ROOT="${ROOT:-/root/work/g1dg}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"

rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"

# tag              T     wgb(nm)  ldom(nm)  katt      t_end
DEFAULT_CASES=(
  "w2nm_T1950    1950   2.0     1000      1e6       1.0e-4"
  "w5nm_T1950    1950   5.0     1000      1e6       1.0e-4"
  "w10nm_T1950   1950  10.0     1000      1e6       1.0e-4"
  "w20nm_T1950   1950  20.0     1000      1e6       1.0e-4"
  "w5nm_T923      923   5.0     1000      1e6       1.0e-4"
  "w5nm_T1500    1500   5.0     1000      1e6       1.0e-4"
)
if [ -n "${CASES_OVERRIDE:-}" ]; then
  IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"
else
  CASES=("${DEFAULT_CASES[@]}")
fi

echo "=============================================================="
echo " 1D Gibbs 面模型（低维 Γ）"
echo "=============================================================="
for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; T=$2; wnm=$3; lnm=$4; katt=$5; tend=$6
  D="$ROOT/$tag"; mkdir -p "$D"; cd "$D"
  WGB=$(python3 -c "print($wnm*1e-9)")
  LDOM=$(python3 -c "print($lnm*1e-9)")
  DX=$(python3 -c "print($WGB/8.0)")
  timeout 600 python3 "$HERE/make_1d_gb_gam.py" --out gb.i \
      --temp "$T" --wgb "$WGB" --ldom "$LDOM" --dx "$DX" \
      --katt "$katt" --t-end "$tend" --n-steps 2000 > gen.log 2>&1 \
      || { echo "$tag 生成失败"; tail -3 gen.log; continue; }
  timeout 3600 "$MOOSE" -i gb.i > run.log 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A5 -m1 '\*\*\* ERROR' | head -6
    continue
  fi
  mkdir -p "$SAVE/$tag"
  cp -f gb.i run.log gb_out.csv gen.log params.json "$SAVE/$tag/" 2>/dev/null
  sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'JIT compile failed' > "$SAVE/$tag/jit.txt"
  sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'Solve Did NOT Converge' > "$SAVE/$tag/nconv.txt"
  echo "  $tag 完成"
  cd "$ROOT"
done

echo
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
        print("  %-14s 读失败 %s" % (d, e)); continue
    if not r:
        continue
    last, first = r[-1], r[0]

    def f(k):
        return float(last[k])

    cmax, cmin, cedge, ctot = f("c_max"), f("c_min"), f("c_edge"), f("total_c")
    gam = f("gam_gb"); gamint = f("gam_int")
    jit = int((open(os.path.join(p, "jit.txt")).read().strip() or "1"))
    ncv = int((open(os.path.join(p, "nconv.txt")).read().strip() or "1"))
    # 守恒：初末 ∫c dx + Γ（域内只有一个晶界 ⇒ Γ 计入一次）
    tot0 = float(first["total_c"]) + float(first["gam_int"])
    tot1 = ctot + gamint
    drift = (tot1 - tot0) / abs(tot0)
    # 解析：由总量守恒反解 c_far
    rho = m["rho_mol"]; L = m["ldom"]; As = m["A_s"]; c0 = m["c0"]
    cfar_pred = c0 * rho * L / (rho * L + As)
    gam_pred = As * cfar_pred
    rows.append(dict(tag=d, T=m["T"], wgb=m["wgb"], K=m["K"], As=As, katt=m["k_att"],
                     gam=gam, gampred=gam_pred, glang=m["Gamma_eq_langmuir"],
                     ratio=gam / gam_pred, ratioL=gam / m["Gamma_eq_langmuir"],
                     overK=gam / m["K"], cfar=cedge, cfar_pred=cfar_pred,
                     cmin=cmin, drift=drift, jit=jit, ncv=ncv, nx=m["nx"]))

print()
print("=" * 116)
print(" C1/C2：Γ 与 wgb 无关（固定域长 1000 nm）—— 弥散表示做不到这件事")
print("=" * 116)
print("  %-14s %8s %6s %13s %13s %9s %9s %9s" %
      ("tag", "wgb(nm)", "nx", "Gamma(实测)", "A_s*c_far(解析)", "实测/解析",
       "Γ/Langmuir", "Γ/K(T)"))
print("  " + "-" * 112)
sub = [r for r in rows if abs(r["T"] - 1950.0) < 1e-6]
for r in sorted(sub, key=lambda x: x["wgb"]):
    print("  %-14s %8.1f %6d %13.6e %13.6e %9.4f %9.4f %13.4e" %
          (r["tag"], r["wgb"] * 1e9, r["nx"], r["gam"], r["gampred"],
           r["ratio"], r["ratioL"], r["overK"]))
if len(sub) >= 2:
    gs = [r["gam"] for r in sub]
    print("  ⇒ Γ 的极差/均值 = %.4f  （判据：应 ~0，即与 wgb 无关）" %
          ((max(gs) - min(gs)) / (sum(gs) / len(gs))))

print()
print("=" * 116)
print(" C3：温度依赖（wgb = 5 nm）—— Γ 应 ∝ K(T)")
print("=" * 116)
print("  %-14s %6s %11s %13s %13s %13s" %
      ("tag", "T(K)", "K(T)", "Gamma(实测)", "A_s*c_far", "Gamma/K"))
print("  " + "-" * 112)
for r in sorted(rows, key=lambda x: -x["T"]):
    print("  %-14s %6.0f %11.5f %13.6e %13.6e %13.4e" %
          (r["tag"], r["T"], r["K"], r["gam"], r["gampred"], r["overK"]))

print()
print("=" * 116)
print(" C4/C5：守恒与健康")
print("=" * 116)
print("  %-14s %12s %11s %10s %8s %8s" % ("tag", "守恒漂移", "c_min", "c_far", "JIT", "未收敛"))
for r in sorted(rows, key=lambda x: x["tag"]):
    print("  %-14s %12.3e %11.7f %10.7f %8d %8d" %
          (r["tag"], r["drift"], r["cmin"], r["cfar"], r["jit"], r["ncv"]))
PY