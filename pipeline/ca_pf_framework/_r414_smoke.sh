#!/bin/bash
# _r414_smoke.sh —— ★ **目标第 (1) 项：修正配置的"接线冒烟"**（先证明形核真的发生）
#
# ## 为什么先冒烟，不直接上大盒子
# goal 第 (1) 项要求打开 `--grow-stack` + `--nuc-law athermal` + `--nuc-init N`，
# 并**先验证形核事件真的发生**（上一轮我漏掉的检查）。
# 直接从 10 µm 盒子跑 400 步，若接线不对就是白烧几小时。
# ⇒ 先用 N=64（4 µm 盒，约 1/8 成本）跑 60 步，只看**事件行**。
#
# ## 判据（预先写死，跑完逐条核）
#   S-1 日志里 `形核事件`/`引擎形核`/`athermal 形核` 至少出现 **1** 次
#       （上一轮归档臂全部为 **0** —— 这就是缺陷①的直接证据）
#   S-2 `nreg`（或 `region` 里出现的标号数）**随时间增加** ⇒ 新场真的被占用
#   S-3 最终块数 > 初始块数（新块真的在**随机位点**长出来，不是只有原地的两片）
#   S-4 无 Traceback / 无顶层异常
#
# ⚠ 本脚本**只跑小盒子冒烟**，不是生产跑。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1
LOG=_r414_smoke.log
: > "$LOG"
{
  echo "############ 冒烟：N=64，4 µm 盒，60 步，形核三开关全开  $(date '+%F %T')"
  echo "  命令：--grow-stack --nuc-law athermal --nuc-init 8 --facet-proj 0 --facet-excl 0"
  echo
  timeout 3000 "$PY" -u _bk_exp.py \
    --N 64 --dx-nm 62.5 --steps 60 --every 5 --snap-every 20 --pair-every 20 \
    --norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
    --laths 1,1,2,2 --multi-block --block-gap-nm 1300 \
    --grow-stack --nuc-law athermal --nuc-init 8 \
    --facet-proj 0 --facet-excl 0 \
    --tag smoke1 --out _exp/_bk_mb
  _RC=$?
  echo
  echo "############ 退出码 = $_RC"
} >> "$LOG" 2>&1
echo "=== SMOKE DONE rc=$_RC ===" >> "$LOG"

echo "==== S-1 形核事件行 ===="
grep -nE '形核事件|引擎形核|athermal 形核|形核' "$LOG" | head -20
echo
echo "==== S-1 计数 ===="
echo -n "  '形核事件' 次数 = "; grep -c '形核事件' "$LOG" || true
echo -n "  'athermal 形核' 次数 = "; grep -c 'athermal 形核' "$LOG" || true
echo -n "  '被引擎拒' 次数 = "; grep -c '被引擎拒' "$LOG" || true
echo
echo "==== S-2/S-3 末态结构 ===="
grep -nE '块|nreg|blk_nprof|F3|nf3|cov_norm' "$LOG" | tail -25
echo
echo "==== S-4 异常 ===="
echo -n "  Traceback = "; grep -c 'Traceback' "$LOG" || true
echo -n "  顶层异常 = "; grep -cE '^(ValueError|TypeError|NameError|KeyError|IndexError|RuntimeError):' "$LOG" || true
echo
echo "==== 尾部 ===="
tail -25 "$LOG"
