#!/bin/bash
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_2d_gb_slab.py" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_g2d}"
ROOT="${ROOT:-/root/work/g2dref}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gibbs/gibbs-opt}"
rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"
CASES=(
  "res4    4.0"
  "res2    2.0"
  "res8    8.0"
)
if [ -n "${CASES_OVERRIDE:-}" ]; then IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"; fi
echo "==================== G1-2D：晶界面电导 δ·D_GB ===================="
for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; res=$2
  D="$ROOT/$tag"; mkdir -p "$D"; cd "$D"
  timeout 600 python3 "$HERE/make_2d_gb_slab.py" --out gb2d.i --res "$res" \
      --t-end 1.0e-4 > gen.log 2>&1 || { echo "$tag 生成失败"; tail -3 gen.log; continue; }
  echo "--- $tag 开始（$(grep -o '单元 [0-9]*' gen.log)）---"
  timeout 3000 "$MOOSE" -i gb2d.i > run.log 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A5 -m1 '\*\*\* ERROR' | head -6
    continue
  fi
  mkdir -p "$SAVE/$tag"; cp -f gb2d.i gen.log run.log gb2d_out.csv params.json "$SAVE/$tag/" 2>/dev/null
  grep -c 'JIT compile failed' run.log > "$SAVE/$tag/jit.txt"
  grep -c 'Solve Did NOT Converge' run.log > "$SAVE/$tag/nconv.txt"
  echo "$tag 完成"
  cd "$ROOT"
done
echo
python3 - "$SAVE" <<'PY'
import csv, json, os, sys
root = sys.argv[1]
rows = []
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p): continue
    try:
        m = json.load(open(os.path.join(p, "params.json"), encoding="utf-8"))
        r = list(csv.DictReader(open(os.path.join(p, "gb2d_out.csv"))))
    except Exception as e:
        print("  %-8s 读失败 %s" % (d, e)); continue
    if not r: continue
    last = r[-1]
    fin = float(last["flux_in"]); fout = float(last["flux_out"])
    dmin = float(last["D_min"]); dmax = float(last["D_max"])
    jit = int((open(os.path.join(p,"jit.txt")).read().strip() or "1"))
    ncv = int((open(os.path.join(p,"nconv.txt")).read().strip() or "1"))
    # 基准（纯体相，无晶界）：j_bulk = D_S*(c_hi-c_lo)/Ly*W
    jbulk = m["D_S"] * (m["c_hi"] - m["c_lo"]) / m["ly"] * m["W"]
    Rm = abs(fin) / jbulk
    # 反解 δ·D_GB:  R = 1 + (D_GB-D_S)*δ/(D_S*W)  ⇒  D_GB*δ = (R-1)*D_S*W + D_S*δ
    triple_m = (Rm - 1.0) * m["D_S"] * m["W"] + m["D_S"] * m["delta"]
    rows.append(dict(tag=d, res=m["res"], ncell=m["ncell"], rth=m["R_theory"],
                     Rm=Rm, tth=m["triple_theory"], tm=triple_m,
                     fin=fin, fout=fout, dmin=dmin, dmax=dmax, jit=jit, ncv=ncv))
print()
print("=" * 108)
print(" 判据：增强比 R 实测 vs 解析；并反解 δ·D_GB")
print("=" * 108)
print("  %-8s %6s %9s %11s %11s %9s %13s %13s %8s" %
      ("tag","δ/dx","单元数","R_实测","R_解析","R偏差","δ·D_GB实测","δ·D_GB解析","比值"))
print("  " + "-" * 104)
for r in sorted(rows, key=lambda x: x["res"]):
    print("  %-8s %6.1f %9d %11.4f %11.4f %8.2f%% %13.5e %13.5e %8.4f" %
          (r["tag"], r["res"], r["ncell"], r["Rm"], r["rth"],
           (r["Rm"]-r["rth"])/r["rth"]*100, r["tm"], r["tth"], r["tm"]/r["tth"]))
print()
print("  %-8s %13s %13s %10s %10s %6s %8s" % ("tag","flux_in","flux_out","D_min","D_max","JIT","未收敛"))
for r in sorted(rows, key=lambda x: x["res"]):
    print("  %-8s %13.5e %13.5e %10.3e %10.3e %6d %8d" %
          (r["tag"], r["fin"], r["fout"], r["dmin"], r["dmax"], r["jit"], r["ncv"]))
print()
print("  ⇒ 若 R 随 δ/dx 增大而收敛到解析值 ⇒ 判据通过（'能解析出 δ·D_GB'）")
PY