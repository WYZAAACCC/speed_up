// =============================================================================
// ScaledTimeDerivative —— 时间导数乘以一个**材料系数**
// =============================================================================
// 残差：  scale(x, T, eta) * du/dt * test
//
// 为什么要这个核（Gibbs 面模型的"修法 A"，见 pipeline/gibbs/README.md §4）
// -------------------------------------------------------------------------
// 低维晶界 Γ 的方程是  dΓ/dt = k_att*(Γ_eq - Γ)。
// 物理上 k_att ~ 1e6~1e9 /s（原子尺度附着速率），而晶界邻域的体相变化时标是
// wGB^2/D（液相 13 µs、固相 40 s）⇒ **局域平衡是严格渐近极限**。
// 取 k_att -> ∞ 解析极限后 Γ = Γ_eq(c,T) 严格成立，体相方程变成
//
//      (1 + shape*As) * dc/dt = div(D grad c)
//
// ⇒ 快速速率被解析消掉，**既没有刚度、又严格保持局域平衡**。
//
// 为什么不直接用现成对象
// ----------------------
//   * CoupledTimeDerivative 没有系数参数；
//   * ADScaledCoupledTimeDerivative 需要 **AD material**，而本项目的
//     DerivativeParsedMaterial 是非 AD 的（改 AD 会牵动整条链，风险大）。
//   ⇒ 只能自己写这 ~50 行。
//
// 实现要点（AGENTS.md 教训 7）
// ---------------------------
//   `TimeDerivative` 派生自 `TimeKernel`，但它自己 override 了
//   `computeJacobian()`（有 lumping 分支）。为了不把行为交给基类的自定义路径，
//   本核**直接从 `TimeKernel` 派生**，三个 computeQp* 全部显式实现。
//
// 雅可比完整性（AGENTS.md §3.1 坑 1 / 教训 28）
// -------------------------------------------
//   scale 依赖 η 与 T ⇒ 除对角项外还必须发射 d(scale)/dη 的非对角项，
//   否则残差一拍、雅可比少一块 —— 正是本项目反复踩的那类坑。
//   ※ 提醒：`DerivativeParsedMaterial` 只对**表达式里字面出现**的变量发射导数；
//     scale 的表达式里必须把 η 内联，不能经 material_property_names 转一手。
// =============================================================================
#pragma once

#include "TimeKernel.h"
#include "DerivativeMaterialInterface.h"
#include "JvarMapInterface.h"

class ScaledTimeDerivative : public DerivativeMaterialInterface<JvarMapKernelInterface<TimeKernel>>
{
public:
  static InputParameters validParams();

  ScaledTimeDerivative(const InputParameters & parameters);

protected:
  virtual void initialSetup() override;
  virtual Real computeQpResidual() override;
  virtual Real computeQpJacobian() override;
  virtual Real computeQpOffDiagJacobian(unsigned int jvar) override;

  /// 乘在时间导数上的材料系数
  const MaterialProperty<Real> & _scale;
  /// d(scale)/d(本变量)  —— 存在的意义是让 MatReaction 式的一致性好核出来
  const MaterialProperty<Real> & _dscale_du;
  /// d(scale)/d(args_i) 的个数与指针
  const unsigned int _n_args;
  std::vector<const MaterialProperty<Real> *> _dscale_darg;
};