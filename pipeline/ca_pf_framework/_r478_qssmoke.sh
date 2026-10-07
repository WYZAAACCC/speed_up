#!/usr/bin/env bash
# R478 —— **准静态钟（1B）的冒烟与判据**（任务(2) ① 的验收）
#
# ## 预登记判据（**先写死**）
#
#   Q1【钟真的按温度走】`--qs-clock 1` 时，CSV 的 `t_s` 必须**只由温度决定**：
#       `t_s ≈ (T_start − T)/q`，且**单调**。
#       核对方式：用 `_r465_clockbudget.py` 的口径算 `t_s·q` 与 `ΔT` 是否一致。
#   Q2【分档数正确】档数 ≈ `(T_start − T_end)/ΔT`（ΔT = 1/α_KM）⇒ ±2 以内。
#       这是"每档恰好 1 根核"的直接体现（= 复现 C-2 的 T_k 序列）。
#   Q3【收敛判据真的在跑（负对照，必须能失败）】把 `--qs-tol` 压到 `1e-12`
#       且 `--qs-max-relax 5` ⇒ **每一档都必须撞到 max-relax 上限**
#       （步数 ≈ 档数 × 5）⇒ 若步数远小于此，说明判据根本没被求值。
#   Q4【默认路径不变】由 `_r30_regress.sh` 的"共有列逐位一致"把关（本脚本不重复）。
#
# ⚠ 全部用小盒子、少步数；**不与 abA 抢资源**（它仍在跑）。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=3
COMMON="--N 48 --dx-nm 62.5 --every 1 --snap-every 99999 --phi-band-every 99999 \
 --pair-every 0 --norm-smooth 0 --nthreads $NT --laths 1,1,2,2,3,3 \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 3 --nuc-fresh-every 4 \
 --alpha-km 0.041739 --T-end 600.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 --out $OUT"
# ⚠ 记账：① `--snap-every 0` 会让 `_bk_exp.py:1638` 的 `it % a.snap_every` 抛
#   ZeroDivisionError（**驱动里既有的边界缺口**，与 1B 改动无关）⇒ 用 99999 绕开。
#   ② `--every 1` 是**必须**的：第一版用 `--every 5` ⇒ CSV 行 ≠ 步 ⇒
#   我的判决工具把"行数/档数"当成"步数/档数"，算出 1.08 步/档这种自相矛盾的读数。
#   ⇒ **判据里凡涉及步数的，必须 `--every 1`**。

echo "=============================================================="
echo "== Q1/Q2：准静态钟正向（--qs-clock 1）  $(date '+%F %T')"
echo "=============================================================="
$PY -u _bk_exp.py $COMMON --qs-clock 1 --steps 2500 --tag qsA \
    > _w2_r478_qsA.log 2>&1
echo "qsA 退出码=$?"
# ⚠ 记账：第一版给 qsA 只留 900 步 ⇒ 只走完 **5 档**（末温 753 K），Q2 因此 FAIL。
#   实测每档 ≈ **180 步**（`--qs-tol 2e-3`、窗口 20）⇒ 10.4 档需要 ≈ 1900 步
#   ⇒ **那是我的预算给少了，不是钟坏了**。这里改成 2500 步重跑。

echo
echo "=============================================================="
echo "== Q3：负对照（--qs-tol 1e-12 --qs-max-relax 5 ⇒ 必须每档撞上限）"
echo "=============================================================="
$PY -u _bk_exp.py $COMMON --qs-clock 1 --qs-tol 1e-12 --qs-max-relax 5 \
    --steps 900 --tag qsB > _w2_r478_qsB.log 2>&1
echo "qsB 退出码=$?"
echo
echo "=============================================================="
echo "== 读数  $(date '+%F %T')"
echo "=============================================================="
for T in qsA qsB; do
  echo "---- $T ----"
  grep -cE '到达 T_end|提前结束' _w2_r478_$T.log 2>/dev/null | sed 's/^/   钟相关行数: /'
  grep -E '准静态钟|每档|到达 T_end|提前结束' _w2_r478_$T.log 2>/dev/null | head -4
  if [ -f $OUT/dry_$T/series.csv ]; then
    echo "   行数: $(wc -l < $OUT/dry_$T/series.csv)"
  fi
done
echo
echo "== 判据求值（Q1/Q2/Q3）=="
$PY -u _r478_qsverdict.py
