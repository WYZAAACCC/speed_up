#!/bin/bash
# 探针 B：驱动晶界稳态迁移 + 解析正对照 v = 1.5*L*Df*sqrt(2k/mu)
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_probe_driven_gb.py" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_probeB}"
ROOT="${ROOT:-/root/work/probeB}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gibbs/gibbs-opt}"
rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"
# tag  Df
CASES=( "df0 0" "df1e3 1.0e3" "df1e4 1.0e4" )
if [ -n "${CASES_OVERRIDE:-}" ]; then IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"; fi
echo "============ 探针 B：驱动晶界稳态迁移 ============"
for spec in "${CASES[@]}"; do
  set -- $spec; tag=$1; df=$2
  D="$ROOT/$tag"; mkdir -p "$D"; cd "$D"
  timeout 300 python3 "$HERE/make_probe_driven_gb.py" --out gb.i \
     --df "$df" --ldom 40e-9 --nx 320 --wint 1.0e-9 \
     --kappa 5.0e-13 --mu 1.0e6 --l-mob 0.6667 \
     --t-end 1.0e-3 --n-steps 4000 > gen.log 2>&1 || { echo "$tag 生成失败"; tail -3 gen.log; continue; }
  timeout 1800 "$MOOSE" -i gb.i > run.log 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag 运行失败 rc=$rc"
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
import csv, json, math, os, sys
root = sys.argv[1]
rows = []
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p): continue
    try:
        m = json.load(open(os.path.join(p, "params.json"), encoding="utf-8"))
        r = list(csv.DictReader(open(os.path.join(p, "gb_out.csv"))))
    except Exception as e:
        print("  %-8s 读失败 %s" % (d, e)); continue
    if len(r) < 5: continue
    # 取中后段做线性拟合（跳过初始瞬态）
    t = [float(x["time"]) for x in r]; x = [float(x["xI"]) for x in r]
    n = len(t); i0 = n // 4
    ts, xs = t[i0:], x[i0:]
    nf = len(ts); mt = sum(ts)/nf; mx = sum(xs)/nf
    sxx = sum((a-mt)**2 for a in ts); sxy = sum((a-mt)*(b-mx) for a, b in zip(ts, xs))
    v = sxy/sxx if sxx else 0.0
    # 拟合残差（线性度）
    ss = sum((b-(mx+v*(a-mt)))**2 for a, b in zip(ts, xs))
    st = sum((b-mx)**2 for b in xs) or 1e-30
    R2 = 1.0 - ss/st
    a0 = math.sqrt(2*m["kappa"]/m["mu"])
    vth = 1.5*m["L"]*m["df"]*a0
    jit = int((open(os.path.join(p,"jit.txt")).read().strip() or "1"))
    ncv = int((open(os.path.join(p,"nconv.txt")).read().strip() or "1"))
    emax = float(r[-1]["eta_max"]); emin = float(r[-1]["eta_min"])
    rows.append(dict(tag=d, df=m["df"], v=v, vth=vth, a=a0, R2=R2,
                     jit=jit, ncv=ncv, emax=emax, emin=emin,
                     dx0=x[0], dxn=x[-1]))
print()
print("=" * 100)
print(" 判据：v 恒定（线性拟合 R²）+ v 与解析 v=1.5·L·Δf·a 一致")
print("=" * 100)
print("  %-8s %10s %13s %13s %9s %9s %9s %8s %6s %6s" %
      ("tag","Df","v_实测","v_解析","实测/解析","R²","界面位移","η范围","JIT","未收敛"))
print("  " + "-" * 96)
for r in sorted(rows, key=lambda x: x["df"]):
    print("  %-8s %10.3g %13.4e %13.4e %9.3f %9.5f %9.3g %8s %6d %6d" %
          (r["tag"], r["df"], r["v"], r["vth"], (r["v"]/r["vth"] if r["vth"] else float("nan")),
           r["R2"], r["dxn"]-r["dx0"], "[%.2f,%.2f]" % (r["emin"], r["emax"]), r["jit"], r["ncv"]))
print()
print("  a = sqrt(2κ/μ) = %.3g m（界面宽）" % (rows[0]["a"] if rows else 0))
print("  ⇒ Df=0 档 v 应 ≈ 0（正对照）；v/Df 应恒定（线性）")
if len(rows) >= 2:
    nz = [r for r in rows if r["df"] > 0]
    if len(nz) >= 2:
        print("  ⇒ v/Df = %s" % ["%.4e" % (r["v"]/r["df"]) for r in sorted(nz, key=lambda x: x["df"])])
PY