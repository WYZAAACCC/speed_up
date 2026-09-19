#!/bin/bash
# =============================================================================
# Phase 1.3 的 2D 动力学验证：分层迁移率在**真实生产模型**里跑得动吗
# =============================================================================
# 审计对 1.3 的要求是分两步：
#   「先在 1D 静态相界面上验证守恒和化学势平衡，再验证移动前沿。」
#
# 1D 部分已完成（见 VALIDATION_STATUS.md §1.3）：
#   * T6 三态 —— D = M·∂²f/∂c² 逐点等于输入定义
#   * 剖面判据 —— D 的极大值在晶界中心、固相 D 精确等于 D_S
#   * 精确退化 —— D_S 取 3.9984e-9 时与常数模式**逐列全等**
#   * T12 —— 小扰动衰减量出的 D 与目标值差 0.35%
#
# **本脚本做第二步**：把分层迁移率放进 2D 生产输入（8 个序参量、
# 真实的热场、晶粒追踪），看它
#   ① 能不能稳定跑（雅可比、收敛）
#   ② 观测量与常数模式差多少
#
# ⚠ **这个对照测的不是"改动幅度"，而是"能不能跑"。**
#   在 t_end = 1e-6 s 上，溶质的扩散长度只有 sqrt(D_S·t) = sqrt(4e-13 × 1e-6)
#   ≈ 6e-10 m = **0.6 nm** —— c 场几乎没动。
#   要让溶质真正演化需要 t ~ L²/D_S ≈ 2.5 s（L=1 µm），那已经超出"短时间局部算例"。
#   ⇒ 本脚本要回答的是：**分层迁移率（5 个新的二阶导材料 + 8 个耦合变量）
#     能不能在完整生产模型里跑起来、守恒有没有坏、雅可比有没有缺项。**
#   想看改动的物理幅度，要去 1D（那里已经做完：T6 / 剖面 / 退化 / T12）。
#
# ⚠ 用缩小域（审计对 T10 的同类要求："只比较短时间局部算例，不跑生产"）。
#
# 用法： bash run_phase13_2d.sh
# =============================================================================
set +u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/p13_2d}"
XMIN="${XMIN:--1.8e-4}"
XMAX="${XMAX:--0.8e-4}"
YMIN="${YMIN:-0.0}"
YMAX="${YMAX:-1.0e-4}"
DX="${DX:-2.0e-6}"
END="${END:-1.0e-6}"
# 分层参数（**calibration**，不是材料常数 —— 见 make_variant.py 的注释）
DL="${DL:-2.52e-9}"
DS="${DS:-4.0e-13}"
DGB="${DGB:-4.0e-10}"
# ⚠ 【2026-09-19】默认源改成 **合入前** 的 C 源副本（同 run_t10.sh 的理由）：
#   1.3（迁移率分层）已合入生产，`../stage1_meltpool_c.i` 里再也没有那个常数 `M`
#   的 `[ch_params]` 块，`make_variant.py --d-layer` 会因匹配不到而报错退出。
#   本脚本比的是"常数 M vs 分层 D"，所以基准要用还没分层的版本。
SRC="${SRC:-$HERE/stage1_meltpool_c.premerge.i}"
SEEDS_ALL="${SEEDS_ALL:-/root/work/valid/columnar_seeds.csv}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

NX=$(python3 -c "print(int(round(($XMAX-($XMIN))/$DX)))")
NY=$(python3 -c "print(int(round(($YMAX-($YMIN))/$DX)))")

rm -rf "$ROOT"; mkdir -p "$ROOT"
awk -F, -v a="$XMIN" -v b="$XMAX" -v c="$YMIN" -v d="$YMAX" \
    'NR==1{print;next} $1>=a && $1<=b && $2>=c && $2<=d' "$SEEDS_ALL" \
    > "$ROOT/seeds_win.csv"

echo "窗口 x ∈ [$XMIN, $XMAX]  y ∈ [$YMIN, $YMAX]   dx = $DX"
echo "网格 ${NX} x ${NY} = $((NX*NY)) 单元；窗口内种子 $(($(wc -l < "$ROOT/seeds_win.csv") - 1)) 个"
echo "end_time = $END s"
echo

# --- 生成两个变体 ---
# const: **原样**复制生产输入（不加任何补丁）—— 这样两个变体只差 d-layer 一处
cp "$SRC" "$ROOT/const.i"
# layer: 只加分层迁移率
python3 "$HERE/make_variant.py" --src "$SRC" --out "$ROOT/layer.i" \
    --d-layer "$DL" "$DS" "$DGB" > "$ROOT/gen_layer.log" 2>&1
[ -f "$ROOT/layer.i" ] || { echo "分层变体没生成出来："; tail -5 "$ROOT/gen_layer.log"; exit 1; }
echo "变体已生成：const.i（原样生产输入） / layer.i（+分层 D_L=$DL D_S=$DS D_GB=$DGB）"
echo

for tag in const layer; do
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
  echo "    退出码=$RC  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac 'Missing coupled')"
  grep -a "墙钟" "$D/run.log" 2>/dev/null
done

echo
echo "=== 对比（末态）==="
python3 - "$ROOT" <<'PY'
import csv, os, sys, time
sys.path.insert(0, "/mnt/f/speed_up/pipeline/validated")
root = sys.argv[1]
try:
    from robust_csv import read_rows
except Exception:
    def read_rows(p):
        return list(csv.DictReader(open(p)))
tags, rows = [], {}
for t in ("const", "layer"):
    f = os.path.join(root, t, "N_out.csv")
    if not os.path.exists(f):
        print("  %s: 没有 N_out.csv" % t); continue
    r = read_rows(f)
    if not r: continue
    tags.append(t); rows[t] = r[-1]
if len(tags) < 2:
    sys.exit("不足以对比")
keys = [k for k in rows[tags[0]] if k != "time"]
def sp(k):
    vs = []
    for t in tags:
        try: vs.append(abs(float(rows[t][k])))
        except (TypeError, ValueError): pass
    return 0.0 if not vs or max(vs) == 0 else (max(vs)-min(vs))/max(vs)
keys.sort(key=sp, reverse=True)
w = max(len(k) for k in keys) + 2
print("  " + "量".ljust(w) + "".join(t.rjust(16) for t in tags) + "   相对差")
print("  " + "-" * (w + 16*len(tags) + 12))
for k in keys:
    vals = []
    for t in tags:
        try: vals.append("%.6g" % float(rows[t].get(k, "")))
        except (TypeError, ValueError): vals.append(str(rows[t].get(k, "")))
    s = sp(k)
    print("  " + k.ljust(w) + "".join(v.rjust(16) for v in vals)
          + "   %9.3e%s" % (s, "  <-" if s > 1e-9 else ""))
PY
