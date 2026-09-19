#!/bin/bash
# =============================================================================
# T14b：把 AMR 测试挪到**移动前沿**算例上
# =============================================================================
# 【为什么需要这个 —— 1D 静态界面**本质上测不到粗化**】
#
# `run_t14.sh` 用的是 1D 静态界面（`make_1d_static.py`）。实测发现：
#
#     refine（只加密）与 both（加密+粗化）的输出 **逐字节相同**
#
# 原因不是配置写错，而是**构型本身决定的**：
#   界面不动 ⇒ 精化区不动 ⇒ 没有任何 level-1 单元"不再需要精化"
#   ⇒ 没有可粗化的对象。
#
# ⇒ 要真正测「加密+粗化」，必须用**界面在动**的算例。
#   本脚本用 `tests/front1d.i`（移动前沿）：它有守恒量 `total_c`，
#   且前沿以 ~1.2e-3 m/s 推进 ⇒ 精化区跟着走 ⇒ 尾巴上的单元会被粗化。
#
# 【判据】
#   守恒漂移 ≤ 1e-8；前沿速度与 k_eff 相对 uniform 的变化 ≤ 5%。
#
# 【⚠ 注意】不要在本脚本运行期间编辑它 —— bash 是增量读取脚本的，
#   跑到一半被改会报 `syntax error near unexpected token`。
#   （`run_t14.sh` 就是这么坏过一次。）
#
# 用法： bash run_t14_moving.sh
# =============================================================================
set +u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t14b}"
END="${END:-2.0e-3}"
SRC="$HERE/../tests/front1d.i"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

[ -f "$SRC" ] || { echo "找不到 $SRC"; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"

# --- 自适应块 ---
ADAPT_REFINE='
[Adaptivity]
  marker = marker
  interval = 5
  max_h_level = 2
  [Indicators]
    [jump]
      type = GradientJumpIndicator
      variable = eta
    []
  []
  [Markers]
    [marker]
      type = ErrorFractionMarker
      indicator = jump
      refine = 0.7
      coarsen = 0
    []
  []
[]
'

ADAPT_BOTH='
[Adaptivity]
  marker = marker
  interval = 5
  max_h_level = 2
  [Indicators]
    [jump]
      type = GradientJumpIndicator
      variable = eta
    []
  []
  [Markers]
    [marker]
      type = ErrorFractionMarker
      indicator = jump
      refine = 0.7
      coarsen = 0.3
    []
  []
[]
'

mk() {
  local tag=$1 block=$2
  local D="$ROOT/$tag"; mkdir -p "$D"
  cp "$SRC" "$D/case.i"
  [ -n "$block" ] && printf '%s\n' "$block" >> "$D/case.i"
}

mk uniform ""
mk refine  "$ADAPT_REFINE"
mk both    "$ADAPT_BOTH"

echo "三个变体已生成（uniform / refine / both），都基于 tests/front1d.i"
echo "end_time = $END"
echo

for tag in uniform refine both; do
  D="$ROOT/$tag"
  echo "=== 跑 [$tag] ==="
  RC=0
  ( cd "$D" && timeout 2400 "$MOOSE" -i case.i Executioner/end_time="$END" \
      > run.log 2>&1 ) || RC=$?
  echo "    退出码=$RC  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac 'Missing coupled')"
  if [ $RC -ne 0 ]; then
    sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 "ERROR" | head -6
  fi
done

echo
echo "=== 对比 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/validated")
try:
    from robust_csv import read_rows
except Exception:
    def read_rows(p): return list(csv.DictReader(open(p)))

root = sys.argv[1]
res = {}
for tag in ("uniform", "refine", "both"):
    f = os.path.join(root, tag, "case_out.csv")
    if not os.path.exists(f):
        print("  %s 没跑出来" % tag); continue
    r = read_rows(f)
    if not r:
        print("  %s 空" % tag); continue
    tot = [float(x["total_c"]) for x in r if x.get("total_c")]
    drift = abs(tot[-1] - tot[0]) / abs(tot[0]) if tot and tot[0] else 0.0
    L0, L1 = float(r[0]["solid_len"]), float(r[-1]["solid_len"])
    t0, t1 = float(r[0]["time"]), float(r[-1]["time"])
    v = (L1 - L0) / (t1 - t0) if t1 > t0 else float("nan")
    keff = float(r[-1]["c_max"]) / float(r[-1]["c_solid"]) if float(r[-1]["c_solid"]) else float("nan")
    res[tag] = (drift, v, keff, len(r))

print("  %-10s %-8s %-14s %-14s %-12s %s" %
      ("变体", "步数", "守恒漂移", "前沿速度(m/s)", "k_eff", "判定"))
print("  " + "-" * 74)
base = None
for tag in ("uniform", "refine", "both"):
    if tag not in res:
        continue
    drift, v, keff, n = res[tag]
    if base is None:
        base = (v, keff)
    ok = drift <= 1e-8
    print("  %-10s %-8d %-14.3e %-14.6g %-12.6f %s" %
          (tag, n, drift, v, keff, "OK" if ok else "**守恒超 1e-8**"))

if base and "refine" in res and "both" in res:
    print()
    print("  与 uniform 的相对变化（判据 ≤ 5%）：")
    for tag in ("refine", "both"):
        drift, v, keff, n = res[tag]
        dv = abs(v - base[0]) / abs(base[0]) * 100
        dk = abs(keff - base[1]) / abs(base[1]) * 100
        print("    %-8s 速度 %6.3f%%   k_eff %6.3f%%   %s" %
              (tag, dv, dk, "OK" if max(dv, dk) <= 5 else "**超 5%**"))
PY
