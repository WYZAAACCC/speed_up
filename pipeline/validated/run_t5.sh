#!/bin/bash
# =============================================================================
# T5：kappa_c 极限 —— 每档**至少两种 dx**
# =============================================================================
# 审计原文：
#   「2.1 kappa_c 极限：比较 1e-11, 1e-13, 1e-14, 1e-15, 0。对于每档至少使用两种 dx。」
#   「T5 | kappa_c 极限 | 静止平界面 | k_eff 对继续减小 kappa_c 收敛；不得只看单档」
#   「如果 kappa_c=0 可稳定工作，优先将溶质方程改为守恒二阶扩散形式，
#     减少四阶刚性和一个变量 w。」
#
# 【为什么要两种 dx】
#   kappa_c 决定 c 自己的界面宽 w_c = sqrt(kappa_c/f_cc)。
#   审计 P23 的核心担忧正是 **w_c 比 dx 小一个数量级**（w_c ≈ 0.105 µm，dx = 1 µm）。
#   只跑一种 dx，"k_eff 随 kappa_c 收敛"这句话就无法与"网格是否解析了 w_c"区分开。
#   ⇒ 至少取一个**解析 w_c** 的 dx 和一个**不解析**的 dx。
#
# 用法： bash run_t5.sh
#   DX_LIST 可覆盖，例如 DX_LIST="0.5e-6 0.1e-6" bash run_t5.sh
# =============================================================================
set +u   # conda 的 activate 脚本引用未定义的 $CONDA_BUILD，不能开 set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t5}"
DX_LIST="${DX_LIST:-0.5e-6 0.1e-6}"
KC_LIST="${KC_LIST:-1.125e-11 1e-13 1e-14 1e-15 0}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

for kc in $KC_LIST; do
  for dx in $DX_LIST; do
    tag="kc${kc}_dx${dx}"
    D="$ROOT/$tag"; mkdir -p "$D"
    # ⚠ kappa_c = 0 时 DerivativeParsedMaterial 里会出现 0/0 风险，先试；失败就记下来
    if ! python3 "$HERE/make_1d_static.py" --out "$D/case.i" \
            --kc "$kc" --dx "$dx" > "$D/gen.log" 2>&1; then
      echo "$tag: 生成失败"; continue
    fi
    ( cd "$D" && "$MOOSE" -i case.i > run.log 2>&1 )
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "$tag: 运行失败 rc=$rc"
      sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 "ERROR" | head -5
      continue
    fi
    printf "%-28s " "$tag"
    tail -1 "$D/case_out.csv"
  done
done

echo
echo "=== 汇总：k_eff = c_solid / c_max，理论值 0.6302521008 ==="
python3 - "$ROOT" "$KC_LIST" "$DX_LIST" <<'PY'
import csv, os, sys
root, kcs, dxs = sys.argv[1], sys.argv[2].split(), sys.argv[3].split()
THEORY = 0.9 / (0.9 + 2 * 0.264)
print()
print("  %-12s" % "kappa_c" + "".join("%22s" % ("dx=" + d) for d in dxs) + "   w_c (um)")
print("  " + "-" * (12 + 22 * len(dxs) + 12))
for kc in kcs:
    row = ""
    for dx in dxs:
        f = os.path.join(root, "kc%s_dx%s" % (kc, dx), "case_out.csv")
        if not os.path.exists(f):
            row += "%22s" % "--"
            continue
        r = list(csv.DictReader(open(f)))
        if not r:
            row += "%22s" % "--"
            continue
        cs = float(r[-1]["c_solid"]); cl = float(r[-1]["c_max"])
        keff = cs / cl
        row += "%14.8f(%5.2f%%)" % (keff, (keff - THEORY) / THEORY * 100)
    import math
    wc = math.sqrt(float(kc) / 0.9) * 1e6 if float(kc) > 0 else 0.0
    print("  %-12s" % kc + row + "   %8.4f" % wc)
print()
print("  括号里是相对理论值的偏差（%%）。判据 T4：|偏差| <= 1%%。")
PY
