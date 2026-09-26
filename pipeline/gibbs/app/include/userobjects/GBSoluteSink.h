// =============================================================================
// GBSoluteSink —— 【交错耦合】把 Gibbs 面拿走的溶质，**按构造成比例地**从体相扣掉
// =============================================================================
// 为什么必须有它（2026-09-21 实测）：
//   mortar 约束给体相的那条 primal 残差，在**每个节点上只有 ~1e-17**，
//   而体相自己的残差 ~1e-12～1e-15。求解器按"残差范数 < 容差"停 ⇒
//   这个汇**永远落在分辨率之下**：容差从 1e-7 扫到 1e-16，体相积分浓度逐位不变。
//   ⇒ 不能指望"同一个牛顿解出来"，只能**按构造成立**：
//      每步量出面上 Γ 的增量 ΔM，再把 -ΔM 直接写回体相在界面节点的 c。
//   ⇒ 守恒变成**代数恒等式**，与容差、与残差量级都无关。
//
// 这也正是项目 2×2 架构里的"交错耦合"：拓扑/体相走传统求解器，
// 晶界那一层单独推一步，两步之间交换通量。
//
// 执行时机：timestep_end（解完之后）
// 写回：solution / solutionOld / solutionOldOld **同时**加同一个 Δc
//       （不改时间导数：整条历史平移同一个常量 ⇒ u̇ 不变）
// =============================================================================
#pragma once

#include "GeneralUserObject.h"

class GBSoluteSink : public GeneralUserObject
{
public:
  static InputParameters validParams();
  GBSoluteSink(const InputParameters & parameters);

  virtual void initialize() override {}
  virtual void execute() override;
  virtual void finalize() override {}

protected:
  /// 面上的 Γ 总量 [mol]：Σ_k ∫ A_s(T)*Gam_k dA
  Real surfaceContent() const;

  /// A_s(T) = Γ0*exp(-ΔH_seg/(R T))   [mol/m^2]
  Real As(Real T) const;

  const Real _rho_mol;
  const Real _gam0;
  const Real _dh_seg;
  const Real _ds_seg;
  const Real _r_gas;

  // ⚠ 一律用**纯 std::string**，不要用 VariableName/SubdomainName：
  //   实测把 VariableName 写进参数会让 MOOSE 把它当**耦合变量**去改雅可比/稀疏结构，
  //   而 Gam 只定义在低维块上 ⇒ **雅可比装配段错误**（日志停在 "0 Nonlinear |R|" 之后）。
  //   这里自己用系统 API 查变量，绕开 MOOSE 的耦合登记。
  const std::vector<std::string> _gam_names;   ///< 每条晶界的低维状态量名
  const std::vector<std::string> _gb_blocks;   ///< 每条晶界的低维块名
  const std::string _c_name;                   ///< 体相浓度
  const std::string _T_name;                   ///< 温度（AuxVariable）

  Real _M_old;
  bool _have_old;

  // 缓存的接口节点与它们的体相"节点体积"之和
  std::vector<const Node *> _iface_nodes;
  Real _V_int;
  bool _setup_done;
  /// 诊断：累计改到过多少个 dof
  unsigned int _napplied = 0;
};
