"""GridFlex: constrained storage dispatch for renewable microgrids."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Sequence

@dataclass(frozen=True)
class DispatchProblem:
    demand: Sequence[float]
    renewable: Sequence[float]
    price: Sequence[float]
    capacity: float
    initial_soc: float
    max_charge: float
    max_discharge: float
    efficiency: float = 0.95
    import_limit: float = math.inf
    degradation_cost: float = 0.02

@dataclass(frozen=True)
class DispatchResult:
    charge: tuple[float, ...]
    discharge: tuple[float, ...]
    soc: tuple[float, ...]
    grid_import: tuple[float, ...]
    objective: float
    iterations: int


def optimize_dispatch(problem: DispatchProblem, *, tolerance: float = 1e-8, max_iterations: int = 1200) -> DispatchResult:
    """Minimize energy cost plus quadratic wear subject to linear battery constraints.

    Uses accelerated projected gradient; projection is Dykstra's algorithm over
    box, SOC-prefix, and grid-import halfspaces. All power values are per interval.
    """
    p=problem; n=len(p.demand)
    if not (len(p.renewable)==len(p.price)==n): raise ValueError("demand, renewable and price lengths must match")
    vals=[*p.demand,*p.renewable,*p.price,p.capacity,p.initial_soc,p.max_charge,p.max_discharge,p.degradation_cost]
    if any(not math.isfinite(float(x)) for x in vals): raise ValueError("inputs must be finite")
    if not 0 < p.efficiency <= 1: raise ValueError("efficiency must be in (0, 1]")
    if p.capacity < 0 or not 0 <= p.initial_soc <= p.capacity or p.max_charge < 0 or p.max_discharge < 0 or p.degradation_cost < 0: raise ValueError("invalid battery limits or degradation cost")
    if p.import_limit < 0: raise ValueError("import_limit must be nonnegative")
    if any(x < 0 for x in (*p.demand,*p.renewable)): raise ValueError("demand and renewable must be nonnegative")
    if n==0: return DispatchResult((),(),(),(),0.0,0)
    if math.isfinite(p.import_limit) and any(float(p.demand[t])-float(p.renewable[t])-p.max_charge > p.import_limit+1e-12 for t in range(n)):
        raise ValueError("import_limit is infeasible with available charging headroom")
    # Decision z=[charge_0..charge_n-1, discharge_0..discharge_n-1].
    dim=2*n; base=[float(d-r) for d,r in zip(p.demand,p.renewable)]
    constraints=[]
    # Box constraints as one coordinate projection.
    lo=[0.0]*dim; hi=[p.max_charge]*n+[p.max_discharge]*n
    # Prefix SOC: initial + eta*sum(charge) - sum(discharge)/eta in [0, capacity].
    for t in range(n):
        a=[0.0]*dim
        for j in range(t+1): a[j]=p.efficiency; a[n+j]=-1.0/p.efficiency
        constraints.append((a,p.capacity-p.initial_soc))
        constraints.append(([-x for x in a],p.initial_soc))
    # Grid import base+charge-discharge <= cap.
    if math.isfinite(p.import_limit):
        for t in range(n):
            a=[0.0]*dim; a[t]=1.0; a[n+t]=-1.0
            constraints.append((a,p.import_limit-base[t]))
    def project(y):
        x=y[:]
        corrections=[[0.0]*dim for _ in range(len(constraints)+1)]
        for _ in range(120):
            old=x[:]
            # Dykstra box projection
            q=[x[i]+corrections[0][i] for i in range(dim)]
            z=[min(hi[i],max(lo[i],q[i])) for i in range(dim)]
            corrections[0]=[q[i]-z[i] for i in range(dim)]; x=z
            for k,(a,b) in enumerate(constraints,1):
                q=[x[i]+corrections[k][i] for i in range(dim)]
                dot=sum(a[i]*q[i] for i in range(dim)); norm=sum(v*v for v in a)
                if dot>b and norm:
                    z=[q[i]-(dot-b)/norm*a[i] for i in range(dim)]
                else: z=q
                corrections[k]=[q[i]-z[i] for i in range(dim)]; x=z
            if max(abs(x[i]-old[i]) for i in range(dim)) < 1e-11: break
        return x
    # f = sum price*(base+charge-discharge) + wear*(charge²+discharge²)
    # Lipschitz constant 2*wear; lower bounded safely for tiny wear.
    L=max(2*p.degradation_cost,1e-6); step=1.0/L
    x=project([0.0]*dim); y=x[:]; momentum=1.0
    for it in range(1,max_iterations+1):
        grad=[0.0]*dim
        for t in range(n):
            grad[t]=p.price[t]+2*p.degradation_cost*x[t]
            grad[n+t]=-p.price[t]+2*p.degradation_cost*x[n+t]
        nx=project([y[i]-step*grad[i] for i in range(dim)])
        if max(abs(nx[i]-x[i]) for i in range(dim)) <= tolerance:
            x=nx; break
        m=(1+math.sqrt(1+4*momentum*momentum))/2
        y=[nx[i]+((momentum-1)/m)*(nx[i]-x[i]) for i in range(dim)]
        x=nx; momentum=m
    charge=x[:n]; discharge=x[n:]
    soc=[]; state=p.initial_soc
    imports=[]
    for t in range(n):
        state += p.efficiency*charge[t]-discharge[t]/p.efficiency
        soc.append(state); imports.append(base[t]+charge[t]-discharge[t])
    objective=sum(p.price[t]*imports[t]+p.degradation_cost*(charge[t]**2+discharge[t]**2) for t in range(n))
    return DispatchResult(tuple(charge),tuple(discharge),tuple(soc),tuple(imports),objective,it)
