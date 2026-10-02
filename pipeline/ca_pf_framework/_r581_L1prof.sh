#!/bin/bash
# _r581_L1prof.sh --- ★ L1 的**分块记账**判据：直接量 `adv.extend` 这个块的墙钟。
#
# ## 为什么必须用记账器而不是整步墙钟
# 整步墙钟的 run-to-run 抖动 ~7–10%（AGENTS §7.5 P1/P4）。而 `adv.extend` 的
# EDT 合一预期收益只有 ~4%/步 ⇒ **被噪声淹没**：`_r581_L1ab.sh` 4 轮实测
# merged 中位 0.954×、区间 [0.730, 1.049] —— **区间跨 1，未确立**。
# 记账器把块切开量（钩子开销 0.2%）⇒ **分辨力高一个量级**。
# 这正是 AGENTS P4/P14 的口径：**"占比大" ≠ "能提速"，要用能看见它的量具**。
#
# ## 目标读数
#   `adv.extend` 的**秒/步**（不是占比 —— 占比会随其它块一起动）。
#   M-1：`near` 的 `adv.extend` 秒/步 必须 **< legacy**；
#   M-2：`P0..P5` 全 PASS（否则量具本身失效，读数不算数）；
#   M-3：`adv.extend` 的 n/步 必须 == 1.00（新钩子活性，防"静默没走"）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
export R576_N="${R581P_N:-64}" R576_NV="${R581P_NV:-24}"
export R576_STEPS="${R581P_STEPS:-8}" R576_WORKERS="${R581P_WORKERS:-4}"
ROUNDS="${R581P_ROUNDS:-3}"
LOG=_w2_r581_L1prof.log
: > "$LOG"

echo "=== R581-L1 分块记账 A/B（3 档 × $ROUNDS 轮）N=$R576_N NV=$R576_NV ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

ARMS=(legacy merged near)
for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r ----" | tee -a "$LOG"
  for a in "${ARMS[@]}"; do
    export R581_EXTEND="$a"
    export R576_TAG="${a}r${r}"
    export R576_OUT="_w2_r581p_${a}_r${r}.log"
    $PY _r576_prof.py > "_w2_r581p_${a}_r${r}_stdout.log" 2>&1
    EX=$(grep -E '^    adv\.extend ' "$R576_OUT" | head -1 | awk '{print $2, $3, $4}')
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$R576_OUT" | head -1)
    PJ=$(grep -E '^  P0=' "$R576_OUT" | head -1)
    echo "  ${a}r${r} 干净单步=$CL  adv.extend=[$EX]  $PJ" | tee -a "$LOG"
  done
done
echo "" | tee -a "$LOG"
echo "############ 汇总" | tee -a "$LOG"
$PY - "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import re, statistics, sys
R = int(sys.argv[1])
ARMS = ['legacy', 'merged', 'near']
sec = {a: [] for a in ARMS}
cln = {a: [] for a in ARMS}
nps = {a: [] for a in ARMS}
for r in range(1, R + 1):
    for a in ARMS:
        p = '_w2_r581p_%s_r%d.log' % (a, r)
        try:
            t = open(p, errors='replace').read()
        except OSError:
            continue
        m = re.search(r'^    adv\.extend\s+([\d.]+) s\s+[\d.]+%\s+n=\s*([\d.]+)/步',
                      t, re.M)
        if m:
            sec[a].append(float(m.group(1))); nps[a].append(float(m.group(2)))
        m2 = re.search(r'干净单步（钩子关）= \*\*([\d.]+) s', t)
        if m2:
            cln[a].append(float(m2.group(1)))
print('  %-8s %-26s %-10s %s' % ('档', 'adv.extend s/步（每轮）', '中位', 'n/步'))
print('  ' + '-' * 78)
for a in ARMS:
    if sec[a]:
        print('  %-8s %-26s %-10.5f %s'
              % (a, ' '.join('%.5f' % x for x in sec[a]),
                 statistics.median(sec[a]), set(nps[a])))
    else:
        print('  %-8s （缺读数）' % a)
base = statistics.median(sec['legacy']) if sec['legacy'] else None
print()
if base:
    for a in ('merged', 'near'):
        if sec[a]:
            m = statistics.median(sec[a])
            print('  ⇒ %-7s `adv.extend` 提速 **%.3f×**（%.5f → %.5f s/步，省 %.2f%% 单步）'
                  % (a, base / m, base, m,
                     100.0 * (base - m) / statistics.median(cln['legacy'])
                     if cln['legacy'] else float('nan')))
    print()
    print('  M-1 判据（merged/near 必须 < legacy）：%s'
          % ('✅ PASS' if all(statistics.median(sec[a]) < base
                              for a in ('merged', 'near') if sec[a]) else '❌ FAIL'))
print('  ⚠ 判据口径：`adv.extend` 的**秒/步**在本会话内部可比；跨会话不可比（AGENTS P1）。')
PYEOF
echo "=== R581 L1 PROF DONE $(date '+%F %T') ===" | tee -a "$LOG"
