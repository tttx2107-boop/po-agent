"""
信标配置文件
定义信标参数和与应急标识的对应关系
"""

# 信标类型与应急标识类型映射
BEACON_MARKER_TYPES = {
    'EXIT_MAIN': '主疏散口标识',
    'EXIT_SIDE': '侧疏散口标识', 
    'EXIT_SIGN': '疏散指示标识（墙装）',
    'EXIT_FLOOR': '疏散指示标识（地装）',
    'FIRE_EXTINGUISHER': '灭火器标识',
    'FIRE_HYDRANT': '消火栓标识',
    'FIRE_ALARM': '手动报警器标识',
    'FIRE_CABINET': '消防柜标识',
    'SAFE_EXIT': '安全出口标识',
    'EMERGENCY_LIGHT': '应急照明标识',
    'CORNER': '角落辅助定位信标'
}

# 信标部署间距建议（米）
BEACON_SPACING = {
    'recommended': 3.0,  # 推荐间距
    'min': 2.0,           # 最小间距
    'max': 5.0,           # 最大间距
}

# RSSI参数
RSSI_CONFIG = {
    'default_tx_power': -59,  # 默认发射功率 dBm
    'env_factor': 2.5,        # 环境因子
    'env_factor_open': 2.0,   # 开放环境
    'env_factor_office': 2.5, # 办公室环境
    'env_factor_complex': 3.0 # 复杂环境
}

# 安装高度建议
INSTALLATION_HEIGHT = {
    'wall': 2.2,   # 墙装高度
    'ceiling': 3.0, # 吊装高度
    'floor_sign': 0.5  # 地装标识高度
}
