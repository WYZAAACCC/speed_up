#!/bin/bash
# =============================================================================
# T13：移动固固晶界上的溶质拖曳
# =============================================================================
# 审计判据：「随浓度/扩散率变化的速度趋势正确；与无溶质对照显著可分」
#
# 量法：**v = d(∫η₀ dx)/dt**。
#   1D 双晶粒里 η₀ + η₁ ≈ 1 处处成立 ⇒ ∫η₀ dx 恰好就是晶界位置（米）。
#   （不去找 η=0.5 的等值线交点 —— 那种做法对离散噪声很敏感，T9 栽过。）
#
# 预期（Cahn 拖曳）：定驱动力下，溶质气氛给晶界一个**反向**的力
#   ⇒ **v 随 c₀ 增大而减小**；c₀ → 0 时回到自由速度 v₀。
#   另设一个 `--no-seg` 对照，看拖曳来自哪条耦合通道。
#
# 用法： bash run_t13.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
# ⚠ 跑在 **ext4**（/root/work）而不是 /mnt/f：MOOSE 的 JIT 会写大量小文件，
#   9p 上慢到不可用（实测同一算例 ext4 11.93 s vs 9p 20+ 分钟，
#   进程状态是 D 不可中断 I/O 等待）。产物跑完再拷回 /mnt/f。
ROOT="${ROOT:-/root/work/t13}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"

# ## ⚠ 两个必须同时满足的时间尺度（第一版就是在这里翻车的）
#
# 1. **界面弛豫时间** τ = 1/(L·μ) ≈ 1.16e-6 s ⇒ `DTMAX` 必须 ≲ τ/4。
#    第一版设成 t_end/20 = 1e-3，比 τ 大三个数量级。
# 2. **Cahn 拖曳只在 v 低于脱钉速度时才有**，`v_c ≈ D_GB/wGB ≈ 1e-3 m/s`。
#    第一版 F_ext = 1000 ⇒ v ≈ 0.1 m/s，**远在脱钉区之上 ⇒ 溶质来不及拖**：
#    实测三档 c₀ 给出**完全相同**的 v（1.04955e-01）和**完全相同**的末位置
#    （1.9949 µm = 域边界）—— 晶界在三种情况下都撞墙了，测的是饱和值。
#
# ⇒ 现在 F_ext = 1 ⇒ v ≈ 1e-4 m/s（拖曳区中段），域放大到 6 µm 留出行程。
FEXT="${FEXT:-1.0}"
LDOM="${LDOM:-6.0e-6}"
XGB="${XGB:-1.0e-6}"
NX="${NX:-1200}"
T_END="${T_END:-5.0e-3}"
DTMAX="${DTMAX:-2.5e-7}"       # ≲ τ/4
# (标签, c0, 是否关掉偏析项)
CASES=(
  "nosolute   1e-06 no"
  "c0.010     0.010 no"
  "c0.036     0.036 no"
  "c0.070     0.070 no"
  "noseg      0.036 yes"
)

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

for spec in "${CASES[@]}"; do
  set -- $spec
  TAG=$1; C0=$2; NOSEG=$3
  D="$ROOT/$TAG"; mkdir -p "$D"; cd "$D"
  EXTRA=""; [ "$NOSEG" = "yes" ] && EXTRA="--no-seg"
  # shellcheck disable=SC2086
  python3 "$HERE/make_1d_drag.py" --out drag.i --c0 "$C0" --fext "$FEXT" \
      --ldom "$LDOM" --xgb "$XGB" --nx "$NX" \
      --t-end "$T_END" --dtmax "$DTMAX" $EXTRA > gen.log 2>&1 \
    || { echo "  $TAG 生成失败"; tail -3 gen.log; continue; }
  timeout 7200 "$MOOSE" -i drag.i > run.log 2>&1 || true
  printf "  %-14s 末步：%s\n" "$TAG" "$(grep -a '^Time Step' run.log | tail -1)"
  cd "$ROOT"
done

echo
echo "=== T13 结果：定驱动力 F_ext=$FEXT 下的晶界速度 ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
print("  %-16s %-14s %-16s %-10s" % ("算例", "c0", "v (m/s)", "拟合 R²"))
print("  " + "-" * 62)
rows = []
for d in sorted(os.listdir(root)):
    f = os.path.join(root, d, "drag_out.csv")
    if not os.path.exists(f):
        continue
    r = list(csv.DictReader(open(f)))
    ts, xs = [], []
    for x in r:
        try:
            t = float(x["time"]); g = float(x["gb_pos"])
        except (KeyError, ValueError):
            continue
        ts.append(t); xs.append(g)
    if len(ts) < 5:
        continue
    # 丢掉最初 20%（初始 transient），线性拟合剩下的
    k = max(1, len(ts) // 5)
    ts, xs = ts[k:], xs[k:]
    n = len(ts)
    mx, my = sum(ts) / n, sum(xs) / n
    sxx = sum((a - mx) ** 2 for a in ts)
    sxy = sum((a - mx) * (b - my) for a, b in zip(ts, xs))
    if sxx == 0:
        continue
    v = sxy / sxx
    inter = my - v * mx
    ss_tot = sum((b - my) ** 2 for b in xs)
    ss_res = sum((b - (inter + v * a)) ** 2 for a, b in zip(ts, xs))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    c0 = d.replace("c0", "").split("_")[0]
    rows.append((d, c0, v, r2))

base = next((v for d, c0, v, r2 in rows if d == "nosolute"), None)
for d, c0, v, r2 in rows:
    if d == "nosolute":
        print("  %-16s %-14s %-16.5e %-10.5f   （基准 = 无溶质）" % (d, c0, v, r2))
    elif d == "noseg":
        print("  %-16s %-14s %-16.5e %-10.5f   （关掉偏析项的对照）" % (d, c0, v, r2))
    else:
        rel = (v - base) / abs(base) * 100 if base else 0
        print("  %-16s %-14s %-16.5e %-10.5f   %+.2f%% vs 无溶质" % (d, c0, v, r2, rel))
print()
print("判读：")
print("  * 定驱动力下 v 应随 c0 **单调下降**（Cahn 拖曳）")
print("  * c0=0.001 那档接近自由速度 v0；与高浓度档应**显著可分**")
print("  * 对照 `_noseg` 用来看拖曳来自偏析项还是分配项")
PY
