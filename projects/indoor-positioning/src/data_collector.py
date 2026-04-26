"""数据采集模块"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from positioning_service import BeaconSignal, IMUData
import asyncio
from typing import List, Callable
import time

class BLEDataCollector:
    def __init__(self, beacon_ids: List[str] = None):
        self.target_beacon_ids = set(beacon_ids) if beacon_ids else None
        self.beacon_signals = []
        self._running = False
    
    async def start_scan(self, callback: Callable = None, interval: float = 0.1):
        self._running = True
        try:
            from bleak import BleakScanner
            while self._running:
                try:
                    devices = await BleakScanner.discover(timeout=interval)
                    for device in devices:
                        if self.target_beacon_ids is None or device.address in self.target_beacon_ids:
                            signal = BeaconSignal(
                                beacon_id=device.address,
                                rssi=device.rssi,
                                tx_power=device.metadata.get('tx_power', -59),
                                timestamp=time.time()
                            )
                            self.beacon_signals.append(signal)
                            self.beacon_signals = self.beacon_signals[-100:]
                            if callback:
                                callback(signal)
                except Exception as e:
                    print(f"Scan error: {e}")
                await asyncio.sleep(0.05)
        except ImportError:
            print("请安装bleak: pip install bleak")
    
    def stop_scan(self):
        self._running = False
    
    def get_latest_signals(self) -> List:
        latest = {}
        for signal in reversed(self.beacon_signals):
            if signal.beacon_id not in latest:
                latest[signal.beacon_id] = signal
        return list(latest.values())


class IMUDataCollector:
    def __init__(self):
        self.sensor_manager = None
    
    def start_collect(self, callback: Callable):
        pass
    
    def get_imu_data(self) -> IMUData:
        return IMUData(timestamp=time.time())
