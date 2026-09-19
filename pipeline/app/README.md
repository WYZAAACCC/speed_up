# `app/` —— 自建 MOOSE app（`GbJac`）

> 建立：2026-09-19
> 目的：**补上 MOOSE 上游 `ACGrGrPoly` 丢掉的两类雅可比项**，
> 而不必换回 AD（AD 版实测每牛顿步 6–7 分钟，不可用）。

---

## 一、为什么需要一个自建 app

上游 `ACGrGrPoly` 的残差是

```
R_i = L(η) · mu · ( η_i³ − η_i + 2·γ(η)·η_i·Σ_{j≠i} η_j² )
```

但它的 `computeQpOffDiagJacobian` **覆盖**了基类
`ACBulk::computeQpOffDiagJacobian` 却没有调用它，并且把 `gamma_asymm`
当成**常数**。对 `η_j` 求导时因此丢掉两项：

| 缺项 | 来源 | 在哪丢的 |
|---|---|---|
| `(∂L/∂η_j) · F_η` | 迁移率乘积法则 | `ACGrGrPoly` 覆盖基类时没调 `ACBulk` 的那一项 |
| `(∂γ/∂η_j) · F_η` | `gamma_asymm` 依赖 η | `computeDFDOP` / `computeQpOffDiagJacobian` 都把它当常数 |

对角线上 `(∂L/∂η_i)` 由 `ACBulk::precomputeQpJacobian` 的 `_dLdop` 项负责，
但 `(∂γ/∂η_i)` 仍然缺 —— 也是一并补上。

### 为什么 C 版没暴露、D 版才暴露

| | `gamma_asymm` | `L` | 缺项 |
|---|---|---|---|
| C 版 | `GenericConstantMaterial` 常数 | 只依赖 `T`（AuxVariable） | **恰好恒为 0** |
| D 版 | `gamma_aniso`，依赖 `gr0…gr7` | `L2a(T,gr) × L2b(gr)`，依赖 `gr0…gr7` | **非零，且被静默丢弃** |

所以这不是"非 AD 版天生差一点"，而是**引入取向差依赖（2a）与取向依赖（2b）之后，
`ACGrGrPoly` 的雅可比就不再与残差一致了**。

> ⚠ **但别把它的影响想大了。** 本轮实测（`../validated/run_jacfix_test.sh`，
> 同一二进制、同一算例，只差核类型）：缺项只有 **~5e-7（相对）**，
> FD 比值 **0.0208202 → 0.0208202，一位都没变**。
> ⇒ **它不是「T1 过不了」的原因**。这个核该留（它是对的、零代价、残差逐位不变），
> 但**主导误差另有来源，尚未定位** —— 见 `../validated/VALIDATION_STATUS.md §1.4`。
>
> 怎么证明核**确实生效**（而不是被静默忽略）：看两份日志的牛顿序列 ——
> 第 1 次迭代的 `|R|` 差最后一位（base `1.964899e-03` / fixed `1.964898e-03`）。
> ⚠ **不要只看 FD 比值**：它对这个量不敏感，会让人误以为核没生效。

### 还差一处：算例里根本没写 `coupled_variables`

`frozen/splice_aniso_nonad.py` 生成的 `[grN_poly]` 块**没有 `coupled_variables`**，
于是 `ACBulk` 的 `_dLdarg` 向量是**空的** —— 就算把上面那一项加回去，
也拿不到 `∂L/∂η_j` 的原料。`validated/make_jacfix.py` 一并补上这一行。

---

## 二、`ACGrGrPolyJ` 做了什么

`include/kernels/ACGrGrPolyJ.h` / `src/kernels/ACGrGrPolyJ.C`，约 90 行。

**残差逐位不变**（完全不改 `computeDFDOP(Residual)`），只改雅可比：

```cpp
Real ACGrGrPolyJ::computeQpOffDiagJacobian(unsigned int jvar)
{
  Real jac = ACGrGrPoly::computeQpOffDiagJacobian(jvar);   // 显式 η_j 项（基类）
  ...
  // (2) γ 的各向异性项：L·mu·2·(∂γ/∂η_j)·η_i·Σ
  for (unsigned int i = 0; i < _op_num; ++i)
    if (jvar == _vals_var[i])
      jac += _L[_qp]*_mu[_qp]*2.0*(*_dgamma_dv[i])[_qp]*_phi[_j][_qp]*op*SumOPj*_test[_i][_qp];

  // (3) 迁移率乘积法则项 —— 直接复用 ACBulk 的实现（AllenCahn.C:65 同写法）
  jac += ACBulk<Real>::computeQpOffDiagJacobian(jvar);
  return jac;
}
```

