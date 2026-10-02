#!/bin/bash
# _t5_append_s75.sh --- 第 75 轮：缺陷完全定位（nan vs None，一行可修）
cd "$(dirname "$0")" || exit 1
cat >> R581_T5_THERM_FRAME.md <<'EOF'

---

## §15 ★★★★★★★ 第 75 轮：缺陷**完全定位** —— `nan` 被当成 `None`（一行可修）

### §15.1 三条路径的**逐行**证据（全部实测 grep，非推理）
```
写入侧： _bk_exp.py:525   st['f3_pos_p0_m'] = np.float64(P0 if P0 is not None else np.nan)
读回侧： _bk_exp.py:741   P0 = (float(np.asarray(z['f3_pos_p0_m']).item())
                              if 'f3_pos_p0_m' in got else None)
回填侧： _bk_exp.py:2280  _p0 = _rb_meta.get('P0')
         _bk_exp.py:2282  if _p0 is not None:  P0 = float(_p0)        ← ★ **病灶**
初始值： _bk_exp.py:1998  P0, t_sim, wall0, tstep = **None**, 0.0, ...
钉基准： 主循环 `if P0 is None and np.isfinite(pm): P0 = pm`（`:518` 的注释所述）
```

### §15.2 ★★★★★ 根因链（三步，逐环可查）
| 步 | 发生什么 |
|---|---|
| **1** | 两臂 step 20 时 **`P0` 都是 `nan`** —— 那时还没有 F3 面，`pm` 不有限 ⇒ `P0` 保持 `None` ⇒ **写盘时被存成 `nan`**（`:525` 的 `else np.nan`）|
| **2** | **A 臂续跑**：读回 `f3_pos_p0_m` = **`float('nan')`**；回填判据是 **`if _p0 is not None`** ⇒ **`nan` **不是** `None`** ⇒ **通过** ⇒ `P0 = nan` |
| **3** | 于是 `P0` **不再是 `None`** ⇒ 主循环那条「**第一次 `pm` 有限时钉基准**」的逻辑**永远不再触发** ⇒ **`P0` 恒为 `nan`** ⇒ `f3_pos_dx` 退化为 `0.0` |

**⇒ B 臂（一次跑完）**从不经过读回** ⇒ `P0` 一直是 `None` ⇒ step 40 时被正常钉住 ⇒ 有真实值 ✓
**⇒ 这解释了两臂在 step 40 的 `P0`（`nan` vs `−2.3157e−6 m`）与 `f3_pos_dx`（`0.0` vs `−0.0357`）**全部观测**。**

### §15.3 ★ 修法（**一行 + 一处判据**，理由明确）
```python
# (a) 读回时把 `nan` 当作"未设定"
_v = z['f3_pos_p0_m'] if 'f3_pos_p0_m' in got else None
P0 = float(_v) if (_v is not None and np.isfinite(float(_v))) else None
# (b) 回填处同理：`_p0 is not None` ⇒ **非 None 且有限**
```

### §15.4 ★ 缺陷的性质（**必须如实分类**）
| 项 | 判定 |
|---|---|
| **影响面** | **只影响 F3 位置诊断**（`f3_pos_dx`）—— **物理列 94/96 全同**（§14.3）|
| **触发条件** | **续跑时"续跑点之前尚无 F3 面"**（本例 step 20）⇒ 即**早期续跑** |
| **不触发的情形** | 续跑点**已有** F3 面（`P0` 已钉住）⇒ 读回真值 ⇒ 无此问题 |
| **对本 goal 已有结论的影响** | **无**（物理量全同）|
| **必须修的理由** | 否则**续跑臂上的 F3 诊断量静默退化**，以后用它的人会拿到 `0.0` 而不知原因 |

### §15.5 ★ 判据（修好后重跑第 8 条，**预先写死**）
1. **两臂同一 step 的 `f3_pos_p0_m` 必须相同**（且都有限，或都为 `None`）；
2. **`f3_pos_dx` 在 96 列（除 `wall_s`）中不再例外** ⇒ 与其余 94 列一样逐位相同；
3. **回归**：修完后 `--therm-hist linear` 的短跑仍与改动前逐位相同（**6a 不能因这次修而破**）。
EOF
echo "已追加，现在 $(wc -l < R581_T5_THERM_FRAME.md) 行"
