#!/bin/bash
# _r445_abfix.sh —— ★★★ **修正配置后重跑 A/B 双臂**（`§198`）
#
# ## 为什么要重跑（**我自己的配置错误，不是物理问题**）
# `_r444` 的参数 diff 查出**两处无意的偏差**：
#   1. `beta_h`：归档**全部**用 **6.477**（= `windowB_wulff.B_H_DEF`，
#      按 Wulff 长厚比 ≈3.51 标定），我用了 CLI 默认 **3.5**；
#   2. `gamma0`：归档**全部**用 **0.25**（文献主情景 Murzinova 2017 [0.201,0.337]），
#      我用了 CLI 默认 **0.15**（`params()` 里明确标着"**占位**"）。
#
# **后果（实测）**：驱动器在启动时就打印了
#   「⚠⚠ **C-5 不满足**：…需要 β_h ≥ 3.892/5.894，而当前 3.50
#     ⇒ 板条会增厚 ≈ e^{0.39}× / e^{2.39}× ⇒ **厚度判据 V-8b 不适用**」
# **而我没有处置**（自查错误 #62）。实测 abB step 660 的板条厚已达 **1418–2410 nm**
# （初始 510 nm）⇒ **"块 = 板条堆叠"的前提被破坏** ⇒ 形态量不可信。
#
# **用 6.477 时**：abA 需要 ≥5.894 ⇒ **满足**；abB 需要 ≥3.892 ⇒ **满足**。
#
# ## 本脚本新增的**防线**（防止同类错误再发生）
# 启动后**自动 grep 启动日志**，出现 `C-5 不满足` 就**当场中止并打印原因**。
# ⇒ 把"启动日志里的警告"变成**硬门禁**（`AGENTS.md` 教训 11/19 的同类纪律）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

echo "########## 0) 先干净地停掉旧的两条臂  $(date '+%F %T')"
# ⚠ 按 AGENTS.md：**不用 `pkill -f`**（会杀掉自己的 shell）；按 tag + cwd 精确定位。
for T in abA abB; do
  for P in $(ps -eo pid=,args= | grep -F -- "--tag $T" | grep -v grep | awk '{print $1}'); do
    CW=$(readlink /proc/$P/cwd 2>/dev/null || echo '?')
    echo "  kill pid=$P tag=$T cwd=$CW"
    kill -9 "$P" 2>/dev/null
  done
done
sleep 3
echo "  剩余 ab 进程：$(ps -eo args= | grep -cF -- '--tag ab' || true)"

echo
echo "########## 1) 启动前**预检**：`--beta-h` 必须 ≥ C-5 下界  $(date '+%F %T')"
"$PY" - <<'PYEOF'
import sys
sys.path.insert(0, '.')
import windowB_closure as CL
DX, T = 62.5e-9, 510e-9
BH, G0 = 6.477, 0.25
ok = True
for tag, steps in (('abA', 5922), ('abB', 800)):
    need = CL.beta_h_min(steps, DX, T)
    good = BH >= need
    ok &= good
    print('  %s: steps=%-5d C-5 需要 β_h ≥ %.3f；本次用 %.3f ⇒ %s'
          % (tag, steps, need, BH, '✅ 满足' if good else '❌ **仍不满足**'))
print('  gamma0 = %.2f（归档口径；默认 0.15 是 `params()` 明标的**占位**）' % G0)
sys.exit(0 if ok else 1)
PYEOF
[ $? -ne 0 ] && { echo "  ⛔ 预检不过，**不启动**"; exit 1; }

LATHS="1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11"
COMMON="--N 112 --dx-nm 62.5 --pair-every 20 --every 20 \
--norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
--laths $LATHS --plate-L 1000 --plate-W 500 --plate-T 510 \
--gamma0 0.25 --beta-h 6.477 \
--grow-stack --nuc-law athermal --nuc-init 6 --nuc-fresh-every 4 \
--alpha-km 0.041739 --T-end 298.0 --facet-proj 0 --facet-excl 0"

rm -rf _exp/_bk_mb/dry_abA _exp/_bk_mb/dry_abB
: > _r445_ab.log
echo
echo "########## 2) 启动两条臂（**已修正 beta_h / gamma0**）  $(date '+%F %T')" | tee -a _r445_ab.log
nohup "$PY" -u _bk_exp.py $COMMON --steps 5922 --snap-every 40 --cool-rate 2.3524e6 \
      --tag abA --out _exp/_bk_mb > _r445_abA.log 2>&1 &
echo "  abA pid=$!" | tee -a _r445_ab.log
nohup "$PY" -u _bk_exp.py $COMMON --steps 800 --snap-every 20 --cool-rate 1.7412e7 \
      --tag abB --out _exp/_bk_mb > _r445_abB.log 2>&1 &
echo "  abB pid=$!" | tee -a _r445_ab.log

echo
echo "########## 3) **门禁**：等启动日志出现 C-5 行，若报"不满足"就中止  $(date '+%F %T')"
sleep 75
FAIL=0
for T in abA abB; do
  if grep -q 'C-5 不满足' "_r445_${T}.log" 2>/dev/null; then
    echo "  ❌ $T：**C-5 仍不满足** —— 见下"
    grep -m1 'C-5' "_r445_${T}.log"
    FAIL=1
  elif grep -q 'C-5' "_r445_${T}.log" 2>/dev/null; then
    echo "  ✅ $T：C-5 通过"
    grep -m1 'C-5' "_r445_${T}.log"
  else
    echo "  ⚠ $T：日志里还没有 C-5 行（可能仍在构造阶段）"
  fi
  echo -n "     Traceback = "; grep -c Traceback "_r445_${T}.log" || true
done
if [ "$FAIL" -ne 0 ]; then
  echo "  ⛔ **门禁触发：中止本次启动**"
  for T in abA abB; do
    for P in $(ps -eo pid=,args= | grep -F -- "--tag $T" | grep -v grep | awk '{print $1}'); do
      kill -9 "$P" 2>/dev/null
    done
  done
  exit 2
fi
echo "  ⇒ 两条臂已通过门禁，继续跑。" | tee -a _r445_ab.log