`computeDFDOP(Jacobian)` 另外补上对角线的 `∂γ/∂η_self` 项。

### ⚠ 两个实现上的坑（都实测踩过）

1. **不要用 `bool mapJvarToCvar(jvar, cvar)` 那个重载** ——
   libmoose 只实例化了对 `KernelValue` 的 `unsigned int` 版本，
   bool 版**编译链接都不报错**，只在**运行期**炸：
   ```
   symbol lookup error: undefined symbol:
     JvarMapInterfaceBase<KernelValue>::mapJvarToCvar(unsigned int, unsigned int&)
   ```
2. **直接调 `ACBulk<Real>::computeQpOffDiagJacobian(jvar)` 是安全的** ——
   `JvarMapKernelInterface::computeOffDiagJacobian` 在 `_jvar_map[jvar] < 0` 时
   **提前返回**（`framework/include/utils/JvarMapInterface.h:204`），
   所以核里收到的 `jvar` 一定在 `coupled_variables` 里。

---

## 三、怎么建

```bash
# 在 WSL 里
bash /mnt/f/speed_up/pipeline/app/build_app.sh
```

脚本会：创建 app 骨架（首次）→ 同步核文件 → 修 stork 生成的两个问题 →
激活 conda → `make -j8` → 自检。

**⚠ 必须先激活 conda 环境 `moose`。** 本机的 MOOSE 源码**没有子模块**，
libMesh / PETSc / WASP 全部来自 conda 的 `moose-dev` 包，
它们的位置由激活环境时设置的 `LIBMESH_DIR` / `PETSC_DIR` / `WASP_DIR` 指定。
不激活就直接 `make` 会报两个**与核代码无关**的错：
`libmesh-config: not found` 和 `***ERROR*** WASP does not seem to be available.`
（脚本已把这一步写在最前面并逐项断言。）

产物：`/root/projects/gb_jac/gb_jac-opt`（+ `lib/libgb_jac-opt.so`）。
它是一个**完整的 MOOSE app**：包含 `phase_field` 模块的全部对象，
所以可以**直接替换** `phase_field-opt`。

---

## 四、怎么用

生产走 `../run_nonad_prod.sh` —— 它已经改用 `gb_jac-opt`，
并在生成阶段自动调 `../validated/make_jacfix.py` 把
`ACGrGrPoly` 换成 `ACGrGrPolyJ`、补上 `coupled_variables`。

单独验证（前后 FD 对照）：

```bash
bash ../validated/run_jacfix_test.sh
```

手动跑任意算例：

```bash
/root/projects/gb_jac/gb_jac-opt -i your.i
```

核是否在二进制里：

```bash
/root/projects/gb_jac/gb_jac-opt --registry | grep ACGrGrPolyJ
```

---

## 五、这个缺陷是**通用**的，值得回馈上游

任何满足以下两条的 MOOSE 模型都会中招：

1. 用非 AD 的 `ACGrGrPoly`（即 `GrainGrowth` 动作 + `variable_mobility`，
   或手写核）；
2. `mob_name`（迁移率）**或** `gamma_asymm` 依赖序参量。

`AllenCahn` 没有这个问题（它显式调用了 `ACBulk::computeQpOffDiagJacobian`），
所以正确的上游修法就是让 `ACGrGrPoly` 也调用它。
本目录的 `ACGrGrPolyJ` 可以直接改成那个补丁的形状。

---

## 六、文件

| 文件 | 用途 |
|---|---|
| `build_app.sh` | 建/更新 app 的**唯一入口**（幂等，可反复跑） |
| `include/kernels/ACGrGrPolyJ.h` | 核的头（含详细推导注释） |
| `src/kernels/ACGrGrPolyJ.C` | 核的实现 |

**`/root/moose/` 一个字都没改** —— MOOSE 保持原版，
与 `VALIDATION_STATUS.md` 里记录的版本号（`b892bff54e`）一致。
