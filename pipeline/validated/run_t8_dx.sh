#!/bin/bash
# =============================================================================
# T8b：在**固定 wGB** 下扫网格 —— 生产网格（dx = 1 µm）到底够不够？
# =============================================================================
#
# 为什么单独做这一个：`run_t8.sh` 扫的是 wGB，且**始终**保持
#     dx = int_width/8 = wGB/16
# 也就是"每档界面分辨率相同"。它回答的是"ε 误差是不是 wGB 的物理性质"。
#
# 但**生产网格不是这个标度**：生产 wGB = 4 µm、dx = 1 µm，即 dx = wGB/4 ——
# 比 T8 的标度**粗 4 倍**。于是有一个 T8 没回答的问题：
#
#     在 wGB = 4 µm 下，dx 一路放到 1 µm，R² 斜率还稳得住吗？
#
# 这正是 `run_nonad_prod.sh` 每次都在打的那条警告：
#     平衡界面宽 w = sqrt(κ/µ) = 0.354·wGB = 1.414 µm，而 dx = 1 µm
#     ⇒ 只有 1.41 个单元/界面宽，Ση² 最大冲到 1.14（解析上界是 1）。
#
# 判据：以最细网格为基准，斜率相对变化 ≤ 5%（与 T8 同判据）。
#   * 若 dx = 1 µm 仍在 5% 内 ⇒ 生产网格可以接受，欠解析只影响 Ση² 那条判据；
#   * 若超出 ⇒ 要么加密网格（代价见下），要么在文档里把这条限制写清楚。
#
# 代价标度（固定 wGB、固定域）：单元数 ∝ 1/dx²，时间步数不变
#   ⇒ 墙钟 ∝ 1/dx²。dx 从 1.0 减到 0.25 ⇒ 16 倍。
#
# 用法： bash run_t8_dx.sh
#   WGB=4e-6 DX_LIST="0.25e-6 0.5e-6 1.0e-6" bash run_t8_dx.sh
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t8dx}"
T_END="${T_END:-6.0e-4}"
WGB="${WGB:-4e-6}"
DX_LIST="${DX_LIST:-0.25e-6 0.5e-6 1.0e-6 2.0e-6}"
SRC="$HERE/../tests/grain_growth_circle.i"
TMO="${TMO:-3600}"          # 每个算例最多 60 分钟

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

echo "固定 wGB = $(python3 -c "print($WGB*1e6)") um，域 30x30 um，t_end = $T_END"
echo

for dx in $DX_LIST; do
  D="$ROOT/dx${dx}"; mkdir -p "$D"
  python3 - "$SRC" "$D/case.i" "$WGB" "$T_END" "$dx" <<'PY'
import sys
src, dst, wgb, tend, dx = (sys.argv[1], sys.argv[2], float(sys.argv[3]),
                           float(sys.argv[4]), float(sys.argv[5]))
A_STAR, SIGMA, M0 = 0.7499763, 0.6, 2.8702e-07
kappa = A_STAR * wgb * SIGMA
mu    = 6.0 * SIGMA / wgb
L     = (4.0 / 3.0) * M0 / wgb
iw    = wgb / 2.0
n     = int(round(3.0e-5 / dx))
scale2 = (wgb / 4.0e-6) ** 2

t = open(src, encoding="utf-8").read()

def rep(old, new, cnt=1):
    global t
    c = t.count(old)
    if c != cnt:
        sys.exit("错误：%r 匹配 %d 次，期望 %d 次" % (old[:60], c, cnt))
    t = t.replace(old, new)

rep("  nx = 120", "  nx = %d" % n)
rep("  ny = 120", "  ny = %d" % n)
rep("    int_width = 2.0e-6", "    int_width = %.6e" % iw, 2)
rep("    prop_values = '0.095673 1.8e-6    1.5          9.0e5'",
    "    prop_values = '%.6e %.6e    1.5          %.6e'" % (L, kappa, mu))
rep("  end_time = 6.0e-4", "  end_time = %.6e" % tend)
rep("  dtmax = 2.0e-6", "  dtmax = %.6e" % (2.0e-6 * scale2))
rep("    dt = 2.0e-7", "    dt = %.6e" % (2.0e-7 * scale2))

open(dst, "w", encoding="utf-8", newline="").write(t)
# 平衡界面宽 w = sqrt(kappa/mu) —— 判据里说的"每界面宽几个单元"用的是它，
# **不是** int_width（int_width = wGB/2 = 1.414·w）。
w = (kappa / mu) ** 0.5
print("  dx=%.4g um  nx=%d  dx/int_width=%.2f  **w/dx=%.2f**"
      % (dx * 1e6, n, dx / iw, w / dx))
PY

  RC=0
  ( cd "$D" && /usr/bin/time -f "  墙钟 %e s" timeout "$TMO" "$MOOSE" -i case.i > run.log 2>&1 ) || RC=$?
  echo "    rc=$RC"
done

echo
echo "=== T8b 结果：R(t) = sqrt(A/pi)，拟合 R² 对 t ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
res = {}
for d in sorted(os.listdir(root)):
    m = re.match(r"dx([\d.e+-]+)$", d)
    if not m:
        continue
    f = os.path.join(root, d, "case_out.csv")
    if not os.path.exists(f):
        continue
    r = list(csv.DictReader(open(f)))
    if len(r) < 8 or "area" not in r[0]:
        continue
    ts, r2s = [], []
    for x in r:
        try:
            t = float(x["time"]); A = float(x["area"])
        except (KeyError, ValueError):
            continue
        if A <= 0:
            continue
        ts.append(t); r2s.append(A / 3.14159265358979)
    n = len(ts)
    if n < 3:
        continue
    mx, my = sum(ts) / n, sum(r2s) / n
    sxx = sum((a - mx) ** 2 for a in ts)
    sxy = sum((a - mx) * (b - my) for a, b in zip(ts, r2s))
    if sxx == 0:
        continue
    k = sxy / sxx
    inter = my - k * mx
    ss_tot = sum((b - my) ** 2 for b in r2s)
    ss_res = sum((b - (inter + k * a)) ** 2 for a, b in zip(ts, r2s))
    R2fit = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    res[float(m.group(1))] = (k, R2fit, n)

if not res:
    sys.exit("没有可用结果")
print("  %-12s %-16s %-10s %-8s" % ("dx (um)", "d(R²)/dt (m²/s)", "拟合 R²", "点数"))
print("  " + "-" * 50)
for w in sorted(res):
    k, rf, n = res[w]
    print("  %-12.4g %-16.5e %-10.5f %-8d" % (w * 1e6, k, rf, n))
ws = sorted(res)
if len(ws) >= 2:
    print()
    print("  以最细网格为基准（审计判据 <= 5%）：")
    base = res[ws[0]][0]
    for w in ws:
        rel = abs(res[w][0] - base) / abs(base) * 100
        tag = ""
        if abs(w - 1.0e-6) < 1e-12:
            tag = "   <- 生产网格" + ("" if rel <= 5 else "  **超 5%**")
        elif rel > 5:
            tag = "   <- 超 5%"
        print("    dx = %-8.4g um : %7.2f%%%s" % (w * 1e6, rel, tag))
PY
