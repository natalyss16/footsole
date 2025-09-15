"""
inspect_h5.py
-------------
Simple HDF5 file inspector:
- Print all datasets inside the file
- For each dataset, show shape and dtype
- Print first N and last N rows of data (default: 3)

To specify your data path, change the data path of yours in line 42
"""

import h5py
import numpy as np
import argparse

def inspect_file(filename, nrows=3):
    """Inspect an HDF5 file and print dataset information."""
    with h5py.File(filename, "r") as f:
        print(f"\n=== File: {filename} ===")

        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"\nDataset: {name}")
                print(f"  shape: {obj.shape}")
                print(f"  dtype: {obj.dtype}")
                if obj.shape[0] > 0:
                    # Head
                    head = obj[:min(nrows, obj.shape[0])]
                    print(f"  First {len(head)} rows:\n{head}")
                    # Tail
                    if obj.shape[0] > nrows:
                        tail = obj[-nrows:]
                        print(f"  Last {len(tail)} rows:\n{tail}")

        f.visititems(visit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect contents of an HDF5 file.")
    parser.add_argument(
        "--filename",
        type=str,
        default=r"Your_File_Path",
        help="Path to HDF5 file (default: your .h5 file)"
    )
    parser.add_argument(
        "--nrows", type=int, default=3,
        help="Number of rows to preview from head and tail"
    )
    args = parser.parse_args()
    inspect_file(args.filename, args.nrows)
