"""
Visualize Velostat pressure (NO video).

This script visualizes pressure data from HDF5 files without video synchronization.
It creates a dual-pane visualization with pressure time series on the left and sensor distribution on the right.

Command Line Arguments:
    hdf5_path : Path to the HDF5 file containing Velostat sensor pressure data.
    e.g. python viz_sensor_data_no_video.py data/sensor_left_2024-01-01-12-00-00.h5

Usage:
    Run the script with path to HDF5 file to start the data visualization process:
        python viz_sensor_data_no_video.py hdf5_path

Features:
    - Reads and processes force data from HDF5 files.
    - Creates a dual-pane visualization: time series plot and real-time sensor distribution.
    - Uses color-mapped scatter plot to represent sensor data on images of the sensor layout.
    - Dynamically updates visualizations to show changes in force over time.
    - No video synchronization required - purely data-driven visualization.

Left: average pressure vs time
Right: sensor map with colormap + live frame title

"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import h5py
from datetime import datetime
import matplotlib.dates as mdates
from matplotlib.colors import LogNorm
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import LogLocator, ScalarFormatter
import argparse
from velostat_sensor_to_pressure import lookup_pressure
from matplotlib.animation import FuncAnimation

# ---- Animation duration (ms) ----
TOTAL_MS = 1500  # Increase = slower, decrease = faster

parser = argparse.ArgumentParser(description='Visualize force data from HDF5 (no video).')
parser.add_argument('hdf5_path', help='Path to the HDF5 file containing force data.')
args = parser.parse_args()

def load_data(hdf5_path):
    """Load timestamps and sensor values from HDF5 file."""
    with h5py.File(hdf5_path, 'r') as f:
        dataset = list(f.keys())[0]
        if dataset != 'sensor_left':
            raise ValueError(f"Only 'sensor_left' is supported; got '{dataset}'")

        points_df = pd.read_csv('../config/foil_sensor_positions_left.csv')
        image_path = '../images/foot_sole_sensor_scan_left.png'

        image_height_mm = 255
        scatter_size = 150
        label = 'Velostat Sensor Left'

        data = f[dataset][:]  # [timestamp(ns), s1, s2, ...]
        timestamps = [datetime.fromtimestamp(ts / 1e9) for ts in data[:, 0]]
        sensor_values = data[:, 1:]
        points_df = points_df.sort_values(by='ID', na_position='first').reset_index(drop=True)
        return timestamps, sensor_values, points_df, image_path, image_height_mm, scatter_size, label

def create_visualization():
    """Prepare figure, axes, scatter plot, and return all objects needed for animation."""
    (timestamps, sensor_values, points_df, image_path,
     image_height_mm, scatter_size, label) = load_data(args.hdf5_path)

    # Convert sensor values to pressure (kPa)
    sensor_values = lookup_pressure(sensor_values) / 1e3  

    # Build sensor mask from IDs
    n_sensors = sensor_values.shape[1]
    sensor_mask = np.zeros(n_sensors, dtype=bool)
    ids = points_df['ID'].astype(int).to_numpy() - 1
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
    # Always show full time (HH:MM:SS)
    ax_time.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax_time.set_ylim(top=8)
    ax_time.grid(True, alpha=0.3)
    ax_time.legend()
    vline = ax_time.axvline(timestamps[0], color='red', linewidth=2, alpha=0.8)

    # ---- Right panel: sensor distribution ----
    image = plt.imread(image_path)
    image_width_mm = (image.shape[1] / image.shape[0]) * image_height_mm
    ax_sensor.imshow(image, extent=[0, image_width_mm, 0, image_height_mm], cmap='gray', alpha=0.2)

    total_frames = len(timestamps)
    title_text = ax_sensor.set_title(f'{label} - Frame 1/{total_frames}',
                                     fontsize=14, fontweight='bold', pad=6)
    ax_sensor.set_xlabel('Width (mm)', fontsize=12)
    ax_sensor.set_ylabel('Height (mm)', fontsize=12)

    # Safe LogNorm to avoid zero/negative values
    positive_vals = sensor_values[sensor_values > 0]
    safe_min = max(1e-3, float(np.nanmin(positive_vals)) * 3.0) if positive_vals.size else 1e-3
    norm = LogNorm(vmin=safe_min, vmax=65)

    # Create one scatter object for all sensors
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
    return fig, ax_time, ax_sensor, vline, sc, title_text, sensor_mask, timestamps, sensor_values, norm

def animate_visualization():
    """Create and run the animation."""
    (fig, ax_time, ax_sensor, vline, sc, title_text,
     sensor_mask, timestamps, sensor_values, norm) = create_visualization()

    total_frames = len(timestamps)
    interval = max(10, int(TOTAL_MS / max(1, total_frames)))  # ms per frame

    def update_frame(i):
        # Update vertical time indicator
        vline.set_xdata([timestamps[i], timestamps[i]])
        # Update scatter face colors
        sc.set_array(sensor_values[i, sensor_mask])
        # Update title with frame index
        title_text.set_text(f'Velostat Sensor Left - Frame {i + 1}/{total_frames}')
        return ()

    print(f"Frames: {total_frames} | Interval: {interval} ms")
    ani = FuncAnimation(fig, update_frame, frames=total_frames,
                        interval=interval, blit=False, repeat=True)
    plt.show()
    return ani

if __name__ == '__main__':
    try:
        _ = animate_visualization()
    except FileNotFoundError as e:
        print(f"Error: Required file not found - {e}")
        print("Make sure these files exist in the working directory:")
        print("- foil_sensor_positions_left.csv")
        print("- foot_sole_sensor_scan_left.png")
        print("- velostat_sensor_to_pressure.py")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
