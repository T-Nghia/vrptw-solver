from typing import Any, Dict
from gurobipy import GRB, quicksum
from algorithms.branch_and_bound.node import BBNode
from models.vrptw_model import build_gurobi_vrptw_model
from utils.solution import get_solution_values
from algorithms.branch_and_cut.cutting_planes import graph_shrinking

def solve_lp_relaxation_with_cuts(
        data: Dict[str, Any],
        node: BBNode,
        time_limit: float,
):
    """Hàm giải LP mới tích hợp thêm vòng lặp sinh mặt cắt."""
    # 1. Gọi lại hàm dựng mô hình gốc từ bài toán của bạn
    model, x, t, y = build_gurobi_vrptw_model(
        data=data, node=node, relax=True,
        name=f"BC_node_depth_{node.depth}", time_limit=time_limit, output_flag=0
    )

    # 2. Áp các mặt cắt toàn cục đã tìm thấy từ các node trước (Cut Pool)
    if "global_cuts" in data:
        for cut_expr, rhs in data["global_cuts"]:
            # cut_expr là biểu thức tuyến tính được map lại theo biến x của model mới
            # Tùy thuộc vào cách bạn lưu cut pool, bạn tái áp dụng tại đây
            pass

    # 3. Vòng lặp Cutting Plane Loop
    while True:
        model.optimize()

        if model.Status in [GRB.INFEASIBLE, GRB.INF_OR_UNBD, GRB.UNBOUNDED] or model.SolCount == 0:
            return {"status": model.Status, "feasible": False, "reason": "Infeasible", "node": node}

        # Trích xuất nghiệm phân số hiện tại
        x_sol, t_sol, y_sol = get_solution_values(x, t, y)

        # Tìm và nạp mặt cắt vào model
        new_cuts = graph_shrinking(model, x, x_sol, data)

        # Nếu không còn mặt cắt nào bị vi phạm nữa -> Thoát vòng lặp cắt
        if new_cuts == 0:
            break

    # 4. Trả nghiệm cuối cùng sau khi đã thắt chặt không gian tìm kiếm về đúng định dạng B&B yêu cầu
    x_sol, t_sol, y_sol = get_solution_values(x, t, y)
    return {
        "status": model.Status,
        "feasible": True,
        "obj": float(model.ObjVal),
        "x": x_sol,
        "t": t_sol,
        "y": y_sol,
        "node": node,
    }