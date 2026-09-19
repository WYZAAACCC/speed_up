#!/bin/bash
# =============================================================================
# 在**小网格**上跑多个分支输入，对比后处理量（不改生产、不跑全尺寸）
# =============================================================================
#
# 用途：T10（温度截断）、T6（迁移率分层）这类「改一个因素，看观测量怎么动」
#       的对照实验。每个变体在**独立目录**里跑 —— 本项目的 CSV 是按输入文件名
#       命名的，同一个 .i 并发跑会互相覆盖（AGENTS.md §3.2 坑 8）。
#
# 用法：
#     bash compare_variants.sh off=/root/work/valid/cap_off.i \
#                              cap3200=/root/work/valid/cap_3200.i \
#                              cap3500=/root/work/valid/cap_3500.i
#
# 环境变量：NX NY END OUT_ROOT（默认 24 12 4e-7 /root/work/valid/cmp）
# =============================================================================
set -e

NX="${NX:-24}"
NY="${NY:-12}"
END="${END:-4e-7}"
OUT_ROOT="${OUT_ROOT:-/root/work/valid/cmp}"
SEEDS="${SEEDS:-/root/work/valid/columnar_seeds.csv}"

[ $# -ge 1 ] || { echo "用法: compare_variants.sh <标签>=<文件.i> [...]"; exit 1; }

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$OUT_ROOT"; mkdir -p "$OUT_ROOT"

for spec in "$@"; do
  TAG="${spec%%=*}"
  FILE="${spec#*=}"
  [ -f "$FILE" ] || { echo "跳过 $TAG：找不到 $FILE"; continue; }

  D="$OUT_ROOT/$TAG"
  mkdir -p "$D"
  cp "$FILE" "$D/N.i"
  [ -f "$SEEDS" ] && cp "$SEEDS" "$D/" || true

  echo "=== 跑 [$TAG]  $FILE ==="
  # ⚠ 不能写 `( ... ); RC=$?` —— 脚本开了 set -e，子 shell 非零会直接退出，
  #   拿不到退出码。用 `|| RC=$?` 把失败吃掉。
  RC=0
  ( cd "$D" && \
    "$MOOSE" -i N.i Mesh/gen/nx="$NX" Mesh/gen/ny="$NY" \
             Executioner/end_time="$END" > run.log 2>&1 ) || RC=$?
  NS=$(grep -ac "Solve Converged" "$D/run.log" 2>/dev/null || echo 0)
  NL=$(grep -ac "Nonlinear \|R\|" "$D/run.log" 2>/dev/null || echo 0)
  echo "    退出码=$RC  收敛步=$NS  牛顿迭代行=$NL"
  grep -ac "Missing coupled variables" "$D/run.log" 2>/dev/null | \
    awk '{ if ($1>0) print "    ⚠ Missing coupled variables: " $1 " 条" }'
  echo "    数据丢失检查：" $(grep -aic "DIVERGED\|NANORINF\|Assertion" "$D/run.log" 2>/dev/null || echo 0) "条异常"
done

echo
echo "=== 对比 ==="
python3 - "$OUT_ROOT" "$@" <<'PY'
import csv, os, sys

root, specs = sys.argv[1], sys.argv[2:]
tags, rows = [], {}
for spec in specs:
    tag = spec.split("=")[0]
    f = os.path.join(root, tag, "N_out.csv")
    if not os.path.exists(f):
        print(f"  {tag}: 没有 N_out.csv（跑失败了？）")
        continue
    with open(f) as fh:
        r = list(csv.DictReader(fh))
    if not r:
        continue
    tags.append(tag)
    rows[tag] = r[-1]          # 最后一行 = 末态

if not tags:
    sys.exit("没有任何可对比的结果")

keys = [k for k in rows[tags[0]] if k != "time"]
# 把变化明显的列放前面
def spread(k):
    vs = [abs(float(rows[t][k])) for t in tags if rows[t].get(k) not in (None, "")]
    if not vs or max(vs) == 0:
        return 0.0
    return (max(vs) - min(vs)) / max(vs)

keys.sort(key=spread, reverse=True)

w = max(len(k) for k in keys) + 2
print("  " + "量".ljust(w) + "".join(t.rjust(18) for t in tags) + "   相对差")
print("  " + "-" * (w + 18 * len(tags) + 12))
for k in keys:
    vals = []
    for t in tags:
        v = rows[t].get(k, "")
        try:
            vals.append(f"{float(v):.6g}")
        except (TypeError, ValueError):
            vals.append(str(v))
    s = spread(k)
    mark = "  <-" if s > 1e-12 else ""
    print("  " + k.ljust(w) + "".join(v.rjust(18) for v in vals) +
          f"   {s:9.3e}{mark}")
PY
