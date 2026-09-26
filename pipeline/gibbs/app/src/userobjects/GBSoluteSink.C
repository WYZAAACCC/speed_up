#include "GBSoluteSink.h"

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

#include <algorithm>
#include <cmath>
#include <set>

registerMooseObject("GibbsApp", GBSoluteSink);

InputParameters
GBSoluteSink::validParams()
{
  InputParameters params = GeneralUserObject::validParams();
  params.addClassDescription("交错耦合：把 Gibbs 面拿走的溶质按构造成比例地从体相界面节点的 c 里"
                             "扣掉。守恒是代数恒等式，与非线性容差无关。");
  // ⚠ 故意用 std::string 而不是 VariableName/SubdomainName（见头文件说明：
  //   写成 VariableName 会让 MOOSE 去改耦合/稀疏结构，而 Gam 只在低维块上 ⇒ 雅可比段错误）
  params.addRequiredParam<std::vector<std::string>>("gam_names",
                                                    "每条晶界的低维状态量（Gam≡Γ/A_s）");
  params.addRequiredParam<std::vector<std::string>>("gb_blocks", "对应的低维块名");
  params.addRequiredParam<std::string>("c_name", "体相浓度变量");
  params.addRequiredParam<std::string>("T_name", "温度（AuxVariable）");
  params.addRequiredParam<Real>("rho_mol", "体相摩尔密度 [mol/m^3]");
  params.addParam<Real>("gamma_mono", 2.1421e-5, "Γ0 [mol/m^2]");
  params.addParam<Real>("dh_seg", -11931.1, "ΔH_seg [J/mol]");
  params.addParam<Real>("ds_seg", 0.0, "ΔS_seg [J/mol/K]");
  params.addParam<Real>("r_gas", 8.314462618, "R");
  params.addParam<bool>("probe_stub", false, "诊断：掏空 execute()");
  // ⚠ 必须是 **timestep_begin**，不能是 timestep_end！
  //   实测（2026-09-21）：在 timestep_end 改 solution，会被 MOOSE 的 advance()/同步丢掉 ——
  //   体相只变了该变量的 ~1/1000（dc 明明算对了）。
  //   改到"下一步开始前"施加 ⇒ 修正进入初值、进入这一步的解，才真正生效。
  params.set<ExecFlagEnum>("execute_on") = {EXEC_TIMESTEP_BEGIN};
  return params;
}

GBSoluteSink::GBSoluteSink(const InputParameters & parameters)
  : GeneralUserObject(parameters),
    _rho_mol(getParam<Real>("rho_mol")),
    _gam0(getParam<Real>("gamma_mono")),
    _dh_seg(getParam<Real>("dh_seg")),
    _ds_seg(getParam<Real>("ds_seg")),
    _r_gas(getParam<Real>("r_gas")),
    _gam_names(getParam<std::vector<std::string>>("gam_names")),
    _gb_blocks(getParam<std::vector<std::string>>("gb_blocks")),
    _c_name(getParam<std::string>("c_name")),
    _T_name(getParam<std::string>("T_name")),
    _M_old(0.0),
    _have_old(false),
    _V_int(0.0),
    _setup_done(false)
{
}

Real
GBSoluteSink::As(Real T) const
{
  if (T <= 1.0)
    T = 1.0; // 防 0 除（实际 T >= 353 K）
  return _gam0 * std::exp(-(_dh_seg - _ds_seg * T) / (_r_gas * T));
}

Real
GBSoluteSink::surfaceContent() const
{
  auto & mesh = _subproblem.mesh().getMesh();
  auto & nl = _fe_problem.getNonlinearSystemBase(0);
  auto & aux = _fe_problem.getAuxiliarySystem();
  auto & dm = nl.system().get_dof_map();
  // ⚠ T 住在**辅助系统**里，它有自己的 dof_map 与编号！
  //   实测（2026-09-21）：拿非线性系统的 dof_map 去查 T 的 dof ⇒ 越界 ⇒ **段错误**。
  auto & aux_dm = aux.system().get_dof_map();
  const auto & sol = nl.solution();
  const auto & aux_sol = aux.solution();
  _console << "[GBSink] surfaceContent: sol.size=" << sol.size()
           << " aux.size=" << aux_sol.size() << std::endl;
  const unsigned int T_var = aux.getVariable(_tid, _T_name).number();
  _console << "[GBSink]   T_var=" << T_var << std::endl;

  Real M = 0.0;
  for (unsigned int k = 0; k < _gam_names.size(); ++k)
  {
    const unsigned int g_var = nl.getVariable(_tid, _gam_names[k]).number();
    _console << "[GBSink]   gam " << _gam_names[k] << " var=" << g_var << std::endl;
    const auto bid = _subproblem.mesh().getSubdomainID(SubdomainName(_gb_blocks[k]));

    for (const auto * e : mesh.active_element_ptr_range())
    {
      if (e->subdomain_id() != bid)
        continue;
      const unsigned int nn = e->n_nodes();
      if (nn != 4) // 低维面元应当是四边形
        mooseError("GBSoluteSink: 低维面元有 ", nn, " 个节点，预期 4");

      // 平面四边形：面积 = 0.5*|(p2-p0) x (p3-p1)|
      const Point d1 = e->point(2) - e->point(0);
      const Point d2 = e->point(3) - e->point(1);
      const Real area = 0.5 * (d1.cross(d2)).norm();
      if (area <= 0.0)
        continue;

      for (unsigned int n = 0; n < nn; ++n)
      {
        const auto * nd = e->node_ptr(n);
        std::vector<dof_id_type> gd, td;
        dm.dof_indices(nd, gd, g_var);
        aux_dm.dof_indices(nd, td, T_var);
        const Real gam = gd.empty() ? 0.0 : sol(gd[0]);
        const Real T = td.empty() ? 300.0 : aux_sol(td[0]);
        M += As(T) * gam * (area / 4.0);
      }
    }
  }
  return M;
}

