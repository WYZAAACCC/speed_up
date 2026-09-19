#!/bin/bash
# 回到**非 AD 版**做生产跑。理由（都有实测支撑）：
#
#   AD 版（雅可比精确）的实际代价超过收益：
#     * 每牛顿迭代 6-7 分钟（L 依赖 8 个 eta + T + 梯度 -> 每单元 44 维对偶数，
#       解析表达式解释执行）
#     * **线性求解反而更难**：非 AD + l_max_its=300 是零失败，AD + 300 有
#       2 次 DIVERGED_ITS 300 -> 牛顿迭代成对出现、每步只降约 0.1%，
#       54 分钟才走到迭代 8
#     * MPI -n 8 反而更慢（25 分钟没走完迭代 1）
#
#   【2026-09-19 已修】原文这里写的是
#        「非 AD 版唯一的缺陷是 ACGrGrPoly 丢 dL/deta_j（雅可比误差 1.2e-3）」
#      **这句话有两处不对，现在都能定案了**：
#
#      (1) **缺陷本身说少了**。核对 MOOSE 源码后确认 `ACGrGrPoly` 丢**两类**项：
#            (a) (∂L/∂η_j)·F_η  —— 它覆盖了 ACBulk::computeQpOffDiagJacobian 却没调它
#            (b) (∂γ/∂η_j)·F_η  —— 它把 gamma_asymm 当常数，
#                                   而 D 版的 `gamma_aniso` 是依赖 η 的
#          并且算例里 `[grN_poly]` **根本没写 coupled_variables**，
#          所以 (a) 连原料（_dLdarg）都是空的。
#          C 版之所以没暴露：γ 是常数、L 只依赖 T ⇒ 两项恰好都恒等于零。
#
#      (2) **但它的影响说大了**。本轮实测（validated/run_jacfix_test.sh，
#          同一二进制同一算例只差核类型）：缺项只有 **~5e-7（相对）**，
#          FD 比值 **0.0208202 → 0.0208202，一位都没变**。
#          ⇒ **它不是 T1 过不了的原因**，那句 1.2e-3 从来就只是引用、没人测过。
#          ⚠ 所以：**别把 "T1 过不了" 归因到这一条上**——
#            主导误差还没定位（见 VALIDATION_STATUS.md §1.4 的排除表）。
#
#      **修法仍然保留**（它是对的、零代价、残差逐位不变）：
#      `pipeline/app/` 里的自建 MOOSE 核 `ACGrGrPolyJ`，由本脚本自动替换进去。
#      所以本脚本现在跑的是 `gb_jac-opt`，不再是 `phase_field-opt`。
#
#   **材料值已逐位验证与 AD 版相同**（kappa_op/gamma_asymm/L 的 max/min 全一致），
#   所以物理不变；差的是雅可比完备性，影响收敛速率、不影响收敛解。
#
#   ⚠⚠ 【2026-09-18 Gate 0 更正】原文这里写的是
#        「-> 牛顿残差地板 7.3e-07（只比 nl_abs_tol=1e-7 高 7 倍）
#          => 把 nl_abs_tol 放到 1e-6 即可推进」
#      **这个归因已被实测推翻。** 残差地板来自 **ASM/ILU 预条件子**，不是
#      雅可比不完备：非 AD + MUMPS 能**二次收敛到 4.01e-10**。
#      （AD 的 ||J-Jfd||=3.2e-08 对非 AD 的 1.2e-3 这个对照仍然成立、仍可写进
#       论文——但它证明的是**雅可比完备性差异**，不是残差地板的存在。）
#      ⇒ **不得**据此把 nl_abs_tol 放宽到 1e-6。生产值就是源文件里的 1e-9。
#
#   ⚠ 生产版生成器已冻结入仓库：pipeline/frozen/（含 SHA256）。
#     本脚本原先从 /root/work/bak/ 取，那里**无版本管理**、随时可能丢失。
#     详见 frozen/README.md 与 GATE0_PROGRESS.md。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
# 【2026-09-19】改用自建 app 的二进制：它 = phase_field-opt 的全部对象
# + 本项目的 ACGrGrPolyJ（雅可比补全核）。理由见文件头。
# ⚠ 进程名也跟着变了，下面所有 pgrep 都已同步改成 gb_jac-opt。
MOOSE=/root/projects/gb_jac/gb_jac-opt
[ -x "$MOOSE" ] || {
  echo "错误：找不到 $MOOSE。"
  echo "      先跑： bash /mnt/f/speed_up/pipeline/app/build_app.sh"
  exit 1; }
