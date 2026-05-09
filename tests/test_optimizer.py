import pytest
from optimizer import solve_app, DEFAULT_PARAMS


DEMAND_6M = [1600, 3000, 3200, 3800, 2200, 2200]


def test_lp_feasible():
    result, err = solve_app(DEMAND_6M, DEFAULT_PARAMS, "LP")
    assert err is None, f"LP solver error: {err}"
    assert result is not None


def test_lp_cost_approx():
    result, _ = solve_app(DEMAND_6M, DEFAULT_PARAMS, "LP")
    assert abs(result['total_cost'] - 422275) < 1000, (
        f"Expected ~422275, got {result['total_cost']}"
    )


def test_ip_feasible():
    result, err = solve_app(DEMAND_6M, DEFAULT_PARAMS, "IP")
    assert err is None, f"IP solver error: {err}"
    assert result is not None


def test_ip_cost_approx():
    result, _ = solve_app(DEMAND_6M, DEFAULT_PARAMS, "IP")
    assert abs(result['total_cost'] - 422660) < 1000, (
        f"Expected ~422660, got {result['total_cost']}"
    )


def test_final_inventory_constraint():
    result, _ = solve_app(DEMAND_6M, DEFAULT_PARAMS, "IP")
    assert result['I'][-1] >= DEFAULT_PARAMS['I_final_min'] - 1


def test_cost_breakdown_sums_to_total():
    result, _ = solve_app(DEMAND_6M, DEFAULT_PARAMS, "LP")
    breakdown_total = sum(result['cost_breakdown'].values())
    assert abs(breakdown_total - result['total_cost']) < 1


def test_empty_demand_returns_error():
    result, err = solve_app([], DEFAULT_PARAMS, "LP")
    assert result is None
    assert err is not None


def test_negative_demand_returns_error():
    result, err = solve_app([-100, 200], DEFAULT_PARAMS, "LP")
    assert result is None
    assert err is not None
