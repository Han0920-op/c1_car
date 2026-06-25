# 串口通信协议说明

## 一、硬件信息

- **串口**: USART2
- **TX**: PA9
- **RX**: PA10
- **波特率**: 1000000 (默认)
- **数据位**: 8
- **停止位**: 1
- **校验位**: 无

## 二、通信协议格式

### 2.1 数据帧结构

```
+------------+------------+----------+----------+----------+------------+
| 起始字节 1 | 起始字节 2 | 功能字   | 数据长度 | 数据内容 | 校验和     |
|   0xAA     |   0x55     |  1 字节  |  1 字节  |  N 字节  |   1 字节   |
+------------+------------+----------+----------+----------+------------+
```

### 2.2 协议说明

- **帧头**: `0xAA 0x55` (固定 2 字节)
- **功能字**: 标识命令类型 (1 字节)
- **数据长度**: 数据内容的字节数 (1 字节)
- **数据内容**: 实际命令数据 (0-255 字节)
- **校验和**: CRC8 查表法, 计算范围从功能字到数据内容最后一个字节 (与 STM32 `checksum.c::checksum_crc8` 一致)

## 三、电机控制命令

### 3.1 功能字定义

| 功能字 | 名称 | 说明 |
|--------|------|------|
| 0x00 | PACKET_FUNC_SYS | 系统控制 |
| 0x01 | PACKET_FUNC_LED | LED 控制 |
| 0x02 | PACKET_FUNC_BUZZER | 蜂鸣器控制 |
| **0x03** | **PACKET_FUNC_MOTOR** | **电机控制** |
| 0x04 | PACKET_FUNC_PWM_SERVO | PWM 舵机控制 |
| 0x05 | PACKET_FUNC_BUS_SERVO | 总线舵机控制 |
| 0x06 | PACKET_FUNC_KEY | 按键事件 |
| 0x07 | PACKET_FUNC_IMU | IMU 数据 (BMI088) |
| 0x08 | PACKET_FUNC_GAMEPAD | 遥控器数据 |
| 0x09 | PACKET_FUNC_SBUS | SBUS 接收机 |
| 0x0A | PACKET_FUNC_OLED | OLED 显示 |
| 0x0B | PACKET_FUNC_RGB | RGB 灯控制 |

### 3.2 电机控制命令详解

#### 命令格式

```
AA 55 03 [LEN] [CMD] [MOTOR_NUM] [DATA...] [CRC]
```

#### 子命令说明

##### 1. 单电机速度控制 (CMD=0x00)

**命令格式**:
```
AA 55 03 06 00 ID SP0 SP1 SP2 SP3 CRC
```

**参数说明**:
- `06`: 数据长度 (6 字节)
- `00`: 子命令 (单电机控制)
- `ID`: 电机 ID (0~3, 对应 M1~M4, STM32 检查 `id < 4`)
- `SP0-SP3`: 速度值 (float, 4 字节，小端格式)
  - 速度单位: RPM (转/分), 实际范围约 ±1270 (受 STM32 `R_VX_LIMIT=1500` 限制)
  - 正值：正转
  - 负值：反转
  - **注意**: 不是 -1.0~1.0 归一化值, 直接作为 PID 目标转速

**示例**:
- 电机 0 (M1) 以 200 RPM 正转: `AA 55 03 06 00 00 00 00 48 43 CRC`
- 电机 0 (M1) 以 200 RPM 反转: `AA 55 03 06 00 00 00 00 48 C3 CRC`

##### 2. 多电机协同控制 (CMD=0x01)

**命令格式**:
```
AA 55 03 [LEN] 01 [NUM] [ID1] [SP0-3] [ID2] [SP0-3] ... CRC
```

**参数说明**:
- `LEN`: 数据长度 = 2 + NUM * 5
- `01`: 子命令 (多电机控制)
- `NUM`: 电机数量 (1-4)
- `ID1`: 电机 1 ID (0~3)
- `SP0-3`: 电机 1 速度 (float, 4 字节, RPM)
- `ID2`: 电机 2 ID (0~3)
- `SP0-3`: 电机 2 速度 (float, 4 字节, RPM)
- ...

**示例**: 控制 4 个电机都以 200 RPM 转动
```
AA 55 03 16 01 04
   00 00 00 48 43     # ID=0, +200 RPM
   01 00 00 48 C3     # ID=1, -200 RPM
   02 00 00 48 43     # ID=2, +200 RPM
   03 00 00 48 C3     # ID=3, -200 RPM
   CRC
```

##### 3. 单电机停止 (CMD=0x02)

**命令格式**:
```
AA 55 03 02 02 ID CRC
```

