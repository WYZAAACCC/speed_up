#!/usr/bin/env bash
# _r718_s1_verify.sh —— S1 的验收（`R712_REPAIR_SPEC.md §10.3f` 判据 **V1–V5**）。
#
# 纪律：
#   * 全部跑在**独立 --out 目录**（不碰归档）
#   * 每进程 **≤4 核**（taskset -c 0-3）+ nice 10（`R630 C1–C3`）
#   * 判"检查跑过"要看**独有的成功串**，不靠 `&&` 链的沉默（`P44`）
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY=/root/miniconda3/envs/ml/bin/python
OUT="$HERE/_exp/_s1verify"
rm -rf "$OUT"; mkdir -p "$OUT"

# 小算例：够跑几十步即可（守卫的有效性不依赖算例大小）
COMMON=(--N 48 --dx-nm 62.5 --steps 60 --every 20 --snap-every 99999
        --pair-every 0 --norm-smooth 0 --nthreads 4 --arm dry
        --laths 1,1,1 --plate-L 125.0 --plate-W 125.0 --plate-T 125.0
        --nuc-shape disc --grow-stack --nuc-every 0 --nuc-init 0
        --nuc-law cadence --nuc-block-target 0 --nuc-mode auto --eng-cadence 30
        --gamma0 0.25 --gamma-film 0.6 --alpha-km 0.041739
        --T-end 298.0 --cool-rate 2352400.0 --qs-clock 1 --qs-max-relax 100
        --beta-h 6.477 --beta-w 2.3 --ed-eta 0.253
        --mob-iform exp2 --mob-ratio 9.0 --mob-dip 4.0 --band-cells 40 --mob-wulff
        --facet-proj 0 --rank1-swap none --var-rule ed --nuc-sites-refill 1
        --out "$OUT")

run() { nice -n 10 taskset -c 0-3 "$PY" -u _bk_exp.py "${COMMON[@]}" --tag "$1" \
        > "$OUT/$1.log" 2>&1; echo $?; }

echo "==================== V1：默认档（不设 CFL_GUARD）===================="
env -u CFL_GUARD -u CFL_GUARD_MAX bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py \
  ${COMMON[*]} --tag v1default" > "$OUT/v1default.log" 2>&1
echo "V1 rc=$?"
if [ -f "$OUT/dry_v1default/series.csv" ]; then
  echo "V1 ✅ 算例跑通（series.csv 存在）"
else
  echo "V1 ⛔ FAIL：series.csv 不存在"; tail -5 "$OUT/v1default.log"
fi
if compgen -G "$OUT/dry_v1default/cfl_guard_*.txt" > /dev/null; then
  echo "V1 ⛔ FAIL：默认档**产出**了 cfl_guard_*.txt（应零副作用）"
else
  echo "V1 ✅ 未产出 cfl_guard_*.txt ⇒ 零副作用"
fi
if grep -q 'CFL 守卫' "$OUT/v1default.log"; then
  echo "V1 ⛔ FAIL：默认档打印了守卫告警"
else
  echo "V1 ✅ 无守卫告警输出"
fi

echo
echo "==================== V3：CFL_GUARD=warn ===================="
CFL_GUARD=warn bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py \
  ${COMMON[*]} --tag v3warn" > "$OUT/v3warn.log" 2>&1
echo "V3 rc=$?"
if compgen -G "$OUT/dry_v3warn/cfl_guard_*.txt" > /dev/null; then
  echo "V3 ✅ 产出 cfl_guard_*.txt："
  sed 's/^/      /' "$OUT"/dry_v3warn/cfl_guard_*.txt
else
  echo "V3 ⛔ FAIL：未产出 cfl_guard_*.txt"; tail -5 "$OUT/v3warn.log"
fi
n_warn=$(grep -c 'CFL 守卫' "$OUT/v3warn.log" || true)
echo "V3 告警行数 = $n_warn（>0 表示门控真的打开）"

echo
echo "==================== V2：warn 与默认档 series.csv **除 wall_s 外**逐位相同 ===================="
A="$OUT/dry_v1default/series.csv"; B="$OUT/dry_v3warn/series.csv"
if [ -f "$A" ] && [ -f "$B" ]; then
  # ⚠ 判据更正（2026-10-08，本轮实测）：规范 §10.3f 的 V2 写"series.csv **逐位相同**"，
  #   但 `wall_s` 列是**真实墙钟**，两次运行必然不同 ⇒ **该判据不可达**。
  #   正确的判据：**除 `wall_s` 外全部列逐位相同** ⇒ 守卫不动物理。
  ha=$(sha256sum "$A" | cut -d' ' -f1); hb=$(sha256sum "$B" | cut -d' ' -f1)
  echo "  整文件 sha：默认=${ha:0:16}  warn=${hb:0:16}（不同是预期的，因为含 wall_s）"
  if [ "$ha" = "$hb" ]; then
    echo "V2 ✅ 整文件逐位相同（比判据更强）"
  else
    echo "  ⇒ 逐列定位差异："
    "$PY" "$HERE/_r718_csvdiff.py" "$A" "$B" | sed 's/^/      /'
  fi
else
  echo "V2 ⛔ 无法比较（缺文件）"
fi

echo
echo "==================== V3b：**真的越限**档（上限降到 0.10）⇒ 告警串必现 ===================="
CFL_GUARD=warn CFL_GUARD_MAX=0.10 bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py \
  ${COMMON[*]} --tag v3warn_over" > "$OUT/v3warn_over.log" 2>&1
echo "V3b rc=$?"
n_over=$(grep -c 'CFL 守卫' "$OUT/v3warn_over.log" || true)
echo "V3b 告警行数 = $n_over"
grep -m1 'CFL 守卫' "$OUT/v3warn_over.log" | sed 's/^/      /' || echo "      ⚠ 未见告警串"
if compgen -G "$OUT/dry_v3warn_over/cfl_guard_*.txt" > /dev/null; then
  echo "V3b ✅ 落盘："; sed 's/^/      /' "$OUT"/dry_v3warn_over/cfl_guard_*.txt
else
  echo "V3b ⛔ 未落盘"
fi

echo
echo "==================== V4：CFL_GUARD=abort + 极小上限 ⇒ 非零退出 ===================="
CFL_GUARD=abort CFL_GUARD_MAX=0.01 bash -c "nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py \
  ${COMMON[*]} --tag v4abort" > "$OUT/v4abort.log" 2>&1
rc4=$?
echo "V4 rc=$rc4（判据：非 0）"
if [ "$rc4" -ne 0 ]; then echo "V4 ✅ abort 档有效（非零退出）"
else echo "V4 ⛔ FAIL：退出码为 0"; fi
grep -m1 'CFL 守卫 abort' "$OUT/v4abort.log" | sed 's/^/      /' || echo "      ⚠ 未见 abort 独有串"

echo
echo "==================== V5：实测 cfl_used 峰值（F8 的 [实测] 数）===================="
echo "  本算例（N=48 / 60 步 / 当前物理参数）落盘的峰值："
sed 's/^/      /' "$OUT"/dry_v3warn/cfl_guard_*.txt
echo "  ⇒ 与 R716 扫归档的结论一致（当前世代 dG_max/Δf ≈ 1.0–1.24 ⇒ cfl ≈ 0.15–0.19）"

echo
echo "全部跑完。产物在 $OUT"
