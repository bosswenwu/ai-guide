"""
钴铜 Excel 数据处理脚本
功能：读取、清洗、分析、可视化并导出钴铜样品/矿冶数据
用法：python cobalt_copper_processor.py [--input 数据文件.xlsx] [--output 结果目录]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------- 配置 ----------

# 默认列名映射（支持中英文表头，可在此扩展）
COLUMN_ALIASES = {
    "sample_id": ["样品编号", "sample_id", "id", "编号", "Sample ID"],
    "date":      ["日期", "date", "采样日期", "Date"],
    "location":  ["地点", "location", "采样地点", "矿区", "Location"],
    "cobalt":    ["钴含量", "Co(%)", "Co", "cobalt", "钴", "Co_pct"],
    "copper":    ["铜含量", "Cu(%)", "Cu", "copper", "铜", "Cu_pct"],
    "ore_grade": ["品位", "grade", "矿石品位", "Grade"],
    "weight_kg": ["重量(kg)", "weight", "重量", "Weight_kg"],
    "notes":     ["备注", "notes", "Notes", "remark"],
}

COBALT_RANGE  = (0.0, 30.0)   # 合理钴含量范围 %
COPPER_RANGE  = (0.0, 60.0)   # 合理铜含量范围 %


# ---------- 工具函数 ----------

def detect_column(df: pd.DataFrame, field: str) -> str | None:
    """在 DataFrame 中查找与 field 匹配的实际列名。"""
    candidates = [c.strip().lower() for c in COLUMN_ALIASES.get(field, [])]
    for col in df.columns:
        if col.strip().lower() in candidates:
            return col
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将 DataFrame 的列名统一映射为标准内部名称。"""
    rename_map = {}
    for std_name in COLUMN_ALIASES:
        actual = detect_column(df, std_name)
        if actual and actual != std_name:
            rename_map[actual] = std_name
    return df.rename(columns=rename_map)


def read_excel(path: Path) -> pd.DataFrame:
    """读取 Excel 文件，自动识别表头行。"""
    # 先尝试第一行为表头
    df = pd.read_excel(path, header=0)
    # 如果第一行全是数字，可能表头在第二行
    if df.columns.dtype == np.float64 or all(str(c).isdigit() for c in df.columns):
        df = pd.read_excel(path, header=1)
    df.columns = [str(c).strip() for c in df.columns]
    return df


# ---------- 清洗 ----------