**参数说明**:
- `02`: 数据长度 (2 字节)
- `02`: 子命令 (单电机停止)
- `ID`: 电机 ID (0~3)

##### 4. 多电机停止 (CMD=0x03)

**命令格式**:
```
AA 55 03 02 03 MASK CRC
```

**参数说明**:
- `02`: 数据长度 (2 字节)
- `03`: 子命令 (多电机停止)
- `MASK`: 电机掩码
  - bit0: 电机 0 (M1)
  - bit1: 电机 1 (M2)
  - bit2: 电机 2 (M3)
  - bit3: 电机 3 (M4)
  - 1=停止，0=保持

**示例**: 停止所有电机
```
AA 55 03 02 03 0F CRC
```

## 四、校验和计算

**算法**: CRC8 查表法 (与 STM32 `checksum.c::checksum_crc8` 一致, 非简单求和)

```c
/* CRC8 查表 (源自 STM32 checksum.c) */
static const uint8_t crc8_table[256] = {
    0, 94,188,226, 97, 63,221,131,194,156,126, 32,163,253, 31, 65,
    157,195, 33,127,252,162, 64, 30, 95,  1,227,189, 62, 96,130,220,
    /* ... 完整 256 项见 STM32 checksum.c ... */
};

uint8_t checksum_crc8(const uint8_t *buf, uint16_t len)
{
    uint8_t check = 0;
    while (len--) {
        check = crc8_table[check ^ (*buf++)];
    }
    return check;
}
```

**计算范围**: 从功能字到数据内容最后一个字节

**示例**:
```
帧: AA 55 03 06 00 00 00 00 48 43 [CRC]
CRC = checksum_crc8([03, 06, 00, 00, 00, 00, 48, 43]) = 0x9C
完整: AA 55 03 06 00 00 00 00 48 43 9C
```

> **警告**: 错误使用求和算法会导致 STM32 拒收所有命令。

## 五、完整示例

### 5.1 Python 发送示例

```python
import serial
import struct
import time

# CRC8 查表 (与 STM32 checksum.c::checksum_crc8 一致)
_CRC8_TABLE = [
    0, 94,188,226, 97, 63,221,131,194,156,126, 32,163,253, 31, 65,
    157,195, 33,127,252,162, 64, 30, 95,  1,227,189, 62, 96,130,220,
    35,125,159,193, 66, 28,254,160,225,191, 93,  3,128,222, 60, 98,
    190,224,  2, 92,223,129, 99, 61,124, 34,192,158, 29, 67,161,255,
    70, 24,250,164, 39,121,155,197,132,218, 56,102,229,187, 89,  7,
    219,133,103, 57,186,228,  6, 88, 25, 71,165,251,120, 38,196,154,
    101, 59,217,135,  4, 90,184,230,167,249, 27, 69,198,152,122, 36,
    248,166, 68, 26,153,199, 37,123, 58,100,134,216, 91,  5,231,185,
    140,210, 48,110,237,179, 81, 15, 78, 16,242,172, 47,113,147,205,
    17, 79,173,243,112, 46,204,146,211,141,111, 49,178,236, 14, 80,
    175,241, 19, 77,206,144,114, 44,109, 51,209,143, 12, 82,176,238,
    50,108,142,208, 83, 13,239,177,240,174, 76, 18,145,207, 45,115,
    202,148,118, 40,171,245, 23, 73,  8, 86,180,234,105, 55,213,139,
    87,  9,235,181, 54,104,138,212,149,203, 41,119,244,170, 72, 22,
    233,183, 85, 11,136,214, 52,106, 43,117,151,201, 74, 20,246,168,
    116, 42,200,150, 21, 75,169,247,182,232, 10, 84,215,137,107, 53
]

def calculate_crc(data):
    """CRC8 查表法 (与 STM32 一致, 非简单求和)"""
    check = 0
    for b in data:
        check = _CRC8_TABLE[check ^ b]
    return check & 0xFF

def send_motor_command(cmd, motor_id, speed_rpm):
    """发送单电机控制命令
    motor_id: 0~3 (M1~M4)
    speed_rpm: 目标转速 RPM, 范围约 ±1270
    """
    func = 0x03
    data_len = 6
    speed_bytes = struct.pack('<f', float(speed_rpm))

    frame = bytes([func, data_len, cmd, motor_id,
                   speed_bytes[0], speed_bytes[1],
                   speed_bytes[2], speed_bytes[3]])
    crc = calculate_crc(frame)
    full_frame = bytes([0xAA, 0x55]) + frame + bytes([crc])
    ser.write(full_frame)
    print(f"Sent: {full_frame.hex()}")

# 打开串口 (波特率 1000000)
ser = serial.Serial('/dev/ttyUSB0', 1000000, timeout=0.1)

# 示例 1: 电机 0 (M1) 正转 200 RPM
send_motor_command(0x00, 0, 200.0)
time.sleep(1)

# 示例 2: 电机 0 (M1) 反转 200 RPM
send_motor_command(0x00, 0, -200.0)
time.sleep(1)

# 示例 3: 停止电机 0 (CMD=0x02)
send_motor_command(0x02, 0, 0)
time.sleep(0.5)

# 示例 4: 控制 4 个电机 (CMD=0x01)
def send_multi_motor(speeds):
    """speeds: 4 个电机的 RPM 列表, 电机 ID 0~3"""
    motor_num = len(speeds)
    data_len = 2 + motor_num * 5
    frame = bytes([0x03, data_len, 0x01, motor_num])
    for i, speed in enumerate(speeds):
        frame += bytes([i]) + struct.pack('<f', float(speed))
    crc = calculate_crc(frame)
    full_frame = bytes([0xAA, 0x55]) + frame + bytes([crc])
    ser.write(full_frame)
    print(f"Sent multi: {full_frame.hex()}")

# 4 个电机各 200 RPM (原地旋转: 左前+右后正转, 右前+左后反转)
send_multi_motor([200.0, -200.0, 200.0, -200.0])
time.sleep(2)

# 停止所有电机 (CMD=0x03, MASK=0x0F)
stop_frame = bytes([0xAA, 0x55, 0x03, 0x02, 0x03, 0x0F])
stop_frame += bytes([calculate_crc(stop_frame[2:])])
ser.write(stop_frame)

ser.close()
```




