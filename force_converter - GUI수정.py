import math
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


def convert_force(value: float, unit: str = "kN") -> dict[str, float]:
    """Convert a force value to N, kgf, and kN."""
    if unit == "N":
        newtons = value
    elif unit == "kgf":
        newtons = value * 9.81
    elif unit == "kN":
        newtons = value * 1000
    else:
        raise ValueError(f"지원하지 않는 단위입니다: {unit}")

    return {
        "N": newtons,
        "kgf": newtons / 9.81,
        "kN": newtons / 1000,
    }


def update_result_placeholders() -> None:
    """Show empty results for the units other than the selected input unit."""
    selected_unit = input_unit.get()
    result_units = [unit for unit in ("N", "kgf", "kN") if unit != selected_unit]
    first_result_unit, second_result_unit = result_units
    first_result.config(text=f"- {first_result_unit}")
    second_result.config(text=f"- {second_result_unit}")


def convert_input() -> None:
    """Validate the input and display the converted force values."""
    try:
        value = float(force_input.get().strip())
        if not math.isfinite(value):
            raise ValueError
    except ValueError:
        messagebox.showerror("입력 오류", "숫자를 입력해 주세요.")
        return

    selected_unit = input_unit.get()
    converted = convert_force(value, selected_unit)
    result_units = [unit for unit in ("N", "kgf", "kN") if unit != selected_unit]
    first_result_unit, second_result_unit = result_units
    first_result.config(text=f"{converted[first_result_unit]:,.2f} {first_result_unit}")
    second_result.config(text=f"{converted[second_result_unit]:,.2f} {second_result_unit}")


def reset_converter() -> None:
    """Clear the input and conversion results."""
    force_input.delete(0, tk.END)
    update_result_placeholders()
    force_input.focus_set()


def main() -> None:
    root = tk.Tk()
    root.title("힘 단위 변환기")
    root.geometry("390x390")
    root.resizable(False, False)
    root.configure(bg="#f4f7fb")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("App.TFrame", background="#f4f7fb")
    style.configure("Card.TFrame", background="#ffffff")
    style.configure(
        "Title.TLabel",
        background="#ffffff",
        foreground="#172033",
        font=("맑은 고딕", 17, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background="#ffffff",
        foreground="#6b7280",
        font=("맑은 고딕", 9),
    )
    style.configure(
        "Unit.TLabel",
        background="#ffffff",
        foreground="#4b5563",
        font=("맑은 고딕", 10, "bold"),
    )
    style.configure(
        "Unit.TCombobox",
        background="#e5edff",
        fieldbackground="#f8faff",
        foreground="#172033",
        selectbackground="#f8faff",
        selectforeground="#172033",
        arrowcolor="#2563eb",
        font=("맑은 고딕", 10, "bold"),
        padding=(8, 5),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Unit.TCombobox",
        fieldbackground=[("readonly", "#f8faff"), ("focus", "#ffffff")],
        background=[("readonly", "#e5edff"), ("active", "#dbe7ff")],
        foreground=[("readonly", "#172033")],
        arrowcolor=[("active", "#1d4ed8"), ("focus", "#1d4ed8")],
    )
    style.configure(
        "Result.TLabel",
        background="#eef4ff",
        foreground="#1e3a8a",
        font=("맑은 고딕", 11, "bold"),
        padding=(12, 9),
    )
    style.configure(
        "Primary.TButton",
        background="#2563eb",
        foreground="#ffffff",
        font=("맑은 고딕", 10, "bold"),
        padding=(16, 8),
        borderwidth=0,
        anchor="center",
        justify="center",
    )
    style.map("Primary.TButton", background=[("active", "#1d4ed8")])
    style.configure(
        "Secondary.TButton",
        background="#e5e7eb",
        foreground="#374151",
        font=("맑은 고딕", 10),
        padding=(14, 8),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", "#d1d5db")])

    main_frame = ttk.Frame(root, style="App.TFrame", padding=18)
    main_frame.pack()

    card = ttk.Frame(main_frame, style="Card.TFrame", padding=(22, 20))
    card.pack()

    ttk.Label(card, text="힘 단위 변환기", style="Title.TLabel").grid(
        row=0, column=0, columnspan=3, sticky="w"
    )
    ttk.Label(card, text="입력 단위를 선택하면 나머지 단위로 변환합니다.", style="Subtitle.TLabel").grid(
        row=1, column=0, columnspan=3, sticky="w", pady=(4, 18)
    )

    global force_input, input_unit, first_result, second_result
    force_input = ttk.Entry(card, width=20, font=("맑은 고딕", 10))
    force_input.grid(row=2, column=0, padx=(0, 8), ipady=4)
    force_input.focus_set()

    input_unit = ttk.Combobox(
        card,
        values=("N", "kgf", "kN"),
        state="readonly",
        width=6,
        style="Unit.TCombobox",
        exportselection=False,
    )
    input_unit.set("kN")
    input_unit.selection_clear()
    input_unit.grid(row=2, column=1, padx=(0, 14))
    input_unit.bind(
        "<<ComboboxSelected>>",
        lambda _event: (input_unit.selection_clear(), update_result_placeholders()),
    )

    convert_button = ttk.Button(
        card,
        text="변환",
        command=convert_input,
        style="Primary.TButton",
        compound="center",
        width=6,
    )
    convert_button.grid(row=2, column=2)

    first_result = ttk.Label(card, text="- N", anchor="w", width=27, style="Result.TLabel")
    first_result.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(22, 6))

    second_result = ttk.Label(
        card, text="- kgf", anchor="w", width=27, style="Result.TLabel"
    )
    second_result.grid(row=4, column=0, columnspan=3, sticky="ew")

    button_frame = ttk.Frame(card, style="Card.TFrame")
    button_frame.grid(row=5, column=0, columnspan=3, pady=(20, 0))

    ttk.Button(button_frame, text="초기화", command=reset_converter, style="Secondary.TButton").pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(button_frame, text="종료", command=root.destroy, style="Secondary.TButton").pack(
        side="left"
    )

    root.bind("<Return>", lambda _event: convert_input())
    root.mainloop()


if __name__ == "__main__":
    main()