# 确认补全核真的在这个二进制里（构建失败会静默退化成只有 phase_field 的对象集）
"$MOOSE" --registry 2>/dev/null | grep -q "ACGrGrPolyJ" || {
  echo "错误：$MOOSE 里没有注册 ACGrGrPolyJ —— app 没建好。"; exit 1; }
# ⚠ 目标目录。脚本开头会 `rm -rf "$D"`，所以试跑时**务必**用环境变量指到别处：
#       D=/root/work/s1d_test bash run_nonad_prod.sh
#   默认仍是生产目录，以免改变既有用法。
D="${D:-/root/work/s1d_nonad}"

# =============================================================================
# 【Gate 0 修正】清理残留进程：**只清本目标目录的**，不再杀掉全机器
# =============================================================================
# 原版是：
#     pgrep -f 'phase_field-opt -i' > /tmp/mp.txt 2>/dev/null
#     xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
# 它**无条件杀掉整台机器上的每一个 MOOSE 进程**（只按命令行匹配，不看目录）。
#
# 后果（实测，代价很大）：为了测试本脚本，用 `head -N` 截断后反复运行它，
# **每一次都把正在跑的长算例杀掉了**。全尺寸跑前后"神秘地"死了四次
# （退出码 137，非 OOM、非 WSL 重启），我当时误判成"外部 SIGKILL、原因未定"，
# 还把这个错误结论写进了文档。真相就是这段代码。
#
# ⇒ 现在按 **cwd 是否等于 $D** 精确限定：只清本目录的残留，别人的算例不动。
#    另外打印被杀的 PID 与目录，让"谁杀了谁"永远可见。
KILLED=0
for P in $(pgrep -x gb_jac-opt 2>/dev/null); do
  CWD=$(readlink /proc/$P/cwd 2>/dev/null | sed 's/ (deleted)$//')
  if [ "$CWD" = "$D" ]; then
    echo "  停掉本目录（$D）的残留进程 pid=$P"
    kill -9 "$P" 2>/dev/null
    KILLED=$((KILLED + 1))
  fi
done
sleep 3
echo "已停本目录残留进程 $KILLED 个；机器上仍有 $(pgrep -xc gb_jac-opt 2>/dev/null || echo 0) 个 MOOSE 在跑（不属于本目录，未动）"

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# =============================================================================
# 【Gate 0 步骤 2b 修正】生成器与源输入一律从**仓库**取，不再从 WSL 的临时目录取
# =============================================================================
# 原版是：
#     cp /root/work/bak/gen_aniso.py /root/work/bak/splice_aniso.py .
#     cp /root/work/s1d_w/stage1_meltpool_c.i .
#     cp /root/work/s1d_w/columnar_seeds.csv .
# 两个后果（都已实测确认，不是推测）：
#
#   1. **源输入文件漂移（严重）**：s1d_w 的 c.i 是 2026-09-17 22:16 的快照，
#      里面溶质还是**占位参数** c0 = 0.35、A_part = 0.45（k = 0.5），
#      而仓库版 2026-09-18 已换成 Ti64 真实值 c0 = 0.036、A_part = 0.264（k = 0.63）。
#      ⇒ 2026-09-18 那次生产跑（/root/work/s1d_nonad，产物 N.e / N_out.csv）
#        用的是占位参数，**不是** Ti64 真实值。
#        反证：N_out.csv 首行 total_solute = 2.2575e-08 = 0.35 × 域面积 6.45e-8。
#      ⇒ 该批数据对"溶质物理"而言不可用；作为纯数值测试仍有效。
#
#   2. 生成器来自 /root/work/bak/（**无版本管理**，随时可能丢失/被改）。
#      已冻结入 pipeline/frozen/ 并登记 SHA256。
#
# 现在改为：从仓库取 + **哈希校验**。哈希不符就报错退出，
# 而不是像以前那样悄悄用另一个版本跑完。
REPO=/mnt/f/speed_up/pipeline
cp "$REPO/frozen/gen_aniso_nonad.py"    .
cp "$REPO/frozen/splice_aniso_nonad.py" .
cp "$REPO/stage1_meltpool_c.i"          .
cp "$REPO/columnar_seeds.csv"           .