def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    清洗数据，返回 (clean_df, issues_df)。
    issues_df 记录所有被标注或移除的问题行。
    """
    issues = []

    # 去除完全空行
    df = df.dropna(how="all").reset_index(drop=True)

    for col in ["cobalt", "copper"]:
        if col not in df.columns:
            continue
        # 转换为数值，无法转换的变为 NaN
        original = df[col].copy()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        bad_mask = df[col].isna() & original.notna()
        for idx in df[bad_mask].index:
            issues.append({
                "row": idx + 2,
                "field": col,
                "value": original[idx],
                "issue": "无法解析为数字",
            })

    # 范围异常检测
    range_map = {"cobalt": COBALT_RANGE, "copper": COPPER_RANGE}
    for col, (lo, hi) in range_map.items():
        if col not in df.columns:
            continue
        mask = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        for idx in df[mask].index:
            issues.append({
                "row": idx + 2,
                "field": col,
                "value": df.at[idx, col],
                "issue": f"超出合理范围 [{lo}, {hi}]",
            })

    # 重复样品编号
    if "sample_id" in df.columns:
        dup_mask = df.duplicated(subset=["sample_id"], keep=False)
        for idx in df[dup_mask].index:
            issues.append({
                "row": idx + 2,
                "field": "sample_id",
                "value": df.at[idx, "sample_id"],
                "issue": "重复样品编号",
            })

    issues_df = pd.DataFrame(issues)
    return df, issues_df


# ---------- 统计分析 ----------

def analyze(df: pd.DataFrame) -> dict:
    """计算钴、铜的核心统计指标及相关性。"""
    stats = {}
    for col in ["cobalt", "copper"]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        stats[col] = {
            "count":  int(s.count()),
            "mean":   round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std":    round(float(s.std()), 4),
            "min":    round(float(s.min()), 4),
            "max":    round(float(s.max()), 4),
            "p25":    round(float(s.quantile(0.25)), 4),
            "p75":    round(float(s.quantile(0.75)), 4),
        }

    if "cobalt" in df.columns and "copper" in df.columns:
        valid = df[["cobalt", "copper"]].dropna()
        if len(valid) >= 2:
            stats["correlation"] = round(
                float(valid["cobalt"].corr(valid["copper"])), 4
            )

    return stats


def flag_high_grade(df: pd.DataFrame,
                    co_threshold: float = 1.0,
                    cu_threshold: float = 5.0) -> pd.DataFrame:
    """标记高品位样品（钴≥co_threshold 或 铜≥cu_threshold）。"""
    df = df.copy()
    co_mask = df["cobalt"] >= co_threshold if "cobalt" in df.columns else False
    cu_mask = df["copper"] >= cu_threshold if "copper" in df.columns else False
    df["high_grade"] = np.where(co_mask | cu_mask, "是", "否")
    return df


# ---------- 可视化 ----------

def plot_charts(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    """生成分布图和散点图，返回保存路径列表。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.family"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError:
        print("  [跳过图表] 未安装 matplotlib，跳过可视化。")
        return []

    paths = []
    out_dir.mkdir(parents=True, exist_ok=True)

    # 直方图
    for col, label, color in [
        ("cobalt", "钴含量 Co (%)", "#4472C4"),
        ("copper", "铜含量 Cu (%)", "#ED7D31"),
    ]:
        if col not in df.columns:
            continue
        data = df[col].dropna()
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(data, bins=20, color=color, edgecolor="white", alpha=0.85)
        ax.set_title(f"{label} 分布直方图", fontsize=13)
        ax.set_xlabel(label)
        ax.set_ylabel("频数")
        ax.axvline(data.mean(), color="red", linestyle="--", label=f"均值 {data.mean():.3f}")
        ax.legend()
        fig.tight_layout()
        p = out_dir / f"hist_{col}.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        paths.append(p)

    # 散点图（钴 vs 铜）
    if "cobalt" in df.columns and "copper" in df.columns:
        valid = df[["cobalt", "copper"]].dropna()
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(valid["cobalt"], valid["copper"],
                   alpha=0.6, color="#70AD47", edgecolors="grey", linewidths=0.4)
        ax.set_xlabel("钴含量 Co (%)")
        ax.set_ylabel("铜含量 Cu (%)")
        ax.set_title("钴 vs 铜 散点图")
        fig.tight_layout()
        p = out_dir / "scatter_co_cu.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        paths.append(p)

    # 箱线图
    plot_cols = [c for c in ["cobalt", "copper"] if c in df.columns]
    if plot_cols:
        data_to_plot = [df[c].dropna().values for c in plot_cols]
        labels = ["钴 Co (%)" if c == "cobalt" else "铜 Cu (%)" for c in plot_cols]
        fig, ax = plt.subplots(figsize=(6, 5))
        bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True,
                        boxprops=dict(facecolor="#BDD7EE"),
                        medianprops=dict(color="red", linewidth=2))
        ax.set_title("钴铜含量箱线图")
        ax.set_ylabel("含量 (%)")
        fig.tight_layout()
        p = out_dir / "boxplot_co_cu.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        paths.append(p)

    return paths


# ---------- 导出 ----------

def export_results(df: pd.DataFrame,
                   issues_df: pd.DataFrame,
                   stats: dict,
                   chart_paths: list[Path],
                   out_path: Path) -> None:
    """将清洗后数据、问题记录、统计摘要写入多 Sheet Excel 文件，并嵌入图表。"""
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # Sheet 1: 清洗后数据
        df.to_excel(writer, sheet_name="清洗数据", index=False)

        # Sheet 2: 问题记录
        if not issues_df.empty:
            issues_df.to_excel(writer, sheet_name="问题记录", index=False)
        else:
            pd.DataFrame({"状态": ["无问题记录"]}).to_excel(
                writer, sheet_name="问题记录", index=False)

        # Sheet 3: 统计摘要
        summary_rows = []
        for field, s in stats.items():
            if isinstance(s, dict):
                for k, v in s.items():
                    summary_rows.append({"指标分类": field, "统计项": k, "值": v})
            else:
                summary_rows.append({"指标分类": "相关性", "统计项": field, "值": s})
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="统计摘要", index=False)

        wb = writer.book

        # Sheet 4: 图表
        if chart_paths:
            try:
                from openpyxl.drawing.image import Image as XLImage
                ws_chart = wb.create_sheet("可视化图表")
                ws_chart["A1"] = "钴铜数据可视化"
                ws_chart["A1"].font = Font(bold=True, size=14)
                row_offset = 3
                for p in chart_paths:
                    if p.exists():
                        img = XLImage(str(p))
                        img.width, img.height = 480, 300
                        ws_chart.add_image(img, f"A{row_offset}")
                        row_offset += 20
            except Exception as e:
                print(f"  [图表嵌入] 跳过: {e}")

    # 美化表头
    _style_headers(out_path)
    print(f"  结果已保存: {out_path}")


