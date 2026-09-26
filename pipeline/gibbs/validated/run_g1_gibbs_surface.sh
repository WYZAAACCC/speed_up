#!/bin/bash
# =============================================================================
# G1 验证：1D Gibbs 面（面 = 点）
# =============================================================================
# 判据：
#   V1  Γ_实测 与 A_s·c_far 的解析值一致
#   V2  ★ Γ 与指示带宽 w **无关**   ← 这是"它真是面、不是带"的证明
#   V3  Γ ∝ K(T)（温度依赖）
#   V4  收敛（末两步一致）、c_min>0、JIT=0
#
# Γ_实测 = ρ_mol·(c0·L − ∫c dx)   ← 由总量守恒**精确**给出（不是"两个大数相减"）
# =============================================================================
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_1d_gibbs_surface.py" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_g1}"
ROOT="${ROOT:-/root/work/g1ref}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gibbs/gibbs-opt}"
LDOM="${LDOM:-20e-9}"
TEND="${TEND:-1.0e-2}"
rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"

# tag        T(K)   w(nm)
CASES=(
  "w0.5_T1950   1950  0.5"
  "w0.25_T1950  1950  0.25"
  "w0.125_T1950 1950  0.125"
  "w0.5_T1500   1500  0.5"
  "w0.5_T923     923  0.5"
)
if [ -n "${CASES_OVERRIDE:-}" ]; then IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"; fi

echo "=============================================================="
echo " G1：1D Gibbs 面（面 = 点）   二进制 = $MOOSE"
echo "=============================================================="
for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; T=$2; wnm=$3
  D="$ROOT/$tag"; mkdir -p "$D"; cd "$D"
  W=$(python3 -c "print($wnm*1e-9)")
  timeout 600 python3 "$HERE/make_1d_gibbs_surface.py" --out gb.i \
      --temp "$T" --wgb "$W" --ldom "$LDOM" --t-end "$TEND" --n-steps 4000 \
      > gen.log 2>&1 || { echo "$tag 生成失败"; tail -3 gen.log; continue; }
  timeout 1800 "$MOOSE" -i gb.i > run.log 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A5 -m1 '\*\*\* ERROR' | head -6
    continue
  fi
  mkdir -p "$SAVE/$tag"; cp -f gb.i gen.log run.log gb_out.csv params.json "$SAVE/$tag/" 2>/dev/null
  grep -c 'JIT compile failed' run.log > "$SAVE/$tag/jit.txt"
  grep -c 'Solve Did NOT Converge' run.log > "$SAVE/$tag/nconv.txt"
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
        print("  %-16s 读失败 %s" % (d, e)); continue
    if not r: continue
    last, prev, first = r[-1], r[-2], r[0]
    tc = float(last["total_c"]); tc0 = float(first["total_c"])
    cmin = float(last["c_min"]); cfarm = float(last["c_far"])
    bmax = float(last.get("beta_max", "nan"))
    jit = int((open(os.path.join(p,"jit.txt")).read().strip() or "1"))
    ncv = int((open(os.path.join(p,"nconv.txt")).read().strip() or "1"))
    # Γ_实测 = ρ_mol (c0 L − ∫c dx)
    Gm = m["rho_mol"] * (m["c0"] * m["ldom"] - tc)
    Gt = m["Gamma_theory"]
    cf_t = m["c_far_theory"]
    drift = abs(tc - float(prev["total_c"])) / max(abs(tc), 1e-30)
    rows.append(dict(tag=d, T=m["T"], w=m["wgb"], K=m["K"], As=m["A_s"], ASR=m["ASR"],
                     beta=m["beta"], Gm=Gm, Gt=Gt, ratio=Gm/Gt if Gt else float("nan"),
                     cfarm=cfarm, cft=cf_t, cmin=cmin, bmax=bmax,
                     overK=Gm/m["K"] if m["K"] else float("nan"),
                     drift=drift, jit=jit, ncv=ncv, nx=m["nx"], nel=m["nel_gb"]))

print()
print("=" * 112)
print(" V1/V2：Γ_实测 vs 解析，以及 ★ Γ 与带宽 w 的关系")
print("=" * 112)
print("  %-16s %6s %9s %6s %7s %13s %13s %8s %10s" %
      ("tag","T(K)","w(nm)","带单元","β","Γ_实测","Γ_解析","实测/解析","c_far"))
print("  " + "-" * 108)
sub = [r for r in rows if abs(r["T"]-1950.0) < 1e-6]
for r in sorted(sub, key=lambda x: -x["w"]):
    print("  %-16s %6.0f %9.3f %6d %7.3f %13.6e %13.6e %8.4f %10.7f" %
          (r["tag"], r["T"], r["w"]*1e9, r["nel"], r["beta"], r["Gm"], r["Gt"],
           r["ratio"], r["cfarm"]))
if len(sub) >= 2:
    gs = [r["Gm"] for r in sub]
    print("  ⇒ ★ Γ 的极差/均值 = %.4f   （判据：应 ~0，即与 w 无关）" %
          ((max(gs)-min(gs))/(sum(gs)/len(gs))))

print()
print("=" * 112)
print(" V3：温度依赖（w = 0.5 nm）—— Γ 应 ∝ K(T)")
print("=" * 112)
print("  %-16s %6s %11s %13s %13s %10s" % ("tag","T(K)","K(T)","Γ_实测","Γ_解析","Γ/K"))
print("  " + "-" * 108)
for r in sorted(rows, key=lambda x: -x["T"]):
    print("  %-16s %6.0f %11.5f %13.6e %13.6e %10.4e" %
          (r["tag"], r["T"], r["K"], r["Gm"], r["Gt"], r["overK"]))

print()
print("=" * 112)
print(" V4：健康与收敛")
print("=" * 112)
print("  %-16s %11s %11s %10s %8s %8s" % ("tag","末步相对变化","c_min","β_max","JIT","未收敛"))
for r in sorted(rows, key=lambda x: x["tag"]):
    print("  %-16s %11.2e %11.7f %10.4f %8d %8d" %
          (r["tag"], r["drift"], r["cmin"], r["bmax"], r["jit"], r["ncv"]))
PY