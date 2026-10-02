#!/bin/bash
# _r581_mqueue4.sh --- ★★★★★ **C5 的**生产级完整配方**（三旋钮全开，N=160）**
#
# ## R80/R82 的结论（本队列的依据）
# **总根数 ≈ `V` · `m`**，其中：
#   * **`m`**（每变体根数上限）：**已实测**（`m=4`⇒4、`m=12`⇒11）—— R74/R79/R82/R83；
#   * **`V`**（用到的变体数）：**`ed` 下受"温度档数"限制（≈5）** —— R80/R82；
#     而 **`--var-rule random` 可望到 12**（物理上限，Burgers OR）。
# **⇒ C5（220–450 根）要求 `V·m ≥ 220`** ⇒ 在 `V≈12` 下需 **`m ≥ 19`**。
#
# ## ★ R85 查出的**缺口**
# | 队列 | 内容 | `m` | S4 | **`--var-rule`** |
# |---|---|---|---|---|
# | `mqueue`  | `p2_m12`/`p2_m12b` | 12 | ❌ | ❌ |
# | `mqueue2` | `p2_m20`            | 20 | ❌ | ❌ |
# | `mqueue3` | `p2_m12ov`          | 12 | ✅ | ❌ |
# | **`mqueue4`（本队列）** | **`p2_m20full`** | **20** | **✅** | **✅ `random`** |
# **⇒ 到 R85 为止，**N=160 上还没有任何一条臂三旋钮全开** —— 而那是 C5 的配方。**
#
# ## 判据（**预先写死**）
# * **总根数（快照里 `region>0` 的场数）进入 220–450** ⇒ **C5 达成**；
# * **总根数 ≈ `V`·`m`，且 `V` 明显 > 5** ⇒ **R80/R82 的 `--var-rule` 结论成立**；
# * **总根数仍 ≪ 220** ⇒ **当前模型即使三旋钮全开也到不了 C5** ⇒ 要另找机制。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r581_mqueue4.log
MIN_FREE_MB="${1:-13000}"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_arms() { ps -eo args --no-headers 2>/dev/null | grep '_r581_p2\.py' | grep -vc grep; }
_have()   { [ -d "_exp/_bk_p2/dry_$1" ]; }

say "=== R581-R85：C5 的生产级完整配方（m=20 + S4 + var-rule random）==="
say "阶段 1：等所有臂结束…"
_w=0
while [ "$(_n_arms)" -gt 0 ]; do sleep 60; _w=$((_w+1)); [ "$_w" -ge 60 ] && break; done
say "阶段 1 完成"

say "阶段 2：等前置 tag（`p2_m12`/`p2_m20`/`p2_m12ov`）都出现…"
_w=0
while :; do
  [ "$(_n_arms)" -gt 0 ] && { sleep 60; continue; }
  if _have p2_m12 && _have p2_m20 && _have p2_m12ov; then break; fi
  sleep 60; _w=$((_w+1)); [ "$_w" -ge 1440 ] && { say "❌ 等 24 h ⇒ 退出"; exit 4; }
done
say "阶段 2 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB（要求 ≥ ${MIN_FREE_MB}）"
[ "$avail" -lt "$MIN_FREE_MB" ] && { say "❌ 内存不足 ⇒ 不起跑"; exit 3; }

say "起 p2_m20full：--m 20 --B 5 --overlap-nm 62.5 --var-rule random（**单臂**，P23）cores 0-7"
$PY _r581_p2.py --run --tag p2_m20full --N 160 --m 20 --B 5 \
    --overlap-nm 62.5 --var-rule random --cores 0-7 --archive-old \
    > _w2_r581_p2_p2_m20full.log 2>&1
say "臂结束 exit=$?"

say "── 总根数与 C5 判决 ──"
$PY - <<'PYEOF'
import os
from collections import Counter
import numpy as np
d = '_exp/_bk_p2/dry_p2_m20full'
if not os.path.isdir(d):
    print('  ❌ 无目录'); raise SystemExit
snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
               key=lambda f: int(f.split('_')[1].split('.')[0]))
CELL = 160 ** 3
V_TOT = 160 ** 3 * (62.5e-9) ** 3
one = 0.25500e-18     # 单根体积（m³）
for s in snaps:
    z = np.load(os.path.join(d, s))
    reg = z['region']; vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                                     [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
    byvar = Counter()
    nz = 0
    for f in np.unique(reg):
        f = int(f)
        if f > 0:
            nz += 1; byvar[vm.get(f, -1)] += 1
    vol = float((reg > 0).sum()) / CELL
    print('  %-16s step=%-5d 场数=%-4d **V=%-3d** 每变体 max=%-3d 体积分数=%.4f%% 折合根数≈%.0f'
          % (s, int(z['step']), nz, len(byvar), max(byvar.values()) if byvar else 0,
             100 * vol, vol * V_TOT / one))
    print('       每变体：%s' % dict(sorted(byvar.items())))
print()
print('  ★ C5 判据：折合根数落在 **220–450** ⇒ 达成；每变体分布 ⇒ V 是否铺开')
PYEOF
say "=== R581 MQUEUE4 DONE ==="
