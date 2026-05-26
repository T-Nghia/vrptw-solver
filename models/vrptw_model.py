from typing import Any, Dict, Optional

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception as exc:
    raise ImportError(
        "Chưa import được gurobipy. Hãy cài Gurobi, cài gurobipy và kích hoạt license trước khi chạy."
    ) from exc

from algorithms.branch_and_bound.node import BBNode


def build_gurobi_vrptw_model(
    data: Dict[str, Any],
    node: Optional[BBNode] = None,
    relax: bool = True,
    name: str = "VRPTW",
    time_limit: Optional[float] = None,
    output_flag: int = 1,
):
    """
    Xây dựng mô hình VRPTW bằng Gurobi.

    relax=True  -> LP relaxation, x_ij là biến liên tục trong [0, 1].
    relax=False -> MILP, x_ij là biến nhị phân.
    """
    nodes = data["nodes"]
    customers = data["customers"]
    depot = data["depot"]
    arcs = data["arcs"]
    c = data["c"]
    tau = data["tau"]
    M_time = data["M_time"]
    q = data["q"]
    a = data["a"]
    b = data["b"]
    Q = data["Q"]
    m = data["m"]

    model = gp.Model(name)
    model.Params.OutputFlag = output_flag

    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    x_vtype = GRB.CONTINUOUS if relax else GRB.BINARY

    # x_ij: 1 nếu xe đi từ i tới j.
    x = model.addVars(arcs, lb=0.0, ub=1.0, vtype=x_vtype, name="x")

    # t_i: thời điểm bắt đầu phục vụ tại node i.
    t = model.addVars(nodes, lb=0.0, vtype=GRB.CONTINUOUS, name="t")

    # y_i: tải trọng tích lũy sau khi phục vụ/rời khỏi node i.
    y = model.addVars(nodes, lb=0.0, ub=Q, vtype=GRB.CONTINUOUS, name="y")

    # Objective: tối thiểu hóa tổng quãng đường.
    model.setObjective(gp.quicksum(c[i, j] * x[i, j] for i, j in arcs), GRB.MINIMIZE)

    # R1: mỗi khách hàng có đúng một cung rời đi.
    for i in customers:
        model.addConstr(
            gp.quicksum(x[i, j] for j in nodes if j != i) == 1,
            name=f"R1_out_once_{i}",
        )

    # R2: bảo toàn luồng tại mỗi khách hàng.
    for i in customers:
        model.addConstr(
            gp.quicksum(x[i, j] for j in nodes if j != i)
            - gp.quicksum(x[j, i] for j in nodes if j != i)
            == 0,
            name=f"R2_flow_{i}",
        )

    # R3: giới hạn số xe rời depot.
    vehicle_count = gp.quicksum(x[depot, j] for j in customers)
    model.addConstr(vehicle_count <= m, name="R3_vehicle_ub_m")

    # R4: liên kết thời gian.
    for i in nodes:
        for j in customers:
            if i == j:
                continue
            model.addConstr(
                t[j] >= t[i] + tau[i, j] - M_time[i, j] * (1 - x[i, j]),
                name=f"R4_time_{i}_{j}",
            )

    # R5: liên kết tải trọng.
    for i in nodes:
        for j in customers:
            if i == j:
                continue
            model.addConstr(
                y[j] >= y[i] + q[j] - Q * (1 - x[i, j]),
                name=f"R5_load_{i}_{j}",
            )

    # R6: cửa sổ thời gian.
    for i in nodes:
        lb = a[i]
        ub = b[i]

        if node is not None and i in node.time_bounds:
            lb = max(lb, node.time_bounds[i][0])
            ub = min(ub, node.time_bounds[i][1])

        model.addConstr(t[i] >= lb, name=f"R6_time_lb_{i}")
        model.addConstr(t[i] <= ub, name=f"R6_time_ub_{i}")

    # Depot bắt đầu.
    model.addConstr(t[depot] == a[depot], name="depot_start_time")
    model.addConstr(y[depot] == 0, name="depot_start_load")

    # Ràng buộc bổ sung từ node B&B.
    if node is not None:
        for (i, j), val in node.fixed_arcs.items():
            if (i, j) in x:
                model.addConstr(x[i, j] == int(val), name=f"branch_x_{i}_{j}_{val}")

        if node.vehicle_lb is not None:
            model.addConstr(vehicle_count >= node.vehicle_lb, name="branch_vehicle_lb")

        if node.vehicle_ub is not None:
            model.addConstr(vehicle_count <= node.vehicle_ub, name="branch_vehicle_ub")

    model.update()
    return model, x, t, y
