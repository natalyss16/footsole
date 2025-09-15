#!/usr/bin/env python3

"""
Recording 60 seconds (Default)
Usage:
python log_velostat_sensor_h5_BLE_test.py --name FootSole-C3
python log_velostat_sensor_h5_BLE.py --name FootSole-C3

"""

import asyncio
import h5py
import numpy as np
from bleak import BleakClient, BleakScanner
import struct
import time
import datetime
import argparse


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


async def run_logger(name: str, use_left: bool):
    print("Scanning for:", name)
    dev = await BleakScanner.find_device_by_filter(lambda d, ad: d.name == name)
    if not dev:
        print("Device not found"); return
    logger = FootSoleBLELogger(device_name=name, use_left=use_left)
    try:
        async with BleakClient(dev) as cli:
            print(f"Connected. Logging to {logger.h5_path}.")
            await cli.start_notify(UART_TX, logger.on_notify)
            await asyncio.sleep(60)  # Log for 60 seconds
    finally:
        logger.close()
        print("Logger stopped. Data saved to:", logger.h5_path)



# Entry point for BLE logger
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FootSole BLE → HDF5 logger (matches serial format)")
    parser.add_argument('--name', default="FootSole-C3", help='BLE device name')
    parser.add_argument('--left', action='store_true', help='Log left sensor (default: right)')
    parser.add_argument('--duration', type=int, default=60, help='Seconds to log (default: 60)')
    args = parser.parse_args()

    async def main():
        await run_logger(args.name, args.left)
    asyncio.run(main())


