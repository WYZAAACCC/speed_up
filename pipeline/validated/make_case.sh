#!/bin/bash
# =============================================================================
# 生成一个**验证用小算例**（不是生产跑）
# =============================================================================
#
# 步骤与 run_nonad_prod.sh 的生成段**逐字相同**（同一对冻结生成器、
# 同一套哈希校验、同一套断言），唯一区别是：
#
#   * 生成完就停，不启动 MOOSE（尺寸覆盖在运行时用命令行做，见 README）
#   * 目标目录由 $D 指定，默认 /root/work/valid
#   * 源输入可由 $SRC 指定，默认生产源文件；这样验证分支也能用同一套流程
#
# 用法：
#     bash make_case.sh
#     D=/root/work/valid_cap SRC=/mnt/f/speed_up/pipeline/validated/stage1_meltpool_cap.i \
#         bash make_case.sh
#
# 输出：$D/N.i  （外加 gen.log、case_meta.txt）
# =============================================================================
set -e

REPO=/mnt/f/speed_up/pipeline
D="${D:-/root/work/valid}"
SRC="${SRC:-$REPO/stage1_meltpool_c.i}"

[ -f "$SRC" ] || { echo "错误：源输入不存在：$SRC"; exit 1; }

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

cp "$REPO/frozen/gen_aniso_nonad.py"    .
cp "$REPO/frozen/splice_aniso_nonad.py" .
cp "$SRC"                               stage1_meltpool_c.i
cp "$REPO/columnar_seeds.csv"           .

# --- 冻结生成器哈希校验（与生产脚本同一判据）---
if ! HASHOUT=$( cd "$REPO/frozen" && sha256sum -c SHA256SUMS 2>&1 ); then
  echo "错误：frozen/ 生成器哈希校验失败"
  echo "$HASHOUT" | grep -v ': OK$'
  exit 1
fi
echo "生成器哈希校验通过"

# --- 源输入必须是 Ti64 真实溶质参数 ---
grep -q "constant_expressions = '0.9 0.036 0.264'" stage1_meltpool_c.i || {
  echo "错误：$SRC 的溶质参数不是 Ti64 真实值"; exit 1; }
grep -q "value = 0.036" stage1_meltpool_c.i || {
  echo "错误：c 的初始条件不是 0.036"; exit 1; }
