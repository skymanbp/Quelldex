"""
Quelldex DataViz — Data loading, statistics, chart data generators
Pure logic — no UI dependencies
"""

import csv
import json
import statistics
from pathlib import Path


# ── Data Loading ────────────────────────────────────────────────

def load_csv(filepath: str, encoding: str = 'utf-8') -> dict:
    path = Path(filepath)
    result = {"name": path.name, "path": str(path), "columns": [], "rows": [], "dtypes": {}}
    for enc in [encoding, 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']:
        try:
            with open(path, 'r', encoding=enc, newline='') as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                except csv.Error:
                    dialect = csv.excel
                reader = csv.reader(f, dialect)
                rows = list(reader)
                if not rows:
                    return result
                result["columns"] = [c.strip() for c in rows[0]]
                result["rows"] = rows[1:]
                result["dtypes"] = _detect_types(result["columns"], result["rows"])
                return result
        except (UnicodeDecodeError, UnicodeError):
            continue
    return result


def load_tsv(filepath: str) -> dict:
    path = Path(filepath)
    result = {"name": path.name, "path": str(path), "columns": [], "rows": [], "dtypes": {}}
    for enc in ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']:
        try:
            with open(path, 'r', encoding=enc) as f:
                reader = csv.reader(f, delimiter='\t')
                rows = list(reader)
                if rows:
                    result["columns"] = [c.strip() for c in rows[0]]
                    result["rows"] = rows[1:]
                    result["dtypes"] = _detect_types(result["columns"], result["rows"])
                return result
        except (UnicodeDecodeError, UnicodeError):
            continue
    return result


def load_json_data(filepath: str) -> dict:
    path = Path(filepath)
    result = {"name": path.name, "path": str(path), "columns": [], "rows": [], "dtypes": {}}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            result["columns"] = list(data[0].keys())
            result["rows"] = [[str(row.get(c, "")) for c in result["columns"]] for row in data]
            result["dtypes"] = _detect_types(result["columns"], result["rows"])
    except Exception:
        pass
    return result


def load_data_file(filepath: str) -> dict:
    ext = Path(filepath).suffix.lower()
    if ext == '.csv':   return load_csv(filepath)
    if ext == '.tsv':   return load_tsv(filepath)
    if ext == '.json':  return load_json_data(filepath)
    return {"name": Path(filepath).name, "path": filepath, "columns": [], "rows": [], "dtypes": {}}


def _detect_types(columns, rows) -> dict:
    dtypes = {}
    for i, col in enumerate(columns):
        nums, total = 0, 0
        for row in rows[:200]:
            if i < len(row) and row[i].strip():
                total += 1
                try:
                    float(row[i].replace(',', ''))
                    nums += 1
                except ValueError:
                    pass
        dtypes[col] = "numeric" if total > 0 and nums / total > 0.7 else "text"
    return dtypes


# ── Column Statistics ───────────────────────────────────────────

def compute_column_stats(data: dict, col_name: str) -> dict:
    if col_name not in data["columns"]:
        return {}
    idx = data["columns"].index(col_name)
    raw = [row[idx] if idx < len(row) else "" for row in data["rows"]]
    dtype = data["dtypes"].get(col_name, "text")
    stats = {
        "column": col_name, "type": dtype,
        "total_rows": len(raw),
        "non_empty": sum(1 for v in raw if v.strip()),
        "empty": sum(1 for v in raw if not v.strip()),
        "unique": len(set(raw)),
    }
    if dtype == "numeric":
        values = []
        for v in raw:
            try: values.append(float(v.replace(',', '')))
            except (ValueError, AttributeError): pass
        if values:
            vs = sorted(values)
            n = len(vs)
            stats.update({
                "count": n, "sum": sum(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if n > 1 else 0,
                "variance": statistics.variance(values) if n > 1 else 0,
                "min": min(values), "max": max(values),
                "range": max(values) - min(values),
                "q1": vs[n // 4] if n >= 4 else vs[0],
                "q3": vs[3 * n // 4] if n >= 4 else vs[-1],
                "skewness": _skewness(values) if n > 2 else 0,
            })
    else:
        freq = {}
        for v in raw:
            v = v.strip()
            if v: freq[v] = freq.get(v, 0) + 1
        stats["top_values"] = sorted(freq.items(), key=lambda x: -x[1])[:10]
        stats["distinct_count"] = len(freq)
    return stats


def _skewness(values):
    n = len(values)
    if n < 3: return 0
    m, s = statistics.mean(values), statistics.stdev(values)
    if s == 0: return 0
    return (n / ((n - 1) * (n - 2))) * sum(((x - m) / s) ** 3 for x in values)


def compute_cross_file_stats(datasets: list, col_name: str) -> dict:
    all_values, per_file = [], {}
    for ds in datasets:
        if col_name in ds["columns"] and ds["dtypes"].get(col_name) == "numeric":
            idx = ds["columns"].index(col_name)
            vals = []
            for row in ds["rows"]:
                try: vals.append(float(row[idx].replace(',', '')))
                except (ValueError, IndexError, AttributeError): pass
            per_file[ds["name"]] = vals
            all_values.extend(vals)
    if not all_values:
        return {"column": col_name, "error": "No numeric data"}
    result = {
        "column": col_name, "total_values": len(all_values), "files": len(per_file),
        "global_mean": statistics.mean(all_values),
        "global_median": statistics.median(all_values),
        "global_min": min(all_values), "global_max": max(all_values),
        "global_stdev": statistics.stdev(all_values) if len(all_values) > 1 else 0,
        "per_file": {},
    }
    for fname, vals in per_file.items():
        if vals:
            result["per_file"][fname] = {
                "count": len(vals), "mean": statistics.mean(vals),
                "min": min(vals), "max": max(vals),
            }
    return result


# ── Chart Data Generators ───────────────────────────────────────

def histogram_data(data: dict, col_name: str, bins: int = 20) -> dict:
    idx = data["columns"].index(col_name)
    values = []
    for row in data["rows"]:
        try: values.append(float(row[idx].replace(',', '')))
        except (ValueError, IndexError, AttributeError): pass
    if not values:
        return {"bins": [], "counts": []}
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        return {"bins": [vmin], "counts": [len(values)]}
    width = (vmax - vmin) / bins
    bin_edges = [vmin + i * width for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        b = min(int((v - vmin) / width), bins - 1)
        counts[b] += 1
    return {"bins": bin_edges, "counts": counts, "width": width}


def scatter_data(data: dict, col_x: str, col_y: str) -> dict:
    ix, iy = data["columns"].index(col_x), data["columns"].index(col_y)
    points = []
    for row in data["rows"]:
        try:
            points.append((float(row[ix].replace(',', '')), float(row[iy].replace(',', ''))))
        except (ValueError, IndexError, AttributeError):
            pass
    return {"points": points, "x_label": col_x, "y_label": col_y}


def bar_data(data: dict, col_name: str, top_n: int = 15) -> dict:
    idx = data["columns"].index(col_name)
    freq = {}
    for row in data["rows"]:
        try:
            v = row[idx].strip()
            if v: freq[v] = freq.get(v, 0) + 1
        except IndexError: pass
    top = sorted(freq.items(), key=lambda x: -x[1])[:top_n]
    return {"labels": [t[0] for t in top], "values": [t[1] for t in top]}


def line_data(data: dict, col_name: str) -> dict:
    idx = data["columns"].index(col_name)
    values = []
    for row in data["rows"]:
        try: values.append(float(row[idx].replace(',', '')))
        except (ValueError, IndexError, AttributeError): values.append(None)
    return {"values": values, "label": col_name}


def multi_line_data(datasets: list, col_name: str) -> dict:
    series = {}
    for ds in datasets:
        if col_name in ds["columns"]:
            series[ds["name"]] = line_data(ds, col_name)["values"]
    return {"series": series, "label": col_name}


def correlation_matrix(data: dict) -> dict:
    num_cols = [c for c in data["columns"] if data["dtypes"].get(c) == "numeric"]
    if len(num_cols) < 2:
        return {"columns": num_cols, "matrix": []}
    arrays = {}
    for col in num_cols:
        idx = data["columns"].index(col)
        arrays[col] = [
            (lambda v: float(v.replace(',', '')) if v.strip() else 0)(row[idx] if idx < len(row) else "0")
            for row in data["rows"]
        ]
    n = len(data["rows"])
    matrix = []
    for c1 in num_cols:
        row = []
        for c2 in num_cols:
            if c1 == c2:
                row.append(1.0)
            else:
                a, b = arrays[c1], arrays[c2]
                ma, mb = statistics.mean(a), statistics.mean(b)
                sa = statistics.stdev(a) or 1
                sb = statistics.stdev(b) or 1
                corr = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / ((n - 1) * sa * sb)
                row.append(round(max(-1, min(1, corr)), 4))
        matrix.append(row)
    return {"columns": num_cols, "matrix": matrix}