def _style_headers(path: Path) -> None:
    """为输出 Excel 文件的表头添加样式。"""
    wb = load_workbook(path)
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(bold=True, color="FFFFFF")
    for ws in wb.worksheets:
        if ws.max_row == 0:
            continue
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        # 自适应列宽
        for col_idx, col_cells in enumerate(ws.columns, start=1):
            max_len = max((len(str(c.value or "")) for c in col_cells), default=8)
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)
    wb.save(path)


# ---------- 主流程 ----------

def generate_sample_data(path: Path) -> None:
    """生成演示用样本 Excel，方便直接测试脚本。"""
    rng = np.random.default_rng(42)
    n = 60
    data = {
        "样品编号":  [f"S{str(i+1).zfill(3)}" for i in range(n)],
        "日期":      pd.date_range("2025-01-01", periods=n, freq="3D"),
        "地点":      rng.choice(["矿区A", "矿区B", "矿区C"], n),
        "Co(%)":     np.round(rng.lognormal(mean=-1.2, sigma=0.8, size=n).clip(0, 25), 3),
        "Cu(%)":     np.round(rng.lognormal(mean=0.5,  sigma=0.9, size=n).clip(0, 55), 3),
        "重量(kg)":  np.round(rng.uniform(10, 500, n), 1),
        "备注":      ["" if rng.random() > 0.15 else "待复验" for _ in range(n)],
    }
    # 注入几个异常值用于测试清洗逻辑
    data["Co(%)"][5]  = 99.9   # 超范围
    data["Cu(%)"][10] = -1.0   # 超范围
    data["样品编号"][20] = "S001"  # 重复编号
    pd.DataFrame(data).to_excel(path, index=False)
    print(f"  已生成演示数据: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="钴铜 Excel 数据处理脚本")
    parser.add_argument("--input",  "-i", default="cobalt_copper_data.xlsx",
                        help="输入 Excel 文件路径（默认: cobalt_copper_data.xlsx）")
    parser.add_argument("--output", "-o", default="output",
                        help="输出目录（默认: output/）")
    parser.add_argument("--co-threshold", type=float, default=1.0,
                        help="高品位钴阈值 %（默认: 1.0）")
    parser.add_argument("--cu-threshold", type=float, default=5.0,
                        help="高品位铜阈值 %（默认: 5.0）")
    parser.add_argument("--generate-sample", action="store_true",
                        help="生成演示用样本数据文件后退出")
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_dir  = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成演示数据
    if args.generate_sample:
        generate_sample_data(input_path)
        return

    if not input_path.exists():
        print(f"错误：找不到输入文件 '{input_path}'")
        print("提示：使用 --generate-sample 生成演示数据文件后再运行。")
        sys.exit(1)

    print(f"[1/5] 读取数据: {input_path}")
    df_raw = read_excel(input_path)
    print(f"      原始数据: {len(df_raw)} 行 × {len(df_raw.columns)} 列")

    print("[2/5] 标准化列名 & 清洗数据")
    df = normalize_columns(df_raw)
    df, issues_df = clean_data(df)
    print(f"      清洗后: {len(df)} 行，发现 {len(issues_df)} 条问题记录")

    print("[3/5] 标记高品位样品")
    df = flag_high_grade(df, args.co_threshold, args.cu_threshold)
    high_count = (df["high_grade"] == "是").sum() if "high_grade" in df.columns else 0
    print(f"      高品位样品数: {high_count}")

    print("[4/5] 统计分析")
    stats = analyze(df)
    for field, s in stats.items():
        if isinstance(s, dict):
            print(f"      [{field}] 均值={s['mean']}  中位数={s['median']}  "
                  f"标准差={s['std']}  范围=[{s['min']}, {s['max']}]")
        else:
            print(f"      钴铜相关系数: {s}")

    print("[5/5] 生成图表 & 导出结果")
    chart_paths = plot_charts(df, output_dir / "charts")
    export_results(
        df, issues_df, stats, chart_paths,
        out_path=output_dir / "cobalt_copper_results.xlsx",
    )
    print("\n完成！输出目录:", output_dir.resolve())


if __name__ == "__main__":
    main()
