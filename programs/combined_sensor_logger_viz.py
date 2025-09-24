#!/usr/bin/env python3
"""
Combined BLE Logger and Visualizer for Foot Sole Sensors
Minimal modification version - preserves original code structure

Usage:
    python combined_sensor_logger_viz.py --name FootSole-C3 --duration 60
    python combined_sensor_logger_viz.py --name FootSole-C3 --left --duration 30
"""

import asyncio
import h5py
import numpy as np
from bleak import BleakClient, BleakScanner
import struct
import time
import datetime
import argparse
from pathlib import Path
import os

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LogNorm
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import LogLocator, ScalarFormatter
from matplotlib.animation import FuncAnimation

# ========== Import from velostat_sensor_to_pressure.py ==========
from velostat_sensor_to_pressure import lookup_pressure

# ========== FROM log_velostat_sensor_h5_BLE.py (UNCHANGED) ==========
PACKET_SIZE = 216
FMT = '<HBHB208BH'  # head,u8,len,u8,208B,checksum(u16 LE)

UART_SERVICE = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX      = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"   # notify from ESP32

def checksum16(bs: bytes) -> int:
    return sum(bs) & 0xFFFF

def now_fname(side: str) -> str:
    t = datetime.datetime.now()
    return t.strftime(f"{side}_%Y-%m-%d-%H-%M-%S.h5")

class FootSoleBLELogger:
    def __init__(self, device_name="FootSole-C3", use_left=False, chunk_rows=1):
        self.device_name = device_name
        self.buffer = bytearray()
        self.chunk = []
        self.chunk_rows = chunk_rows
        side = "sensor_left" if use_left else "sensor_right"
        self.h5_path = now_fname(side)
        self.h5 = h5py.File(self.h5_path, "a")
        if side not in self.h5:
            self.ds = self.h5.create_dataset(side, shape=(0, 209), maxshape=(None, 209), dtype='float64')
        else:
            self.ds = self.h5[side]

    def _flush_chunk(self):
        if not self.chunk: return
        a = np.asarray(self.chunk, dtype='float64')
        n0 = self.ds.shape[0]
        self.ds.resize(n0 + a.shape[0], axis=0)
        self.ds[n0:] = a
        self.chunk.clear()
        self.h5.flush()

    def close(self):
        try: self._flush_chunk()
        finally: self.h5.close()

    def _process_packet(self, pkt: bytes) -> bool:
        print(f"[PKT] {pkt.hex()}")
        head = pkt[0] | (pkt[1] << 8)
        if head not in (0x5AA5, 0x015A):
            print(f"[SYNC] Bad header: {head:04X}")
            return False
        try:
            # Unpack with little-endian format
            _, ftype, flen, ptype, *vals, rx = struct.unpack('<HBHB208BH', pkt)
        except struct.error:
            print("[SYNC] struct.error in unpacking")
            return False
        if flen != PACKET_SIZE:
            print(f"[SYNC] Bad length: {flen}")
            return False
        if checksum16(pkt[:-2]) != rx:
            print(f"[SYNC] Bad checksum: got {rx}, expected {checksum16(pkt[:-2])}")
            return False
        ts = time.time_ns()
        # Only save timestamp + 208 sensor values, matching data.py
        self.chunk.append([ts] + vals)
        if len(self.chunk) >= self.chunk_rows:
            self._flush_chunk()
        return True

    def _drain(self):
        sync_errors = 0
        while len(self.buffer) >= PACKET_SIZE:
            pkt = bytes(self.buffer[:PACKET_SIZE])
            try:
                head, ftype, plen, ptype, *vals, rx = struct.unpack(FMT, pkt)
                cksum = checksum16(pkt[:-2])
            except Exception as e:
                print(f"[SYNC] struct.error: {e}")
                self.buffer.pop(0)
                sync_errors += 1
                continue
            if plen != PACKET_SIZE or cksum != rx:
                print(f"[SYNC] Skipped packet: head={head:04X} ftype={ftype} plen={plen} ptype={ptype} rx={rx} cksum={cksum}")
                self.buffer.pop(0)
                sync_errors += 1
                continue
            if self._process_packet(pkt):
                del self.buffer[:PACKET_SIZE]
            else:
                print(f"[SYNC] Bad packet: head={head:04X} ftype={ftype} plen={plen} ptype={ptype} rx={rx} cksum={cksum}")
                self.buffer.pop(0)
                sync_errors += 1
        # Discard any trailing bytes that can't form a full packet
        if len(self.buffer) > 0 and len(self.buffer) < PACKET_SIZE:
            print(f"[SYNC] Discarding {len(self.buffer)} trailing bytes: {self.buffer.hex()}")
            self.buffer.clear()
        if sync_errors:
            print(f"[SYNC] {sync_errors} bytes skipped due to misalignment or bad packet.")
            if len(self.buffer) >= 32:
                print(f"[SYNC] First 32 bytes of buffer: {self.buffer[:32].hex()}")

    def on_notify(self, _h, data: bytearray):
        self.buffer.extend(data)
        self._drain()

