import pulp

DEFAULT_PARAMS = {
    'W0': 80,
    'I0': 1000,
    'I_final_min': 500,
    'S0': 0,
    'wage_regular': 4,
    'wage_overtime': 6,
    'cost_hire': 300,
    'cost_fire': 500,
    'cost_inventory': 2,
    'cost_backlog': 5,
    'cost_material': 10,
    'cost_outsource_extra': 30,
    'work_days': 20,
    'work_hours': 8,
    'overtime_limit': 10,
    'std_time': 4,
}


def solve_app(demand: list, params: dict, model_type: str = "LP"):
    """
    Solve Aggregate Production Planning using PuLP + CBC.

    Returns (results_dict, error_message).
    """
    TH = len(demand)
    if TH == 0:
        return None, "demand 리스트가 비어 있습니다."
    if any(d < 0 for d in demand):
        return None, "demand 값은 0 이상이어야 합니다."

    T = list(range(1, TH + 1))
    TIME = list(range(0, TH + 1))
    D = [0] + list(demand)

    p = params
    labor_unit = p['wage_regular'] * p['work_hours'] * p['work_days']
    cap_reg = p['work_hours'] * p['work_days'] / p['std_time']
    cap_ot = 1.0 / p['std_time']
    cat = 'Integer' if model_type == "IP" else 'Continuous'

    prob = pulp.LpProblem("APP", pulp.LpMinimize)

    W = {t: pulp.LpVariable(f"W_{t}", lowBound=0, cat=cat) for t in TIME}
    H = {t: pulp.LpVariable(f"H_{t}", lowBound=0, cat=cat) for t in TIME}
    L = {t: pulp.LpVariable(f"L_{t}", lowBound=0, cat=cat) for t in TIME}
    P = {t: pulp.LpVariable(f"P_{t}", lowBound=0, cat=cat) for t in TIME}
    Iv = {t: pulp.LpVariable(f"I_{t}", lowBound=0, cat=cat) for t in TIME}
    S = {t: pulp.LpVariable(f"S_{t}", lowBound=0, cat=cat) for t in TIME}
    C = {t: pulp.LpVariable(f"C_{t}", lowBound=0, cat=cat) for t in TIME}
    O = {t: pulp.LpVariable(f"O_{t}", lowBound=0, cat=cat) for t in TIME}

    prob += pulp.lpSum(
        labor_unit * W[t] + p['wage_overtime'] * O[t]
        + p['cost_hire'] * H[t] + p['cost_fire'] * L[t]
        + p['cost_inventory'] * Iv[t] + p['cost_backlog'] * S[t]
        + p['cost_material'] * P[t] + p['cost_outsource_extra'] * C[t]
        for t in T
    )

    prob += W[0] == p['W0']
    prob += Iv[0] == p['I0']
    prob += S[0] == p['S0']

    for t in T:
        prob += W[t] == W[t - 1] + H[t] - L[t]
        prob += P[t] <= cap_reg * W[t] + cap_ot * O[t]
        prob += Iv[t] == Iv[t - 1] + P[t] + C[t] - D[t] - S[t - 1] + S[t]
        prob += O[t] <= p['overtime_limit'] * W[t]

    prob += Iv[TH] >= p['I_final_min']
    prob += S[TH] == 0

    try:
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=300)
        status = prob.solve(solver)
    except Exception as e:
        return None, f"Solver error: {e}"

    if pulp.LpStatus[status] not in ('Optimal', 'Feasible'):
        return None, f"최적해 없음: {pulp.LpStatus[status]}"

    def v(var_dict, t):
        val = pulp.value(var_dict[t])
        return float(val) if val is not None else 0.0

    W_v  = [v(W,  t) for t in TIME]
    H_v  = [v(H,  t) for t in TIME]
    L_v  = [v(L,  t) for t in TIME]
    P_v  = [v(P,  t) for t in TIME]
    I_v  = [v(Iv, t) for t in TIME]
    S_v  = [v(S,  t) for t in TIME]
    C_v  = [v(C,  t) for t in TIME]
    O_v  = [v(O,  t) for t in TIME]

    cost_breakdown = {
        '정규노동비': sum(labor_unit * W_v[t] for t in T),
        '초과노동비': sum(p['wage_overtime'] * O_v[t] for t in T),
        '고용비':    sum(p['cost_hire'] * H_v[t] for t in T),
        '해고비':    sum(p['cost_fire'] * L_v[t] for t in T),
        '재고유지비': sum(p['cost_inventory'] * I_v[t] for t in T),
        '부재고비':  sum(p['cost_backlog'] * S_v[t] for t in T),
        '재료비':    sum(p['cost_material'] * P_v[t] for t in T),
        '하청비':    sum(p['cost_outsource_extra'] * C_v[t] for t in T),
    }

    return {
        'model_type': model_type,
        'total_cost': pulp.value(prob.objective),
        'months': T,
        'D': D[1:],
        'W': W_v[1:], 'H': H_v[1:], 'L': L_v[1:],
        'P': P_v[1:], 'I': I_v[1:], 'S': S_v[1:],
        'C': C_v[1:], 'O': O_v[1:],
        'cost_breakdown': cost_breakdown,
    }, None
