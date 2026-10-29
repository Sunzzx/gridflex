# GridFlex ⚡

**Dependency-free convex battery dispatch for renewable microgrids.** GridFlex allocates battery charging and discharging across a forecast horizon to reduce energy cost and peak imports while respecting power and state-of-charge constraints.

[![CI](https://github.com/Sunzzx/gridflex/actions/workflows/ci.yml/badge.svg)](https://github.com/Sunzzx/gridflex/actions/workflows/ci.yml) · [MIT](LICENSE) · [Sponsor](https://github.com/sponsors/Sunzzx) · [Commercial licensing](https://buy.stripe.com/) · Enterprise: ayushkandwal2007@gmail.com

## Why it matters

Small clinics, community microgrids, shelters, and remote facilities need to stretch limited renewable generation and battery capacity through price spikes and local grid constraints. GridFlex provides an auditable optimization kernel that can be embedded in a site controller or used for planning. It does not require cloud access or third-party numerical libraries. It is a scheduling primitive, not a certified protection controller; operators should retain independent electrical safety interlocks.

## Model

For interval $t$, let $c_t,d_t\ge0$ denote grid-side charging and discharging power, $b_t=D_t-R_t$ the net demand before storage, $p_t$ the energy price, $s_t$ stored energy, and $\eta\in(0,1]$ the one-way efficiency. The optimizer minimizes

$$\min_{c,d}\quad \sum_{t=0}^{T-1}\left[p_t(b_t+c_t-d_t)+\lambda(c_t^2+d_t^2)\right]$$

subject to the box limits $0\le c_t\le C$, $0\le d_t\le P$, grid import $b_t+c_t-d_t\le G$, and battery dynamics

$$s_{t+1}=s_t+\eta c_t-d_t/\eta,\qquad 0\le s_{t+1}\le E.$$

The objective is convex for $\lambda\ge0$; all operational constraints are linear in the decision vector $z=[c_0,\ldots,c_{T-1},d_0,\ldots,d_{T-1}]$. The returned schedule is obtained using accelerated projected gradient. Projection uses Dykstra iterations over the box and halfspaces, approximating the Euclidean projection to a fixed tolerance. This is a convex relaxation: simultaneous charge/discharge is not explicitly forbidden, and positive wear cost discourages it. For deployment requiring a strict no-cycling guarantee, add a mixed-integer formulation or a verified complementarity layer.

### Architecture

```text
Demand / renewable / tariff / asset limits
                 │
                 ▼
        Validate dimensions & physics
                 │
                 ▼
       Convex objective + gradient
                 │
      Accelerated projected gradient
                 │
                 ▼
 Dykstra projection: boxes + SOC prefixes + grid caps
                 │
                 ▼
 charge / discharge / SOC / import / objective
```

**Complexity:** for horizon $T$ and $K$ outer iterations, gradient work is $O(KT)$. Each Dykstra projection sweep touches $O(T)$ prefix constraints, each with dense prefix coefficients, giving a straightforward worst-case $O(T^2)$ sweep and $O(T^2)$ stored projection corrections. Total straightforward bound: $O(KJ T^2)$ time and $O(T^2)$ auxiliary space for $J$ projection sweeps. Prefix-sum / sparse projection implementations can reduce this cost; this initial version favors inspectability and small-horizon microgrid dispatch.

## Quickstart

Python 3.10+, no runtime dependencies:

```bash
python -m gridflex.demo
```

Development tests:

```bash
uv run --with pytest pytest -q
```

or install the test extra: `python -m pip install -e '.[test]' && python -m pytest -q`.

### Example output

The demo prints an 8-interval schedule with tariff, battery actions, SOC and grid import; the reported objective and iteration count are computed at runtime. No fixed benchmark numbers are claimed because they depend on the solver tolerance and runtime.

## API

```python
from gridflex import DispatchProblem, optimize_dispatch
problem = DispatchProblem(
    demand=(4.0, 8.0, 3.0), renewable=(2.0, 2.0, 2.0), price=(1.0, 5.0, 1.0),
    capacity=4.0, initial_soc=2.0, max_charge=2.0, max_discharge=2.0,
    efficiency=0.9, import_limit=10.0, degradation_cost=0.01,
)
result = optimize_dispatch(problem)
print(result.charge, result.soc, result.grid_import, result.objective)
```

Invalid dimensions, nonphysical efficiencies, and impossible import caps are rejected with `ValueError`. Input power/energy units must be consistent with the interval duration. The solver reports the computed schedule but does not claim a formal optimality certificate; callers should validate feasibility against their site-specific operating rules.

## License & support

MIT for the open-source core. [Commercial licensing](https://buy.stripe.com/) · [Sponsor GridFlex](https://github.com/sponsors/Sunzzx) · Enterprise support: **ayushkandwal2007@gmail.com**.