async def run_logger(name: str, use_left: bool, duration: int):
    print("Scanning for:", name)
    dev = await BleakScanner.find_device_by_filter(lambda d, ad: d.name == name)
    if not dev:
        print("Device not found"); return None
    logger = FootSoleBLELogger(device_name=name, use_left=use_left)
    try:
        async with BleakClient(dev) as cli:
            print(f"Connected. Logging to {logger.h5_path}.")
            await cli.start_notify(UART_TX, logger.on_notify)
            await asyncio.sleep(duration)  # Log for specified seconds
    finally:
        logger.close()
        print("Logger stopped. Data saved to:", logger.h5_path)
        return logger.h5_path

# ========== FROM viz_sensor_data_no_video.py ==========
# ---- Animation duration (ms) ----
TOTAL_MS = 1500  # Increase = slower, decrease = faster

# Base directory for relative resources (CSV, images) = script folder
BASE = Path(__file__).resolve().parent

# Map side -> resources
SIDE_RESOURCES = {
    'left': {
        'csv': BASE / '../config/foil_sensor_positions_left.csv',
        'image': BASE / '../images/foot_sole_sensor_scan_left.png',
        'image_height_mm': 255,
        'label': 'Velostat Sensor Left'
    },
    'right': {
        'csv': BASE / '../config/foil_sensor_positions_right.csv',
        'image': BASE / '../images/foot_sole_sensor_scan_right.png',
        'image_height_mm': 255,
        'label': 'Velostat Sensor Right'
    }
}

def detect_dataset_side(h5: h5py.File, cli_side: str) -> str:
    """Return 'left' or 'right' based on CLI hint and actual HDF5 keys."""
    keys = list(h5.keys())
    has_left = 'sensor_left' in keys
    has_right = 'sensor_right' in keys

    if cli_side in ('left', 'right'):
        # Enforce user's choice, but still sanity-check existence
        expected_key = f'sensor_{cli_side}'
        if expected_key not in keys:
            raise ValueError(f"Requested side '{cli_side}' but '{expected_key}' not found in HDF5 keys {keys}")
        return cli_side

    # auto mode
    if has_left and not has_right:
        return 'left'
    if has_right and not has_left:
        return 'right'
    if has_left and has_right:
        # both exist: prefer left unless user specifies --side right
        return 'left'

    raise ValueError(f"No supported dataset found. HDF5 top-level keys: {keys}")

