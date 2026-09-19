#!/bin/bash
# =============================================================================
# T1b 的结构完备性检查：**材料链上到底有哪些导数属性被真正生成了**
# =============================================================================
# ## 为什么用这个判据、而不是全局 FD 比值
#
# T1b 的两条发现（`ACGrGrPoly` 丢项、`L2b` 的 η 导数静默为零）都属于
# **「结构性缺项」**，而 `T1_CRITERION.md` 已经实测证明：
#   * 全局 FD 比值对缺项**不敏感**（`jac_mode=off` 与 `full` 逐位相同，
#     因为缺的 η_i·η_j 项只在晶界单元非零）
#   * 生产规模上比值本身就没有判据意义（同一框架，小算例 3e-10 vs 生产 2e-2）
# ⇒ 正确的工具是**直接问"这个导数属性存不存在、值是不是零"**，
#   也就是 T1′ 的 L3「结构性缺项计数」。
#
# ## 两步
#
#   ① **存在性**：`[Debug] show_material_properties = true` —— MOOSE 把注册的
#      **全部材料属性**逐块打印。一次跑完，无遗漏。然后逐个
#      `DerivativeParsedMaterial` 检查 `d<prop>/d<var>`（var 取它自己声明的
#      `coupled_variables`）在不在里面。
#   ② **非零性**（防"属性存在但恒为 0"这种更隐蔽的情况）：注入 `MaterialRealAux`
#      探针，把值输出到 CSV，检查有 η 梯度处**确实非零**。
#
# ⚠ 教训 19（AGENTS.md）：探针**必须先做正对照**。这里每个材料的**自身属性**
#   （一定存在、一定非零）就是正对照；另外注入一个**故意编的假属性名**当负对照。
#
# ⚠ 必须用自建的 `gb_jac-opt`：生产输入含 `ACGrGrPolyJ`，
#   MOOSE 自带的 `phase_field-opt` 会报 "not a registered object"（实测踩过）。
#
# 用法： bash run_t1b_probe.sh
#   SRC=/root/work/at_check/stage1_meltpool_d.i bash run_t1b_probe.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/t1b}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
SRC="${SRC:-/root/work/at_check/stage1_meltpool_d.i}"
NX="${NX:-86}"; NY="${NY:-30}"
TMO="${TMO:-2400}"
ZERO_PROPS="${ZERO_PROPS:-L2b dL2b/dgr0 dL2b/dgr3 L2a dL2a/dgr0 dL/dgr0 dL/dgr3 f_loc df_loc/dgr0 h_gb dh_gb/dgr0 M dM/dgr0 acomp}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2
  echo "  先用 validated/run_antitrap_check.sh 生成生产链输出，或 SRC= 指定。" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"
SD="$(dirname "$SRC")"
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$SD/$f" ] && cp "$SD/$f" . || true
done

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

# --- 通用注入器：把一段文本插进**已有的**具名块（块必须存在）---
cat > inject.py <<'PYEOF'
import re, sys
path, blk, payload = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(path, encoding="utf-8").read()
# ⚠ 行首锚定 + re.M —— 本仓库的坑：块名在注释里也出现过
m = re.search(rf"^[ \t]*\[{re.escape(blk)}\]\n", t, re.M)
if not m:
    sys.exit(f"inject: 找不到块 [{blk}]（源文件变过了？）")
t = t[:m.end()] + payload + t[m.end():]
open(path, "w", encoding="utf-8", newline="").write(t)
PYEOF

# ===========================================================================
echo "=== ① 存在性：dump 全部材料属性 ==="
cp "$SRC" prod.i
# 生产输入本来没有 [Debug]；有就插进去，没有就追加（下面那段 python 统一处理）
python3 inject.py prod.i Debug "  show_material_properties = true\n" 2>/dev/null || true

# 生产输入本来没有 [Debug]，所以上面会失败；改成追加
python3 - prod.i <<'PY'
import re, sys
p = "prod.i"
t = open(p, encoding="utf-8").read()
if "show_material_properties" not in t:
    t = t.rstrip() + "\n\n[Debug]\n  show_material_properties = true\n[]\n"
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("  [Debug] 不存在 ⇒ 已追加到文件末尾")
else:
    print("  [Debug] 已就位")
PY

set +e
timeout "$TMO" "$MOOSE" -i prod.i Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
    Executioner/end_time=1e-12 > dump.log 2>&1
RC=$?
set -e
sed "s/\x1b\[[0-9;]*m//g" dump.log > dump_clean.log
echo "  rc=$RC，日志 $(wc -l < dump_clean.log) 行"

python3 - <<'PY'
import re, sys
x = open("dump_clean.log", encoding="utf-8", errors="replace").read()
if "Material Properties" not in x:
    print("  ❌ 没抓到属性 dump —— 看 dump_clean.log")
    sys.exit(0)

# MOOSE 逐块打印，形如 "(N) <name> : <type>"；容错地抓 "(N) name"
names = set(re.findall(r"^\s*\(\s*\d+\s*\)\s+([^\s:]+)", x, re.M))
if not names:
    names = set(re.findall(r"\(\s*\d+\s*\)\s+([A-Za-z_][\w/]*)", x))
print(f"  抓到 {len(names)} 个材料属性名")
open("props.txt", "w", encoding="utf-8").write("\n".join(sorted(names)))
have = lambda n: n in names

