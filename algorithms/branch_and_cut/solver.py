from typing import Any, Dict
import algorithms.branch_and_bound.solver as bnb_solver
from algorithms.branch_and_cut.lp_relaxation_cuts import solve_lp_relaxation_with_cuts

def manual_branch_and_cut_vrptw(data: Dict[str, Any], **kwargs):
    """
    Bộ giải Branch and Cut kế thừa 100% lõi xử lý cây của Branch and Bound.
    """
    print("=== Khởi động hệ thống BRANCH AND CUT ===")

    # 1. Khởi tạo một bể chứa mặt cắt toàn cục (Global Cut Pool) bên trong biến data
    data["global_cuts"] = []

    # 2. Thực hiện hoán đổi hàm (Monkey Patching)
    # Lưu lại hàm gốc để khôi phục sau khi chạy xong nhằm tránh side-effect
    original_lp_relaxation_func = bnb_solver.solve_lp_relaxation_at_node

    # Tráo hàm: Ép solver gốc của B&B phải gọi hàm giải LP tích hợp Cắt của chúng ta
    bnb_solver.solve_lp_relaxation_at_node = solve_lp_relaxation_with_cuts

    try:
        # 3. Kích hoạt toàn bộ bộ máy duyệt cây, rẽ nhánh, quản lý heap/stack của B&B
        result = bnb_solver.manual_branch_and_bound_vrptw(data, **kwargs)
        return result

    finally:
        # 4. Trả lại trạng thái nguyên bản cho hệ thống
        bnb_solver.solve_lp_relaxation_at_node = original_lp_relaxation_func