def load_data(hdf5_path: str, side_arg: str):
    """Load timestamps and sensor values from HDF5 file."""
    with h5py.File(hdf5_path, 'r') as f:
        side = detect_dataset_side(f, side_arg)
        dataset = f'sensor_{side}'

        # Resources for this side
        res = SIDE_RESOURCES[side]
        points_csv = res['csv']
        image_path = res['image']
        image_height_mm = res['image_height_mm']
        label = res['label']

        if not points_csv.exists():
            raise FileNotFoundError(f"Sensor positions CSV not found: {points_csv}")
        if not image_path.exists():
            raise FileNotFoundError(f"Background image not found: {image_path}")

        # HDF5 layout: [timestamp(ns), s1, s2, ...]
        data = f[dataset][:]
        timestamps = [datetime.datetime.fromtimestamp(ts / 1e9) for ts in data[:, 0]]
        sensor_values = data[:, 1:]

        # Load and sort sensor positions (expects 'ID','X_in_mm','Y_in_mm')
        points_df = pd.read_csv(points_csv)
        points_df = points_df.sort_values(by='ID', na_position='first').reset_index(drop=True)

        # Additional visuals
        scatter_size = 150

        return side, timestamps, sensor_values, points_df, image_path, image_height_mm, scatter_size, label

def create_visualization(hdf5_path: str, side_arg: str):
    """Prepare figure, axes, scatter plot, and return all objects needed for animation."""
    (side, timestamps, sensor_values, points_df, image_path,
     image_height_mm, scatter_size, label) = load_data(hdf5_path, side_arg)

    # Convert sensor values to pressure (kPa)
    sensor_values = lookup_pressure(sensor_values) / 1e3

    # Build sensor mask from IDs
    n_sensors = sensor_values.shape[1]
    sensor_mask = np.zeros(n_sensors, dtype=bool)
    ids = points_df['ID'].astype(int).to_numpy() - 1
    if (ids < 0).any() or (ids >= n_sensors).any():
        raise ValueError(f"IDs out of range. Max index {n_sensors-1}, got min {ids.min()}, max {ids.max()}")
    sensor_mask[ids] = True

    x = points_df['X_in_mm'].to_numpy()
    y = points_df['Y_in_mm'].to_numpy()

    # Figure layout
    fig = plt.figure(figsize=(16, 8))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1])
    ax_time = fig.add_subplot(gs[0, 0])
    ax_sensor = fig.add_subplot(gs[0, 1])

    # ---- Left panel: average pressure vs time ----
    avg_p = np.mean(sensor_values, axis=1)
    ax_time.plot(timestamps, avg_p, label=label, linewidth=2)
    ax_time.set_title('Average Pressure Over Time', fontsize=18, fontweight='bold', pad=12)
    ax_time.set_xlabel('UTC Time', fontsize=12)
    ax_time.set_ylabel('Average Pressure (kPa)', fontsize=12)
    ax_time.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax_time.set_ylim(top=8)
    ax_time.grid(True, alpha=0.3)
    ax_time.legend()
    
    # Add date label in bottom left
    date_str = timestamps[0].strftime('%Y-%m-%d')
    ax_time.text(0.02, 0.02, f'Date: {date_str}', transform=ax_time.transAxes, 
                 fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    vline = ax_time.axvline(timestamps[0], color='red', linewidth=2, alpha=0.8)

    # ---- Right panel: sensor distribution ----
    image = plt.imread(image_path)
    image_height_mm = float(image_height_mm)
    image_width_mm = (image.shape[1] / image.shape[0]) * image_height_mm
    ax_sensor.imshow(image, extent=[0, image_width_mm, 0, image_height_mm], cmap='gray', alpha=0.2)

    total_frames = len(timestamps)
    title_text = ax_sensor.set_title(f'{label} - Frame 1/{total_frames}',
                                     fontsize=14, fontweight='bold', pad=6)
    ax_sensor.set_xlabel('Width (mm)', fontsize=12)
    ax_sensor.set_ylabel('Height (mm)', fontsize=12)

    # Use LogNorm safely
    positive_vals = sensor_values[sensor_values > 0]
    safe_min = max(1e-3, float(np.nanmin(positive_vals)) * 3.0) if positive_vals.size else 1e-3
    norm = LogNorm(vmin=safe_min, vmax=65)

    # Create one scatter object for all active sensors
    c0 = sensor_values[0, sensor_mask]
    sc = ax_sensor.scatter(
        x, y, s=scatter_size,
        c=c0, cmap='jet', norm=norm,
        edgecolors='face', linewidth=0.5
    )

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap='jet', norm=norm)
    cbar = plt.colorbar(sm, ax=ax_sensor, label='Pressure (kPa)')
    cbar.ax.yaxis.set_major_locator(LogLocator(subs='all'))
    fmt = ScalarFormatter(); fmt.set_scientific(False)
    cbar.ax.yaxis.set_major_formatter(fmt)

    plt.tight_layout()
    return side, fig, ax_time, ax_sensor, vline, sc, title_text, sensor_mask, timestamps, sensor_values, norm, label