### 6.3 常见问题

**Q1: 电机不转**
- 检查电源供电是否正常
- 检查电机驱动使能信号
- 检查 TIM7 是否已启动

**Q2: 通信无响应**
- 检查串口连接 (TX/RX 是否接反)
- 检查波特率是否匹配
- 检查校验和是否正确

**Q3: 电机转动方向相反**
- 调整速度值为负数
- 或交换电机相线

## 七、速度单位说明

### 7.1 直接控制模式 (CMD=0x00/0x01/0x04)

`kinematics_set_raw_wheel(id, speed)` 中 `speed` 直接作为 PID 目标值 `Wheel_*.TG`：

```c
/* STM32 kinematics.c (raw wheel 模式) */
Wheel_A.TG = wheel_raw_tg[0];   /* ← speed 直接赋值 */
Wheel_A.PWM = speed_pid_ctl_a(Wheel_A.TG, Wheel_A.RT);  /* PID 计算 PWM */
```

- **单位**: RPM (转/分), 经编码器反馈与 `MEC_WHEEL_SCALE` 换算后比对
- **有效范围**: 约 ±1270 RPM (受 `R_VX_LIMIT=1500` 间接限制)
- **典型值**: 100~300 RPM 用于测试, 1000+ 用于高速
- **注意**: 不是 -1.0~1.0 归一化值

### 7.2 整体速度模式 (VX/VY/VW, 仅手柄/上位机协议)

`Vel.TG_IX/IY/IW` 是带放大倍数的速度积分目标 (用于手柄控制)：

```c
/* STM32 app_gamepad.c 中, 手柄杆值 *10 后送入 TG_IX */
Vel.TG_IX = (128 - (short)ps2_buf[4]) * 10;
```

- 手柄杆值范围: -128~+127 → TG_IX 范围: -1280~+1270
- 上位机直接控制时, TG_IX 单位是 mm/s 的 1000 倍
- 经过 `Vel.TG_FX = Vel.TG_IX / 1000.0` 转换为 m/s 后送入麦轮运动学

**注意**: 直接通过电机命令 (CMD=0x00/0x01/0x04) 不走这条路径, 单位是 RPM。

## 八、其他控制命令

### 8.1 LED 控制 (功能字 0x01)

```
AA 55 01 07 01 LED_ID ON_TL ON_TH OFF_TL OFF_TH REP CRC
```

### 8.2 蜂鸣器控制 (功能字 0x02)

```
AA 55 02 09 FREQ_L FREQ_H ON_TL ON_TH OFF_TL OFF_TH REP_L REP_H CRC
```

### 8.3 RGB 灯控制 (功能字 0x0B)

```
AA 55 0B [LEN] CMD COUNT [IDX R G B]... CRC
```

---

**文档版本**: v1.0  
**更新日期**: 2026-05-19  
**适用固件**: car1_base_controller_client
