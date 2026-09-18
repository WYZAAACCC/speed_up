#!/bin/bash
# 跑核序列化自证：CK(手写核) vs CR(未改动 C 版)，材料完全相同，只比首步残差。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_ker

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
for f in stage1_meltpool_c.i columnar_seeds.csv verify_kernels.py; do
  sed 's/\r$//' "/mnt/f/speed_up/pipeline/$f" > "$f"
done
python3 verify_kernels.py || exit 1

for t in CK CR; do
  mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/
done

echo "=== 并行跑 CK / CR ==="
for t in CK CR; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "=== 逐变量残差（iteration 0）对比 ==="
for t in CR CK; do
  echo "--- $t ---"
  grep -a -A12 "individual variables" "/root/work/s1d_ker/$t/run.log" | head -13 | sed 's/^/  /'
done

echo
echo "=== 收敛对比 ==="
for t in CR CK; do
  printf "  %s: 收敛步=%s\n" "$t" "$(grep -ac 'Solve Converged' /root/work/s1d_ker/$t/run.log)"
  echo "     牛顿:"; grep -a "Nonlinear |R|" "/root/work/s1d_ker/$t/run.log" | head -5 | sed 's/^/       /'
  grep -a -m2 -E '\*\*\* ERROR|SUBPC|DIVERGED' "/root/work/s1d_ker/$t/run.log" | sed 's/^/      /'
done

echo
echo "=== 判定 ==="
python3 - <<'PY'
import re
def resid(tag):
    s = open(f"/root/work/s1d_ker/{tag}/run.log", encoding="utf-8", errors="replace").read()
    m = re.search(r"individual variables:\s*\n((?:\s+\S+:\s+\S+\n)+)", s)
    if not m:
        return None
    return {k: float(v) for k, v in re.findall(r"(\S+):\s+([0-9.eE+-]+)", m.group(1))}

a, b = resid("CR"), resid("CK")
if a is None or b is None:
    print("  拿不到残差，无法判定")
else:
    keys = sorted(set(a) & set(b))
    worst = 0.0
    for k in keys:
        if a[k] == 0 and b[k] == 0:
            continue
        denom = max(abs(a[k]), abs(b[k]), 1e-300)
        rel = abs(a[k] - b[k]) / denom
        worst = max(worst, rel)
        if rel > 1e-6:
            print(f"  {k:>6}: CR={a[k]:.6e}  CK={b[k]:.6e}  相对差 {rel:.2e}  <== 不一致")
    print(f"  最大相对差 = {worst:.3e}")
    print("  ==>" + ("核序列化忠实（逐位一致）" if worst < 1e-6
                     else "**核序列化不等价，必须继续修**"))
PY
