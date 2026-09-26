#include "ConstAdvection.h"

registerMooseObject("GibbsApp", ConstAdvection);

InputParameters
ConstAdvection::validParams()
{
  InputParameters params = Kernel::validParams();
  params.addClassDescription("残差 = v · grad(u) · test。v 来自 RealVectorValue 材料。"
                             "用于在晶界参考系里表示材料以速度 v 流过晶界。");
  params.addRequiredParam<MaterialPropertyName>("vel_name", "速度材料属性名");
  return params;
}

ConstAdvection::ConstAdvection(const InputParameters & parameters)
  : Kernel(parameters), _vel(getMaterialProperty<RealVectorValue>("vel_name"))
{
}

Real
ConstAdvection::computeQpResidual()
{
  return _vel[_qp] * _grad_u[_qp] * _test[_i][_qp];
}

Real
ConstAdvection::computeQpJacobian()
{
  return _vel[_qp] * _grad_phi[_j][_qp] * _test[_i][_qp];
}