echo "源输入校验通过（Ti64 真实溶质参数 k=0.63）"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i > gen.log 2>&1 \
  || { echo "gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso_nonad.py >> gen.log 2>&1 \
  || { echo "splice 失败"; tail -5 gen.log; exit 1; }
grep -E "自检|kappa_op   :|gamma_asymm:|最大相对误差" gen.log | head -5 || true

# --- 结构与自洽性断言：与 run_nonad_prod.sh 完全一致 ---
# 这些断言是"解的是同一个方程"的守卫，验证分支同样必须过。
python3 - "$D" <<'PY'
import re, sys, hashlib, pathlib
D = pathlib.Path(sys.argv[1])
s = (D / "stage1_meltpool_d.i").read_text(encoding="utf-8")
genlog = (D / "gen.log").read_text(encoding="utf-8", errors="replace")

assert s.count("type = TimeDerivative") == 8, "核没修好（缺 TimeDerivative）"
assert "variable_L = true" in s, "缺 variable_L"
assert s.count("type = ADGrainGrowth") == 0, "这是 AD 版，不是非 AD 版"

EXPECT = {"l_max_its": "300", "l_tol": "1e-6", "nl_abs_tol": "1e-9",
          "nl_rel_tol": "1e-8", "dtmax": "2e-6", "end_time": "6.5e-4"}
for k, want in EXPECT.items():
    m = re.search(rf"^  {k} = (\S+)\s*$", s, re.M)
    if not m:
        sys.exit(f"错误：找不到 Executioner/{k}")
    if m.group(1) != want:
        sys.exit(f"错误：Executioner/{k} = {m.group(1)}，期望 {want}")

m = re.search(r"^    dt = (\S+)\s*$", s, re.M)
if not m or m.group(1) != "1e-7":
    sys.exit(f"错误：初始 dt = {m.group(1) if m else '(缺)'}，期望 1e-7")

# ④ 自洽性：ACGrGrPoly 的常数势垒必须与熔化开关的 mu0 逐位相同
def block(text, name):
    out, inside = [], False
    for ln in text.splitlines():
        if not inside:
            if ln.strip() == f"[{name}]":
                inside = True
            continue
        if ln.strip() == "[]":
            break
        out.append(ln)
    return "\n".join(out)

mu0 = float(re.search(r"constant_expressions = '(\S+)", block(s, "barrier_muT")).group(1))
mu_const = float(re.search(r"prop_values = '(\S+)'", block(s, "mu_barrier_const")).group(1))
if abs(mu_const - mu0) > 1e-12 * abs(mu0):
    sys.exit(f"错误（④ 自洽性）：mu={mu_const:.6g} != mu0={mu0:.6g}")

gp = re.search(r"GENERATED_PARAMS\s+wgb=(\S+)\s+kappa_op_iso=(\S+)\s+gamma_asymm_iso=(\S+)\s+mu0=(\S+)", s)
if gp:
    kappa_op = float(gp.group(2))
    mu0_gen = float(gp.group(4))
else:
    # ⚠ 拼接器**不输出** GENERATED_PARAMS（已核对：d.i 里没有这一行）。
    #   run_nonad_prod.sh 的同一段检查因此**从未生效过**——它落到下面这个
    #   fallback，而 fallback 读的是文件头那行静态模板文本
    #   `[consts] kappa_op=1.8e-6`，不随 --wgb 变化（脚本自己的注释也这么说）。
    #
    #   这里改用**生成器自己打印的 mu_qp**（gen.log）——它是生成器真算出来的
    #   6*σ/wGB，且生成器明确断言它必须逐位等于算例的 mu0。
    #   这样不依赖任何静态注释，也不需要改冻结的生成器。
    mk = re.search(r"kappa_op\s*:\s*(\S+)", genlog)
    if not mk:
        raise ValueError("gen.log 里找不到 kappa_op 自检行")
    kappa_op = float(mk.group(1))
    mq = re.search(r"mu_qp\s*:\s*(\S+)", genlog)
    if not mq:
        raise ValueError("gen.log 里找不到 mu_qp —— 生成器版本可能变了")
    mu0_gen = float(mq.group(1))

if mu0_gen is not None and abs(mu0_gen - mu0) > 1e-9 * abs(mu0):
    sys.exit(f"错误：mu0 不自洽 —— 生成器 MU_QP={mu0_gen:.6g} 但 "
             f"[barrier_muT] mu0={mu0:.6g}。改了 --wgb 就必须同步改 barrier_muT"
             f"（mu0 = 6σ/wGB）。当前配置会产生错误的晶界能，拒绝运行。")
print(f"  mu0 自洽：生成器 mu_qp = 算例 [barrier_muT] mu0 = {mu0:.6g}  (逐位一致)")

nx = int(re.search(r"^\s+nx = (\d+)\s*$", s, re.M).group(1))
xmin = float(re.search(r"^\s+xmin = \s*(\S+)\s*$", s, re.M).group(1))
xmax = float(re.search(r"^\s+xmax = \s*(\S+)\s*$", s, re.M).group(1))
dx = (xmax - xmin) / nx
w_eq = (kappa_op / mu0) ** 0.5
print(f"  界面分辨率：w = {w_eq*1e6:.3f} um, dx = {dx*1e6:.3f} um -> {w_eq/dx:.2f} 单元/界面")
print(f"  d = sqrt(2*kappa/mu0) = {(2*kappa_op/mu0)**0.5*1e6:.3f} um")

# --- 元数据：把这一份算例的来龙去脉钉死 ---
meta = []
for f in ("gen_aniso_nonad.py", "splice_aniso_nonad.py", "stage1_meltpool_c.i",
          "stage1_meltpool_d.i"):
    h = hashlib.sha256((D / f).read_bytes()).hexdigest()
    meta.append(f"{h}  {f}")
(D / "case_meta.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")
print("  case_meta.txt 写好（4 个文件的 SHA256）")
PY

cp stage1_meltpool_d.i N.i
echo
echo "算例已生成：$D/N.i  ($(wc -c < N.i) 字节)"
echo "（生成文件与生产逐字相同；尺寸在运行时用命令行覆盖，见 README）"
