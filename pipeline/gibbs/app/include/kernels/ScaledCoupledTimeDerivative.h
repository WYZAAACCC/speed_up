// =============================================================================
// ScaledCoupledTimeDerivative —— 残差 = scale * d(v)/dt * test
// =============================================================================
// 与 CoupledTimeDerivative 的区别：多一个**材料系数** scale。
//
// 用途（Gibbs 面模型的"修法 A"，见 pipeline/gibbs/README.md §4）
// ----------------------------------------------------------
// 分裂式 Cahn–Hilliard 里，体相溶质守恒写成两步：
//     w 方程 :  dc/dt  +  div(M grad w) = 0      <- dc/dt 来自 CoupledTimeDerivative(variable=w, v=c)
//     c 方程 :  w = df/dc                          <- SplitCHParsed
// 晶界在局域平衡下把溶质存在面上：u = c + shape*As*c   （Γ = As*c 是面上的过剩）
// 守恒是 du/dt = div(...)  ⇒
//     (1 + shape*As) * dc/dt + div(M grad w) = 0
// ⇒ **把 w 方程里那个 CoupledTimeDerivative 换成带系数 scale = 1 + shape*As 的版本**。
//
// ⚠ 为什么不能用现成的 ADScaledCoupledTimeDerivative：
//   它要求 **AD material**，而本项目的 DerivativeParsedMaterial 是非 AD。
//
// 雅可比完整性：scale 依赖 η 与 T ⇒ 除 d/dv 外还要发射 d(scale)/dη 与 d(scale)/d(args)。
// =============================================================================
#pragma once

#include "CoupledTimeDerivative.h"
#include "DerivativeMaterialInterface.h"
#include "JvarMapInterface.h"

class ScaledCoupledTimeDerivative
  : public DerivativeMaterialInterface<JvarMapKernelInterface<CoupledTimeDerivative>>
{
public:
  static InputParameters validParams();

  ScaledCoupledTimeDerivative(const InputParameters & parameters);

protected:
  virtual void initialSetup() override;
  virtual Real computeQpResidual() override;
  virtual Real computeQpJacobian() override;
  virtual Real computeQpOffDiagJacobian(unsigned int jvar) override;

  /// 乘在 d(v)/dt 上的材料系数
  const MaterialProperty<Real> & _scale;
  /// d(scale)/d(本变量)
  const MaterialProperty<Real> & _dscale_du;
  /// d(scale)/d(v)
  const MaterialProperty<Real> & _dscale_dv;
  /// d(scale)/d(args_i)
  const unsigned int _n_args;
  std::vector<const MaterialProperty<Real> *> _dscale_darg;
};