//* 自建 MOOSE 核：ACGrGrPoly 的雅可比补全版
//*
//* 与 MOOSE 上游 ACGrGrPoly 的关系：**残差逐位相同，只补雅可比缺项**。
#pragma once

#include "ACGrGrPoly.h"

/**
 * ACGrGrPoly 的雅可比补全版。
 *
 * ---- 它修的是什么 ----
 *
 * ACGrGrPoly 的残差是
 *     R_i = L(η)·mu·( η_i³ − η_i + 2·γ(η)·η_i·Σ_{j≠i} η_j² )
 * 但它的 computeDFDOP(Jacobian) 与 computeQpOffDiagJacobian 都把
 * **γ 当常数**、并且 computeQpOffDiagJacobian **覆盖**掉了
 * ACBulk::computeQpOffDiagJacobian（后者才含迁移率的乘积法则项）。
 * 于是对 η_j 求导时丢掉两项：
 *
 *   ∂R_i/∂η_j =  (∂L/∂η_j)·mu·( η_i³−η_i+2γΣ )        ← 丢（跨材料属性）
 *              + L·mu·2·γ·η_i·(2η_j)                  ← 基类有（Σ 里的显式 η_j）
 *              + L·mu·2·(∂γ/∂η_j)·η_i·Σ               ← 丢（跨材料属性）
 *
 * 对角线上 (∂L/∂η_i) 由 ACBulk::precomputeQpJacobian 的 `_dLdop` 项负责，
 * 但 (∂γ/∂η_i) 仍然缺 —— 由本类覆盖 computeDFDOP(Jacobian) 补上。
 *
 * ---- 为什么 C 版没暴露、D 版才暴露 ----
 *
 * C 版里 `gamma_asymm`、`mu` 是 GenericConstantMaterial，L 只依赖 T。
 * 于是 ∂L/∂η_j ≡ 0、∂γ/∂η_j ≡ 0，**缺项恰好为零**，雅可比是完备的。
 * D 版引入 2a（κ、γ 的取向差依赖）与 2b（L 的取向依赖）后两者都依赖 η，
 * 缺项变成非零且被静默丢弃 ⇒ 雅可比与残差不一致。
 *
 * ---- 用法 ----
 *
 *   [gr0_poly]
 *     type = ACGrGrPolyJ
 *     variable = gr0
 *     v = 'gr1 gr2 ... gr7'
 *     mob_name = L
 *     # 必须写全：L 与 gamma_asymm 都依赖这些变量，
 *     # 少了的话 _dLdarg 里没有对应项，缺项照旧。
 *     coupled_variables = 'T gr1 gr2 ... gr7'
 *   []
 *
 * 注意 `coupled_variables` 是给 **ACBulk 的 `_dLdarg`** 用的（所以含 T），
 * 而 γ 的导数按 `v` 列表单独取（`gamma_asymm` 不依赖 T，取 dγ/dT 会报错）。
 */
class ACGrGrPolyJ : public ACGrGrPoly
{
public:
  static InputParameters validParams();

  ACGrGrPolyJ(const InputParameters & parameters);

protected:
  virtual Real computeDFDOP(PFFunctionType type) override;
  virtual Real computeQpOffDiagJacobian(unsigned int jvar) override;
  /// 仅用于 `jac_mode = zero_all`：把本核的**对角**贡献也归零
  ///
  /// ⚠ **必须是 `precomputeQpJacobian`，不是 `computeQpJacobian`。**
  /// `ACBulk` 派生自 `KernelValue`，而 `KernelValue::computeJacobian()` 走的是
  /// `precomputeQpJacobian()`（`framework/src/kernels/KernelValue.C:52`）。
  /// `Kernel::computeQpJacobian()` 默认为 0 **且在本类里根本不会被调用** ——
  /// 本轮先 override 了它，结果 `full` 与 `zero_all` 实际是同一个东西，
  /// 白跑一轮。（教训见 AGENTS.md 3.3-21：对照必须真的改到东西。）
  virtual Real precomputeQpJacobian() override;

  /// gamma_asymm 的属性名（默认就是 MOOSE 约定的 "gamma_asymm"）
  const MaterialPropertyName _gamma_name;

  /// d(gamma_asymm)/d(eta_self) —— 补对角的 γ 项
  const MaterialProperty<Real> & _dgamma_dop;

  /// d(gamma_asymm)/d(v[i])，下标与 `_vals_var` 一一对应
  std::vector<const MaterialProperty<Real> *> _dgamma_dv;

  /**
   * 雅可比采样模式 —— **只用于 T1 判据的正对照**，不影响残差。
   *
   * `full`（默认，生产用）：完整的雅可比补全。
   * `off`：不贡献 off-diagonal 与非对角 γ 项。
   * `zero_all`：**连对角贡献也归零**。
   *
   * ⚠ **为什么需要 `zero_all`**：第一版正对照用了 `off`，以为「删掉整个 η–η 非对角块」
   * 是个大项。**实测推翻了**：`||J||` 从 0.30410 只变到 0.30409（**−0.003%**）——
   * 因为 `ACGrGrPoly` 的非对角项是 `η_i·η_j` 型的，**只在晶界单元上非零**，
   * 而 `||J||` 被**处处支撑**的对角项主导。
   * ⇒ `off` 在 Frobenius 范数下几乎是零扰动，**没有排他性**。
   *
   * `zero_all` 把 `computeQpJacobian` 与 `computeDFDOP(Jacobian)` 也归零 ——
   * 这个核在**每个单元**上都有对角贡献，删掉它是真正的量级级扰动。
   *
   * ⚠ 生产输入**绝不能**出现 `jac_mode != full`；`run_nonad_prod.sh` 有断言拦截。
   */
  const MooseEnum _jac_mode;
};
