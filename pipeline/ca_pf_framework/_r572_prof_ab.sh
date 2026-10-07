#!/bin/bash
# _r572_prof_ab.sh --- 用**同一把量具**（`_r561_opfacct.py`）量"改之前 / 改之后"的剖面。
# 参数走环境变量：R561_N / R561_NV / R561_STEPS / R561_WORKERS（默认 64/24/8/4）。
# 判据：两臂用同一配置，且各自 P0/P0b/P2 自检必须 PASS。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R561_N="${R561_N:-64}" R561_NV="${R561_NV:-24}"
export R561_STEPS="${R561_STEPS:-8}" R561_WORKERS="${R561_WORKERS:-4}"
TAGSUF="${R561_NV}x${R561_N}_w${R561_WORKERS}"

run() {  # run <标签> <env赋值...>
  local tag="$1"; shift
  echo ""
  echo "################ 剖面 $TAGSUF：$tag ################"
  env "$@" "$PY" _r561_opfacct.py > /dev/null 2>&1
  cp -f _w2_r561_acct.log "_w2_r572_acct_${tag}_${TAGSUF}.log"
  grep -E '干净单步|region\(\)|argmin2\(\)|elastic_driving_pair|el\.sigma_tensor|el\.eps0_fields|fe\.ed\.|finish\(\)|for_each（|par\.gradient|par\.upwind_flux_vec|op\._minmod|P1 覆盖|= \*\*[0-9]|P0=|el\.sigma_tensor  |el\.eps0_fields  ' \
    "_w2_r572_acct_${tag}_${TAGSUF}.log"
  # ★★★ R572 **计数回归**（本轮新增的纪律）：
  #   只比数值的 `_r30_regress.sh` **抓不到**"同一算子被多调一遍"这类性能回归
  #   （重复调用数值完全一样）—— 我自己就这么埋进去一个 30% 的坑。
  #   ⇒ 这里硬断言每步调用次数。
  local bad=0
  for pair in "el.sigma_tensor:1" "el.eps0_fields:1" "fe.ed.soft_phi:1" "argmin2:1"; do
    local k="${pair%%:*}" want="${pair##*:}"
    local got
    got=$(grep -E "^    ${k} " "_w2_r572_acct_${tag}_${TAGSUF}.log" | head -1 | awk '{print $2}')
    if [ -z "$got" ]; then
      echo "  ❌ 计数回归：日志里找不到 '${k}' 的调用次数"; bad=1; continue
    fi
    if awk "BEGIN{exit !($got == $want)}"; then
      echo "  ✅ 计数回归 ${k} = ${got}/步（应为 ${want}）"
    else
      echo "  ❌ 计数回归 ${k} = ${got}/步（应为 ${want}）**性能回归**"; bad=1
    fi
  done
  [ "$bad" = 0 ] || echo "  ⚠⚠ 计数回归 FAIL —— 数值回归抓不到这一类，必须修"
}

run BEFORE
run AFTER R561_FFT=rfft R561_EPS0=einsum R561_EDPAIR=gather
echo ""
echo "=== R572 PROF A/B DONE $(date '+%F %T') ==="
