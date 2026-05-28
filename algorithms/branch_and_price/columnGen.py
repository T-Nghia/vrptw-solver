Đã dùng 70% bộ nhớ … Nếu hết bộ nhớ, bạn không thể tạo, chỉnh sửa và tải tệp lên. Hãy mua bộ nhớ 30 GB với giá 5.000 ₫ cho 3 tháng thay vì 19.000 ₫.
import gurobipy as gp
from gurobipy import GRB
from .paramsVRP import ParamsVRP
from .route import Route
from .SPPRC import SPPRC
import numpy as np


class ColumnGeneration:
    def __init__(self, user_param):
        self.paramsVRP = user_param
        self.routes = []

    def compute_col_gen(self, initial_routes):
        model = gp.Model("Column Generation")
        model.setParam("OutputFlag", 0)
        model.setParam("LogToConsole", 0)

        for route in initial_routes:
            cost = sum(self.paramsVRP.dist[route.path[i]][route.path[i + 1]] for i in range(len(route.path) - 1))
            route.set_cost(cost)
            self.routes.append(route)

        y = {}
        for i in range(len(self.routes)):
            y[i] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, obj=self.routes[i].cost, name=f"y_{i}")

        constraints = {}
        for client in range(1, self.paramsVRP.nbclients - 1):
            constraints[client] = model.addConstr(
                gp.quicksum(y[i] for i, route in enumerate(self.routes) if client in route.path[1:-1]) >= 1,
                name=f"ClientService_{client}"
            )

        model.update()

        iteration = 0
        while True:
            model.optimize()
            if model.status != GRB.OPTIMAL:
                print(f"Model not optimal. Status: {model.status}")
                break

            print(f"[ColumnGeneration] Iteration {iteration}: Objective = {model.objVal}")

            pi = {c: constraints[c].Pi for c in range(1, self.paramsVRP.nbclients - 1)}

            for i in range(1, self.paramsVRP.nbclients - 1):
                for j in range(self.paramsVRP.nbclients):
                    self.paramsVRP.cost[i][j] = self.paramsVRP.dist[i][j] - pi[i]

            sp = SPPRC(self.paramsVRP)
            new_routes = []
            sp.shortestPath(self.paramsVRP, new_routes, self.paramsVRP.nbclients - 1)
            print(new_routes)

            if not new_routes:
                print("No new negative cost paths found.")
                break

            for new_route in new_routes:
                cost = sum(self.paramsVRP.dist[new_route.path[i]][new_route.path[i + 1]] for i in range(len(new_route.path) - 1))
                new_route.set_cost(cost)
                self.routes.append(new_route)

                idx = len(self.routes) - 1

                col = gp.Column()
                for client_idx, constr in constraints.items():
                    if client_idx in new_route.path[1:-1]:
                        col.addTerms(1.0, constr)

                y[idx] = model.addVar(
                    vtype=GRB.CONTINUOUS,
                    lb=0.0,
                    obj=cost,
                    column=col,
                    name=f"y_{idx}"
                )

            model.update()
            iteration += 1

        for i in y:
            val = y[i].X
            self.routes[i].set_Q(val)
            if val > 1e-6:
                print(f"Route {i}: Cost = {self.routes[i].cost:.2f}, Q = {val:.4f}, Path = {self.routes[i].path}")

        return model.objVal, self.routes
