"""
室内定位服务 v1.0
核心模块：BLE定位 + PDR + 融合 + 地图约束
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import time


@dataclass
class Position:
    """定位结果"""
    x: float
    y: float
    floor: int = 1
    confidence: float = 1.0
    mode: str = 'NORMAL'
    timestamp: float = 0


@dataclass
class BeaconSignal:
    """信标信号"""
    beacon_id: str
    rssi: float
    tx_power: float = -59
    timestamp: float = 0


@dataclass
class IMUData:
    """IMU数据"""
    acc_x: float = 0
    acc_y: float = 0
    acc_z: float = 9.8
    gyro_x: float = 0
    gyro_y: float = 0
    gyro_z: float = 0
    timestamp: float = 0


@dataclass
class Beacon:
    """信标设备（与应急标识集成）"""
    beacon_id: str
    x: float
    y: float
    z: float = 2.5
    tx_power: float = -59
    floor: int = 1
    marker_id: str = ''
    marker_type: str = 'EXIT'


class PositioningService:
    """定位服务主类"""
    
    def __init__(self, building_map: 'BuildingMap'):
        self.map = building_map
        self.ble_positioning = BLEPositioning(building_map.beacons)
        self.pdr = PDRModule()
        self.fusion = KalmanFilterFusion()
        self.map_matcher = MapMatcher(building_map)
        self.last_position: Optional[Position] = None
        self.mode = 'NORMAL'
        self.confidence = 1.0
        self.min_beacons = 3
        
    def update(self, beacon_signals: List[BeaconSignal], 
               imu_data: IMUData) -> Position:
        """定位更新（主入口）"""
        # BLE定位
        if len(beacon_signals) >= self.min_beacons:
            ble_position = self.ble_positioning.locate(beacon_signals)
            ble_confidence = self._calculate_ble_confidence(beacon_signals)
        else:
            ble_position = None
            ble_confidence = 0.0
        
        # PDR定位
        pdr_delta = self.pdr.update(imu_data, self.last_position)
        pdr_position = self._apply_pdr_delta(pdr_delta)
        pdr_confidence = self.pdr.get_confidence()
        
        # 融合
        if ble_position:
            fused = self.fusion.fuse(ble_position, ble_confidence,
                                     pdr_position, pdr_confidence)
            self.mode = 'BLE_PDR'
        else:
            fused = pdr_position
            self.mode = 'PDR_ONLY'
            self.confidence = pdr_confidence
        
        # 地图约束
        if not self.map_matcher.is_valid(fused):
            fused = self.map_matcher.snap_to_wall(fused)
            self.confidence *= 0.7
        
        # 保存状态
        self.last_position = Position(
            x=fused[0], y=fused[1],
            floor=self.last_position.floor if self.last_position else 1,
            confidence=self.confidence,
            mode=self.mode,
            timestamp=time.time()
        )
        
        return self.last_position
    
    def _apply_pdr_delta(self, delta) -> Tuple[float, float]:
        if self.last_position:
            return (self.last_position.x + delta[0],
                    self.last_position.y + delta[1])
        return (delta[0], delta[1])
    
    def _calculate_ble_confidence(self, signals: List[BeaconSignal]) -> float:
        if not signals:
            return 0.0
        base = 0.7 + min(len(signals) - 3, 2) * 0.1
        rssi_values = [s.rssi for s in signals]
        std = np.std(rssi_values)
        stability = max(0, 1 - std / 10)
        return min(base * (0.5 + 0.5 * stability), 1.0)
    
    def set_initial_position(self, x: float, y: float, floor: int = 1):
        """设置初始位置"""
        self.last_position = Position(x=x, y=y, floor=floor,
                                       confidence=1.0, mode='INITIAL',
                                       timestamp=time.time())
        self.pdr.reset()


class BLEPositioning:
    """BLE定位模块 - 改进的三边定位"""
    
    def __init__(self, beacons: Dict[str, Beacon]):
        self.beacons = beacons
        self.env_factor = 2.5
    
    def locate(self, signals: List[BeaconSignal]) -> Optional[Tuple[float, float]]:
        """定位入口"""
        valid_signals = [s for s in signals if s.beacon_id in self.beacons]
        if len(valid_signals) < 3:
            return None
        
        positions, distances = [], []
        for signal in valid_signals:
            beacon = self.beacons[signal.beacon_id]
            d = self._rssi_to_distance(signal.rssi, beacon.tx_power)
            d = max(0.5, min(d, 15))  # 限制距离范围
            positions.append((beacon.x, beacon.y))
            distances.append(d)
        
        return self._weighted_trilateration(positions, distances)
    
    def _rssi_to_distance(self, rssi: float, tx_power: float = -59) -> float:
        """RSSI转距离"""
        if rssi >= 0:
            return 0.5
        return 10 ** ((tx_power - rssi) / (10 * self.env_factor))
    
    def _weighted_trilateration(self, positions: List, distances: List) -> Tuple[float, float]:
        """加权三边定位"""
        if len(positions) < 3:
            return None
        
        # 简单加权平均
        weights = []
        for d in distances:
            if d > 0:
                weights.append(1.0 / (d ** 2))
            else:
                weights.append(1.0)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return None
        
        x = sum(p[0] * w for p, w in zip(positions, weights)) / total_weight
        y = sum(p[1] * w for p, w in zip(positions, weights)) / total_weight
        
        return (float(x), float(y))


class PDRModule:
    """PDR行人航位推算"""
    
    def __init__(self):
        self.step_length = 0.7
        self.heading = 0.0
        self.step_threshold = 1.0
        self.step_count = 0
        self.last_step_time = 0
        self.last_acc_magnitude = 0
        self.bias_x = 0.0
        self.bias_y = 0.0
        
    def update(self, imu_data: IMUData, 
               last_position: Optional[Position]) -> Tuple[float, float]:
        """PDR更新"""
        acc_mag = np.sqrt(imu_data.acc_x**2 + imu_data.acc_y**2 + imu_data.acc_z**2)
        acc_mag = abs(acc_mag - 9.8)  # 相对重力加速度
        
        is_step = self._detect_step(acc_mag, imu_data.timestamp)
        
        if is_step:
            self.step_count += 1
            self._update_heading(imu_data)
            delta_x = self.step_length * np.sin(self.heading) - self.bias_x
            delta_y = self.step_length * np.cos(self.heading) - self.bias_y
            return (delta_x, delta_y)
        return (0.0, 0.0)
    
    def _detect_step(self, acc_magnitude: float, timestamp: float) -> bool:
        """步态检测"""
        if timestamp - self.last_step_time < 200:
            return False
        if acc_magnitude > self.step_threshold and self.last_acc_magnitude < acc_magnitude:
            self.last_step_time = timestamp
            return True
        self.last_acc_magnitude = acc_magnitude
        return False
    
    def _update_heading(self, imu_data: IMUData):
        """更新航向角"""
        self.heading += imu_data.gyro_z * 0.02
        self.heading = self.heading % (2 * np.pi)
    
    def get_confidence(self) -> float:
        """获取PDR置信度"""
        decay = 0.98 ** min(self.step_count, 50)
        return max(0.3, decay)
    
    def reset(self):
        """重置"""
        self.step_count = 0
        self.heading = 0.0


class KalmanFilterFusion:
    """卡尔曼滤波融合"""
    
    def __init__(self):
        self.x = np.array([0.0, 0.0, 0.0, 0.0])
        self.P = np.eye(4) * 100
        self.Q = np.diag([0.01, 0.01, 0.01, 0.01])
        self.R_ble = 1.0
        self.R_pdr = 5.0
    
    def fuse(self, ble_pos: Optional[Tuple], ble_conf: float,
             pdr_pos: Tuple, pdr_conf: float) -> Tuple[float, float]:
        """融合BLE和PDR定位结果"""
        self.R_ble = 10.0 / (ble_conf + 0.1)
        self.R_pdr = 10.0 / (pdr_conf + 0.1)
        
        if ble_pos:
            z = np.array([ble_pos[0], ble_pos[1]])
            H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
            R = np.eye(2) * self.R_ble
            self._update(z, H, R)
        
        self._predict()
        return (float(self.x[0]), float(self.x[1]))
    
    def _predict(self):
        """预测步骤"""
        F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.Q
    
    def _update(self, z: np.ndarray, H: np.ndarray, R: np.ndarray):
        """更新步骤"""
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I = np.eye(len(self.x))
        self.P = (I - K @ H) @ self.P


class MapMatcher:
    """地图匹配"""
    
    def __init__(self, building_map: 'BuildingMap'):
        self.map = building_map
    
    def is_valid(self, position: Tuple[float, float]) -> bool:
        """检查位置是否有效"""
        x, y = position
        if x < 0 or x > self.map.width or y < 0 or y > self.map.height:
            return False
        for obstacle in self.map.obstacles:
            if obstacle.contains(x, y):
                return False
        return True
    
    def snap_to_wall(self, position: Tuple[float, float]) -> Tuple[float, float]:
        """穿墙修正"""
        x, y = position
        for obstacle in self.map.obstacles:
            if obstacle.contains(x, y):
                edges = obstacle.get_edges()
                min_dist = float('inf')
                best_point = position
                for edge in edges:
                    closest = self._closest_point_on_segment((x, y), edge[0], edge[1])
                    dist = np.sqrt((closest[0] - x)**2 + (closest[1] - y)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_point = closest
                return best_point
        return (max(0, min(x, self.map.width)), max(0, min(y, self.map.height)))
    
    def _closest_point_on_segment(self, p: Tuple, a: Tuple, b: Tuple) -> Tuple:
        """点到线段最近点"""
        ax, ay = a
        bx, by = b
        px, py = p
        ab = (bx - ax, by - ay)
        ap = (px - ax, py - ay)
        t = max(0, min(1, (ap[0]*ab[0] + ap[1]*ab[1]) / (ab[0]**2 + ab[1]**2 + 1e-10)))
        return (ax + t * ab[0], ay + t * ab[1])


class Obstacle:
    """障碍物"""
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.center = (x + width/2, y + height/2)
    
    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
    
    def get_edges(self):
        return [
            ((self.x, self.y), (self.x + self.width, self.y)),
            ((self.x + self.width, self.y), (self.x + self.width, self.y + self.height)),
            ((self.x + self.width, self.y + self.height), (self.x, self.y + self.height)),
            ((self.x, self.y + self.height), (self.x, self.y)),
        ]


@dataclass
class BuildingMap:
    """建筑地图"""
    name: str = "Building"
    width: float = 10.0
    height: float = 10.0
    beacons: Dict[str, Beacon] = field(default_factory=dict)
    obstacles: List[Obstacle] = field(default_factory=list)
    floors: int = 1
    walls: List[Tuple[Tuple[float, float], Tuple[float, float]]] = field(default_factory=list)