void
GBSoluteSink::execute()
{
  // 【二分诊断】暂时掏空：只留参数、不碰任何系统/网格 API。
  //   若仍段错误 ⇒ 崩溃来自"对象在场"（参数/注册/执行组），与内部逻辑无关。
  if (getParam<bool>("probe_stub"))
    return;

  // ⚠ 2026-09-21 实测：MOOSE 会在 **EXEC_INITIAL** 就调用本对象的 execute()，
  //   而那时非线性/辅助系统的解向量还没建好 ⇒ 读它们**直接段错误**（rc=139，
  //   日志停在第一步的雅可比装配处，且本对象一行输出都没有）。
  //   二分证据：把 execute() 掏空（probe_stub=true）⇒ rc=0、11 步正常跑完。
  //   ⇒ 必须在最前面挡掉 initial，把基准量推迟到**第一次 timestep_end** 再取。
  if (_fe_problem.getCurrentExecuteOnFlag() == EXEC_INITIAL)
    return;
  auto & mesh = _subproblem.mesh().getMesh();
  _console << "[GBSink] execute: flag=" << (int)_fe_problem.getCurrentExecuteOnFlag()
           << " setup_done=" << _setup_done << std::endl;

  if (!_setup_done)
  {
    std::set<dof_id_type> iface_ids;
    for (unsigned int k = 0; k < _gb_blocks.size(); ++k)
    {
      const auto bid = _subproblem.mesh().getSubdomainID(SubdomainName(_gb_blocks[k]));
      _console << "[GBSink]   block " << _gb_blocks[k] << " -> id " << bid << std::endl;
      for (const auto * e : mesh.active_element_ptr_range())
        if (e->subdomain_id() == bid)
          for (unsigned int n = 0; n < e->n_nodes(); ++n)
            iface_ids.insert(e->node_ptr(n)->id());
    }
    _console << "[GBSink]   iface node ids = " << iface_ids.size() << std::endl;
    _iface_nodes.clear();
    for (const auto * nd : mesh.active_node_ptr_range())
      if (iface_ids.count(nd->id()))
        _iface_nodes.push_back(nd);
    _console << "[GBSink]   iface nodes = " << _iface_nodes.size() << std::endl;

    // V_int = Σ_界面节点 (节点在**体相**里的体积份额) = Σ_e vol_e * (#界面节点数 / n_nodes_e)
    // ⚠ 必须**排掉低维面元**：它们的 "volume()" 是面积（4e-12），量进不去就错 5~6 个数量级
    //   （实测：含低维元时 V_int = 1.92e-9，正确值 2.4e-15）。
    Real V = 0.0;
    for (const auto * e : mesh.active_element_ptr_range())
    {
      if (e->dim() < mesh.mesh_dimension())
        continue; // 低维面元不算
      unsigned int cnt = 0;
      for (unsigned int n = 0; n < e->n_nodes(); ++n)
        if (iface_ids.count(e->node_ptr(n)->id()))
          ++cnt;
      if (cnt)
        V += e->volume() * (Real)cnt / (Real)e->n_nodes();
    }
    _V_int = V;
    _console << "[GBSink]   V_int = " << _V_int << std::endl;
    _setup_done = true;
    _console << "[GBSink]   量初始面含量..." << std::endl;
    _M_old = surfaceContent();
    _console << "[GBSink]   M0 = " << _M_old << std::endl;
    _have_old = true;
    _console << "[GBSoluteSink] 界面节点 " << _iface_nodes.size() << " 个，V_int = " << _V_int
             << " m^3，初始面含量 M = " << _M_old << " mol" << std::endl;
    return;
  }

  const Real M = surfaceContent();
  const Real dM = M - _M_old;
  _M_old = M;
  if (dM == 0.0 || _V_int <= 0.0)
    return;

  const Real dc = -dM / (_rho_mol * _V_int);

  auto & nl = _fe_problem.getNonlinearSystemBase(0);
  auto & sys = nl.system();
  auto & dm = sys.get_dof_map();
  const unsigned int c_var = nl.getVariable(_tid, _c_name).number();

  auto & sol = nl.solution();
  auto & sol_old = nl.solutionOld();
  // ⚠ BDF2 的**第三个**解向量必须一起平移！
  //   u_dot_BDF2 = (1.5*u - 2*u_old + 0.5*u_older)/dt
  //   只平移前两个 ⇒ 剩下 -0.5*dc/dt 的**伪造时间导数**（量级与修正本身相同）
  //   ⇒ 实测：体相多丢了 48%（1.439e-15 vs 应丢 0.972e-15）。
  //   三个一起平移 ⇒ 1.5*dc - 2*dc + 0.5*dc = 0 ⇒ u_dot 不变 ✓
  auto & sol_older = nl.solutionOlder();

  for (const auto * nd : _iface_nodes)
  {
    std::vector<dof_id_type> dofs;
    dm.dof_indices(nd, dofs, c_var);
    for (const auto d : dofs)
      if (d >= sol.first_local_index() && d < sol.last_local_index())
      {
        ++_napplied;
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

  _console << "[GBSoluteSink] t=" << _t << "  dM = " << dM << " mol  =>  dc = " << dc
           << "  扣的总额 = " << (_rho_mol * dc * _V_int) << " mol（应 = " << -dM
           << "）  V_int=" << _V_int << "  累计改到的 dof 数 = " << _napplied << std::endl;
}
