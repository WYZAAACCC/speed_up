#!/bin/bash
# =============================================================================
# T11：晶界过剩 Γ_GB 对 dx 与 w_gb 的收敛性
# =============================================================================
# 审计原文：
#   「T11 | 晶界过剩 | 1D 固固晶界 | Γ_GB 对 dx、wGB 收敛」
#   「判据：Γ_GB 对 dx、wGB 收敛」—— 注意判据是**收敛**，不是"等于某个值"。
#   晶界过剩本身是模型的一个输出，没有独立的理论真值可直接比；
#   能验的是它**随离散参数收敛**，那才说明 Γ_GB 是模型的性质而不是网格的产物。
#
# 用法： bash run_t11.sh
# =============================================================================
# ⚠ 不要开 set -u：conda 的 activate 脚本引用了未定义的 $CONDA_BUILD，
#   开了 set -u 会在 conda activate 那一步直接退出（实测踩过，脚本静默什么都不做）。
set +u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t11}"
T_END="${T_END:-30.0}"
# ⚠ 域长必须跟着 w_gb 放大。tanh 剖面在 ±3.5·w_gb 处才基本回到体相值，
#   若域半长 < 3.5·w_gb，"晶粒内"就不纯（实测 w_gb=0.8 µm、ldom=4 µm 时
#   D_in_grain 是 D_S 的 6 倍、hgb_in_grain = 0.005）。
#   ⇒ 扫 w_gb 时必须用 LDOM=1.2e-5 这样的放大域，否则测到的是边界污染。
LDOM="${LDOM:-4.0e-6}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

# (dx, w_gb) 单位 um。两组：固定 w_gb 扫 dx；固定 dx 扫 w_gb。
# ⚠ 必须用数组：`for s in $CASES` 是按**空白分词**而不是按行，
#   多行的 CASES 会被拆成一堆单词（实测踩过，每个 case 被拆成三块）。
# 可用 CASES_OVERRIDE 覆盖，例如只跑放大域的 w_gb 扫描。
if [ -n "${CASES_OVERRIDE:-}" ]; then
  # ⚠ 用 `|` 分隔而不是空白：CASES 的每一项本身含空格（tag dx wgb），
  #   用空白分词会把一项拆成三块。IFS='|' 才能正确切分。
  IFS='|' read -r -a CASES <<< "$CASES_OVERRIDE"
else
  CASES=(
    "dx0.100_w0.400  0.100  0.400"
    "dx0.050_w0.400  0.050  0.400"
    "dx0.025_w0.400  0.025  0.400"
    "dx0.0125_w0.400 0.0125 0.400"
    "dx0.025_w0.200  0.025  0.200"
    "dx0.025_w0.800  0.025  0.800"
  )
fi

for spec in "${CASES[@]}"; do
  set -- $spec
  tag=$1; dx=$2; wgb=$3
  D="$ROOT/$tag"
  mkdir -p "$D"
  python3 "$HERE/make_1d_gb.py" --out "$D/gb.i" \
      --dx "${dx}e-6" --wgb "${wgb}e-6" --t-end "$T_END" --ldom "$LDOM" > "$D/gen.log" 2>&1 || {
    echo "$tag: 生成失败"; continue; }
  ( cd "$D" && "$MOOSE" -i gb.i > run.log 2>&1 )
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "$tag: 运行失败 rc=$rc"
    sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 "ERROR" | head -6
    continue
  fi
  nwarn=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac "Missing coupled")
  printf "%-22s dx=%-7s w_gb=%-6s 警告=%s  " "$tag" "$dx" "$wgb" "$nwarn"
  tail -1 "$D/gb_out.csv"
done

echo
echo "=== 汇总：Γ_GB 的收敛性 ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
data = {}
for d in sorted(os.listdir(root)):
    f = os.path.join(root, d, "gb_out.csv")
    if not os.path.exists(f):
        continue
    m = re.match(r"dx([\d.]+)_w([\d.]+)$", d)
    if not m:
        continue
    r = list(csv.DictReader(open(f)))
    if not r:
        continue
    data[d] = (float(m.group(1)), float(m.group(2)), float(r[-1]["gamma_gb"]))

def show(title, rows):
    print()
    print(title)
    print("  %-10s %-10s %14s %14s" % ("dx (um)", "w_gb (um)", "Gamma_GB", "相对上一档"))
    prev = None
    for dx, wgb, g in rows:
        d = "" if prev is None else "%9.2f%%" % ((g - prev) / prev * 100)
        print("  %-10s %-10s %14.5e %14s" % (dx, wgb, g, d))
        prev = g

if data:
    wvals = sorted({v[1] for v in data.values()})
    dvals = sorted({v[0] for v in data.values()})
    if len(dvals) > 1:
        wfix = max(set(v[1] for v in data.values()), key=lambda w: sum(1 for v in data.values() if v[1] == w))
        show("固定 w_gb = %g um，扫 dx（判据：dx 变小时变化应趋于 0）" % wfix,
             sorted([v for v in data.values() if v[1] == wfix], key=lambda v: -v[0]))
    if len(wvals) > 1:
        dfix = max(set(v[0] for v in data.values()), key=lambda d: sum(1 for v in data.values() if v[0] == d))
        show("固定 dx = %g um，扫 w_gb（判据：Γ_GB 应稳定，不应正比于 w_gb）" % dfix,
             sorted([v for v in data.values() if v[0] == dfix], key=lambda v: v[1]))
PY
