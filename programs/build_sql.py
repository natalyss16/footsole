from pathlib import Path
import re
import numpy as np
import pandas as pd
import h5py
import sqlite3

output_dir = Path("data_csv"); output_dir.mkdir(exist_ok=True)

def sanitize(name: str) -> str:
    base = name.strip("/").replace("/", "_") or "root"
    return re.sub(r"[^0-9A-Za-z_]", "_", base)

def describe_file(h5_path):
    print(f"Structure of {h5_path}")
    with h5py.File(h5_path, "r") as f:
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"[DATASET] {name} shape={obj.shape} dtype={obj.dtype}")
            elif isinstance(obj, h5py.Group):
                print(f"[GROUP]   {name}")
        f.visititems(show)

def dataset_to_dataframe(ds: h5py.Dataset) -> pd.DataFrame:
    data = ds[()]
    if hasattr(data, "dtype") and data.dtype.names:
        df = pd.DataFrame({k: data[k] for k in data.dtype.names})
    else:
        if data.ndim == 1:
            df = pd.DataFrame({sanitize(ds.name): data})
        elif data.ndim == 2:
            df = pd.DataFrame(data)
            df.columns = [f"c{i}" for i in range(df.shape[1])]
        else:
            raise ValueError(f"Skip non-tabular dataset {ds.name} with ndim={data.ndim}")
    for c in df.columns:
        col = df[c]
        if col.dtype.kind in {"S", "O"}:
            try:
                sample = next((x for x in col.dropna().values if isinstance(x, (bytes, bytearray))), None)
                if isinstance(sample, (bytes, bytearray)):
                    df[c] = col.apply(lambda x: x.decode("utf-8", "ignore") if isinstance(x, (bytes, bytearray)) else x)
            except Exception:
                pass
    return df

def export_all(h5_path, out_dir: Path):
    csv_paths = []
    with h5py.File(h5_path, "r") as f:
        def handle(name, obj):
            if not isinstance(obj, h5py.Dataset):
                return
            tbl = sanitize(name)
            try:
                df = dataset_to_dataframe(obj)
            except Exception as e:
                print(f"- Skipped {name}: {e}")
                return
            csv_path = out_dir / f"{Path(h5_path).stem}_{tbl}.csv"
            df.to_csv(csv_path, index=False)
            csv_paths.append((tbl, str(csv_path)))
            print(f"+ Wrote {csv_path} rows={len(df)} cols={len(df.columns)}")
        f.visititems(handle)
    return csv_paths

data_h5_path = Path("data_h5")
for file in data_h5_path.glob("*.h5"):
    print(f"\nProcessing {file}")
    describe_file(file)
    export_all(file, output_dir)

db_path = "footsole.sqlite" 

mapping = {
    # fullsole - stone/wiese/wood
    "fullsoul_left_stone1_sensor_left.csv": ("fullsole_stone", "stone_type", 1),
    "fullsoul_left_stone2_sensor_left.csv": ("fullsole_stone", "stone_type", 2),
    "fullsoul_left_wiese_onlyfront_sensor_left.csv": ("fullsole_wiese", "wiese_type", None),
    "fullsoul_left_wiese0_sensor_left.csv": ("fullsole_wiese", "wiese_type", 0),
    "fullsoul_left_wiese1_sensor_left.csv": ("fullsole_wiese", "wiese_type", 1),
    "fullsoul_left_wood1_sensor_left.csv":  ("fullsole_wood",  "wood_type",  1),

    # nrshoes - stone/wiese/wood
    "nrshoes_left_onlyfront_sensor_left.csv": ("nrshoes_wiese", "wiese_type", None),
    "nrshoes_left_stone1_sensor_left.csv":    ("nrshoes_stone", "stone_type", 1),
    "nrshoes_left_stone2_sensor_left.csv":    ("nrshoes_stone", "stone_type", 2),
    "nrshoes_left_wiese1_sensor_left.csv":    ("nrshoes_wiese", "wiese_type", 1),
    "nrshoes_left_wiese2_sensor_left.csv":    ("nrshoes_wiese", "wiese_type", 2),
    "nrshoes_left_wood1_sensor_left.csv":     ("nrshoes_wood",  "wood_type",  1),

    # standing
    "sensor_left_2025-3points_barefoot+sole_try1_sensor_left.csv": ("fullsole_standing", "try_num", 1),
    "sensor_left_2025-3points_barefoot+sole_try2_sensor_left.csv": ("fullsole_standing", "try_num", 2),
    "sensor_left_2025-3points_barefoot+sole_try3_sensor_left.csv": ("fullsole_standing", "try_num", 3),

    "sensor_left_2025-3points_shoe+sole_try1_sensor_left.csv": ("nrshoes_standing", "try_num", 1),
    "sensor_left_2025-3points_shoe+sole_try2_sensor_left.csv": ("nrshoes_standing", "try_num", 2),
    "sensor_left_2025-3points_shoe+sole_try3_sensor_left.csv": ("nrshoes_standing", "try_num", 3),
}