# 逐个 DerivativeParsedMaterial。
# ⚠ 不要用"从 [name] 匹配到下一个 ^[]$"那种写法 —— 生产输入的 [ICs] 等块**有嵌套**，
#   非贪婪匹配会在内层 `[]` 处截断。改成：从 `type = DerivativeParsedMaterial`
#   这一行**往回找最近的 [name]**，天然免疫嵌套。
src = open("prod.i", encoding="utf-8").read()
lines = src.split("\n")
dpm, cur = [], None
for i, L in enumerate(lines):
    m = re.match(r"^\[(\w+)\]\s*$", L)
    if m:
        cur = (m.group(1), i)
    if "type = DerivativeParsedMaterial" in L and cur:
        j = i
        while j < len(lines) and lines[j].strip() != "[]":
            j += 1
        dpm.append((cur[0], "\n".join(lines[cur[1]:j])))
print(f"  DerivativeParsedMaterial 块 {len(dpm)} 个")
print()
print("  %-20s %-14s %-9s %s" % ("材料块", "property", "导数个数", "链式法则传播了吗"))
print("  " + "-" * 72)
bad = []
for name, body in dpm:
    m = re.search(r"property_name\s*=\s*(\S+)", body)
    if not m:
        continue
    prop = m.group(1)
    cv = re.search(r"coupled_variables\s*=\s*'([^']*)'", body)
    vs = cv.group(1).split() if cv else []
    if not vs:
        print("  %-20s %-14s %-9s ⚠ 未声明 coupled_variables ⇒ 无导数可查" % (name, prop, 0))
        continue
    absent = [v for v in vs if not have(f"d{prop}/d{v}")]
    self_ok = "✅" if have(prop) else "❌"
    if absent:
        bad.append((name, prop, absent))
        print("  %-20s %-14s %-9s ❌ 缺 %d/%d：%s" %
              (name, prop, f"{len(absent)}", len(vs), ",".join(absent[:4])))
    else:
        print("  %-20s %-14s %-9s ✅ 全部 %d 个都在（自身 %s）" %
              (name, prop, len(vs), self_ok))
print()
if bad:
    print(f"  ❌ **{len(bad)} 个材料的 η 导数没被生成** —— 那些项在雅可比里静默缺失：")
    for n, p, a in bad:
        print(f"       [{n}] property={p} 缺 d{p}/d{{{','.join(a[:5])}}}")
else:
    print("  ✅ **所有 DerivativeParsedMaterial 的导数属性都已生成**（含 L2b 这条 T1b 核心疑点）")
PY

# ===========================================================================
echo
echo "=== ② 非零性：值探针（自身属性 = 正对照，acomp = 负对照）==="
python3 - prod.i "$ZERO_PROPS" <<'PY'
import re, sys
p = "prod.i"
t = open(p, encoding="utf-8").read()
props = list(dict.fromkeys(sys.argv[2].split()))
av = ""
ak = ""
for q in props:
    safe = re.sub(r"\W", "_", q)
    av += f"  [{safe}]\n    family = MONOMIAL\n    order = CONSTANT\n  []\n"
    ak += (f"  [{safe}]\n    type = MaterialRealAux\n    variable = {safe}\n"
           f"    property = '{q}'\n  []\n")
# ⚠ 生产输入**已有** [AuxVariables] / [AuxKernels] ⇒ 必须插进去，不能重复建块
for blk, payload in (("AuxVariables", av), ("AuxKernels", ak)):
    m = re.search(rf"^\[{blk}\]\n", t, re.M)
    assert m, f"找不到 [{blk}]"
    t = t[:m.end()] + payload + t[m.end():]
if "csv = true" not in t:
    m = re.search(r"^\[Outputs\]\n", t, re.M)
    assert m, "找不到 [Outputs]"
    t = t[:m.end()] + "  csv = true\n" + t[m.end():]
open(p, "w", encoding="utf-8", newline="").write(t)
print(f"  注入 {len(props)} 个探针（含负对照 acomp）")
PY

set +e
timeout "$TMO" "$MOOSE" -i prod.i Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
    Executioner/end_time=1e-12 > probe.log 2>&1
RC=$?
set -e
sed "s/\x1b\[[0-9;]*m//g" probe.log > probe_clean.log
echo "  rc=$RC"
grep -a -m3 "is not defined\|not found\|*** ERROR" probe_clean.log | sed 's/^/    /' || true

CSV=$(ls prod_out.csv *out.csv 2>/dev/null | head -1)
if [ -n "$CSV" ]; then
  CSV="$CSV" python3 - <<'PY'
import csv, os
rows = list(csv.DictReader(open(os.environ["CSV"])))
if not rows:
    raise SystemExit("  CSV 空")
last = rows[-1]
print()
print("  %-22s %-14s %s" % ("属性", "末态 |值|", "判读"))
print("  " + "-" * 62)
for k, v in last.items():
    if k.strip() == "time" or v in (None, ""):
        continue
    try:
        f = abs(float(v))
    except ValueError:
        continue
    if k == "acomp":
        tag = "负对照（编的假名字）—— 不该有值"
    elif k.startswith("d"):
        tag = "✅ 非零（导数真的生成了且有值）" if f > 0 else "⚠ **恒为零 ⇒ 静默缺项**"
    else:
        tag = "✅ 非零（正对照）" if f > 0 else "⚠ 正对照却为零?!"
    print("  %-22s %-14.4e %s" % (k, f, tag))
PY
else
  echo "  ⚠ 没有 CSV 输出 —— 看 probe_clean.log"
fi
