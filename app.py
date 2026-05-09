import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from optimizer import solve_app, DEFAULT_PARAMS

st.set_page_config(page_title="총괄생산계획 대시보드", layout="wide")
st.title("원예장비 제조업체 총괄생산계획 (APP)")
st.caption("Pyomo + GLPK 최적화 | Streamlit 대시보드")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("파라미터 설정")

    st.subheader("월별 예상수요")
    n_months = st.number_input("계획 기간 (개월)", min_value=1, max_value=24, value=6, step=1)
    default_demand = [1600, 3000, 3200, 3800, 2200, 2200]
    demand = []
    cols = st.columns(2)
    for i in range(int(n_months)):
        col = cols[i % 2]
        v = default_demand[i] if i < len(default_demand) else 2000
        demand.append(col.number_input(f"{i+1}월", min_value=0, value=v, step=100, key=f"d{i}"))

    st.subheader("비용 파라미터 (천원)")
    cost_material        = st.number_input("재료비 (/개)", value=DEFAULT_PARAMS['cost_material'], step=1)
    cost_inventory       = st.number_input("재고유지비 (/개/월)", value=DEFAULT_PARAMS['cost_inventory'], step=1)
    cost_backlog         = st.number_input("부재고비용 (/개/월)", value=DEFAULT_PARAMS['cost_backlog'], step=1)
    cost_outsource_extra = st.number_input("하청 추가비용 (/개)", value=DEFAULT_PARAMS['cost_outsource_extra'], step=1)

    st.subheader("인력 파라미터")
    W0            = st.number_input("초기 종업원 수 (명)", value=DEFAULT_PARAMS['W0'], step=1)
    I0            = st.number_input("초기 재고 (개)", value=DEFAULT_PARAMS['I0'], step=100)
    I_final       = st.number_input("최종 재고 목표 (개)", value=DEFAULT_PARAMS['I_final_min'], step=100)
    wage_regular  = st.number_input("정규임금 (천원/시간)", value=DEFAULT_PARAMS['wage_regular'], step=1)
    wage_overtime = st.number_input("초과근무임금 (천원/시간)", value=DEFAULT_PARAMS['wage_overtime'], step=1)
    cost_hire     = st.number_input("고용비용 (천원/인)", value=DEFAULT_PARAMS['cost_hire'], step=10)
    cost_fire     = st.number_input("해고비용 (천원/인)", value=DEFAULT_PARAMS['cost_fire'], step=10)
    work_days     = st.number_input("작업일수 (일/월)", value=DEFAULT_PARAMS['work_days'], step=1)
    work_hours    = st.number_input("작업시간 (시간/일)", value=DEFAULT_PARAMS['work_hours'], step=1)
    overtime_limit = st.number_input("초과시간 제한 (시간/인/월)", value=DEFAULT_PARAMS['overtime_limit'], step=1)
    std_time      = st.number_input("작업표준시간 (시간/개)", value=DEFAULT_PARAMS['std_time'], step=1)

    st.subheader("최적화 방식")
    mode = st.radio("방식 선택", ["LP + IP 비교", "LP만", "IP만"], index=0)

    solve_btn = st.button("계획 수립", type="primary", use_container_width=True)

params = {
    'W0': int(W0), 'I0': int(I0), 'I_final_min': int(I_final), 'S0': 0,
    'wage_regular': int(wage_regular), 'wage_overtime': int(wage_overtime),
    'cost_hire': int(cost_hire), 'cost_fire': int(cost_fire),
    'cost_inventory': int(cost_inventory), 'cost_backlog': int(cost_backlog),
    'cost_material': int(cost_material), 'cost_outsource_extra': int(cost_outsource_extra),
    'work_days': int(work_days), 'work_hours': int(work_hours),
    'overtime_limit': int(overtime_limit), 'std_time': int(std_time),
}

# ── Optimization trigger ───────────────────────────────────────────────────────
if solve_btn:
    with st.spinner("최적화 계산 중..."):
        lp_result = ip_result = None
        lp_err = ip_err = None
        if mode in ["LP + IP 비교", "LP만"]:
            lp_result, lp_err = solve_app(demand, params, "LP")
        if mode in ["LP + IP 비교", "IP만"]:
            ip_result, ip_err = solve_app(demand, params, "IP")

        if lp_err:
            st.error(f"LP 최적화 실패: {lp_err}")
        if ip_err:
            st.error(f"IP 최적화 실패: {ip_err}")

        st.session_state['lp'] = lp_result
        st.session_state['ip'] = ip_result
        st.session_state['mode'] = mode

if 'mode' not in st.session_state:
    st.info("사이드바에서 파라미터를 설정하고 **계획 수립** 버튼을 클릭하세요.")
    st.stop()

lp = st.session_state.get('lp')
ip = st.session_state.get('ip')
primary = lp if lp else ip

if primary is None:
    st.warning("최적해를 찾지 못했습니다. 파라미터를 조정해 주세요.")
    st.stop()

months_labels = [f"{m}월" for m in primary['months']]

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.subheader("핵심 지표 (KPI)")
k1, k2, k3 = st.columns(3)
label = primary['model_type']
k1.metric(f"최소 총비용 ({label})", f"{primary['total_cost']:,.0f} 천원")
k2.metric("총 생산량", f"{sum(primary['P']):,.0f} 개")
k3.metric("부족재고 발생 월", f"{sum(1 for s in primary['S'] if s > 0)} 개월")

st.divider()

# ── Charts placeholder (Tasks 5–8) ─────────────────────────────────────────────
st.info("차트는 다음 단계에서 추가됩니다.")
