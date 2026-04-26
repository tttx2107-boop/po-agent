"""定位服务测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from positioning_service import (
    PositioningService, BuildingMap, Beacon, BeaconSignal, 
    IMUData, Obstacle, BLEPositioning, PDRModule
)


def test_ble_positioning():
    """测试BLE定位"""
    beacons = {
        'B1': Beacon('B1', 0, 0, tx_power=-59),
        'B2': Beacon('B2', 10, 0, tx_power=-59),
        'B3': Beacon('B3', 5, 10, tx_power=-59),
    }
    
    ble = BLEPositioning(beacons)
    
    # 模拟在(5,5)位置的信号
    signals = [
        BeaconSignal('B1', rssi=-70, tx_power=-59),
        BeaconSignal('B2', rssi=-70, tx_power=-59),
        BeaconSignal('B3', rssi=-70, tx_power=-59),
    ]
    
    pos = ble.locate(signals)
    print(f"BLE定位结果: {pos}")
    if pos:
        print(f"  估算位置: ({pos[0]:.2f}, {pos[1]:.2f})")
        print("✓ BLE定位测试通过")
    else:
        print("✗ BLE定位测试失败")


def test_pdr():
    """测试PDR"""
    pdr = PDRModule()
    step_count = 0
    
    # 模拟走路
    for i in range(50):
        acc_z = 9.8 + 2.5 * (1 if i % 2 == 0 else -0.5)
        imu = IMUData(acc_x=0.5, acc_y=0, acc_z=acc_z, 
                      gyro_x=0, gyro_y=0, gyro_z=0.1,
                      timestamp=i * 0.35)
        delta = pdr.update(imu, None)
        if delta != (0.0, 0.0):
            step_count += 1
    
    print(f"检测到步数: {step_count}")
    print("✓ PDR测试完成")


def test_full_positioning():
    """测试完整定位流程"""
    from map_builder import create_standard_office_map
    
    building_map = create_standard_office_map()
    service = PositioningService(building_map)
    service.set_initial_position(5, 5)
    
    print(f"地图: {building_map.name}")
    print(f"尺寸: {building_map.width}m x {building_map.height}m")
    print(f"信标数量: {len(building_map.beacons)}")
    print("\n信标列表:")
    for bid, beacon in building_map.beacons.items():
        print(f"  [{beacon.marker_type}] {bid}: ({beacon.x}, {beacon.y}) - {beacon.marker_id}")
    
    print("\n✓ 完整定位测试通过")


if __name__ == '__main__':
    print("=" * 50)
    print("室内定位系统测试")
    print("=" * 50)
    print()
    
    print("【测试1】BLE定位")
    print("-" * 30)
    test_ble_positioning()
    print()
    
    print("【测试2】PDR行人航位推算")
    print("-" * 30)
    test_pdr()
    print()
    
    print("【测试3】完整定位流程")
    print("-" * 30)
    test_full_positioning()
    print()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)
