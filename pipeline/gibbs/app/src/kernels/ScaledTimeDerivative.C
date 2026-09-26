#include "ScaledTimeDerivative.h"

registerMooseObject("GibbsApp", ScaledTimeDerivative);

InputParameters
ScaledTimeDerivative::validParams()
{
  InputParameters params = TimeKernel::validParams();
  params.addClassDescription(
      "Residual = scale * du/dt * test, where scale is a material property. "
      "用于 Gibbs 面模型的局域平衡表述：(1 + shape*As) * dc/dt = div(D grad c)");
  params.addRequiredParam<MaterialPropertyName>("scale",
                                                "乘在 du/dt 上的材料系数 ");
  params.addCoupledVar("args",
                       "scale 依赖的**非线性**变量（用于补齐非对角雅可比）");
  return params;
}

ScaledTimeDerivative::ScaledTimeDerivative(const InputParameters & parameters)
  : DerivativeMaterialInterface<JvarMapKernelInterface<TimeKernel>>(parameters),
    _scale(getMaterialProperty<Real>("scale")),
    _dscale_du(getMaterialPropertyDerivative<Real>("scale", _var.name())),
    _n_args(coupledComponents("args")),
    _dscale_darg(_n_args)
{
  // 与 MatReaction 同一套写法（照抄框架里已在用的，不要自己发明）
  for (unsigned int i = 0; i < _n_args; ++i)
    _dscale_darg[i] = &getMaterialPropertyDerivative<Real>("scale", i);
}

void
ScaledTimeDerivative::initialSetup()
{
  // 把"材料依赖 ⊄ args"这类漏项变成告警（AGENTS.md §3.1 坑 3：告警要当错误看）
  validateNonlinearCoupling<Real>("scale");
}

Real
ScaledTimeDerivative::computeQpResidual()
{
  return _scale[_qp] * _u_dot[_qp] * _test[_i][_qp];
}

Real
ScaledTimeDerivative::computeQpJacobian()
{
  return _scale[_qp] * _du_dot_du[_qp] * _phi[_j][_qp] * _test[_i][_qp];
}

Real
ScaledTimeDerivative::computeQpOffDiagJacobian(unsigned int jvar)
{
  const auto cvar = mapJvarToCvar(jvar);
  return (*_dscale_darg[cvar])[_qp] * _u_dot[_qp] * _phi[_j][_qp] * _test[_i][_qp];
}