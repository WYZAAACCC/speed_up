#!/bin/bash
# _r581_killtest.sh --- ★★★★★★ **goal 的头号场景：真的 `kill -9` 一次，再续跑，必须逐位相同**
#
# ## 为什么这一条不能省
# 前面所有验证（门 1 / 门 3）都是**让进程正常跑完**再从检查点续跑 ——
# 而 goal 逐字要的是：
# > **跑一段 → 存检查点 → **被杀/中断** → 从检查点恢复并继续，且续跑后的轨迹与"从未中断"逐位相同**
# **"被杀"与"正常退出"是两件不同的事**：
# * 被杀时 **`series.csv` 可能只写到一半**（最后一行可能截断）；
# * 被杀时**可能正在写检查点**（原子写要保证"要么旧帧完整、要么新帧完整"）；
# * 被杀时**内存里的驱动层状态可能领先于磁盘**（`--every` 与 `--ckpt-every` 不同步时）。
#
# ## 设计（三段）
# | 段 | 做什么 | 判据 |
# |---|---|---|
# | **K1** | **A 路**：一次跑完 24 步（真值，不被打断） | exit 0 |
# | **K2** | **B 路**：同配置跑，`--ckpt-every 4`，**跑到约 step 13 时 `kill -9`** | **必须真的被杀**（exit 137/非0） |
# | **K3** | **从 B 路最后一个完整检查点 `--resume` 续跑到 24** | **与 A 路逐位相同** |
#
# ## ★ 关键判据
# 1. **K2 确实是被杀的**（不是自己跑完的）—— 检查 exit code 与"末步 < 24"；
# 2. **K3 必须把断掉的那一段补齐**（从 `ckpt.step+1` 跑到 24）；
# 3. **K3 与 A 路在**共有 step** 上 `series.csv` 逐位相同**（NaN 感知 + 比符号位）；
# 4. **`ckpt/` 里**没有半截文件**（原子写的证据：`.tmp` 要么不存在、要么不参与恢复）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_kill
LOG=_w2_r581_kill.log
STEPS=24
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 2 --snap-every 100 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")
clean() { [ -d "$ROOT/dry_$1" ] && mv "$ROOT/dry_$1" "$ROOT/dry_$1_superseded_$(date '+%Y%m%d_%H%M%S')"; }

say '════ K1：A 路 —— **一次跑完** 24 步（真值）════'
clean killA
timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps $STEPS \
  --out "$ROOT" --tag killA --laths "$LATHS" > _w2_r581_kill_A.log 2>&1
say "  A exit=$?  末步=$(tail -1 "$ROOT/dry_killA/series.csv" 2>/dev/null | cut -d, -f1)"

say '════ K2：B 路 —— 同配置跑，**跑到中途 `kill -9`** ════'
clean killB
env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps $STEPS \
  --ckpt-every 4 --ckpt-keep 2 \
  --out "$ROOT" --tag killB --laths "$LATHS" > _w2_r581_kill_B.log 2>&1 &
BPID=$!
say "  B 的 pid = $BPID；等它写出**至少 2 帧**再杀"
for i in $(seq 1 200); do
  sleep 2
  NF=$(ls -1 "$ROOT/dry_killB/ckpt/" 2>/dev/null | grep -c '\.npz$')
  LAST=$(grep -oE '\[ckpt +[0-9]+\]' _w2_r581_kill_B.log 2>/dev/null | tail -1)
  if [ "${NF:-0}" -ge 2 ]; then
    say "  已有 $NF 帧（$LAST）⇒ **现在 `kill -9`**"
    break
  fi
  kill -0 "$BPID" 2>/dev/null || { say '  ⚠ B 自己结束了（没杀成）⇒ 这一轮不算'; break; }
done
kill -9 "$BPID" 2>/dev/null
for p in $(pgrep -f "dry_killB" 2>/dev/null); do kill -9 "$p" 2>/dev/null; done
wait "$BPID" 2>/dev/null
BRC=$?
say "  **B 被杀**：exit=$BRC（137 = SIGKILL 是预期的）"
say "  B 的 series 末步 = $(tail -1 "$ROOT/dry_killB/series.csv" 2>/dev/null | cut -d, -f1)（< $STEPS ⇒ 确实被打断）"
say '  ── 断点时的 ckpt/ 目录（**原子写的证据**）──'
ls -la "$ROOT/dry_killB/ckpt/" 2>/dev/null | sed 's/^/    /'
if ls -1 "$ROOT/dry_killB/ckpt/" 2>/dev/null | grep -q '\.tmp$'; then
  say '    ⚠ 有残留 `.tmp`（说明杀在写的中间）—— **不影响恢复**（恢复只认正式帧）'
fi

say '════ K3：**从最后一个完整检查点续跑**到 24 ════'
clean killC
timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py $CFG --steps $STEPS \
  --resume "$ROOT/dry_killB/ckpt" \
  --out "$ROOT" --tag killC --laths "$LATHS" > _w2_r581_kill_C.log 2>&1
say "  C exit=$?  末步=$(tail -1 "$ROOT/dry_killC/series.csv" 2>/dev/null | cut -d, -f1)"
grep -E '自动选|检查点 step=|从 step|驱动层已回填|P0 已回填|版本哈希' _w2_r581_kill_C.log 2>/dev/null \
  | sed 's/^/    /'

say '════ 逐位比较：C（被杀后恢复） vs A（从未中断） ════'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_killC/series.csv" "$ROOT/dry_killA/series.csv" step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致|共有 step|Vt |f_var|nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'

say '════ 汇总 ════'
say '  K2 真被杀 = 见上 exit/末步    K3 续跑 = 见上    逐位 = 见上"差异字段数"'
say '=== KILLTEST DONE ==='