conn = sqlite3.connect(db_path)
for csv_path in output_dir.glob("*.csv"):
    # tables
    fname = csv_path.name
    table, type_col, type_val = mapping[fname]

    df = pd.read_csv(csv_path)
    df.columns = [re.sub(r"[^0-9A-Za-z_]", "_", str(c)) or "col" for c in df.columns]

    if type_col is not None:
        df[type_col] = type_val

    df.to_sql(table, conn, if_exists="append", index=False)

# views

# fullsole & nrshoes on stone
conn.execute(f"DROP VIEW IF EXISTS stone_view")
conn.execute(f"""
CREATE VIEW stone_view AS
    SELECT *, 'fullsole' AS shoe_type FROM fullsole_stone
    UNION ALL
    SELECT *, 'nrshoes' AS shoe_type FROM nrshoes_stone;
    """)

# fullsole & nrshoes on wiese
conn.execute(f"DROP VIEW IF EXISTS wiese_view")
conn.execute(f"""
CREATE VIEW wiese_view AS
    SELECT *, 'fullsole' AS shoe_type FROM fullsole_wiese
    UNION ALL
    SELECT *, 'nrshoes' AS shoe_type FROM nrshoes_wiese;
    """)

# fullsole & nrshoes on wood
conn.execute(f"DROP VIEW IF EXISTS wood_view")
conn.execute(f"""
CREATE VIEW wood_view AS
    SELECT *, 'fullsole' AS shoe_type FROM fullsole_wood
    UNION ALL
    SELECT *, 'nrshoes' AS shoe_type FROM nrshoes_wood;
""")

# fullsole & nrshoes standing
conn.execute(f"DROP VIEW IF EXISTS standing_view")
conn.execute(f"""
CREATE VIEW standing_view AS
    SELECT *, 'fullsole' AS shoe_type FROM fullsole_standing
    UNION ALL
    SELECT *, 'nrshoes' AS shoe_type FROM nrshoes_standing;
""")

# fullsole combined
conn.execute(f"DROP VIEW IF EXISTS fullsole_view")
conn.execute(f"""
CREATE VIEW fullsole_view AS
    SELECT *, 'stone' AS ground_type FROM fullsole_stone
    UNION ALL
    SELECT *, 'wiese' AS ground_type FROM fullsole_wiese
    UNION ALL
    SELECT *, 'wood' AS ground_type FROM fullsole_wood
    UNION ALL
    SELECT *, 'standing' AS ground_type FROM fullsole_standing;
""")

# nrshoes combined
conn.execute(f"DROP VIEW IF EXISTS nrshoes_view")
conn.execute(f"""
CREATE VIEW nrshoes_view AS
    SELECT *, 'stone' AS ground_type FROM nrshoes_stone
    UNION ALL
    SELECT *, 'wiese' AS ground_type FROM nrshoes_wiese
    UNION ALL
    SELECT *, 'wood' AS ground_type FROM nrshoes_wood
    UNION ALL
    SELECT *, 'standing' AS ground_type FROM nrshoes_standing;
""")

# all combined
conn.execute(f"DROP VIEW IF EXISTS combined_view")
conn.execute(f"""
CREATE VIEW combined_view AS
    SELECT *, 'fullsole' AS shoe_type FROM fullsole_view
    UNION ALL
    SELECT *, 'nrshoes' AS shoe_type FROM nrshoes_view;
""")


conn.close()

