// =============================================================================
// GBFluxExchange —— 体相 ↔ Gibbs 面 的**守恒通量交换**（mortar 约束）
// =============================================================================
// 为什么必须自己写（路线 1 的侦察结论，有实测证据）：
//   · `LowerDBlockFromSidesetGenerator` 造出的低维块**不是体块的子域邻居**
//     ⇒ `InterfaceKernel` 找不到面配对（实测：Γ 纹丝不动）
//   · MOOSE 用低维块的现成例子**全是 mortar 约束**，**没有"通量型"的**
//   ⇒ 只能自己写一个 MortarConstraint。
//
// 物理
//   面:   (A_s/ρ_mol)·dGam/dt = K·(c − Gam)      Gam ≡ Γ/A_s   [无量纲]
//   体:   面从体相抽走溶质，单位面积通量 = K·(c − Gam)
//   K = A_s·k_att/ρ_mol
//
//   残差（三个 mortar 类型）：
//     Lower     : + K·(Gam − c)·test_lower
//     Secondary : − K·(c − Gam)·test_secondary
//     Primary   : − K·(c − Gam)·test_primary
//   ⇒ 两侧同号同形式 ⇒ 面拿到的正是体相失去的 ⇒ **总量守恒**
//
// ⚠ 时间导数项不在这里（ADMortarConstraint 不暴露 dGam/dt）：
//   面上另放 ScaledTimeDerivative 负责储存项。
// =============================================================================
#pragma once

#include "ADMortarConstraint.h"

class GBFluxExchange : public ADMortarConstraint
{
public:
  static InputParameters validParams();

  GBFluxExchange(const InputParameters & parameters);

protected:
  ADReal computeQpResidual(Moose::MortarType mortar_type) final;

  /// K = A_s·k_att/ρ_mol
  const MaterialProperty<Real> & _kex;

  /// 诊断开关（debug_print）：打印前若干个 QP 的 sec/pri/lam/kex
  const bool _debug;
  unsigned int _dbg_n;
  unsigned int _dbg_per_type[3] = {0, 0, 0};
};
