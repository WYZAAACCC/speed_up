#!/bin/bash
# _r579_par.sh --- ★ R579 **并行编排**：互不依赖的作业分组，用 taskset 绑到**互不相交**的核上同时跑。
#
# ## 为什么可以并行（判据为什么仍然有效）
# 本项目所有**有效**的性能判据都是**同一个作业内部的配对比值**（交错 A/B）。
# 绝对墙钟早已记为"跨会话不可比"（`AGENTS.md §7.5 P1`）。
# ⇒ 只要同一个作业的两臂绑在**同一组核**上，比值仍有效；作业之间只需**互不重叠**。
#
# ## 核分配（20 逻辑核，全部用上）
#   T  0-5   §(3) 六臂轮换 A/B（计时；4 worker + 主线程）        ~15 min
#   MA 6-9   N=160 内存清单 f64/nv=4 → f32/nv=4（**串行两道**）   ~9 min
#   MB 10-13 N=160 内存清单 f64/nv=8 → f32/nv=8（**串行两道**）   ~9 min
#   G  14-15 GPU 处置（§9）                                       ~4 min
#   P  16-17 §(7) 两个单变量实验                                  ~8 min
#   R  18-19 归档路径**逐位回归**（新开关必须不动默认路径）        ~15 min
#
# ## 为什么内存道要分两波（而不是 4 个进程一起上）
#   每个 N=160 构型峰值约 3–4 GB（`Lam` 1.18 GB + `lambda_packed` 内部临时量）。
#   4 个一起 ≈ 16 GB，加上 T/P/G/R 会逼近 WSL 的 23 GB ⇒ **有 swap 抖动 / 整机卡死的风险**
#   （`AGENTS.md §3.12` 记过 WSL 因内存压力整体无响应）。⇒ 两波，峰值控制在 ~8 GB。
#
# ## 口径记账
#   绑核 ⇒ **绝对墙钟只在批次内可比**。T 道与内存道并存 ⇒ 带宽被分享 ⇒ 比值噪声更大，
#   因此 T 的结论仍以"每轮配对中位 + 区间"给出，并与 R578 安静机器上的 1.064× 对照。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
OUT=_w2_r579_par
: > ${OUT}_orchestrator.log

say() { echo "$@" | tee -a ${OUT}_orchestrator.log; }

say "=== R579 并行批次 $(date '+%F %T') ==="
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a ${OUT}_orchestrator.log
say "  核分配：T=0-5 MA=6-9 MB=10-13 G=14-15 P=16-17 R=18-19"
say "  ⚠ 绑核 ⇒ **绝对墙钟只在批次内可比**；T 与内存道并存 ⇒ 比值噪声更大（只给区间）。"
free -m | head -2 | tee -a ${OUT}_orchestrator.log

# ---------------- Lane T：§(3) 六臂轮换 A/B ----------------
(
  taskset -c 0-5 env R578_ROUNDS=3 bash _r578_r3_ab.sh > ${OUT}_T.log 2>&1
  echo "T  rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PT=$!

# ---------------- Lane MA / MB：N=160 内存清单（各串行两道，两波控制内存）----------------
rm -f _w2_r579_one_*.json
(
  taskset -c 6-9 env R579_ONE=f64,4 R579_N=160 $PY _r579_mem160.py > ${OUT}_MA1.log 2>&1
  echo "MA1 rc=$? $(date '+%T')"
  taskset -c 6-9 env R579_ONE=f32,4 R579_N=160 $PY _r579_mem160.py > ${OUT}_MA2.log 2>&1
  echo "MA2 rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PMA=$!
(
  taskset -c 10-13 env R579_ONE=f64,8 R579_N=160 $PY _r579_mem160.py > ${OUT}_MB1.log 2>&1
  echo "MB1 rc=$? $(date '+%T')"
  taskset -c 10-13 env R579_ONE=f32,8 R579_N=160 $PY _r579_mem160.py > ${OUT}_MB2.log 2>&1
  echo "MB2 rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PMB=$!

# ---------------- Lane G：GPU 处置（§9）----------------
(
  taskset -c 14-15 env R579G_N=64 R579G_NV=24 $PY _r579_gpu.py > ${OUT}_G.log 2>&1
  echo "G  rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PG=$!

# ---------------- Lane P：§(7) 两个单变量实验 ----------------
(
  taskset -c 16-17 env R579E_N=64 $PY _r579_exp7.py > ${OUT}_P.log 2>&1
  echo "P  rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PP=$!

# ---------------- Lane R：归档路径逐位回归（新开关必须不动默认路径）----------------
(
  taskset -c 18-19 bash _r576_regress.sh > ${OUT}_R.log 2>&1
  echo "R  rc=$? $(date '+%T')"
) >> ${OUT}_orchestrator.log 2>&1 &
PR=$!

say "  已启动：T=$PT MA=$PMA MB=$PMB G=$PG P=$PP R=$PR"

# 内存看门狗（每 60 s 记一次；低于 1.5 GB 就报警）
(
  for i in $(seq 1 60); do
    sleep 60
    AV=$(free -m | awk '/^Mem:/{print $7}')
    echo "  [watch] $(date '+%T') avail=${AV}MB" >> ${OUT}_orchestrator.log
    [ "${AV:-9999}" -lt 1500 ] && echo "  ⚠⚠ 内存 < 1.5 GB！" >> ${OUT}_orchestrator.log
  done
) >> ${OUT}_orchestrator.log 2>&1 &
PW=$!

wait $PT $PMA $PMB $PG $PP $PR
kill $PW 2>/dev/null || true

say ""
say "=== 各道完成 $(date '+%F %T') ==="
for f in T MA1 MA2 MB1 MB2 G P R; do
  say "  ---- $f ----"
  tail -5 ${OUT}_$f.log 2>/dev/null | sed 's/^/    /' | tee -a ${OUT}_orchestrator.log
done

say ""
say "=== 汇总 N=160 内存报告（goal §5）==="
$PY _r579_report.py 2>&1 | tee -a ${OUT}_orchestrator.log

say ""
say "=== R579 并行批次 DONE $(date '+%F %T') ==="
