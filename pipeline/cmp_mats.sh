#!/bin/bash
# 判定 AD 版与非 AD 版的材料值是否**逐点**相同。
#
# 背景：两个版本的 [Mesh]/[ICs]/[Functions]/[UserObjects] 已证实无差异，
# 所以 t=0 状态相同，R(u_IC) 应当逐位相同。但实测差 4.6%，且逐变量差异
# 不是整体缩放而是重新分配 -> 指向 L / align4 的逐点值不同。
#
# 之前只比过 max/min 极值 —— **极值相同不等于逐点相同**（两个不同函数可共享极值）。
# 本次比**全域积分**：若积分逐位相同，则逐点值几乎必然相同（强证据）；
# 若不同，就直接定位到是哪个材料。
#
# 用 ADElementIntegralMaterialProperty 对 kappa_op / gamma_asymm / L / align4 求积分。
# end_time=0 -> 只做初值求值，几秒钟。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/cmp_mat
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

for src in base_ad base_nonad; do
  mkdir -p "$src"
  cp "/root/work/s1d_full/$src.i" "$src/x.i"
  cp /root/work/s1d_full/columnar_seeds.csv "$src/"
done

python3 - <<'PY'
import re
diag = []
for prop in ("kappa_op", "gamma_asymm", "L", "align4"):
    diag.append(f"""  [I_{prop}]
    type = ADElementIntegralMaterialProperty
    mat_prop = {prop}
    execute_on = 'initial'
  []
""")
diag = "".join(diag)
for src in ("base_ad", "base_nonad"):
    p = f"{src}/x.i"
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"^  end_time = .*$", "  end_time = 0", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 1", s, flags=re.M)
    i = s.index("\n[Postprocessors]\n") + len("\n[Postprocessors]\n")
    s = s[:i] + diag + s[i:]
    open(p, "w", encoding="utf-8").write(s)
    print(f"  {p} 已加积分后处理")
PY

for src in base_ad base_nonad; do
  ( cd "$src" && setsid --wait "$MOOSE" -i x.i > run.log 2>&1; echo "$src rc=$?" ) &
done
wait

echo
echo "================ 材料全域积分对比 ================"
for src in base_nonad base_ad; do
  echo "--- $src ---"
  head -1 "/root/work/cmp_mat/$src/x_out.csv" 2>/dev/null | tr ',' '\n' | sed 's/^/    /'
  sed -n 2p "/root/work/cmp_mat/$src/x_out.csv" 2>/dev/null | tr ',' '\n' | sed 's/^/    /'
  grep -a -m2 -E '\*\*\* ERROR|Aborting' "/root/work/cmp_mat/$src/run.log" 2>/dev/null | sed 's/^/    /'
done

echo
echo "================ 判定 ================"
python3 - <<'PY'
import csv, os
def load(tag):
    p = f"/root/work/cmp_mat/{tag}/x_out.csv"
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    return rows[-1] if rows else None
a, b = load("base_nonad"), load("base_ad")
if not a or not b:
    print("  拿不到数据")
else:
    worst = 0.0
    for k in sorted(set(a) & set(b)):
        if k == "time":
            continue
        try:
            va, vb = float(a[k]), float(b[k])
        except ValueError:
            continue
        den = max(abs(va), abs(vb), 1e-300)
        rel = abs(va - vb) / den
        worst = max(worst, rel)
        flag = "  <== 不同！" if rel > 1e-10 else ""
        print(f"  {k:22} 非AD={va:.12e}  AD={vb:.12e}  相对差={rel:.3e}{flag}")
    print()
    print(f"  最大相对差 = {worst:.3e}")
    print("  ==> " + ("材料逐点相同（积分逐位一致）-> 差异在残差装配层面，不在材料"
                      if worst < 1e-10 else
                      "**材料逐点不同 -> 定位成功，这就是 4.6% 的来源**"))
PY
