#include "GBFluxExchange.h"

registerMooseObject("GibbsApp", GBFluxExchange);

InputParameters
GBFluxExchange::validParams()
{
  InputParameters params = ADMortarConstraint::validParams();
  params.addClassDescription(
      "体相 <-> Gibbs 面 的守恒通量交换。内部界面上 Secondary/Primary 是两个不同的体相自由度，"
      "晶界同时与两侧交换 => 每侧分一半；面侧收两份半额 => 总量守恒。"
      "时间导数项请另外在低维块上放 ScaledTimeDerivative。");
  params.addRequiredParam<MaterialPropertyName>("kex", "K = A_s*k_att/rho_mol");
  params.addParam<bool>("debug_print", false,
                        "诊断用：打印前若干个 (secondary,primary,lambda,kex,qp) 取值");
  return params;
}

GBFluxExchange::GBFluxExchange(const InputParameters & parameters)
  : ADMortarConstraint(parameters),
    _kex(getMaterialProperty<Real>("kex")),
    _debug(getParam<bool>("debug_print")),
    _dbg_n(0)
{
}

ADReal
GBFluxExchange::computeQpResidual(Moose::MortarType mortar_type)
{
  // ⚠ 每种 mortar_type 各打前 2 次（不要用一个总计数器：前 12 次会被 Secondary 用光，
  //   而 MOOSE 的枚举是 {Secondary=0, Primary=1, Lower=2} —— 这一点我判读过一次，
  //   当时误以为"只有 Lower 被算"，其实看到的全是 Secondary）。
  const unsigned int mt = static_cast<unsigned int>(mortar_type);
  if (_debug && mt < 3 && _dbg_per_type[mt] < 2)
  {
    _dbg_per_type[mt]++;
    _dbg_n++;
    _console << "[GBDBG] n=" << _dbg_n << " type=" << mt
             << " sec=" << MetaPhysicL::raw_value(_u_secondary[_qp])
             << " pri=" << MetaPhysicL::raw_value(_u_primary[_qp])
             << " lam=" << MetaPhysicL::raw_value(_lambda[_qp])
             << " kex=" << _kex[_qp]
             << " test_sec=" << _test_secondary.size()
             << " test_pri=" << _test_primary.size()
             << " test_low=" << _test.size()
             << " qp=" << _qp << " i=" << _i << std::endl;
  }
  const ADReal half = 0.5;
  switch (mortar_type)
  {
    case Moose::MortarType::Lower:
      // 面方程（已乘 A_s/ρ_mol）： -(K/2)[(c_sec-Gam) + (c_pri-Gam)]
      return -_kex[_qp] * half *
             ((_u_secondary[_qp] - _lambda[_qp]) + (_u_primary[_qp] - _lambda[_qp])) *
             _test[_i][_qp];

    case Moose::MortarType::Secondary:
      // 体相 secondary 侧失去： +(K/2)(c_sec - Gam)
      return _kex[_qp] * half * (_u_secondary[_qp] - _lambda[_qp]) * _test_secondary[_i][_qp];

    case Moose::MortarType::Primary:
      // 体相 primary 侧失去： +(K/2)(c_pri - Gam)
      return _kex[_qp] * half * (_u_primary[_qp] - _lambda[_qp]) * _test_primary[_i][_qp];

    default:
      return 0;
  }
}