# --- 哈希校验：冻结的生成器必须与登记值逐位一致 ---
#   注意不能写成 `sha256sum -c | grep -v ': OK$' && exit 1` —— 管道取的是 grep 的
#   退出码，`cd` 失败或 frozen/ 不存在时 grep 拿到空输入会返回 1，于是**假通过**。
#   必须直接取 sha256sum -c 的退出码。
if ! HASHOUT=$( cd "$REPO/frozen" && sha256sum -c SHA256SUMS 2>&1 ); then
  echo "错误：frozen/ 下的生成器哈希校验失败 —— 文件被改过，或 frozen/ 不存在。"
  echo "$HASHOUT" | grep -v ': OK$'
  echo "先查清再跑（见 frozen/README.md）。"
  exit 1
fi
echo "生成器哈希校验通过（frozen/SHA256SUMS）"

# --- 源输入必须已是 Ti64 真实值，否则拒绝跑 ---
# ⚠ **必须用前缀匹配，不能要求闭合引号。** 2026-09-19 合入 Phase 3 后，
#   `f_loc` 的常量表变成了 `'0.9 0.036 0.264 -5e-11 4e-06'`（多了 Omega0/wgb），
#   原来那句 `grep -q "constant_expressions = '0.9 0.036 0.264'"`
#   会把**合法**输入判成"参数不对"而拒绝跑 —— 是冒烟测试抓出来的。
grep -qE "^[[:space:]]*constant_expressions = '0\.9 0\.036 0\.264" stage1_meltpool_c.i || {
  echo "错误：stage1_meltpool_c.i 的溶质参数不是 Ti64 真实值"
  echo "      （期望 k_c=0.9, c0=0.036, A_part=0.264 ⇒ k=0.63）。"
  echo "      若确实要用占位参数（k=0.5），**必须显式说明理由**，不要默认跑。"
  exit 1; }
grep -q "value = 0.036" stage1_meltpool_c.i || {
  echo "错误：c 的初始条件不是 0.036"; exit 1; }
