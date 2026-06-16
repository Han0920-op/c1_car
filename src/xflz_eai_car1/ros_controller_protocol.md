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
- **校验和**: 从功能字到数据内容最后一个字节的和 (取低 8 位)

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
| 0x08 | PACKET_FUNC_GAMEPAD | 遥控器数据 |
| 0x09 | PACKET_FUNC_IMU | IMU 数据 |
| 0x0D | PACKET_FUNC_RGB | RGB 灯控制 |

### 3.2 电机控制命令详解

#### 命令格式

```
AA 55 03 [LEN] [CMD] [MOTOR_NUM] [DATA...] [CRC]
```

#### 子命令说明

##### 1. 单电机速度控制 (CMD=0x00)

**命令格式**:
```
AA 55 03 06 00 01 SP0 SP1 SP2 SP3 CRC
```

**参数说明**:
- `06`: 数据长度 (6 字节)
- `00`: 子命令 (单电机控制)
- `01`: 电机 ID (1-4)
- `SP0-SP3`: 速度值 (float, 4 字节，小端格式)
  - 速度范围：-1.0 ~ 1.0
  - 正值：正转
  - 负值：反转

**示例**:
- 电机 1 以 0.5 速度正转: `AA 55 03 06 00 01 00 00 00 3F xx`
- 电机 1 以 0.5 速度反转: `AA 55 03 06 00 01 00 00 00 BF xx`

##### 2. 多电机协同控制 (CMD=0x01)

**命令格式**:
```
AA 55 03 [LEN] 01 [NUM] [ID1] [SP0-3] [ID2] [SP0-3] ... CRC
```

**参数说明**:
- `LEN`: 数据长度 = 2 + NUM * 5
- `01`: 子命令 (多电机控制)
- `NUM`: 电机数量 (1-4)
- `ID1`: 电机 1 ID
- `SP0-3`: 电机 1 速度 (float, 4 字节)
- `ID2`: 电机 2 ID
- `SP0-3`: 电机 2 速度 (float, 4 字节)
- ...

**示例**: 控制 4 个电机都以 0.5 速度转动
```
AA 55 03 16 01 04 
   01 00 00 00 3F 
   02 00 00 00 3F 
   03 00 00 00 3F 
   04 00 00 00 3F 
   CRC
```

##### 3. 单电机停止 (CMD=0x02)

**命令格式**:
```
AA 55 03 03 02 01 00 CRC
```

**参数说明**:
- `03`: 数据长度 (3 字节)
- `02`: 子命令 (单电机停止)
- `01`: 电机 ID
- `00`: 保留字节

##### 4. 多电机停止 (CMD=0x03)

**命令格式**:
```
AA 55 03 03 03 MASK 00 CRC
```

**参数说明**:
- `03`: 数据长度 (3 字节)
- `03`: 子命令 (多电机停止)
- `MASK`: 电机掩码
  - bit0: 电机 1
  - bit1: 电机 2
  - bit2: 电机 3
  - bit3: 电机 4
  - 1=停止，0=保持

**示例**: 停止所有电机
```
AA 55 03 03 03 0F 00 CRC
```

## 四、校验和计算

```c
uint8_t calculate_crc(uint8_t *data, uint16_t len)
{
    uint8_t crc = 0;
    for (uint16_t i = 0; i < len; i++) {
        crc += data[i];
    }
    return crc;
}
```

**计算范围**: 从功能字到数据内容最后一个字节

**示例**:
```
AA 55 03 06 00 01 00 00 00 3F
CRC = 03 + 06 + 00 + 01 + 00 + 00 + 00 + 3F = 0x48
```

## 五、完整示例

### 5.1 Python 发送示例

```python
import serial
import struct
import time

# 打开串口
ser = serial.Serial('COM3', 115200, timeout=0.1)

def calculate_crc(data):
    return sum(data) & 0xFF

def send_motor_command(cmd, motor_id, speed):
    """发送单电机控制命令"""
    # 构建数据帧 (不含帧头和 CRC)
    func = 0x03
    data_len = 6
    speed_bytes = struct.pack('<f', speed)  # float 转 4 字节，小端
    
    frame = bytes([
        func,           # 功能字
        data_len,       # 数据长度
        cmd,            # 子命令
        motor_id,       # 电机 ID
        speed_bytes[0], # 速度字节 0
        speed_bytes[1], # 速度字节 1
        speed_bytes[2], # 速度字节 2
        speed_bytes[3], # 速度字节 3
    ])
    
    # 计算 CRC
    crc = calculate_crc(frame)
    
    # 完整帧：帧头 + 数据 + CRC
    full_frame = bytes([0xAA, 0x55]) + frame + bytes([crc])
    
    # 发送
    ser.write(full_frame)
    print(f"Sent: {full_frame.hex()}")

# 示例 1: 电机 1 正转 (速度 0.5)
send_motor_command(0x00, 1, 0.5)
time.sleep(1)

# 示例 2: 电机 1 反转 (速度 -0.5)
send_motor_command(0x00, 1, -0.5)
time.sleep(1)

# 示例 3: 停止电机 1
send_motor_command(0x02, 1, 0)
time.sleep(1)

# 示例 4: 控制 4 个电机
def send_multi_motor(speeds):
    """控制多个电机"""
    motor_num = len(speeds)
    data_len = 2 + motor_num * 5
    
    frame = bytes([
        0x03,           # 功能字
        data_len,       # 数据长度
        0x01,           # 子命令 (多电机)
        motor_num,      # 电机数量
    ])
    
    for i, speed in enumerate(speeds):
        speed_bytes = struct.pack('<f', speed)
        frame += bytes([i + 1])  # 电机 ID
        frame += speed_bytes     # 速度
    
    crc = calculate_crc(frame)
    full_frame = bytes([0xAA, 0x55]) + frame + bytes([crc])
    
    ser.write(full_frame)
    print(f"Sent multi: {full_frame.hex()}")

# 4 个电机都以 0.3 速度转动
send_multi_motor([0.3, 0.3, 0.3, 0.3])
time.sleep(2)

# 停止所有电机
send_multi_motor([0, 0, 0, 0])

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

## 七、速度映射关系

代码中的速度映射：

```c
Vel.TG_IX = (short)(mscc->speed * 1000.0f);
```

- 速度 1.0 → TG_IX = 1000
- 速度 0.5 → TG_IX = 500
- 速度 0.0 → TG_IX = 0
- 速度 -0.5 → TG_IX = -500
- 速度 -1.0 → TG_IX = -1000

**注意**: 实际速度还受 PID 参数和电机最大速度限制。

## 八、其他控制命令

### 8.1 LED 控制 (功能字 0x01)

```
AA 55 01 07 01 LED_ID ON_TL ON_TH OFF_TL OFF_TH REP CRC
```

### 8.2 蜂鸣器控制 (功能字 0x02)

```
AA 55 02 09 FREQ_L FREQ_H ON_TL ON_TH OFF_TL OFF_TH REP_L REP_H CRC
```

### 8.3 RGB 灯控制 (功能字 0x0D)

```
AA 55 0D [LEN] CMD COUNT [IDX R G B]... CRC
```

---

**文档版本**: v1.0  
**更新日期**: 2026-05-19  
**适用固件**: car1_base_controller_client
