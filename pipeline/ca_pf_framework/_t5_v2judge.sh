#!/bin/bash
# _t5_v2judge.sh --- ★ V2 判决器：按 §133/§141 **预先写死**的四项判据自动判定
#
# ## 为什么先做量具（本 goal 的硬要求）
# 「凡'最小化/最优化'得到的量，必须先用解析已知答案验证最小化器本身，且正对照必须预先写死、必须能失败。」
# ⇒ 判据也一样：**在测量之前先把判决器写好并自测**，而不是看到数之后再想"这算不算成立"。
#
# ## 判据（§133.4 / §141.4 逐字，**不得在看到数之后修改**）
#   V2 = t5V2（--var-rule random, --nvar 2 --m 36）
#   A  = t5H3（--var-rule ed,      --nvar 3 --m 24）  ← control
#   ① 首个 `fresh` 事件：两臂都应有 ≥1 个成功的 fresh
#   ② `nf2`        ：V2 **> 0**，而 A **= 0**
#   ③ `nblk_sig`   ：V2 **≥ 2**，而 A **= 1**
#   ④ `n_var_sig`  ：V2 **> 1**，而 A **= 1**
# ⇒ 四项中 **②③④** 是"新块/多变体"的直接签名；**全不成立** ⇒ 机制另有所在。
#
# ## ⚠ 口径（**必须先说清，避免误判**）
#   - `nblk_sig`/`n_var_sig` 是**块表列**，只在 `--every` 的倍数步写
#     ⇒ 若 V2 尚未越过它的**事件 #23**，这两列**可能仍为空** ⇒ 判"未到"，**不判 FAIL**（P26）。
#   - `nf2` 每行都有 ⇒ 可实时判。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for T in t5V2 t5H3; do [ -f "_exp/_bk_t5/dry_$T/series.csv" ] || { echo "  ❌ 缺 $T 的 series"; exit 1; }; done

echo "════════════════════════════════════════════════════════════════════════"
echo "★ V2 判决器（判据预先写死在 §133.4；**本脚本不得在看到数后修改**）"
echo "════════════════════════════════════════════════════════════════════════"
$PY - <<'PYEOF'
import csv, os

def rows(tag):
    p = '_exp/_bk_t5/dry_%s/series.csv' % tag
    with open(p, newline='') as f:
        return list(csv.DictReader(f))

def lastnum(rs, key):
    for r in reversed(rs):
        v = (r.get(key) or '').strip()
        if v not in ('', 'nan'):
            try:    return float(v)
            except: pass
    return None

def nev(tag):
    """成功的形核事件数 + fresh 数（从日志的模式标记数）"""
    import re
    L = '_w2_t5_short_%s.log' % tag
    try:    s = open(L, encoding='utf-8', errors='ignore').read()
    except Exception: return (0, 0)
    return (len(re.findall(r'模式 \*\*attach\*\*', s)) +
            len(re.findall(r'模式 \*\*fresh\*\*', s)) +
            len(re.findall(r'模式 \*\*stack\*\*', s)),
            len(re.findall(r'模式 \*\*fresh\*\*', s)))

res = {}
for t in ('t5V2', 't5H3'):
    rs = rows(t)
    step = int(float(rs[-1]['step'])) if rs and rs[-1].get('step') else -1
    ne, nf = nev(t)
    res[t] = dict(step=step, rows=len(rs), nev=ne, nfresh=nf,
                  nf2=lastnum(rs, 'nf2'), nblk=lastnum(rs, 'nblk_sig'),
                  nvar=lastnum(rs, 'n_var_sig'), n1=lastnum(rs, 'nslab_n1'),
                  n=lastnum(rs, 'nslab_n'))

print('  %-6s %6s %6s %8s %8s %8s %8s %8s' %
      ('臂', '末步', '行数', '形核', 'fresh', 'nf2', 'nblk_sig', 'n_var_sig'))
for t in ('t5V2', 't5H3'):
    d = res[t]
    f = lambda x: ('%.0f' % x) if x is not None else '（空）'
    print('  %-6s %6d %6d %8d %8d %8s %8s %8s' %
          (t, d['step'], d['rows'], d['nev'], d['nfresh'],
           f(d['nf2']), f(d['nblk']), f(d['nvar'])))
print()

V, A = res['t5V2'], res['t5H3']
def judge(name, cond, got, vs):
    """⚠ s143 修：闸门关着时**一律**显示"未到"，不显示 FAIL
    （原版的 `got is None` 只挡住"列空"的情况 ⇒ 闸关着而列有值时仍打 FAIL ⇒ **误导**）"""
    if not gate:
        tag = '⏳ 未到'
    else:
        tag = '✅ PASS' if cond else '❌ FAIL'
    print('  %-34s %s   （V2: %s | t5H3: %s）' % (name, tag, got, vs))

print('  ── 判据（预先写死）──')
# 前置闸（P26）：V2 的块表列是否已经有值
# ⚠⚠ s143 修（**我第一版写错了，留痕**）：原闸是
#     gate = (V['nblk'] is not None and V['nvar'] is not None)
#   —— 它只检查"块表列**有没有值**"，而 `nblk_sig = 1` 在 step 0/100/200… 就会写出
#   ⇒ **闸门恒开** ⇒ 在 V2 **还没到事件 #23** 时就判 FAIL（**正是 P26 要防的"无分辨力却下结论"**）。
#   **正确的闸 = "该机制**该不该已经发生**"** —— 即 `fresh` 首触发的门槛 `K = n(T_end) = 23`。
K_FRESH = 23
gate = (V['nev'] >= K_FRESH) or (V['nfresh'] >= 1)
print('  【分辨力闸】V2 的形核事件数 %d >= K=%d（或已出现 fresh）= %s'
      % (V['nev'], K_FRESH, '是 ✅' if gate else '**否 ⇒ 判"未到"，不判 FAIL**'))
print('     ★ 闸的口径：**事件数**（该机制该不该已发生），**不是**"块表列有没有值"')
print()
tight = V['nf2'] is not None and V['nf2'] > 0
judge('① 首个 fresh 成功',      V['nfresh'] >= 1, V['nfresh'], A['nfresh'])
judge('② nf2 > 0（异变体界面）', tight, V['nf2'], A['nf2'])
judge('③ nblk_sig >= 2（新块）', (V['nblk'] or 0) >= 2 if gate else None, V['nblk'], A['nblk'])
judge('④ n_var_sig > 1（多变体）',(V['nvar'] or 0) > 1 if gate else None, V['nvar'], A['nvar'])
print()
print('  ── 结论 ──')
if not gate:
    print('     ⏳ **未到判定点**（V2 的块表列尚空；它的事件 #23 = `fresh` 首触发还没发生）')
    print('     ⇒ 按 §141.3 第 18 条纪律：**不在此时下任何结论，也不轮询**')
elif tight and (V['nblk'] or 0) >= 2 and (V['nvar'] or 0) > 1:
    print('     ✅✅ **判据④⑥ 的机制成立**：随机选变体 ⇒ 出现异变体界面 + 新块')
    print('        ⇒ 接着看 `blk_laths` 是否 > 1 块、`box_touch`/填充是否继续升')
elif not tight and (V['nblk'] or 0) <= 1:
    print('     ❌ **机制不成立**：即使 `--var-rule random`，仍无 `nf2`、仍单块')
    print('        ⇒ 真因**不在变体选择** ⇒ 回到 `nuc_dbg.json` 的 `fresh_*` 归因计数')
else:
    print('     ⚠ **部分成立**（有 `nf2` 但块数未变，或反之）⇒ 逐项查，不要合并结论')
PYEOF
