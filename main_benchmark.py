import os
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict

# Import các thuật toán từ thư mục gốc
from algorithms.branch_and_bound.solver import manual_branch_and_bound_vrptw
from algorithms.branch_and_cut.solver import manual_branch_and_cut_vrptw


def load_real_solomon_data(file_name: str, num_customers: int = 10) -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", file_name)

    if not os.path.exists(file_path):
        if not file_path.endswith(".txt"):
            file_path += ".txt"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu tại: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    Q_capacity = 200
    for i, line in enumerate(lines):
        if "CAPACITY" in line:
            Q_capacity = int(lines[i+1].split()[1])
            break

    start_index = 0
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) > 0 and parts[0].isdigit() and int(parts[0]) == 0:
            start_index = i
            break

    nodes = []
    customers = []
    coords = {}
    q = {}
    a = {}
    b = {}
    s_time = {}

    num_customers = max(10, min(num_customers, 15))

    for idx in range(0, num_customers + 1):
        line_data = lines[start_index + idx].split()
        if len(line_data) < 7:
            break

        c_id = int(line_data[0])
        nodes.append(c_id)
        if c_id != 0:
            customers.append(c_id)

        coords[c_id] = (float(line_data[1]), float(line_data[2]))
        q[c_id] = int(line_data[3])
        a[c_id] = float(line_data[4])
        b[c_id] = float(line_data[5])
        s_time[c_id] = float(line_data[6])

    c = {}
    tau = {}
    M_time = {}

    for i in nodes:
        for j in nodes:
            if i == j:
                c[i, j] = 0.0
                tau[i, j] = 0.0
                M_time[i, j] = 0.0
            else:
                x1, y1 = coords[i]
                x2, y2 = coords[j]
                dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

                c[i, j] = dist
                tau[i, j] = s_time[i] + dist
                M_time[i, j] = max(0.0, b[i] + tau[i, j] - a[j])

    arcs = [(i, j) for i in nodes for j in nodes if i != j]

    return {
        "nodes": nodes,
        "customers": customers,
        "depot": 0,
        "arcs": arcs,
        "c": c,
        "tau": tau,
        "M_time": M_time,
        "q": q,
        "a": a,
        "b": b,
        "Q": Q_capacity,
        "m": 2
    }


class BenchmarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ Thống Đối Sánh Thuật Toán VRPTW (Academic UI)")
        self.root.geometry("800x550")
        self.root.configure(bg="#f4f6f9")

        # Tiêu đề chính
        title_label = tk.Label(root, text="VRPTW BENCHMARK PLATFORM", font=("Helvetica", 16, "bold"), fg="#2c3e50", bg="#f4f6f9")
        title_label.pack(pady=15)

        # Khung điều khiển
        control_frame = tk.Frame(root, bg="#f4f6f9")
        control_frame.pack(pady=10)

        tk.Label(control_frame, text="Chọn cấu hình file:", font=("Helvetica", 10), bg="#f4f6f9").grid(row=0, column=0, padx=5)
        self.file_entry = tk.Entry(control_frame, font=("Helvetica", 10), width=12)
        self.file_entry.insert(0, "r101")
        self.file_entry.grid(row=0, column=1, padx=5)

        tk.Label(control_frame, text="Số lượng KH (10-15):", font=("Helvetica", 10), bg="#f4f6f9").grid(row=0, column=2, padx=5)
        self.cust_entry = tk.Entry(control_frame, font=("Helvetica", 10), width=8)
        self.cust_entry.insert(0, "10")
        self.cust_entry.grid(row=0, column=3, padx=5)

        # Nút kích hoạt giải toán
        self.run_btn = tk.Button(control_frame, text="KÍCH HOẠT BENCHMARK", font=("Helvetica", 10, "bold"), bg="#2ecc71", fg="white", command=self.start_benchmark, padx=10)
        self.run_btn.grid(row=0, column=4, padx=15)

        # Trạng thái hệ thống
        self.status_label = tk.Label(root, text="Trạng thái: Sẵn sàng thử nghiệm.", font=("Helvetica", 10, "italic"), fg="#7f8c8d", bg="#f4f6f9")
        self.status_label.pack(pady=5)

        # Bảng hiển thị kết quả (Treeview)
        table_frame = tk.Frame(root)
        table_frame.pack(pady=15, padx=20, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=("Metric", "BB", "BC"), show="headings", height=8)
        self.tree.heading("Metric", text="TIÊU CHÍ ĐÁNH GIÁ (METRICS)")
        self.tree.heading("BB", text="BRANCH AND BOUND (B&B)")
        self.tree.heading("BC", text="BRANCH AND CUT (B&C)")

        self.tree.column("Metric", width=320, anchor="w")
        self.tree.column("BB", width=200, anchor="center")
        self.tree.column("BC", width=200, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Thêm phong cách thanh lịch cho bảng
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), foreground="#2c3e50")
        style.configure("Treeview", font=("Helvetica", 10), rowheight=28)

    def start_benchmark(self):
        file_name = self.file_entry.get().strip()
        try:
            num_cust = int(self.cust_entry.get().strip())
        except ValueError:
            messagebox.showerror("Lỗi dữ liệu", "Vui lòng nhập số lượng khách hàng hợp lệ!")
            return

        self.status_label.config(text="[HỆ THỐNG] Đang nạp dữ liệu từ file...", fg="#e67e22")
        self.root.update()

        try:
            data = load_real_solomon_data(file_name, num_cust)
        except Exception as e:
            messagebox.showerror("Lỗi đọc file", str(e))
            self.status_label.config(text="Trạng thái: Thất bại.", fg="#c0392b")
            return

        # 1. Chạy Branch and Bound
        self.status_label.config(text="⚡ Đang tính toán: 1. Pure Branch and Bound...", fg="#9b59b6")
        self.root.update()

        t0 = time.time()
        res_bb = manual_branch_and_bound_vrptw(data, max_nodes=300, node_selection="best_bound", time_limit_per_lp=15.0, use_initial_heuristic=False)
        time_bb = time.time() - t0

        # 2. Chạy Branch and Cut
        self.status_label.config(text="⚡ Đang tính toán: 2. Advanced Branch and Cut...", fg="#3498db")
        self.root.update()

        t1 = time.time()
        res_bc = manual_branch_and_cut_vrptw(data, max_nodes=300, node_selection="best_bound", time_limit_per_lp=15.0, use_initial_heuristic=False)
        time_bc = time.time() - t1

        # Cập nhật kết quả lên bảng Pop-up đồ họa
        self.status_label.config(text="🎉 Đã xử lý xong dữ liệu đối sánh!", fg="#27ae60")
        self.display_results(res_bb, time_bb, res_bc, time_bc)

    def display_results(self, r_bb, t_bb, r_bc, t_bc):
        # Xóa dữ liệu cũ trên bảng nếu có
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Chuẩn bị bộ nhãn dòng dữ liệu học thuật
        metrics_list = [
            ("Hàm mục tiêu tốt nhất (Objective)", f"{r_bb['best_obj']:.4f}" if r_bb['best_obj'] != math.inf else "No Sol", f"{r_bc['best_obj']:.4f}" if r_bc['best_obj'] != math.inf else "No Sol"),
            ("Tổng thời gian thực thi (Seconds)", f"{t_bb:.4f}", f"{t_bc:.4f}"),
            ("Tổng số Nodes đã giải (Solved)", str(r_bb["stats"]["nodes_solved"]), str(r_bc["stats"]["nodes_solved"])),
            ("Số lần thực hiện rẽ nhánh", str(r_bb["stats"]["branch_count"]), str(r_bc["stats"]["branch_count"])),
            ("Số Nodes bị chặn cắt (Pruned)", str(r_bb["stats"]["pruned_by_bound"]), str(r_bc["stats"]["pruned_by_bound"])),
            ("Số Nodes vô nghiệm LP (Infeasible)", str(r_bb["stats"]["lp_infeasible"]), str(r_bc["stats"]["lp_infeasible"])),
            ("Chứng minh được tối ưu?", str(r_bb["optimal_proved"]), str(r_bc["optimal_proved"]))
        ]

        for idx, row in enumerate(metrics_list):
            # Tạo hiệu ứng màu xen kẽ cho các dòng cho dễ đọc
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", tk.END, values=row, tags=(tag,))

        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("odd", background="#f9f9f9")


if __name__ == "__main__":
    main_window = tk.Tk()
    app = BenchmarkApp(main_window)
    main_window.mainloop()