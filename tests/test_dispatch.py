from gridflex import DispatchProblem, optimize_dispatch


def test_empty_horizon():
    r = optimize_dispatch(DispatchProblem((), (), (), 0, 0, 0, 0))
    assert r.charge == r.discharge == r.soc == r.grid_import == ()
    assert r.objective == 0 and r.iterations == 0


def test_rejects_bad_efficiency():
    p = DispatchProblem((1,), (0,), (1,), 2, 0, 1, 1, efficiency=0)
    try:
        optimize_dispatch(p)
    except ValueError as e:
        assert "efficiency" in str(e)
    else:
        raise AssertionError("invalid efficiency accepted")


def test_no_storage_respects_grid_and_cost():
    p = DispatchProblem((3, 4), (1, 1), (2, 3), 0, 0, 0, 0)
    r = optimize_dispatch(p)
    assert r.charge == r.discharge == (0.0, 0.0)
    assert r.grid_import == (2.0, 3.0)
    assert r.objective == 13.0


def test_dispatch_is_feasible_and_shifts_energy_from_peak():
    p = DispatchProblem((4, 8, 3), (2, 2, 2), (1, 5, 1), 4, 2, 2, 2,
                        efficiency=0.9, import_limit=10, degradation_cost=0.01)
    r = optimize_dispatch(p)
    assert len(r.charge) == len(r.discharge) == len(r.soc) == 3
    assert all(-1e-7 <= s <= 4 + 1e-7 for s in r.soc)
    assert all(0 <= c <= 2 for c in r.charge)
    assert all(0 <= d <= 2 for d in r.discharge)
    assert all(g <= 10+1e-7 for g in r.grid_import)
    baseline = sum(max(0,d-ren)*price for d,ren,price in zip(p.demand,p.renewable,p.price))
    assert r.objective < baseline
    assert r.discharge[1] > 0.1


def test_infeasible_import_cap_is_rejected():
    p = DispatchProblem((10,), (0,), (1,), 0, 0, 0, 0, import_limit=2)
    try:
        optimize_dispatch(p)
    except ValueError as e:
        assert "infeasible" in str(e)
    else:
        raise AssertionError("infeasible grid import cap accepted")
