// =============================================================================
// GBStaggeredUpdate —— 【交错耦合】面↔体相 一步交换（显式，双向都在这一个对象里）
// =============================================================================
// 为什么整个换掉 mortar 方案（2026-09-21 实测）：
//   · mortar 给体相的汇 ~1e-17/节点，而体相自身残差 ~1e-12 ⇒ 容差从 1e-7 扫到 1e-16
//     体相**逐位不动** ⇒ 强耦合根本约束不住那一项；
//   · 把 kex 修对之后熔池第 1 步就 |R| = 1.92e1（耦合真打开后体相的强瞬变把它顶崩）。
//   ⇒ 改成**显式交错**：两边都用"上一步已知量"，不做隐式联立。
//
// 与 RESEARCH_INTENT.md §3.2 的架构完全一致：
//   「离散开来看就是上一步的拓扑变化得到的结果影响这一步溶质的变化，
//     这一步晶界上溶质的变化会影响下一步的拓扑变化。」
//
// 每步（timestep_begin）做两件事，**同时**做 ⇒ 守恒是代数恒等式：
//   (1) 面：Γ 按 McLean 弛豫推一步（用精确解，无条件稳定）
//         Γ_eq = A_s(T)·c          （Henry 极限的 McLean）
//         Γ    ← Γ_eq + (Γ_old − Γ_eq)·exp(−k_att·dt)
//   (2) 体相：把面拿走的量 ΔM = Σ_n A_s(T_n)·ΔΓ_n·w_n 按节点体积**原样扣掉**
//         Δc   = −ΔM/(ρ_mol·V_int)   （加在全部界面节点上）
//   ⇒ ρ_mol·Δ∫c dV + ΔM ≡ 0 **恒成立**（不是"解出来的"，是构造出来的）
//
// 为什么用指数精确解而不是显式欧拉：k_att·dt 可以 > 1（熔池里 dt 会被切到很小，
//   但也可能涨到 1e-7 ⇒ k_att·dt = 0.1；用精确解则**任意 dt 都稳定**，且一阶精确）。
//
// ⚠ 已知代价（记账）：这是**一阶**交错（O(dt) 分裂误差），
//   判据是把 dtmax 减半、误差应减半。
// =============================================================================
#pragma once

#include "GeneralUserObject.h"

class GBStaggeredUpdate : public GeneralUserObject
{
public:
  static InputParameters validParams();
  GBStaggeredUpdate(const InputParameters & parameters);

  virtual void initialize() override {}
  virtual void execute() override;
  virtual void finalize() override {}

protected:
  /// A_s(T) = Γ0·exp(−ΔH_seg/(R T))   [mol/m^2]
  Real As(Real T) const;

  const Real _rho_mol;
  const Real _gam0;
  const Real _dh_seg;
  const Real _ds_seg;
  const Real _r_gas;
  const Real _k_att;

  const std::vector<std::string> _gam_names;
  const std::vector<std::string> _gb_blocks;
  const std::string _c_name;
  const std::string _T_name;
  /// 【S11】把面 Γ 投影到体相的 AuxVariable 名（空 = 不做拖曳投影）
  std::string _gamgb_name = "";
  /// 每步重建节点表（AMR 时必须）
  const bool _always_rebuild = false;
  /// 诊断：写进 gamgb 的最大值（若恒为 0 ⇒ 投影没生效）
  Real _gamgb_max = 0.0;

  std::vector<const Node *> _iface_nodes;
  Real _V_int;
  bool _setup_done;

  /// 诊断：累计扣掉的量 [mol]
  Real _dM_total = 0.0;
  /// 诊断：累计改到的 dof 数
  unsigned int _napplied = 0;
  /// 诊断：上一次的 gam_int 后处理器值（用来和"我算的"对账）
  std::vector<Real> _pp_prev{0.0, 0.0};
};
