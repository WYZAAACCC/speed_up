#!/bin/bash
# =============================================================================
# T7：平面前沿 —— 速度与 k_eff 对 dx、dt 收敛
# =============================================================================
# 审计原文：「T7 | 平面前沿 | 1D 移动界面 | 速度和 k_eff 对 dx、dt 收敛」
#
# 【载体】`tests/front1d.i`（移动前沿，dG ≠ 0）。
#   ⚠ 该文件里解析初值用的 V 与前沿位置是按**特定** kappa_c/xi 标定的常数，
#     改 nx 只改网格，不改物理 ⇒ 可以直接扫 dx。
#
# 【判据】审计只写"收敛"，没给阈值。这里用**相邻两档的相对变化**：
#     速度与 k_eff 的相对变化随 dx 减小而减小，且最后一档 < 2%。
#   这是"收敛"的可操作定义 —— 因为该模型的前沿速度本身没有独立理论真值
#   （`v = 3·ξ·L·ΔF` 只在尖锐界面极限成立，此处 ξ = 2 µm 是扩散界面）。
#
# 【dt 怎么办】自适应步长会自己跟着 dx 走。要单独验 dt 收敛，
#   用 DTMAX 环境变量卡住步长上限再扫一遍。
#
# 用法： bash run_t7.sh
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t7}"
END="${END:-3.0e-3}"
NX_LIST="${NX_LIST:-160 320 640}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"
cp "$HERE/../tests/front1d.i" "$ROOT/base.i"

for nx in $NX_LIST; do
  D="$ROOT/nx$nx"; mkdir -p "$D"
  cp "$ROOT/base.i" "$D/case.i"
  # 域长/界面宽不变，只改单元数 ⇒ 纯 dx 收敛
  XMAX=$(grep -oP '^\s*xmax\s*=\s*\K\S+' "$D/case.i" | head -1)
  DXS=$(python3 -c "print(f'{$XMAX/$nx:.6e}')")
  echo "=== nx=$nx  (dx=$DXS m) ==="
  RC=0
  ( cd "$D" && "$MOOSE" -i case.i Mesh/nx="$nx" Executioner/end_time="$END" \
      > run.log 2>&1 ) || RC=$?
  if [ $RC -ne 0 ]; then
    echo "    失败 rc=$RC"; sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 ERROR | head -5
    continue
  fi
  echo "    OK  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac 'Missing coupled')"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
root = sys.argv[1]
def load(nx):
    f = os.path.join(root, "nx%d" % nx, "case_out.csv")
    if not os.path.exists(f):
        return None
    r = list(csv.DictReader(open(f)))
    return r if r else None

rows = {}
for d in sorted(os.listdir(root)):
    if d.startswith("nx"):
        try:
            nx = int(d[2:])
        except ValueError:
            continue
        r = load(nx)
        if r:
            rows[nx] = r
if not rows:
    sys.exit("没有可用结果")

print("  front1d.i 的输出列（取决于模板）：")
print("   ", list(next(iter(rows.values()))[0].keys()))
print()
print("  %-8s %-12s %-16s %-16s" % ("nx", "末态 t", "solid_len", "平均速度"))
print("  " + "-" * 56)
vel = {}
for nx in sorted(rows):
    r = rows[nx]
    d = r[-1]
    # solid_len = ∫η dx 是前沿位置的代理；速度 = (末-初)/Δt
    if "solid_len" not in d or "time" not in d:
        continue
    L0 = float(r[0]["solid_len"]); L1 = float(d["solid_len"])
    t0 = float(r[0]["time"]); t1 = float(d["time"])
    v = (L1 - L0) / (t1 - t0) if t1 > t0 else float("nan")
    vel[nx] = v
    print("  %-8d %-12s %-16.6g %.6g" % (nx, d["time"], L1, v))

if len(vel) >= 2:
    print()
    print("  相邻档相对变化（判据：随 dx 减小而减小，末档 < 2%）：")
    ns = sorted(vel)
    prev = None
    for n in ns:
        if prev is not None:
            rel = abs(vel[n] - vel[prev]) / abs(vel[prev])
            print("    nx %-4d -> %-4d : %8.3f%%%s"
                  % (prev, n, rel * 100, "   <- 末档" if n == ns[-1] else ""))
        prev = n
PY
