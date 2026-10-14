import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from load_analyzer import LoadRow, ResultRow, calculate_stress, read_load_data


SECTION_DIMENSIONS = {
    "사각형": (("폭 b", "b"), ("높이 h", "h")),
    "원형봉": (("외경 D", "D"),),
    "원형관": (("외경 D", "D"), ("내경 d", "d")),
    "사각형관": (
        ("외부 폭 B", "B"),
        ("외부 높이 H", "H"),
        ("내부 폭 b", "b"),
        ("내부 높이 h", "h"),
    ),
    "H형강": (
        ("전체 폭 B", "B"),
        ("전체 높이 H", "H"),
        ("플랜지 두께 tf", "tf"),
        ("웨브 두께 tw", "tw"),
    ),
}
REQUIRED_COLUMNS_MESSAGE = (
    "필수 열이 없습니다. CSV에 다음 열이 정확히 필요합니다:\n"
    "time_s (시간, s), force_N (하중, N)"
)
NO_VALID_DATA_MESSAGE = (
    "유효한 데이터가 없습니다.\n"
    "time_s와 force_N에 숫자로 된 유효한 값을 입력한 행이 필요합니다."
)


class LoadAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("하중 CSV 분석기")
        self.root.geometry("760x680")
        self.root.minsize(640, 520)

        self.path_var = tk.StringVar()
        self.valid_count_var = tk.StringVar(value="유효 데이터 수: -")
        self.section_type_var = tk.StringVar(value="사각형")
        self.dimension_vars: dict[str, tk.StringVar] = {}
        self.area_var = tk.StringVar(value="단면적 A: - mm²")
        self.maximum_stress_var = tk.StringVar(value="최대 응력: -")
        self.maximum_time_var = tk.StringVar(value="최대 응력 시간: -")
        self.analysis_status_var = tk.StringVar(value="분석 전")
        self.rows: list[LoadRow] = []
        self.has_valid_analysis = False

        self._build_widgets()
        self._draw_empty_plot()

    def _build_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        ttk.Button(
            file_frame,
            text="CSV 찾아보기",
            command=self._choose_csv_file,
        ).grid(row=0, column=0, padx=(0, 8))

        path_entry = ttk.Entry(
            file_frame,
            textvariable=self.path_var,
            state="readonly",
        )
        path_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(
            file_frame,
            textvariable=self.valid_count_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        analysis_frame = ttk.LabelFrame(main_frame, text="단면 및 분석")
        analysis_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        analysis_frame.columnconfigure(1, weight=1)

        ttk.Label(analysis_frame, text="단면 종류").grid(
            row=0, column=0, padx=(8, 4), pady=8
        )
        self.section_type_combo = ttk.Combobox(
            analysis_frame,
            textvariable=self.section_type_var,
            values=tuple(SECTION_DIMENSIONS),
            state="readonly",
            width=8,
        )
        self.section_type_combo.grid(
            row=0, column=1, sticky="w", padx=(0, 12), pady=8
        )
        self.section_type_combo.bind(
            "<<ComboboxSelected>>", self._on_section_type_changed
        )

        self.dimension_frame = ttk.Frame(analysis_frame)
        self.dimension_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8)
        )
        self._build_dimension_inputs()

        ttk.Label(analysis_frame, textvariable=self.area_var).grid(
            row=2, column=0, sticky="w", padx=8, pady=(0, 8)
        )
        ttk.Button(
            analysis_frame,
            text="분석",
            command=self._analyze,
        ).grid(row=2, column=1, sticky="e", padx=8, pady=(0, 8))

        ttk.Label(analysis_frame, textvariable=self.maximum_stress_var).grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 8)
        )
        ttk.Label(analysis_frame, textvariable=self.maximum_time_var).grid(
            row=3, column=1, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            analysis_frame, textvariable=self.analysis_status_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

        self.plot_frame = ttk.LabelFrame(main_frame, text="시간-응력 그래프")
        self.plot_frame.grid(row=2, column=0, sticky="nsew")

    def _build_dimension_inputs(self) -> None:
        for child in self.dimension_frame.winfo_children():
            child.destroy()

        self.dimension_vars = {}
        for column, (label, name) in enumerate(
            SECTION_DIMENSIONS[self.section_type_var.get()]
        ):
            variable = tk.StringVar()
            self.dimension_vars[name] = variable
            ttk.Label(self.dimension_frame, text=f"{label} (mm)").grid(
                row=0, column=column * 2, padx=(0, 4)
            )
            entry = ttk.Entry(
                self.dimension_frame, textvariable=variable, width=10
            )
            entry.grid(row=0, column=column * 2 + 1, padx=(0, 12))
            variable.trace_add("write", self._on_dimension_changed)

    def _on_section_type_changed(self, _event: tk.Event[tk.Misc]) -> None:
        self._build_dimension_inputs()
        self._invalidate_results("조건 변경됨: 다시 분석필요")

    def _on_dimension_changed(
        self, _name: str, _index: str, _mode: str
    ) -> None:
        self._invalidate_results("조건 변경됨: 다시 분석필요")

    def _invalidate_results(self, status: str) -> None:
        had_valid_analysis = self.has_valid_analysis
        self.has_valid_analysis = False
        self.area_var.set("단면적 A: 무효")
        self.maximum_stress_var.set("최대 응력: 무효")
        self.maximum_time_var.set("최대 응력 시간: 무효")
        self.analysis_status_var.set(status)
        if had_valid_analysis:
            self._draw_empty_plot()

    def _choose_csv_file(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="분석할 CSV 파일 선택",
            filetypes=(("CSV 파일", "*.csv"), ("모든 파일", "*.*")),
        )
        if not selected_path:
            return

        self.rows = []
        self.path_var.set(selected_path)
        self.valid_count_var.set("유효 데이터 수: -")
        self._invalidate_results("새 CSV 선택됨: 다시 분석필요")

        try:
            rows, _excluded_count = read_load_data(Path(selected_path))
        except (OSError, ValueError) as error:
            message = (
                REQUIRED_COLUMNS_MESSAGE
                if "열 이름" in str(error)
                else str(error)
            )
            messagebox.showerror("CSV 읽기 오류", message, parent=self.root)
            return

        self.valid_count_var.set(f"유효 데이터 수: {len(rows)}개")
        self.rows = rows
        if not rows:
            self._invalidate_results("유효 데이터 없음: 분석할 수 없습니다")
            messagebox.showwarning(
                "분석 중단",
                NO_VALID_DATA_MESSAGE,
                parent=self.root,
            )

    def _analyze(self) -> None:
        self._invalidate_results("분석 중")
        if not self.path_var.get():
            messagebox.showerror("분석 오류", "먼저 CSV 파일을 선택해 주세요.", parent=self.root)
            return
        if not self.rows:
            messagebox.showerror(
                "분석 오류",
                NO_VALID_DATA_MESSAGE + "\n분석을 중단합니다.",
                parent=self.root,
            )
            return

        try:
            dimensions = {
                name: float(variable.get().strip())
                for name, variable in self.dimension_vars.items()
            }
        except (TypeError, ValueError):
            messagebox.showerror(
                "입력 오류",
                "숫자가 아닌 입력이나 빈칸이 있습니다. "
                "0보다 큰 올바른 값을 입력해 주세요.",
                parent=self.root,
            )
            return

        try:
            self._validate_dimensions(dimensions)
            area_mm2 = self._calculate_area(dimensions)
            result_rows = calculate_stress(self.rows, area_mm2)
        except (TypeError, ValueError):
            messagebox.showerror(
                "입력 오류",
                self._dimension_error_message(),
                parent=self.root,
            )
            return

        maximum_row = max(result_rows, key=lambda row: row["stress_MPa"])
        self.area_var.set(f"단면적 A: {area_mm2:g} mm²")
        self.maximum_stress_var.set(
            f"최대 응력: {maximum_row['stress_MPa']:g} MPa"
        )
        self.maximum_time_var.set(
            f"최대 응력 시간: {maximum_row['time_s']:g} s"
        )
        self.analysis_status_var.set("분석 완료")
        self.has_valid_analysis = True
        self._draw_stress_plot(result_rows)

    def _validate_dimensions(self, dimensions: dict[str, float]) -> None:
        if any(not math.isfinite(value) for value in dimensions.values()):
            raise ValueError

        section_type = self.section_type_var.get()
        if section_type == "사각형":
            if not dimensions["b"] > 0 or not dimensions["h"] > 0:
                raise ValueError
        elif section_type == "원형봉":
            if not dimensions["D"] > 0:
                raise ValueError
        elif section_type == "원형관":
            if not dimensions["D"] > dimensions["d"] > 0:
                raise ValueError
        elif section_type == "사각형관":
            if not (
                dimensions["B"] > dimensions["b"] > 0
                and dimensions["H"] > dimensions["h"] > 0
            ):
                raise ValueError
        elif section_type == "H형강":
            if not (
                dimensions["B"] > dimensions["tw"] > 0
                and dimensions["H"] > 2 * dimensions["tf"] > 0
            ):
                raise ValueError

    def _calculate_area(self, dimensions: dict[str, float]) -> float:
        section_type = self.section_type_var.get()
        if section_type == "사각형":
            area_mm2 = dimensions["b"] * dimensions["h"]
        elif section_type == "원형봉":
            area_mm2 = math.pi * dimensions["D"] ** 2 / 4
        elif section_type == "원형관":
            area_mm2 = math.pi * (
                dimensions["D"] ** 2 - dimensions["d"] ** 2
            ) / 4
        elif section_type == "사각형관":
            area_mm2 = dimensions["B"] * dimensions["H"] - (
                dimensions["b"] * dimensions["h"]
            )
        else:
            area_mm2 = 2 * dimensions["B"] * dimensions["tf"] + (
                dimensions["H"] - 2 * dimensions["tf"]
            ) * dimensions["tw"]

        if not math.isfinite(area_mm2) or area_mm2 <= 0:
            raise ValueError
        return area_mm2

    def _dimension_error_message(self) -> str:
        return {
            "사각형": (
                "폭 b와 높이 h에 0보다 큰 올바른 값을 입력해 주세요."
            ),
            "원형봉": "외경 D에 0보다 큰 올바른 값을 입력해 주세요.",
            "원형관": (
                "외경 D와 내경 d에 올바른 값을 입력해 주세요. "
                "조건은 D > d > 0입니다."
            ),
            "사각형관": (
                "올바른 값을 입력해 주세요. "
                "조건은 B > b > 0 및 H > h > 0입니다."
            ),
            "H형강": (
                "올바른 값을 입력해 주세요. "
                "조건은 B > tw > 0 및 H > 2tf > 0입니다."
            ),
        }[self.section_type_var.get()]

    def _draw_empty_plot(self) -> None:
        figure = Figure(figsize=(7, 4.2), dpi=100)
        axes = figure.add_subplot(111)
        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Stress (MPa)")
        axes.grid(True)
        figure.tight_layout()
        self._display_figure(figure)

    def _draw_stress_plot(self, rows: list[ResultRow]) -> None:
        figure = Figure(figsize=(7, 4.2), dpi=100)
        axes = figure.add_subplot(111)

        times = [row["time_s"] for row in rows]
        stresses = [row["stress_MPa"] for row in rows]
        axes.plot(times, stresses, marker="o")

        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Stress (MPa)")
        axes.grid(True)
        figure.tight_layout()
        self._display_figure(figure)

    def _display_figure(self, figure: Figure) -> None:
        for child in self.plot_frame.winfo_children():
            child.destroy()

        canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


def main() -> None:
    root = tk.Tk()
    LoadAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
