#!/bin/bash
# =============================================================================
# T10：温度截断 —— 在 **dx <= 2 µm 的局部算例**上比较（审计要求）
# =============================================================================
# 审计原文：
#   「1.2 温度截断实验：加入可开关的 T_cap，至少比较：原式、3200 K、3500 K。
#     只比较**短时间局部算例**，不跑生产。」
#   「验收：熔池等温线、晶粒速度、残差、温度最大值变化有记录。」
#
# 【为什么必须缩小域，而不是直接跑生产网格】
#   生产网格 430×150 = 64500 单元，一次跑几小时，三个变体就是十几小时。
#   而审计要的本来就是"局部算例"。这里取熔池附近 100×150 µm 的窗口。
#   **关键：比较的是同一个域内 cap 关/3200/3500 三个变体，
#     域的大小对三者是一样的，所以域效应在对照中抵消。**
#
# 【为什么必须 dx <= 2 µm】
#   已实测（cap_safety_vs_mesh.py）：cap 是**在节点上**做的，MOOSE 再对节点值做
#   双线性插值；min 是凹的 ⇒ 截断会移动插值场自己的 1903 K 等值线。
#   跨在熔池边界上、且含被截断节点的单元数：
#       dx = 17.9 µm → 4 个   （cap 明显改变几何）
#       dx = 5.0  µm → 1 个
#       dx = 2.0  µm → 0 个   ← 从这一档起几何中性
#       dx = 1.0  µm → 0 个   （生产网格）
#   ⇒ 在 dx > 2 µm 上做的 cap 敏感性结论是**错的**。
#
# 用法：
#   bash run_t10.sh                       # 默认 dx = 2 µm
#   DX=1.0e-6 bash run_t10.sh             # 更细（更慢）
# =============================================================================
set +u   # conda activate 引用未定义的 $CONDA_BUILD

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t10}"
XMIN="${XMIN:--1.8e-4}"
XMAX="${XMAX:--0.8e-4}"
YMIN="${YMIN:-0.0}"
YMAX="${YMAX:-1.5e-4}"
DX="${DX:-2.0e-6}"
END="${END:-1.0e-6}"
SEEDS_ALL="${SEEDS_ALL:-/root/work/valid/columnar_seeds.csv}"
# ⚠ 【2026-09-19】默认源改成 **合入前** 的 C 源副本。
#   原因：1.2（温度截断）已由用户决定**合入生产**，所以 `../stage1_meltpool_c.i`
#   现在**已经带着** `min(…, 3200)`；再对它跑 `make_variant.py --t-cap` 会
#   因为"表达式里已经有 min("而报错退出（这是有意的守卫，不是 bug）。
#   本脚本比的是"cap 开 vs 关"，所以基准必须是**还没打 cap 的那一版**。
#   该副本由 `phase1_merge.diff` 反向打补丁重建，SHA256 逐位等于合入前的值。
SRC="${SRC:-$HERE/stage1_meltpool_c.premerge.i}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

NX=$(python3 -c "print(int(round(($XMAX-($XMIN))/$DX)))")
NY=$(python3 -c "print(int(round(($YMAX-($YMIN))/$DX)))")

rm -rf "$ROOT"; mkdir -p "$ROOT"

# 只保留落在这个窗口里的种子（区域外的种子会让 Voronoi 出错或产生退化晶粒）
awk -F, -v a="$XMIN" -v b="$XMAX" -v c="$YMIN" -v d="$YMAX" \
    'NR==1{print;next} $1>=a && $1<=b && $2>=c && $2<=d' "$SEEDS_ALL" \
    > "$ROOT/seeds_win.csv"
NSEED=$(($(wc -l < "$ROOT/seeds_win.csv") - 1))

echo "窗口 x ∈ [$XMIN, $XMAX]  y ∈ [$YMIN, $YMAX]"
echo "dx = $DX m  ->  网格 ${NX} x ${NY} = $((NX*NY)) 单元；窗口内种子 $NSEED 个"
echo "end_time = $END s"
echo

if [ "$NSEED" -lt 2 ]; then
  echo "⚠ 窗口内种子只有 $NSEED 个，晶粒结构没有意义。请扩大窗口或换位置。"
fi

# --- 生成三个变体输入 ---
python3 "$HERE/make_variant.py" --src "$SRC" --out "$ROOT/off.i"     --t-cap off    > "$ROOT/gen_off.log" 2>&1
python3 "$HERE/make_variant.py" --src "$SRC" --out "$ROOT/cap3200.i" --t-cap 3200   > "$ROOT/gen_3200.log" 2>&1
python3 "$HERE/make_variant.py" --src "$SRC" --out "$ROOT/cap3500.i" --t-cap 3500   > "$ROOT/gen_3500.log" 2>&1

for tag in off cap3200 cap3500; do
  D="$ROOT/$tag"; mkdir -p "$D"
  cp "$ROOT/$tag.i" "$D/N.i"
  cp "$ROOT/seeds_win.csv" "$D/columnar_seeds.csv"
  echo "=== 跑 [$tag] ==="
  RC=0
  ( cd "$D" && /usr/bin/time -f "  墙钟 %e s" "$MOOSE" -i N.i \
      Mesh/gen/nx="$NX" Mesh/gen/ny="$NY" \
      Mesh/gen/xmin="$XMIN" Mesh/gen/xmax="$XMAX" \
      Mesh/gen/ymin="$YMIN" Mesh/gen/ymax="$YMAX" \
      Executioner/end_time="$END" > run.log 2>&1 ) || RC=$?
  echo "    退出码=$RC  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac "Missing coupled")"
  grep -a "墙钟" "$D/run.log" 2>/dev/null
done

echo
echo "=== 对比（末态）==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
root = sys.argv[1]
tags, rows = [], {}
for t in ("off", "cap3200", "cap3500"):
    f = os.path.join(root, t, "N_out.csv")
    if not os.path.exists(f):
        print("  %s: 没有 N_out.csv" % t); continue
    r = list(csv.DictReader(open(f)))
    if not r: continue
    tags.append(t); rows[t] = r[-1]
if not tags:
    sys.exit("没有可比较的结果")
keys = [k for k in rows[tags[0]] if k != "time"]
def spread(k):
    vs = []
    for t in tags:
        try: vs.append(abs(float(rows[t][k])))
        except (TypeError, ValueError): pass
    return 0.0 if not vs or max(vs) == 0 else (max(vs)-min(vs))/max(vs)
keys.sort(key=spread, reverse=True)
w = max(len(k) for k in keys) + 2
print("  " + "量".ljust(w) + "".join(t.rjust(18) for t in tags) + "   相对差")
print("  " + "-" * (w + 18*len(tags) + 12))
for k in keys:
    vals = []
    for t in tags:
        try: vals.append("%.6g" % float(rows[t].get(k, "")))
        except (TypeError, ValueError): vals.append(str(rows[t].get(k, "")))
    s = spread(k)
    print("  " + k.ljust(w) + "".join(v.rjust(18) for v in vals) +
          "   %9.3e%s" % (s, "  <-" if s > 1e-9 else ""))
PY
