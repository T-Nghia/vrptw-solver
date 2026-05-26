import math
import random
from gurobipy import quicksum

def add_capacity_constraint(model, x_vars, x_hat, S, data):
    """
    Kiểm tra và thêm ràng buộc sức chứa nếu phát hiện vi phạm
    """
    depot = data["depot"]
    customers = data["customers"]
    V = customers + [depot]

    demand = data.get("demand", data.get("q"))
    capacity = data.get("capacity", data.get("Q"))

    sum_q = sum(demand[i] for i in S)

    k_S = math.ceil(sum_q / capacity)

    V_minus_S = [j for j in V if j not in S]
    f_S = sum(x_hat.get((i, j), 0.0) for i in S for j in V_minus_S)

    # Nếu vi phạm ràng buộc sức chứa
    if f_S < k_S - 1e-4:
        if "global_cuts" not in data:
            data["global_cuts"] = []

        cut_tuple = (tuple(sorted(S)), k_S)
        if cut_tuple in data["global_cuts"]:
            return False

        # Thêm ràng buộc
        cut_expr = quicksum(x_vars[i, j] for i in S for j in V_minus_S if (i, j) in x_vars)
        model.addConstr(cut_expr >= k_S, name=f"cap_cut_S{len(S)}_{random.randint(0,10000)}")

        data["global_cuts"].append(cut_tuple)
        return True

    return False


def graph_shrinking(model, x_vars, x_hat, data, max_iter=10, mu=5):
    """
    Heuristic Graph Shrinking tìm các tập vi phạm sức chứa
    """
    depot = data["depot"]

    # Tập cung chỉ chứa khách hàng, loại bỏ Depot 0
    A0 = [(i, j) for (i, j) in x_vars.keys() if i != depot and j != depot]
    cuts_added = 0
    customers = data["customers"]

    for iter_idx in range(max_iter):
        # Khởi tạo supernode
        supernodes = {v: {v} for v in customers}

        # Sắp xếp các cung thuộc A0 theo x_hat_ij giảm dần
        L = [arc for arc in A0 if x_hat.get(arc, 0) > 1e-4]
        L.sort(key=lambda arc: x_hat.get(arc, 0), reverse=True)

        while len(L) > 0:
            # Chọn ngẫu nhiên cung trong \mu cung đầu tiên của L
            limit = min(mu, len(L))
            chosen_idx = random.randint(0, limit - 1)
            u, v = L.pop(chosen_idx)

            Su = supernodes[u]
            Sv = supernodes[v]

            # Gộp nút u,v
            if Su != Sv:
                S_new = Su.union(Sv)

                for node in S_new:
                    supernodes[node] = S_new

                # kiểm tra xem siêu nút và thêm ràng buộc nếu vi phạm
                if add_capacity_constraint(model, x_vars, x_hat, S_new, data):
                    cuts_added += 1

    return cuts_added