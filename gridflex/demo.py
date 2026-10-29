"""Run a deterministic microgrid dispatch demonstration."""
from . import DispatchProblem, optimize_dispatch


def main() -> None:
    p = DispatchProblem(
        demand=(3.2, 3.0, 3.4, 5.8, 7.1, 6.2, 4.6, 3.8),
        renewable=(1.0, 1.5, 3.0, 4.0, 2.0, 0.5, 0.2, 0.0),
        price=(0.10, 0.10, 0.08, 0.07, 0.32, 0.40, 0.22, 0.12),
        capacity=5.0, initial_soc=2.5, max_charge=2.0, max_discharge=2.0,
        efficiency=0.92, import_limit=6.0, degradation_cost=0.025,
    )
    r = optimize_dispatch(p)
    print("GridFlex — resilient microgrid battery dispatch (kW / kWh)")
    print("hr | demand renew price | charge discharge | SOC | grid")
    print("---+--------------------+-----------------+-----+-----")
    for i in range(len(p.demand)):
        print(f"{i:>2} | {p.demand[i]:>5.1f} {p.renewable[i]:>5.1f} {p.price[i]:>5.2f} |"
              f" {r.charge[i]:>6.2f} {r.discharge[i]:>8.2f} | {r.soc[i]:>4.2f} | {r.grid_import[i]:>4.2f}")
    base = sum(p.price[i] * max(0.0, p.demand[i]-p.renewable[i]) for i in range(len(p.demand)))
    print(f"\nObjective: {r.objective:.4f}  | baseline energy bill: {base:.4f}  | iterations: {r.iterations}")

if __name__ == "__main__":
    main()
