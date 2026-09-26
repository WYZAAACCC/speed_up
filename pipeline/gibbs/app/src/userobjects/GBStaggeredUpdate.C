#include "GBStaggeredUpdate.h"

#include "FEProblemBase.h"
#include "NonlinearSystemBase.h"
#include "AuxiliarySystem.h"
#include "MooseMesh.h"
#include "MooseVariableFE.h"

#include "libmesh/mesh_base.h"
#include "libmesh/elem.h"
#include "libmesh/node.h"
#include "libmesh/numeric_vector.h"
#include "libmesh/dof_map.h"
#include "libmesh/system.h"

#include <cmath>
#include <map>
#include <set>
#include <vector>

registerMooseObject("GibbsApp", GBStaggeredUpdate);

InputParameters
GBStaggeredUpdate::validParams()
{
  InputParameters params = GeneralUserObject::validParams();
  params.addClassDescription("交错耦合：面↔体相 一步显式交换（Γ 弛豫 + 体相按构造成比例扣账）。");
  // ⚠ 一律用 std::string：写成 VariableName 会让 MOOSE 去改耦合/稀疏结构（而 Gam 只在
  //   低维块上）⇒ 雅可比装配段错误。变量自己用系统 API 查。
  params.addRequiredParam<std::vector<std::string>>("gam_names", "每条晶界的低维状态量 Gam≡Γ/A_s");
  params.addRequiredParam<std::vector<std::string>>("gb_blocks", "对应的低维块名");
  params.addRequiredParam<std::string>("c_name", "体相浓度变量");
  params.addRequiredParam<std::string>("T_name", "温度（AuxVariable）");
  params.addParam<std::string>("gamgb_name", "",
                               "【S11 拖曳】把面 Γ 投影过去的体相 AuxVariable 名（空=不投影）");
  params.addParam<bool>("always_rebuild", false,
                        "每步都重建界面节点表/V_int（AMR 会改网格 ⇒ 必须；不开则只建一次）");
  params.addRequiredParam<Real>("rho_mol", "体相摩尔密度 [mol/m^3]");
  params.addRequiredParam<Real>("k_att", "面↔体相 附着速率 [1/s]");
  params.addParam<Real>("gamma_mono", 2.1421e-5, "Γ0 [mol/m^2]");
  params.addParam<Real>("dh_seg", -11931.1, "ΔH_seg [J/mol]");
  params.addParam<Real>("ds_seg", 0.0, "ΔS_seg [J/mol/K]");
  params.addParam<Real>("r_gas", 8.314462618, "R");
  // timestep_begin：改的解要进入这一步的初值才不会被 advance() 丢掉（实测）
  params.set<ExecFlagEnum>("execute_on") = {EXEC_TIMESTEP_BEGIN};
  return params;
}

GBStaggeredUpdate::GBStaggeredUpdate(const InputParameters & parameters)
  : GeneralUserObject(parameters),
    _rho_mol(getParam<Real>("rho_mol")),
    _gam0(getParam<Real>("gamma_mono")),
    _dh_seg(getParam<Real>("dh_seg")),
    _ds_seg(getParam<Real>("ds_seg")),
    _r_gas(getParam<Real>("r_gas")),
    _k_att(getParam<Real>("k_att")),
    _gam_names(getParam<std::vector<std::string>>("gam_names")),
    _gb_blocks(getParam<std::vector<std::string>>("gb_blocks")),
    _c_name(getParam<std::string>("c_name")),
    _T_name(getParam<std::string>("T_name")),
    _gamgb_name(getParam<std::string>("gamgb_name")),
    _always_rebuild(getParam<bool>("always_rebuild")),
    _V_int(0.0),
    _setup_done(false)
{
}

Real
GBStaggeredUpdate::As(Real T) const
{
  if (T <= 1.0)
    T = 1.0;
  return _gam0 * std::exp(-(_dh_seg - _ds_seg * T) / (_r_gas * T));
}

