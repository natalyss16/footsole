# Foot Sole Sensor

> **Project Origin and Attribution**
>
> This repository represents a new and independent continuation of the **Foot Sole Pressure Sensing Device** project originally developed by **Kai Burian, Chutong Ren, and Arved Strauch** at the **Technical University of Munich**, as part of the *Clinical Applications of Computational Medicine (CACOM)* course, July 30, 2024.  
>
> **Reference:**  
> Burian, K., Ren, C., & Strauch, A. (2024, July 30). *Foot Sole Pressure Sensing Device and Its Usage in Barefoot Shoes: Fullsoul Runningpad.* Clinical Applications of Computational Medicine (CACOM), Technical University of Munich.  
>
> **Original repository:** [https://github.com/weichkai/footPressureSensor](https://github.com/weichkai/footPressureSensor)
>
> This project **was not forked or cloned** from the original repository but **rebuilt from scratch**, based on the same experimental concept, and carried out **with permission from the original authors**.  
> All reused methods, scripts, and figures are properly cited as per academic integrity requirements.  
>
> The primary extensions in this version are:
> - Integration of **Bluetooth Low Energy (BLE)** for wireless data transmission  
> - Addition of an **SQLite database** for structured data storage and querying

---

## Abstract

This project extends the original wired *Fullsoul* insole pressure sensor system by adding **Bluetooth Low Energy (BLE)** communication and **SQLite database integration**.  
An **ESP32-C3** microcontroller collects data from 208 Velostat-based pressure sensors and transmits them via BLE to a host computer.  
Python scripts record and store the data both as `.h5` files and in an SQLite database for post-processing and analysis.  
The visualization pipeline and sensor layout follow the structure established by Burian et al. (2024).

---

## Prior Work vs. This Work (Software)

| **Burian et al. (2024)** | **This Project (2025)** |
|---------------------------|--------------------------|
| Wired Velostat sensor array inside Fullsoul shoe | Wireless BLE communication using ESP32-C3 |
| Data transfer via USB-C serial connection | Real-time BLE transmission (UART bridge) |
| Data stored only as `.h5` files | Added **SQLite database** for structured queries |
| Python visualization pipeline | Visualization pipeline reused with minimal modification |

---

## Change Log (Software)

- 🔹 **BLE Integration:** replaced wired USB connection with wireless Bluetooth Low Energy communication  
- 🔹 **Database Integration:** added `build_sql.py` to convert `.h5` data into an **SQLite database** with queryable tables and views  
  
---


## Reused Components (from Burian et al., 2024)

To maintain **project completeness**, **backward compatibility**, and facilitate **future forks**, several components from the original repository were intentionally preserved:

* **`config/`** — retains the original **sensor position CSV files** for left and right insoles.
* **`images/`** — includes the original **background images** for left and right foot visualizations.
* **`programs/`** — preserves the following original scripts for reference and potential reuse:

  * `log_velostat_sensor_h5.py`
  * `index_find.py`
  * `velostat_sensor_to_pressure.py`
  * `viz_generate_frames.py`
  * `frames_to_video.py`

These five scripts were kept unmodified to ensure that users can reproduce or compare the wired workflow of the original project.
All BLE-related and database-related scripts in this repository are **newly developed** and independent, except that the function
`velostat_sensor_to_pressure()` from the original codebase was reused within our new BLE workflow.

---


## Table of Contents
- [Hardware Setup](#hardware-setup)
- [UART Communication](#uart-communication)
- [Software Setup](#software-setup)
- [Repository Structure](#repository-structure)
- [Reused Components (from Burian et al., 2024)](#reused-components-from-burian-et-al-2024)
- [Scripts Overview](#scripts-overview)
- [Typical Workflow](#typical-workflow)
- [Data Files](#data-files)
- [BLE Logic](#ble-logic)
- [FAQ](#faq)
- [Acknowledgment](#acknowledgment)
- [License](#license)


---

## Hardware Setup
- **Power & Charging:** Charge the insole sensor with a **USB-C cable**. Ready status is indicated by a **blinking green LED**.  
- **Placement:** Place the insole flat inside the shoe. Specify left/right when running scripts.  
- **Reset:** After every measurement you **must press Reset** to ensure the next recording starts cleanly.

---

## UART Communication (used in this project)
- The sensor module supports both **I²C** and **UART**.  
- In this project, we **use UART**.  
- **Wiring:**
  - **GND ↔ GND**
  - **TX ↔ RX**
  - **RX ↔ TX**
  - **3.3 V ↔ VCC**
- BLE is used to **wirelessly transmit** the UART data to the computer.

---

## Software Setup
1. Install **Python 3.9+**.  
2. From the repository root:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure your computer's **Bluetooth** is enabled.

---

## Repository Structure

* `config/` — sensor position CSV files (left/right).
* `data/` — general data folder (optional scratch space).
* `data_csv/` — exported sensor data in CSV format.
* `data_h5/` — recorded sensor data in HDF5 format.
* `images/` — background images used for visualization.
* `programs/` — main Python scripts for logging/visualization.
* `README.md` — this documentation.
* `footsole.sqlite` — SQLite database file.
* `requirements.txt` — Python dependency list.

> Tip: Run scripts **from the `programs/` folder** so relative paths to `config/` and `images/` resolve correctly.

---

## Scripts Overview

All scripts are located in `programs/`.

### `combined_sensor_logger_viz.py` (recommended)

* Combined **logger + visualizer** in one script.
* Options:

  * `--name` device name (default `FootSole-C3`)
  * `--left` record left foot (default: right)
  * `--duration` recording time in seconds (default: 60)
  * `--side auto|left|right` choose visualization side (default: auto)
  * `--no-viz` only save data, no plot
  * `--save-frames` export PNG frames

**Examples**

```bash
# Right foot, 60 seconds with visualization
python combined_sensor_logger_viz.py (Using default configuration)
python combined_sensor_logger_viz.py --name FootSole-C3 --duration 60 (For personal configuration)

# Left foot, 30 seconds, no visualization
python combined_sensor_logger_viz.py --name FootSole-C3 --left --duration 30 --no-viz (For personal configuration)
```

### `foot_sole_ble_visualizer.py`

* Collects data via BLE and visualizes **after** recording.

**Examples**

```bash
python foot_sole_ble_visualizer.py (Using default configuration)
python foot_sole_ble_visualizer.py --name FootSole-C3 --duration 60
python foot_sole_ble_visualizer.py --name FootSole-C3 --left --duration 30 --no-display
```

### `log_velostat_sensor_h5_BLE.py`

* **Record only** (no visualization).

**Examples**

```bash
python log_velostat_sensor_h5_BLE.py --name FootSole-C3 --duration 60
python log_velostat_sensor_h5_BLE.py --name FootSole-C3 --left --duration 30
```

### `viz_sensor_data_no_video.py`

* Visualize an existing `.h5` file.

**Example**

```bash
python viz_sensor_data_no_video.py ../data_h5/sensor_right_YYYY-MM-DD-HH-MM-SS.h5 --side right
```

### `build_sql.py`

* Tranform `.h5` files to `.csv` and build a database that consists of tables and views. Database schema is available here: https://drawsql.app/teams/tum-12/diagrams/footsole.

### `interactive visualizer.py`
* Interactive Foot Pressure Sensor Data visualization Tool. Supports user upload of H5 data files and video files, with different visualization modes.

### Utilities

* `checkh5.py` — inspect `.h5` structure and preview rows.
* `velostat_sensor_to_pressure.py` — convert raw values to pressure (Pa).
* `frames_to_video.py` / `frames_to_video_html.py` — convert exported frames to video/HTML.

---

## Typical Workflow 

1. Charge the insole → **green LED blinks**.
2. Enable **Bluetooth** on your computer.
3. Open a terminal and go to the scripts folder:

   ```bash
   cd programs
   ```
4. Run:

   ```bash
   python combined_sensor_logger_viz.py --name FootSole-C3 --duration 30
   ```
5. A plot window will show results; a `.h5` file is saved automatically.
6. **Press Reset** before the next measurement.

---

## Data Files
This repository contains data from first iteration done by Kai and team:

  * `fullsoul_left_stone1_sensor_left`
  * `fullsoul_left_stone2_sensor_left`
  * `fullsoul_left_wiese0_sensor_left`
  * `fullsoul_left_wiese1_sensor_left`
  * `fullsoul_left_wiese_onlyfront_sensor_left`
  * `fullsoul_left_wood1_sensor_left`
  * `nrshoes_left_onlyfront_sensor_left`
  * `nrshoes_left_stone1_sensor_left`
  * `nrshoes_left_stone2_sensor_left`
  * `nrshoes_left_wiese1_sensor_left`
  * `nrshoes_left_wiese2_sensor_left`
  * `nrshoes_left_wood1_sensor_left`

And data collected by second year iteration by our team:

  * `sensor_left_2025-3points_barefoot+sole_try1_sensor_left`
  * `sensor_left_2025-3points_barefoot+sole_try2_sensor_left`
  * `sensor_left_2025-3points_barefoot+sole_try3_sensor_left`
  * `sensor_left_2025-3points_shoe+sole_try1_sensor_left`
  * `sensor_left_2025-3points_shoe+sole_try2_sensor_left`
  * `sensor_left_2025-3points_shoe+sole_try3_sensor_left`

* **HDF5 structure**

  * Top-level dataset on different grounds
  * Each row: `[timestamp_ns, s1, s2, …, s208]`

    * `timestamp_ns`: nanoseconds since epoch
    * `s1..s208`: sensor channel values

* **CSV structure**

  * Transformed hierarchical HDF5 files to table format
  * Same content as HDF5 files

---

## BLE Logic (Simplified)

* **Connection:** When powered (green LED blinking), the insole advertises. Scripts connect by device name (`FootSole-C3`). Only **one host** can connect at a time.
* **Transfer:** ESP32 provides a **UART-like BLE** service; scripts **subscribe to notifications** to receive packets continuously.
* **Packets:** Fixed length (216 bytes) containing a header, **208 channel values**, and a checksum. Receiver auto-syncs and discards corrupt frames.
* **Saving:** Each received frame is timestamped and appended to the `.h5` dataset (`sensor_left` or `sensor_right`).
* **Reset:** Required after each measurement to clear buffers and ensure clean alignment.

---

## FAQ

**No green LED blinking**

* Charge with USB-C; low battery prevents BLE from working.

**Device not found**

* Ensure Bluetooth is on; keep within **1–2 m**; **press Reset** and retry; make sure no other device is connected.

**Data not updating / visualization broken**

* Did you **press Reset** after the last run?
* Restart Bluetooth and retry.
* Ensure `--side` matches the dataset (left/right) during visualization.

**Missing CSV/PNG files**

* Run from `programs/`; ensure `config/` and `images/` are present.

**Large file size**

* Use a smaller `--duration` (e.g., 30 s).
* Avoid `--save-frames` unless necessary.

---

## Acknowledgment

We gratefully acknowledge **Kai Burian, Chutong Ren, and Arved Strauch** for their foundational work on the wired *Fullsoul* pressure sensing project (*Burian et al., 2024*), which provided the methodological and conceptual basis for this BLE + database extension.

---

## License

This repository is provided for educational and research purposes.
Reproduction or redistribution must retain full attribution to both the original and current authors.

---
