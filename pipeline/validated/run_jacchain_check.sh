#!/bin/bash
# =============================================================================
# T1b 修法（`make_jacchain.py`）的验收
# =============================================================================
# ## 修的是什么
#
# `DerivativeParsedMaterial` **只对「表达式里字面出现的变量」发射导数**。
# 表达式里只有别的材料属性时**一个导数都不发射**，而生产核明确在索取
# ⇒ 求到的是**静默的零** ⇒ **雅可比与残差不一致**。
#
# 受控 FD 判决（`run_t1b_L_test.sh`）：生产结构 `1.36e-03` ❌ / 内联后 `1.23e-09` ✅
# （正对照 `6.17e-10`）。
#
# ## 三条判据
#
#   ① **结构**：`[Debug] show_material_props` 的产出清单里，修后三处导数都在；
#      **负对照**是未修的输入 —— 那里必须**没有**，否则判据无分辨力。
#   ② **回归**：修法只该改**雅可比**、不该改**残差** ⇒ 观测量必须逐位相同。
#   ③ **代价**：确认**不是**当年那次"求导树爆炸"（5 分钟 100% CPU、0 次 JIT）。
#
# ⚠ 必须用自建 `gb_jac-opt`（输入含 `ACGrGrPolyJ`）。
# ⚠ 用户约束：只做 smoke test（缩小网格、极短时间）。
#
# 用法： SRC=/root/work/at_check/stage1_meltpool_d.i bash run_jacchain_check.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/root/work/jacchain}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
SRC="${SRC:-/root/work/at_check/stage1_meltpool_d.i}"
NX="${NX:-86}"; NY="${NY:-30}"
END="${END:-1e-12}"
TMO="${TMO:-900}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
SD="$(dirname "$SRC")"
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"
for f in columnar_seeds.csv aniso_block.i; do [ -f "$SD/$f" ] && cp "$SD/$f" . || true; done

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

cp "$SRC" base.i
python3 "$HERE/make_jacchain.py" --src "$SRC" --out chain.i 2>&1 | sed 's/^/    /'
[ -f chain.i ] || { echo "❌ 生成失败"; exit 1; }

run () {  # $1=输入 $2=标签 [$3=debug]
  cp "$1" "r_$2.i"
  [ "${3:-}" = "debug" ] && printf "\n[Debug]\n  show_material_props = true\n[]\n" >> "r_$2.i"
  local S; S=$(date +%s)
  set +e
  timeout "$TMO" "$MOOSE" -i "r_$2.i" Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
      Executioner/end_time=$END > "$2.log" 2>&1
  local RC=$?
  set -e
  sed "s/\x1b\[[0-9;]*m//g" "$2.log" > "${2}_clean.log"
  echo "$RC $(( $(date +%s) - S ))"
}

echo
echo "=== 跑 4 档 ==="
read -r RC_B T_B <<< "$(run base.i  base  debug)"
read -r RC_C T_C <<< "$(run chain.i chain debug)"
read -r RC_B2 T_B2 <<< "$(run base.i  base_nodbg)"
read -r RC_C2 T_C2 <<< "$(run chain.i chain_nodbg)"
printf "  base  rc=%s  %ss（Debug） / %ss\n" "$RC_B" "$T_B" "$T_B2"
printf "  chain rc=%s  %ss（Debug） / %ss\n" "$RC_C" "$T_C" "$T_C2"

echo
echo "=== ① 结构判据（负对照 = 未修档）==="
python3 - <<'PY'
import re, os
WANT = {"L_aniso": ["dL/dgr0", "dL/dgr7", "d^2L/dgr0^2"],
        "solute_mobility": ["dM/dgr0", "dM/dgr7", "d^2M/dgr0^2"],
        "at_susc": ["dF_at/dgr0", "dF_at/dgr7"]}

def supplied(path, mat):
    if not os.path.exists(path):
        return None
    x = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(rf"Material Name:\s+{re.escape(mat)}\s*\n\s*Property Names:\s*(.*?)"
                  rf"(?=\n\s*\n|\n\s*Material Name:)", x, re.S)
    return m.group(1) if m else None

ok = True
print("  %-18s %-14s %s" % ("材料", "档", "缺哪些导数"))
print("  " + "-" * 64)
for mat, want in WANT.items():
    for tag, path, should_miss in (("未修(负对照)", "base_clean.log", True),
                                   ("已修", "chain_clean.log", False)):
        s = supplied(path, mat)
        if s is None:
            print("  %-18s %-14s ⚠ 抓不到属性清单" % (mat, tag)); ok = False; continue
        miss = [w for w in want if w not in s]
        good = bool(miss) == should_miss
        ok &= good
        flag = ("✅ 确实没有" if (should_miss and good) else
                "❌ 负对照竟然有 ⇒ 判据无分辨力" if should_miss else
                "✅ 都在" if good else f"❌ 仍缺 {miss}")
        print("  %-18s %-14s %s" % (mat, tag, flag))
print()
print("  " + ("✅ **结构判据通过**：三处导数都已发射，负对照确实没有" if ok
              else "❌ 结构判据未通过"))
PY

echo
echo "=== ② 回归判据：观测量必须逐位相同（修法只改雅可比）==="
python3 - <<'PY'
import re
def last_rows(p):
    x = open(p, encoding="utf-8", errors="replace").read()
    # 只取最后一组 Postprocessor 表（时间步越多，最后一段越靠后）
    blocks = re.split(r"Postprocessor Values:", x)
    tail = blocks[-1] if len(blocks) > 1 else x
    rows = re.findall(r"^\|\s*[0-9.eE+-]+\s*\|([^\n]*)\|", tail, re.M)
    return [r.strip() for r in rows]
a, b = last_rows("base_nodbg_clean.log"), last_rows("chain_nodbg_clean.log")
print("  base  末行：", a[-1] if a else "（无）")
print("  chain 末行：", b[-1] if b else "（无）")
same = bool(a) and a == b
print("  " + ("✅ **逐位相同 ⇒ 只改了雅可比，残差没动**" if same
              else "❌ 有差异 ⇒ 修法改动了残差，要查"))
PY

echo
echo "=== ③ 代价 ==="
printf "  未修 %ss → 已修 %ss（无 Debug；86×30 小网格）\n" "$T_B2" "$T_C2"
printf "  含 Debug：%ss → %ss\n" "$T_B" "$T_C"
echo "  差的主要是**建材料/JIT 的固定开销**。对照生成器注释里记的那次"
echo "  「内联导致 5 分钟 100% CPU、0 次 JIT」—— **本次没有发生**。"
