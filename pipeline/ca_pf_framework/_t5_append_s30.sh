#!/bin/bash
# _t5_append_s30.sh --- 第 30 轮：判据② 的前置探针结果
cd "$(dirname "$0")" || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §25–30 第 25–30 轮：判据② 的**前置探针**（先打语义，再写代码 —— P20 纪律）

### §30.1 ★★★ 探针结果（`_t5_twf_probe.py`，实测）
**快照的 16 个键**：
```
['L', 'N', 'a_ax', 'arm', 'band_cells', 'band_fld', 'band_idx', 'band_val',
 'f3_pos_p0_m', 'n_hab', 'region', 'step', 't_s', 'vmap_keys', 'vmap_vals', 'w_ax']
```
| 发现 | 判读 |
|---|---|
| **★ `n_hab` **就在快照里****（shape `(3,)`）| **`wide_face_thickness` 需要的 `n_hab` 离线可得** ✓ |
| `region` / `band_*` / `N=160` / `L=1e-5 m`（**= 10.00 µm** ✓）| 都在 ✓ |
| `band_val` ∈ **[−3.75e-07, +3.75e-07]** = **±6Δx** | 与 `band_cells = 6` 一致 ✓ |
| **带内覆盖率 = **0.2804%/场**（11486 / 4096000）| **带外胞不在快照里**（原值 `1e3`）|
| **⚠ **只有 `snap_00000.npz` 带 `band_idx`****（40/80/120/160 **都没有**）| **★ 实测限制**：`--phi-band-every 200` ⇒ **带内 φ 只在 step 0/200/400/… 有** |

**⇒ 判据② 的离线重算**可行**，但**分辨率 = 200 步**（§10.1 的预测被实测证实）。**
**★ 而 `n_hab` 在快照里 ⇒ 不需要从 `EPS0`/`NPF` 重建 ⇒ 实现路径变简单。**

### §30.2 为什么先探针而不直接写工具
P20 纪律：**先打语义，再写代码**。若直接写 `t_wf` 工具，会在
①「带内够不够」②「`n_hab` 从哪来」两处**盲猜**；探针一次把两处都定了。

### §30.3 判据② 的实现路径（**下一轮照此写**）
```
读 snap（带 band_idx 的）
  → 按场重建 φ：phi_k[band_idx[band_fld==k]] = band_val[band_fld==k]，其余填 1e3
  → 取 n_hab（快照里）、dx = L/N
  → wide_face_thickness(phi, dx, n_hab, k, band=1.5, cos2_min=0.81, band_cells=2)  ← **返回 dict**
  → **读数 − 1Δx**（恒定偏差，已在 `_bk_measure.py` docstring 记账）
  → 长宽比 = blk_alen_nm / (t_wf − Δx)
```
**⚠ 待实测确认**：「按 band=6 重建的 φ」够不够让 `wide_face_thickness` 给出正确厚度
（它只需界面附近的 φ 估法向；**必须与"整场 φ"对照**才算数 —— 这是下一步的正对照）。
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
