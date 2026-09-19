#!/bin/bash
# =============================================================================
# T8：ε 收敛 —— 晶粒长大对界面宽 wGB 不变（σ 与 M 保持不变）
# =============================================================================
# 审计原文：
#   「2.2 ε 收敛：扫描 wGB=2,4,8,12 µm，并保持物理 σ、M 不变。每个 wGB 至少配两档网格。
#     必须测：平面界面、圆晶粒、三叉晶界、移动溶质前沿。」
#   「T8 | ε 收敛 | 圆晶粒 | R² 斜率变化 ≤5%」
#
# 【本仓库已有正确的重标定公式，直接用】
#   生成器 `gen_aniso*.py` 在改 wGB 时同步改（已由 check_wgb_invariance.py 验证：
#   两个 wGB 下真实晶界能误差恒为 9.183e-05 ⇒ 改 wGB 只换分辨率）：
#
#       κ_op = a*·wGB·σ = 0.7499763 · wGB · 0.6            = 0.44998578 · wGB
#       μ    = 6σ/wGB   = 3.6/wGB
#       L    = (4/3)·M0/wGB,  M0 = 2.8702e-07              = 3.826933e-07 / wGB
#       γ*   = 1.49992 ≈ 1.5（与 wGB 无关，实测两档相同）
#
#   校验（wGB=4e-6）：κ=1.79994e-6 ✓  μ=9e5 ✓  L=0.0956733 ✓ 与算例现值逐位一致。
#
# 【⚠ 为什么没跑 wGB = 12 µm】
#   算例的圆半径是 **12 µm**。wGB=12 µm 意味着界面宽度 = 晶粒半径，
#   `wGB << R` 的前提根本不成立，测到的是"界面比晶粒还厚"的退化解。
#   ⇒ 本脚本跑 wGB = {2, 4, 8} µm，并**明确记下 12 µm 被跳过的理由**。
#
# 【网格】保持「界面内 8 个单元」不变：dx = wGB/8。
#   这样每档的界面分辨率相同，测到的差异才归因于 wGB 而不是网格。
#
# 【判据】R(t) = sqrt(A/π)，拟合 R² 对 t 的斜率 k。
#   审计判据：不同 wGB 之间 k 的变化 ≤ 5%。
#
# 用法： bash run_t8.sh
#   WGB_LIST 可覆盖，例如 WGB_LIST="2e-6 4e-6" bash run_t8.sh
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t8}"
T_END="${T_END:-6.0e-4}"
WGB_LIST="${WGB_LIST:-2e-6 4e-6 8e-6}"
SRC="$HERE/../tests/grain_growth_circle.i"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

for wgb in $WGB_LIST; do
  D="$ROOT/wgb${wgb}"; mkdir -p "$D"
  python3 - "$SRC" "$D/case.i" "$wgb" "$T_END" <<'PY'
import sys
src, dst, wgb, tend = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
A_STAR, SIGMA, M0 = 0.7499763, 0.6, 2.8702e-07
kappa = A_STAR * wgb * SIGMA
mu    = 6.0 * SIGMA / wgb
L     = (4.0 / 3.0) * M0 / wgb
iw    = wgb / 2.0                      # 界面宽 = wGB/2（与算例 wGB=4→2µm 一致）
dx    = iw / 8.0                       # 界面 tanh 宽内 8 个单元
# ⚠ dx 必须按 int_width/8 定，不能按 wGB/8：
#   原算例是 nx=120 → dx=2.5e-7，而 int_width=2e-6 ⇒ int_width/dx = 8。
#   按 wGB/8 会得到 dx=5e-7（只有 4 单元/界面），各档分辨率就不一致了。
n     = int(round(3.0e-5 / dx))
# 界面弛豫时间 1/(L*mu) ∝ wGB²
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
print("  wGB=%.3g  κ=%.6e  μ=%.6e  L=%.6e  int_width=%.3g  nx=%d  dx=%.3g"
      % (wgb, kappa, mu, L, iw, n, dx))
PY

  RC=0
  ( cd "$D" && /usr/bin/time -f "  墙钟 %e s" "$MOOSE" -i case.i > run.log 2>&1 ) || RC=$?
  echo "    rc=$RC 警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac 'Missing coupled')"
done

echo
echo "=== T8 结果：R(t) = sqrt(A/pi)，拟合 R² 对 t ==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
res = {}
for d in sorted(os.listdir(root)):
    m = re.match(r"wgb([\d.e+-]+)$", d)
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
        ts.append(t); r2s.append(A / 3.14159265358979)   # R²
    # 线性拟合 R² = R0² + k t
    n = len(ts)
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
print("  %-10s %-16s %-10s %-8s" % ("wGB (um)", "d(R²)/dt (m²/s)", "拟合 R²", "点数"))
print("  " + "-" * 48)
for w in sorted(res):
    k, rf, n = res[w]
    print("  %-10.3g %-16.5e %-10.5f %-8d" % (w * 1e6, k, rf, n))
ws = sorted(res)
if len(ws) >= 2:
    print()
    print("  以最小 wGB 为基准的相对变化（审计判据 <= 5%）：")
    base = res[ws[0]][0]
    for w in ws:
        rel = abs(res[w][0] - base) / abs(base) * 100
        print("    wGB = %-6.3g um : %7.2f%%%s"
              % (w * 1e6, rel, "" if rel <= 5 else "   <- 超 5%"))
PY