def animate_visualization(hdf5_path: str, side_arg: str, save_frames: bool = False):
    """Create and run the animation."""
    (side, fig, ax_time, ax_sensor, vline, sc, title_text,
     sensor_mask, timestamps, sensor_values, norm, label) = create_visualization(hdf5_path, side_arg)

    total_frames = len(timestamps)
    interval = max(10, int(TOTAL_MS / max(1, total_frames)))  # ms per frame

    def update_frame(i):
        vline.set_xdata([timestamps[i], timestamps[i]])
        sc.set_array(sensor_values[i, sensor_mask])
        title_text.set_text(f'{label} - Frame {i + 1}/{total_frames}')
        return ()

    print(f"[INFO] Detected side: {side}")
    print(f"Frames: {total_frames} | Interval: {interval} ms")

    # Generate frames if requested
    if save_frames:
        h5_filename = os.path.splitext(os.path.basename(hdf5_path))[0]
        output_dir = f'frames/{h5_filename}'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print(f"Generating frames to: {output_dir}")
        for i in range(total_frames):
            update_frame(i)
            plt.savefig(os.path.join(output_dir, f'frame_{i:04d}.png'), dpi=200)
            if i % 10 == 0:
                print(f"Generated frame {i+1}/{total_frames}")
        
        print(f"Frame generation complete! Saved to {output_dir}")

    ani = FuncAnimation(fig, update_frame, frames=total_frames,
                        interval=interval, blit=False, repeat=True)
    plt.show()
    return ani

# ========== MAIN COMBINED FUNCTION ==========
async def main():
    parser = argparse.ArgumentParser(description="FootSole BLE → HDF5 logger with visualization")
    parser.add_argument('--name', default="FootSole-C3", help='BLE device name')
    parser.add_argument('--left', action='store_true', help='Log left sensor (default: right)')
    parser.add_argument('--duration', type=int, default=60, help='Seconds to log (default: 60)')
    parser.add_argument('--side', choices=['auto', 'left', 'right'], default='auto',
                        help="Which dataset to use for visualization. Default: auto")
    parser.add_argument('--no-viz', action='store_true', help='Skip visualization after logging')
    parser.add_argument('--save-frames', action='store_true', help='Save animation frames')
    args = parser.parse_args()

    # Step 1: Run BLE logger
    h5_path = await run_logger(args.name, args.left, args.duration)
    
    # Step 2: Run visualization (unless skipped)
    if h5_path and not args.no_viz:
        try:
            print("\n[VIZ] Starting visualization...")
            _ = animate_visualization(h5_path, args.side, args.save_frames)
        except FileNotFoundError as e:
            print(f"Error: Required file not found - {e}")
            print("Make sure these files exist relative to the script folder:")
            print(" - ../config/foil_sensor_positions_left.csv")
            print(" - ../config/foil_sensor_positions_right.csv")
            print(" - ../images/foot_sole_sensor_scan_left.png")
            print(" - ../images/foot_sole_sensor_scan_right.png")
        except Exception as e:
            print(f"Visualization error: {e}")
            print(f"Data has been saved to: {h5_path}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())