echo "源输入校验通过（Ti64 真实溶质参数 k=0.63）"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
# 【Gate 0】用的是 frozen/ 里的非 AD 生产版，**不能传 --texture**
#   （该版没有这个参数，默认就是 [0,90) 内均匀铺开）。
#   ⚠ 仓库根目录的 gen_aniso.py 是 AD 版，且默认 --texture fiber —— 取向集完全不同。
#     详见 frozen/README.md 的三版取向集实测对照。
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i > gen.log 2>&1 || { echo "gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso_nonad.py >> gen.log 2>&1 || { echo "splice 失败"; tail -5 gen.log; exit 1; }
grep -E "自检|kappa_op   :|gamma_asymm:|最大相对误差" gen.log | head -5

# =============================================================================
# 【2026-09-19】把 ACGrGrPoly 换成 ACGrGrPolyJ（雅可比补全核）
# =============================================================================
# 为什么必须由脚本做、不能靠人工：splice 的职责是**逐字复刻** GrainGrowthAction
# 建的三个核（TimeDerivative / ACGrGrPoly / ACInterface），它不知道本项目
# 补了一个雅可比更全的核。留人工就会漂移 —— 这正是 Gate 0 要消灭的东西。
#
# 替换脚本自己会核对「恰好 8 处、无残留 ACGrGrPoly」，核不上就报错退出。
# 它同时写出 diff，便于复查"到底改了哪几行"。
python3 "$REPO/validated/make_jacfix.py" \
        --src stage1_meltpool_d.i --out stage1_meltpool_d.i.jac --diff >> gen.log 2>&1 \
  || { echo "jacfix 失败"; tail -8 gen.log; exit 1; }
mv stage1_meltpool_d.i.jac stage1_meltpool_d.i
echo "雅可比补全核已替换（diff: stage1_meltpool_d.i.jac.diff）"

# =============================================================================
# 【2026-09-20 T1b 修复】把「经 material_property_names 的链式法则不进雅可比」的三处链拆平
# =============================================================================
# `DerivativeParsedMaterial` **只对「表达式里字面出现的变量」发射导数**。
# 表达式里只有别的材料属性时**一个导数都不发射**，而生产核明确在索取：
#     [grN_int]     ACInterface(variable_L=true)  → dL/dgr0, d^2L/dgr0^2
#     [coupled_res] SplitCHWRes(gr0..gr7)         → dM/dgr0
#     [grN_antitrap] AntitrappingCurrent          → dF_at/dgr*
# ⇒ 求到的是**静默的零** ⇒ **雅可比与残差不一致**。
#
# 判据（validated/run_jacchain_check.sh，三条全过）：
#   ① 结构：修后三处导数都在 `[Debug] show_material_props` 的产出清单里，
#      且**负对照（未修档）确实一个都没有**
#   ② 回归：观测量**逐位相同** ⇒ 只改了雅可比、残差没动
#   ③ 代价：86×30 上 4s → 26s（建材料的固定开销），**没有**出现"求导树爆炸"
#
# 也是必须由脚本做：`L2a`/`align4` 是 splice 生成的，人工改会漂移。
python3 "$REPO/validated/make_jacchain.py" \
        --src stage1_meltpool_d.i --out stage1_meltpool_d.i.jc >> gen.log 2>&1 \
  || { echo "jacchain 失败"; tail -12 gen.log; exit 1; }
mv stage1_meltpool_d.i.jc stage1_meltpool_d.i
echo "材料链已拆平（diff: stage1_meltpool_d.i.jc.diff）"

python3 - <<'PY'
import re, sys
s = open("stage1_meltpool_d.i", encoding="utf-8").read()

# --- 1. 核必须是修好的非 AD 版 ---
assert s.count("type = TimeDerivative") == 8, "核没修好（缺 TimeDerivative）"
assert "variable_L = true" in s, "缺 variable_L"
assert s.count("type = ADGrainGrowth") == 0, "这是 AD 版，不是非 AD 版"

# --- 1b. 【2026-09-19】雅可比补全核已替换（上一步 make_jacfix.py 做的）---
assert s.count("type = ACGrGrPolyJ") == 8, \
    f"ACGrGrPolyJ 有 {s.count('type = ACGrGrPolyJ')} 处，期望 8 —— jacfix 没生效"
assert s.count("type = ACGrGrPoly\n") == 0, "还有裸 ACGrGrPoly 残留"

# --- 1c. 【2026-09-20 T1b 修复】材料链已拆平（上一步 make_jacchain.py 做的）---
#   判据：L_aniso / solute_mobility / at_susc 的表达式里必须**字面含 gr0**。
#   否则导数不发射 ⇒ 雅可比与残差不一致（静默出错）。
def _blk(name, txt):
    m = re.search(rf"^[ \t]*\[{name}\](?P<b>(?:.*?\n)*?)^[ \t]*\[\][ \t]*$", txt, re.M)
    assert m, f"找不到块 [{name}]"
    return m.group("b")

for _n in ("L_aniso", "solute_mobility"):
    _b = _blk(_n, s)
    assert re.search(r"expression\s*=\s*'[^']*gr0", _b), \
        f"[{_n}] 的表达式里没有字面变量 gr0 ⇒ jacchain 没生效（导数仍不会发射）"
# 抗截留项是可选的（尚未合入生产）
if "property_name = F_at" in s:
    _b = _blk("at_susc", s)
    assert re.search(r"expression\s*=\s*'[^']*gr0", _b), \
        "[at_susc] 的表达式里没有字面变量 gr0 ⇒ jacchain 没生效"
# coupled_variables 必须**逐个**写在 [grN_poly] 块里：否则 _dLdarg 是空的，
# (∂L/∂η_j) 那项照旧缺 —— 和 P0-1 是同一个病。
# ⚠ 不能简单地数全文里 `coupled_variables = 'T gr` 的出现次数：实测是 **18** 处
#   （8 个 _poly + 8 个 _int + 2 个材料块），写成 `== 8` 会**假失败**。
#   所以按块检查。
for k in range(8):
    m = re.search(rf"\[gr{k}_poly\](.*?)\n  \[\]", s, re.S)
    assert m, f"找不到 [gr{k}_poly] 块"
    assert "type = ACGrGrPolyJ" in m.group(1), f"[gr{k}_poly] 不是 ACGrGrPolyJ"
    assert "coupled_variables = 'T gr" in m.group(1), \
        f"[gr{k}_poly] 缺 coupled_variables —— (∂L/∂η_j) 项拿不到原料"

# --- 2. 【Gate 0 修正】生产值只**断言**，不覆盖 ---
#   原版这里用 re.sub 把 l_max_its / l_tol / nl_abs_tol / end_time **无条件覆盖**，
#   其中
#       s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-6", s, flags=re.M)
#   把源文件里的值**重新写回 1e-6**（理由是那条已被推翻的"7.3e-07 残差地板"）。
#   后果：源文件里无论写什么都会被静默丢弃 —— "把生产值同步进源文件"永远无效。
#   这正是 Gate 0 要消灭的配置漂移，所以改成断言：
#   源文件是**唯一真源**，漂了就报错退出，而不是悄悄改掉。
EXPECT = {
    "l_max_its":  "300",     # ASM/ILU 下外 GMRES 需要更多迭代（实测 30 太小）
    "l_tol":      "1e-6",
    "nl_abs_tol": "1e-9",    # 两份专家评审一致要求；非 AD + MUMPS 实测可达 4.01e-10
    "nl_rel_tol": "1e-8",
    "dtmax":      "2e-6",    # 界面弛豫时间约束，两份评审都明确不要放宽到 4e-6
    "end_time":   "6.5e-4",
}
for k, want in EXPECT.items():
    m = re.search(rf"^  {k} = (\S+)\s*$", s, re.M)
    if not m:
        sys.exit(f"错误：stage1_meltpool_d.i 里找不到 Executioner/{k}")
    if m.group(1) != want:
        sys.exit(f"错误：Executioner/{k} = {m.group(1)}，期望 {want}。"
                 f" 源文件 stage1_meltpool_c.i 已漂移 —— 先核对再跑，不要在本脚本里覆盖。")
m = re.search(r"^    dt = (\S+)\s*$", s, re.M)
if not m or m.group(1) != "1e-7":
    sys.exit(f"错误：初始 dt = {m.group(1) if m else '(缺)'}，期望 1e-7")

# --- 3. 只改真正属于"本次运行"的东西：输出名 ---
s = s.replace("file_base = stage1d", "file_base = N")
if "file_base = N" not in s:
    sys.exit("错误：没能把 file_base 改成 N（splice 的命名可能变了）")

# --- 4. 【2026-09-18 用户决定】档案密度：每步都存，取消原来的 1 -> 5 降频 ---
#   源码 stage1_meltpool_c.i 写的就是 time_step_interval = 1，理由是
#   「面拓扑每步都在变，隔步存会漏掉大部分拓扑事件，而转移算子正是靠这些事件训练的」。
#   本脚本原来用 re.sub 把它降到 5（磁盘代价考虑），**与源码意图矛盾**。
#   用户已明确：**取 1，每一步都保存**。故删掉覆盖，改为断言。
m = re.search(r"^    time_step_interval = (\S+)\s*$", s, re.M)
if not m:
    sys.exit("错误：stage1_meltpool_d.i 的 [Outputs][exo] 里找不到 time_step_interval")
if m.group(1) != "1":
    sys.exit(f"错误：time_step_interval = {m.group(1)}，期望 1（每步都存，用户 2026-09-18 决定）。"
             f" 源文件 stage1_meltpool_c.i 已漂移 —— 先核对再跑。")
print("  档案密度：time_step_interval = 1（每步都存）—— 取自源文件")

# --- 4b. 【Gate 0 §9.1】检查点必须按**步数**存，不能按墙钟 ---
#   全尺寸跑两次被外部 SIGKILL（137，原因未定）。而 Checkpoint 把
#   wall_time_interval 默认成 3600 s —— 对 ~4.5 min/步 等于 1 小时才存一次，
#   老生产跑 5 小时只留下 N_out_cp/0066 与 0090 两个检查点。
#   Output.C:138-141 的逻辑决定：**必须显式设 time_step_interval** 才按步存。
mck = re.search(r"\[checkpoint\](.*?)\n\s*\[\]", s, re.S)
if not mck:
    sys.exit("错误：缺少 [Outputs][checkpoint] —— 长跑被外部杀掉就没法续跑")
if not re.search(r"^\s*time_step_interval\s*=", mck.group(1), re.M):
    sys.exit("错误：[checkpoint] 没有显式 time_step_interval —— "
             "Checkpoint 默认按墙钟 3600 s 存一次，对约 4.5 min/步 的全尺寸跑"
             "等于 1 小时才存一次。续跑粒度必须是步数。")
print("  检查点：按步数存（可 --recover 续跑）")

# --- 5. 【2026-09-18】界面分辨率核算（**只报告，不阻断**）---
#   平衡界面宽 w = sqrt(kappa_op/mu0)。通行判据：一个界面内应有 4~8 个单元。
#   实测（GATE0_PROGRESS.md §6.5）：生产配置 w = 1.414 um、dx = 1.0 um
#   -> 仅 1.41 个单元，**欠解析 3~6 倍**。
#   后果（已实测）：序参量在晶界处越界 2~7%，Sigma(eta^2) 最大 1.14。
#   而解析解给出 Sigma(eta^2) 的平衡范围是 [0.5, 1.0]（单晶界中点 0.5、
#   三叉晶界 0.4286、晶粒内 1.0）—— **>1 一定是数值伪影**。
#   本脚本不在此处阻断：改变 wGB 会同时动 kappa/mu0/L，属于 Gate 1/2 的
#   参数一致性问题，不该在 Gate 0 里顺手改。但每次运行都把数字打出来，
#   避免它继续隐形（它同时影响界面动力学，不只是越界）。
def block(text, name):
    """按行扫描取 [name] ... [] 之间的内容（比正则稳：正则的 \\s*$ 会吞掉换行）。"""
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

# ⚠ 这是**信息性诊断，绝不能搞崩生产流程** —— 整段包在 try 里。
#   踩过的坑：splice 生成 d.i 时会**删掉 [consts]**（换成 kappa_aniso/gamma_aniso），
#   所以按 [consts] 找 kappa_op 会拿到空串。改为从 d.i 文件头的注释里读
#   （gen_aniso.py 生成的那行 `#   [consts]     kappa_op=1.8e-6, gamma_asymm=1.5`）。
try:
    # 【2026-09-18 ④ 修复】块名改了：barrier_mu -> barrier_muT（性质是 mu_T），
    #   另有一个**正常数**势垒 [mu_barrier_const] 的 mu = mu0。
    # ⚠ block() 用的是 ln.strip() == "[name]" 精确匹配，所以名字必须完全对上；
    #   对不上会静默返回空串 -> 整段诊断被 except 吞掉。
    mu0 = float(re.search(r"constant_expressions = '(\S+)", block(s, "barrier_muT")).group(1))
    mu_const = float(re.search(r"prop_values = '(\S+)'", block(s, "mu_barrier_const")).group(1))
    # ④ 的自洽条件：ACGrGrPoly 的常数势垒必须与熔化开关的 mu0 逐位相同，
    # 否则 f_新 = mu·Ση⁴/4 − mu_T·Ση²/2 + mu·γΣ 的 Landau 结构被破坏。
    if abs(mu_const - mu0) > 1e-12 * abs(mu0):
        sys.exit(f"错误（④ 修复自洽性）：[mu_barrier_const] mu={mu_const:.6g} 与 "
                 f"[barrier_muT] mu0={mu0:.6g} 不一致。两者必须逐位相同，"
                 f"否则自由能不再是 Landau 形式。拒绝运行。")
    # ⚠ 必须读 GENERATED_PARAMS，不能读文件头那行 `[consts] kappa_op=1.8e-6`
    #   —— 那是**静态模板文本**（描述 C 版基线），不随 --wgb 变化。
    # ⚠⚠ 【2026-09-19 修正】下面这段原先**从来没生效过**。
    #   它先找 `GENERATED_PARAMS wgb=... kappa_op_iso=... mu0=...` 这一行，
    #   但**拼接器根本不输出这一行**（已核对：d.i 里 grep 不到）。
    #   于是 mu0_gen 永远是 None，`mu0 一致性`那条硬失败被跳过；
    #   代码落到 else 分支，读的是**文件头那行静态模板注释**
    #   `[consts] kappa_op=1.8e-6` —— 上面 233-234 行的注释自己就写了
    #   "那是静态模板文本（描述 C 版基线），不随 --wgb 变化"。
    #   ⇒ 后果：把 --wgb 改成非 4 µm 而忘了同步 [barrier_muT] 的 mu0，
    #     脚本**不会拦**，会算出一套晶界能错误的算例，而且看起来一切正常。
    #
    #   现在改为读**生成器自己打印的 mu_qp**（gen.log）。它由生成器真算出来，
    #   且生成器自己断言它必须逐位等于算例的 mu0。不依赖任何静态注释，
    #   也不需要改冻结的生成器。
    mu0_gen = None
    kappa_op = None
    try:
        genlog = open("gen.log", encoding="utf-8", errors="replace").read()
        mk = re.search(r"kappa_op\s*:\s*(\S+)", genlog)
        if mk:
            kappa_op = float(mk.group(1))
        mq = re.search(r"mu_qp\s*:\s*(\S+)", genlog)
        if mq:
            mu0_gen = float(mq.group(1))
    except Exception:
        pass
    if kappa_op is None:
        raise ValueError("gen.log 里找不到 kappa_op 自检行 —— 生成器输出格式变了？")
    # mu0 一致性：生成器的 MU_QP = 6σ/wGB 必须逐位等于算例 [barrier_muT] 的 mu0。
    # 不一致 => (a*,gamma*) 与 mu 不自洽 => 晶界能不是目标值。**硬失败**。
    # 【2026-09-19】mu0_gen 取不到时也**硬失败**（不再静默跳过）——
    #   正是"取不到就跳过"让这段检查白挂了不知道多久。
    if mu0_gen is None:
        sys.exit("错误：gen.log 里找不到 mu_qp —— 无法核对 mu0 自洽性。"
                 "宁可拒绝运行，也不要带着未核对的晶界能往下跑。")
    if abs(mu0_gen - mu0) > 1e-9 * abs(mu0):
        sys.exit(f"错误：mu0 不自洽 —— 生成器 MU_QP={mu0_gen:.6g} 但 "
                 f"[barrier_muT] mu0={mu0:.6g}。改了 --wgb 就必须同步改 barrier_muT"
                 f"（mu0 = 6σ/wGB）。当前配置会产生错误的晶界能，拒绝运行。")
    print(f"  mu0 自洽：生成器 mu_qp = 算例 mu0 = {mu0:.6g}（逐位一致）")
    nx = int(re.search(r"^\s+nx = (\d+)\s*$", s, re.M).group(1))
    xmin = float(re.search(r"^\s+xmin = \s*(\S+)\s*$", s, re.M).group(1))
    xmax = float(re.search(r"^\s+xmax = \s*(\S+)\s*$", s, re.M).group(1))
    dx = (xmax - xmin) / nx
    w_eq = (kappa_op / mu0) ** 0.5
    npp = w_eq / dx
    flag = "OK" if npp >= 4.0 else "⚠ 欠解析（判据 4~8）"
    print(f"  界面分辨率：w = sqrt(kappa/mu0) = {w_eq*1e6:.3f} um, dx = {dx*1e6:.3f} um"
          f" -> {npp:.2f} 单元/界面  {flag}")
except Exception as _e:
    print(f"  ⚠ 界面分辨率核算跳过（解析失败：{_e}）—— 不影响运行")

open("N.i", "w", encoding="utf-8").write(s)
print("N.i 写好：非AD | l_max_its=300 | nl_abs_tol=1e-9 | dt=1e-7 | end_time=6.5e-4")
print("  以上全部取自源文件（本脚本只断言不覆盖）；仅 file_base 被改为 N。")
PY

echo "=== 启动生产跑（单进程）==="

# 【Gate 0】峰值内存采样 —— roadmap 要求"每个算例自动输出峰值内存"。
#   写 peak_kb.txt，gate0_report.py 直接读它（无需改报告端）。
#   方法沿用 bench_mpi_mem.sh:45-53：读 /proc/<pid>/status 的 VmRSS，多进程求和。
#   ⚠ 必须用 pgrep -x（精确匹配进程名）：`pkill -f phase_field-opt` 会连
#     命令行里含该字符串的**本脚本自己**一起杀掉（已踩过）。
( PEAK=0
  while true; do
    SUM=0
    for P in $(pgrep -x gb_jac-opt 2>/dev/null); do
      R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
      [ -n "$R" ] && SUM=$((SUM + R))
    done
    [ "$SUM" -gt "$PEAK" ] && PEAK=$SUM && echo "$PEAK" > peak_kb.txt
    pgrep -x gb_jac-opt > /dev/null || break
    sleep 5
  done ) &
SAMPLER=$!

setsid --wait "$MOOSE" -i N.i > run.log 2>&1 &
MPID=$!
echo "MOOSE pid=$MPID  内存采样器 pid=$SAMPLER"
for k in $(seq 1 60); do
  sleep 300
  NS=$(grep -ac "Solve Converged" run.log 2>/dev/null)
  TS=$(grep -a "^Time Step" run.log 2>/dev/null | tail -1)
  NR=$(grep -a "Nonlinear |R|" run.log 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | tail -1)
  echo "[$((k*5)) 分钟] 收敛步=$NS | $TS | 末次牛顿:$NR"
  kill -0 $MPID 2>/dev/null || { echo "MOOSE 已退出"; break; }
done

kill $SAMPLER 2>/dev/null

# =============================================================================
# 【Gate 0】跑完自动出诊断汇总
# =============================================================================
# ⚠ 必须切回 conda 环境 `moose`：前面生成器用的是 `ml`（有 torch），
#   但 gate0_report.py 需要 netCDF4，而 `ml` 里没有。
echo
echo "=== 诊断汇总（gate0_report.py）==="
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
python3 "$REPO/gate0_report.py" . || echo "(诊断汇总失败 —— 不影响算例本身，产物仍在)"
echo
echo "峰值内存记录：$(cat peak_kb.txt 2>/dev/null || echo '(无)') KB"
