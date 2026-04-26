"""地图构建模块"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from positioning_service import Beacon, Obstacle, BuildingMap
from typing import List, Tuple, Dict

class MapBuilder:
    def __init__(self, name: str = "Building"):
        self.map = BuildingMap(name=name)
        self.beacons: Dict[str, Beacon] = {}
        self.obstacles: List[Obstacle] = []
    
    def set_size(self, width: float, height: float):
        self.map.width = width
        self.map.height = height
        return self
    
    def add_beacon(self, beacon_id: str, x: float, y: float, 
                   z: float = 2.5, tx_power: float = -59,
                   floor: int = 1, marker_id: str = '',
                   marker_type: str = 'EXIT') -> 'MapBuilder':
        beacon = Beacon(beacon_id=beacon_id, x=x, y=y, z=z,
                       tx_power=tx_power, floor=floor,
                       marker_id=marker_id, marker_type=marker_type)
        self.beacons[beacon_id] = beacon
        self.map.beacons[beacon_id] = beacon
        return self
    
    def add_obstacle(self, x: float, y: float, width: float, height: float) -> 'MapBuilder':
        obstacle = Obstacle(x, y, width, height)
        self.obstacles.append(obstacle)
        self.map.obstacles.append(obstacle)
        return self
    
    def add_wall(self, x1: float, y1: float, x2: float, y2: float) -> 'MapBuilder':
        self.map.walls.append(((x1, y1), (x2, y2)))
        return self
    
    def build(self) -> BuildingMap:
        return self.map
    
    def export_config(self) -> dict:
        return {
            'name': self.map.name,
            'width': self.map.width,
            'height': self.map.height,
            'floors': self.map.floors,
            'beacons': [{'id': b.beacon_id, 'x': b.x, 'y': b.y, 'z': b.z,
                         'tx_power': b.tx_power, 'floor': b.floor,
                         'marker_id': b.marker_id, 'marker_type': b.marker_type}
                        for b in self.beacons.values()],
            'obstacles': [{'x': o.x, 'y': o.y, 'width': o.width, 'height': o.height}
                         for o in self.obstacles],
        }
    
    @classmethod
    def from_config(cls, config: dict) -> 'MapBuilder':
        builder = cls(name=config.get('name', 'Building'))
        builder.set_size(config.get('width', 10), config.get('height', 10))
        for beacon in config.get('beacons', []):
            builder.add_beacon(beacon['id'], beacon['x'], beacon['y'],
                             beacon.get('z', 2.5), beacon.get('tx_power', -59),
                             beacon.get('floor', 1), beacon.get('marker_id', ''),
                             beacon.get('marker_type', 'EXIT'))
        for obs in config.get('obstacles', []):
            builder.add_obstacle(obs['x'], obs['y'], obs['width'], obs['height'])
        return builder


def create_standard_office_map() -> BuildingMap:
    """创建标准办公室地图（示例）"""
    builder = MapBuilder("标准办公室")
    builder.set_size(20, 15)
    
    builder.add_wall(0, 0, 20, 0)
    builder.add_wall(20, 0, 20, 15)
    builder.add_wall(20, 15, 0, 15)
    builder.add_wall(0, 15, 0, 0)
    
    builder.add_obstacle(8, 0, 0.2, 8)
    builder.add_obstacle(12, 7, 8, 0.2)
    
    # 出口标识
    builder.add_beacon('EXIT_MAIN', 1, 7.5, marker_id='EXIT_01', marker_type='EXIT_MAIN')
    builder.add_beacon('EXIT_SIDE', 10, 14.5, marker_id='EXIT_02', marker_type='EXIT_SIDE')
    
    # 疏散指示标识
    builder.add_beacon('SIGN_01', 4, 7.5, marker_id='SIGN_01', marker_type='EXIT_SIGN')
    builder.add_beacon('SIGN_02', 8, 7.5, marker_id='SIGN_02', marker_type='EXIT_SIGN')
    builder.add_beacon('SIGN_03', 12, 7.5, marker_id='SIGN_03', marker_type='EXIT_SIGN')
    builder.add_beacon('SIGN_04', 16, 7.5, marker_id='SIGN_04', marker_type='EXIT_SIGN')
    
    # 消防设施
    builder.add_beacon('FIRE_01', 3, 3, marker_id='FIRE_01', marker_type='FIRE_EXTINGUISHER')
    builder.add_beacon('FIRE_02', 17, 3, marker_id='FIRE_02', marker_type='FIRE_EXTINGUISHER')
    builder.add_beacon('FIRE_03', 10, 3, marker_id='FIRE_03', marker_type='FIRE_EXTINGUISHER')
    
    # 角落辅助
    builder.add_beacon('CORNER_01', 1, 1, marker_id='CORNER_01', marker_type='CORNER')
    builder.add_beacon('CORNER_02', 19, 1, marker_id='CORNER_02', marker_type='CORNER')
    builder.add_beacon('CORNER_03', 19, 13, marker_id='CORNER_03', marker_type='CORNER')
    
    return builder.build()