void
GBStaggeredUpdate::execute()
{
  // MOOSE 会在 EXEC_INITIAL 也调它，那时解向量还没建好 ⇒ 直接段错误。挡掉。
  if (_fe_problem.getCurrentExecuteOnFlag() == EXEC_INITIAL)
    return;

  auto & mesh = _subproblem.mesh().getMesh();
  auto & nl = _fe_problem.getNonlinearSystemBase(0);
  auto & aux = _fe_problem.getAuxiliarySystem();
  auto & dm = nl.system().get_dof_map();
  auto & aux_dm = aux.system().get_dof_map(); // T 在辅助系统里，用它自己的 dof_map
  auto & sol = nl.solution();
  auto & sol_old = nl.solutionOld();
  auto & sol_older = nl.solutionOlder(); // BDF2 的第三个向量必须一起平移
  auto & aux_sol = aux.solution();
  // 【S11 拖曳】把面上的 Γ 投影到体相节点的 AuxVariable `gamgb` 上，
  //   供体相材料 L_eff = L/(1+β·A_s·gamgb) 读 —— 这样"溶质→拓扑"的反馈才有数据可用。
  //   （Γ 只在低维块上，体相材料读不到它；投影到共享节点是唯一干净的办法。）
  const bool have_gamgb =
      (_gamgb_name != "" && _fe_problem.getAuxiliarySystem().hasVariable(_gamgb_name));
  if (_fe_problem.getCurrentExecuteOnFlag() != EXEC_TIMESTEP_BEGIN)
    ;
  else
    _console << "[GBStagger] 投影 gamgb：name='" << _gamgb_name
             << "'  have=" << have_gamgb << std::endl;
  unsigned int gamgb_var = 0;
  if (have_gamgb)
    gamgb_var = aux.getVariable(_tid, _gamgb_name).number();
  auto & aux_sol_mod = aux.solution();
  const unsigned int T_var = aux.getVariable(_tid, _T_name).number();
  const unsigned int c_var = nl.getVariable(_tid, _c_name).number();

  // ---------------- 只做一次：界面节点表 + V_int ----------------
  if (_always_rebuild)
    _setup_done = false;   // AMR 会改网格 ⇒ 每步重建（代价 O(单元数)，相对求解可忽略）
  if (!_setup_done)
  {
    std::set<dof_id_type> iface_ids;
    for (unsigned int k = 0; k < _gb_blocks.size(); ++k)
    {
      const auto bid = _subproblem.mesh().getSubdomainID(SubdomainName(_gb_blocks[k]));
      for (const auto * e : mesh.active_element_ptr_range())
        if (e->subdomain_id() == bid)
          for (unsigned int n = 0; n < e->n_nodes(); ++n)
            iface_ids.insert(e->node_ptr(n)->id());
    }
    _iface_nodes.clear();
    for (const auto * nd : mesh.active_node_ptr_range())
      if (iface_ids.count(nd->id()))
        _iface_nodes.push_back(nd);

    // V_int = Σ_界面节点 的**体相**节点体积份额；⚠ 必须排掉低维面元（它的 volume() 是面积）
    Real V = 0.0;
    for (const auto * e : mesh.active_element_ptr_range())
    {
      if (e->dim() < mesh.mesh_dimension())
        continue;
      unsigned int cnt = 0;
      for (unsigned int n = 0; n < e->n_nodes(); ++n)
        if (iface_ids.count(e->node_ptr(n)->id()))
          ++cnt;
      if (cnt)
        V += e->volume() * (Real)cnt / (Real)e->n_nodes();
    }
    _V_int = V;
    _setup_done = true;
    _console << "[GBStagger] 界面节点 " << _iface_nodes.size() << " 个，V_int = " << _V_int
             << " m^3；k_att = " << _k_att << " 1/s" << std::endl;
    return;
  }

  // ---------------- 每步：面推一步 + 体相按构造成比例扣账 ----------------
  const Real dt = _dt;
  const Real relax = std::exp(-_k_att * dt); // 精确解因子

  // (1) 面上逐节点的 ΔΓ（Gam 单位），存起来后面一次性写回
  // ⚠ 两条量必须分清（实测踩过两次）：
  //   · **写回给节点的**：该节点自己的 ODE 增量 dgam_n，**只写一次**
  //     （内部节点属于 4 个面元；写 4 次或写"4 个之和"都会把 Gam 放大 4 倍，
  //      实测读回 Gam ∈ [0.0034, 0.0137] 正是这个 4×）
  //   · **记账用的**：Σ_面元 A_s·dgam_n·(A_e/4) —— 这才是 ∫A_s·ΔΓ dA
  //     （节点面积份额 w_n = ∫φ_n dA = Σ_{e∋n} A_e/4）
  std::map<std::pair<unsigned int, dof_id_type>, Real> dgam_by_node;
  Real dM = 0.0; // 面拿到的总量 [mol]
  std::vector<Real> per_gb_raw(   // 诊断：每条晶界 Σ dgam*w（= 我算的 Δ∫Gam dA）
      _gam_names.size(), 0.0);
  // 诊断：读回的 Gam（应用之前）逐条晶界的 min/max —— 判断"求解是否改动了 Gam"
  std::vector<Real> g_lo(_gam_names.size(), 1e30), g_hi(_gam_names.size(), -1e30);

  for (unsigned int k = 0; k < _gam_names.size(); ++k)
  {
    const unsigned int g_var = nl.getVariable(_tid, _gam_names[k]).number();
    const auto bid = _subproblem.mesh().getSubdomainID(SubdomainName(_gb_blocks[k]));
    for (const auto * e : mesh.active_element_ptr_range())
    {
      if (e->subdomain_id() != bid)
        continue;
      const unsigned int nn = e->n_nodes();
      // 低维单元的"测度"：2D 网格里的 1D 线元 ⇒ 长度；3D 网格里的 2D 面元 ⇒ 面积。
      // 统一用 libMesh 的 `volume()`（对低维单元它就是该维度的测度）——
      // 这比手写叉积更稳（非平面面元也正确），且**天然支持二维版**。
      const Real meas = e->volume();
      if (meas <= 0.0)
        continue;
      const Real w = meas / (Real)nn; // 节点份额：∫φ_n d(测度) = meas/n_nodes
      for (unsigned int n = 0; n < nn; ++n)
      {
        const auto * nd = e->node_ptr(n);
        std::vector<dof_id_type> gd, td, cd;
        dm.dof_indices(nd, gd, g_var);
        dm.dof_indices(nd, cd, c_var);
        aux_dm.dof_indices(nd, td, T_var);
        if (gd.empty() || cd.empty() || td.empty())
          continue;
        const Real gam = sol(gd[0]);
        g_lo[k] = std::min(g_lo[k], gam);
        g_hi[k] = std::max(g_hi[k], gam);
        if (have_gamgb)
        {
          std::vector<dof_id_type> ad;
          aux_dm.dof_indices(nd, ad, gamgb_var);
          if (!ad.empty())
          {
            const Real prev = aux_sol_mod(ad[0]);
            aux_sol_mod.set(ad[0], std::max(prev, gam)); // 取各条晶界的最大 Γ
            _gamgb_max = std::max(_gamgb_max, gam);
          }
        }
        const Real c = sol(cd[0]);
        const Real T = aux_sol(td[0]);
        const Real AsT = As(T);
        const Real gam_eq = c;                       // McLean（Henry 极限）：Gam_eq = c
        const Real gam_new = gam_eq + (gam - gam_eq) * relax;
        const Real dgam = gam_new - gam;
        dgam_by_node[{g_var, nd->id()}] = dgam; // 直接赋值（同一个值会被重复覆盖，无害）
        dM += AsT * dgam * w;                        // Γ = A_s·Gam 的增量 × 面积份额
        per_gb_raw[k] += dgam * w;
      }
    }
  }

  if (dgam_by_node.empty() || dM == 0.0)
    return;

  // (2) 写回：面（Gam）+ 体相（c），两边都在 u / u_old / u_older 上一起平移
  for (const auto & kv : dgam_by_node)
  {
    const unsigned int var = kv.first.first;
    const dof_id_type nid = kv.first.second;
    const Real dgam = kv.second;
    const Node * nd = mesh.query_node_ptr(nid);
    if (!nd)
      continue;
    std::vector<dof_id_type> vd;
    dm.dof_indices(nd, vd, var);
    for (const auto d : vd)
      if (d >= sol.first_local_index() && d < sol.last_local_index())
      {
        sol.add(d, dgam);
        if (d < (dof_id_type)sol_old.size())
          sol_old.add(d, dgam);
        if (d < (dof_id_type)sol_older.size())
          sol_older.add(d, dgam);
        ++_napplied;
      }
  }

  const Real dc = -dM / (_rho_mol * _V_int);
  for (const auto * nd : _iface_nodes)
  {
    std::vector<dof_id_type> dofs;
    dm.dof_indices(nd, dofs, c_var);
    for (const auto d : dofs)
      if (d >= sol.first_local_index() && d < sol.last_local_index())
      {
        sol.add(d, dc);
        if (d < (dof_id_type)sol_old.size())
          sol_old.add(d, dc);
        if (d < (dof_id_type)sol_older.size())
          sol_older.add(d, dc);
      }
  }
  sol.close();
  sol_old.close();
  sol_older.close();
  _dM_total += dM;

  // 诊断：把"我算的 Δ∫Gam dA"与"后处理器给的 Δgam_int"直接对比
  for (unsigned int k = 0; k < _gam_names.size(); ++k)
  {
    const Real pp =
        _fe_problem.getPostprocessorValueByName("gam" + std::to_string(k) + "_int");
    const Real d_pp = pp - _pp_prev[k];
    _pp_prev[k] = pp;
    _console << "[GBStagger]   晶界 " << k << ": 读回 Gam ∈ [" << g_lo[k] << ", " << g_hi[k]
             << "]   我算 Δ∫Gam dA = " << per_gb_raw[k]
             << "   后处理器 Δ∫Gam dA = " << d_pp
             << "   比值 = " << (d_pp != 0.0 ? per_gb_raw[k] / d_pp : 0.0) << std::endl;
  }

  _console << "[GBStagger] t=" << _t << "  dt=" << dt << "  dM=" << dM << " mol  dc=" << dc
           << "  (累计面拿 " << _dM_total << " mol；体相扣的总额 = " << -_dM_total
           << " mol)  改到 dof=" << _napplied
           << "  gamgb_max(写到体相的最大 Γ)=" << _gamgb_max << std::endl;
}
