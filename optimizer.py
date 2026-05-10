from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint,
    NonNegativeReals, NonNegativeIntegers,
    SolverFactory, value, minimize
)
from pyomo.opt import SolverStatus, TerminationCondition


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
    Solve Aggregate Production Planning model.

    Returns (results_dict, error_message).
    results_dict is None if infeasible or solver error.
    """
    TH = len(demand)
    if TH == 0:
        return None, "demand 리스트가 비어 있습니다."
    if any(d < 0 for d in demand):
        return None, "demand 값은 0 이상이어야 합니다."
    TIME = range(0, TH + 1)
    T = range(1, TH + 1)
    D = [0] + list(demand)

    domain = NonNegativeIntegers if model_type == "IP" else NonNegativeReals

    m = ConcreteModel()
    m.W = Var(TIME, domain=domain)
    m.H = Var(TIME, domain=domain)
    m.L = Var(TIME, domain=domain)
    m.P = Var(TIME, domain=domain)
    m.I = Var(TIME, domain=domain)
    m.S = Var(TIME, domain=domain)
    m.C = Var(TIME, domain=domain)
    m.O = Var(TIME, domain=domain)

    p = params
    labor_unit = p['wage_regular'] * p['work_hours'] * p['work_days']
    cap_reg = p['work_hours'] * p['work_days'] / p['std_time']
    cap_ot = 1.0 / p['std_time']

    m.Cost = Objective(
        expr=sum(
            labor_unit * m.W[t] + p['wage_overtime'] * m.O[t]
            + p['cost_hire'] * m.H[t] + p['cost_fire'] * m.L[t]
            + p['cost_inventory'] * m.I[t] + p['cost_backlog'] * m.S[t]
            + p['cost_material'] * m.P[t] + p['cost_outsource_extra'] * m.C[t]
            for t in T
        ),
        sense=minimize,
    )

    m.init_W = Constraint(rule=lambda m: m.W[0] == p['W0'])
    m.init_I = Constraint(rule=lambda m: m.I[0] == p['I0'])
    m.init_S = Constraint(rule=lambda m: m.S[0] == p['S0'])

    m.labor = Constraint(T, rule=lambda m, t: m.W[t] == m.W[t - 1] + m.H[t] - m.L[t])
    m.capacity = Constraint(T, rule=lambda m, t: m.P[t] <= cap_reg * m.W[t] + cap_ot * m.O[t])
    m.inventory = Constraint(
        T,
        rule=lambda m, t: m.I[t] == m.I[t - 1] + m.P[t] + m.C[t] - D[t] - m.S[t - 1] + m.S[t],
    )
    m.overtime = Constraint(T, rule=lambda m, t: m.O[t] <= p['overtime_limit'] * m.W[t])
    m.final_I = Constraint(rule=lambda m: m.I[TH] >= p['I_final_min'])
    m.final_S = Constraint(rule=lambda m: m.S[TH] == 0)

    solver = SolverFactory('glpk')
    solver.options['tmlim'] = 300
    try:
        res = solver.solve(m, load_solutions=True)
    except Exception:
        try:
            solver = SolverFactory('highs')
            res = solver.solve(m, load_solutions=True)
        except Exception as e2:
            return None, f"Solver error (glpk + highs 모두 실패): {e2}"

    if res.solver.status != SolverStatus.ok:
        return None, f"Solver status: {res.solver.status}"

    if res.solver.termination_condition not in (
        TerminationCondition.optimal,
        TerminationCondition.feasible,
    ):
        return None, f"Solver termination: {res.solver.termination_condition}"

    def vals(var):
        result = []
        for t in TIME:
            try:
                result.append(value(var[t]))
            except ValueError:
                result.append(0.0)
        return result

    W = vals(m.W)
    H = vals(m.H)
    L = vals(m.L)
    P = vals(m.P)
    I_ = vals(m.I)
    S = vals(m.S)
    C = vals(m.C)
    O = vals(m.O)

    T_list = list(T)

    cost_breakdown = {
        '정규노동비': sum(labor_unit * W[t] for t in T_list),
        '초과노동비': sum(p['wage_overtime'] * O[t] for t in T_list),
        '고용비':    sum(p['cost_hire'] * H[t] for t in T_list),
        '해고비':    sum(p['cost_fire'] * L[t] for t in T_list),
        '재고유지비': sum(p['cost_inventory'] * I_[t] for t in T_list),
        '부재고비':  sum(p['cost_backlog'] * S[t] for t in T_list),
        '재료비':    sum(p['cost_material'] * P[t] for t in T_list),
        '하청비':    sum(p['cost_outsource_extra'] * C[t] for t in T_list),
    }

    return {
        'model_type': model_type,
        'total_cost': value(m.Cost),
        'months': list(T_list),
        'D': D[1:],
        'W': W[1:], 'H': H[1:], 'L': L[1:],
        'P': P[1:], 'I': I_[1:], 'S': S[1:],
        'C': C[1:], 'O': O[1:],
        'cost_breakdown': cost_breakdown,
    }, None
