#!/bin/bash
# _t10_eta253.sh --- ★ 框架修复的实现：η 由唯象 0.375 → **推导值 0.253**，重跑 10 µm 盒
#
# ═══════════════════════════════════════════════════════════════════════════════
# ## 这个改动的物理依据（推导见 `R601_TRIP_THEORY.md`，自检脚本 `_t10_trip_derive.py` / `_t10_trip_v5p.py`）
#
# 模型现状：**纯线弹性、没有塑性耗散通道** ⇒ 弹性罚能 ≈ 驱动力的 2.6 倍
#   ⇒ 板条在长大中**局部掐断** ⇒ 「一个相场里多个马氏体板条」
#      （10 µm 盒 step 100 实测：45 个场只有 27% 是严格单一连通体）
#
# 拟加入的物理：小应变分解 `ε = ε^e + ε⁰(φ) + ε^p`、率无关 J2 关联流动。
# 推导得到两条**已被自检证实**的结论：
#   (a) **径向回退这条路无增量**：立方对称使 12 个变体的 `σ_eq(C:ε⁰_k)` **全等于 6.669 GPa**
#       （V5 实测跨度 0.0000）；对总应力场回退，最优常数 η 的**残差也只有 0.26%**（V5′）
#       ⇒ **不做**（省下一整套新求解器）。
#   (b) **真正的落点是静水/偏量分解**：完全自协调组态下
#         `σ_eq = 0.0000 GPa`（**偏量恰好抵消**，C4：Σ dev(ε⁰_k) = 0）
#         但 `w_el = 7.4742e7 J/m³ ≠ 0` —— 残留 **10.0%**，那是**静水**部分
#       而 J2 判据是**偏量的** ⇒ **弛豫不到静水** ⇒
#         `w_el^物理 = 7.47e7`（全约束 7.467e8 的 10%）
#       ⇒ **η_物理 = 7.47e7 / 2.96e8 = 0.253**（2.96e8 = 引擎实测的单板条 |ed|）
#
# ⚠ **健壮性**：结论**对 σ_y 不敏感** —— 只要 `σ_y²/(6μ) ≪ w_偏量`，
#   η_物理 就只由**静水占比**决定；σ_y 高到约 **2 GPa** 该式仍成立。
#   ⇒ 唯一缺的外部量 `σ_y(873 K)` 的文献出处**待补**（候选已登记），不阻塞本改动。
#
# ⚠ **必须标明的近似**：把引擎实测 `|ed| = 2.96e8` 当作"几何弛豫后、塑性弛豫前"的值
#   是近似（真实塑性还会改几何）⇒ **由判据 J1 检验**：若 J1 FAIL，说明该近似不成立。
# ═══════════════════════════════════════════════════════════════════════════════
#
# ## 预登记判据（**写死，可 FAIL，不得放宽**）
#   **J1** 「一场一板条」占比 **> 27%**（同口径：step 100、逐 26-连通分量、排除场 0）
#   **J2** 板条状（长/厚中位）**≥ 10**（不得变差）
#   **J3** `n_var_sig` **不下降**（基线 = 4）
#   **J4** 形核数**不失控**（η 降低会让超临界判据更易通过；基线：step 100 时 54 个事件）
#   **J5** 门控有效：`--ed-eta 1.0` 与 `0.375` 仍可复现（默认 1.0 ⇒ 归档逐位不变）
#
# ## 与上一跑的唯一差异
#   `--ed-eta 0.375` → **`--ed-eta 0.253`**（其余 argv 逐字相同）
# ═══════════════════════════════════════════════════════════════════════════════
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10E253
LOG=_w2_t10_eta253.log
TS=$(date +%m%d_%H%M)
: > "$LOG"
{
  echo "════ η 0.375 → 0.253（TRIP 推导值）重跑 10 µm 盒  $TS ════"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"

# ① 清掉一切抢占内存的进程（goal 要求）
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_swapalert.sh*|*_t10_auto.sh*|*_t10_mon.sh*|*_t10_wait.sh*|\
    *ca_pf_framework*_t5_armon*|*ca_pf_framework*_t5_blkmon*|*ca_pf_framework*_t5_milewatch*|\
    *ca_pf_framework*_t5_lathmon*|*ca_pf_framework*_t5_mon_keeper*|*ca_pf_framework*_t5_keeper_all*)
      kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;;
  esac
done
sleep 5

# ② 语法/补丁硬门（不靠"我改过"）
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done
{
  echo -n "  补丁在位性（各应 = 1）：s291 "
  awk '/^ *if _ev or not _burst_on:$/{n++} END{printf "%d ", n+0}' _bk_exp.py
  echo -n "s292 "
  awk '/while _do_try and n_ath_tgt < _tgt/{n++} END{printf "%d ", n+0}' _bk_exp.py
  echo -n "s293 "
  awk '/_fresh_now = \(n_fresh_ok < int\(_Bt\)\)/{n++} END{printf "%d ", n+0}' _bk_exp.py
  echo -n "s295 "
  awk '/s295 形核分诊/{n++} END{printf "%d ", n+0}' _bk_exp.py
  echo -n "s296形核闸门η "
  awk '/_eta_sc \* med > fcrit/{n++} END{printf "%d\n", n+0}' windowB_surface.py
} >> "$LOG"

# ③ 起算例：与上一跑**只差 η**（并清除旧 exit 文件，避免陈旧读数）
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_prev_$TS.txt
CMD="$PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27"
setsid bash -c "$CMD ; echo \"EXIT=\$? at \$(date '+%F %T')\" > _w2_t10_exit.txt" \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（--ed-eta 0.253）" >> "$LOG"

# ④ 重挂 swap 报警 + 自动守望（改指向新 tag）
sed "s/^TAG=t10N160/TAG=$TAG/" _t10_swapalert.sh > _t10_swapalert_253.sh
sed "s/^TAG=t10N160/TAG=$TAG/" _t10_auto.sh      > _t10_auto_253.sh
sed -i "s/_w2_t10_swapalert.log/_w2_t10_swapalert253.log/" _t10_swapalert_253.sh
sed -i "s/_w2_t10_auto.log/_w2_t10_auto253.log/"           _t10_auto_253.sh
setsid nohup bash _t10_swapalert_253.sh 28800 20 > /dev/null 2>&1 < /dev/null &
setsid nohup bash _t10_auto_253.sh 21600        > /dev/null 2>&1 < /dev/null &
echo "  已重挂 swap 报警与自动守望（指向 $TAG）" >> "$LOG"

# ⑤ 复验 argv + 亲和性
sleep 90
{
  echo "  ── 复验（90 s 后）──"
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -n "$P" ]; then
    echo "    pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
    echo -n "    ★ 关键开关："
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+|\-\-nuc-block-parallel [0-9]+|\-\-nthreads [0-9]+' | tr '\n' ' '
    echo
    echo "    亲和性: $(taskset -pc $P 2>/dev/null | sed 's/.*list: //')"
  else echo "    ⚠ 未找到进程"; fi
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
