#!/usr/bin/env python3
"""
直接通过串口控制机械臂，使用 PWM 脉冲值（500~2500，1500为中位）。

使用前请先停止 bringup：
  Ctrl+C 停掉 ros2 launch car1_arm_controller arm_controller.launch.py

然后运行：
  python3 test_servo_direct.py
"""
import os
import serial
import struct
import time
import yaml

# --- 配置 ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 1000000

# 舵机范围
SERVO_MIN = 500
SERVO_MAX = 2500
SERVO_MID = 1500

# 默认工作状态 (J0~J5)
WORK_POSITION = [1500, 1100, 2200, 1850, 1500, 1500]

# CRC8 查表（与 board_sdk.py 一致）
_CRC8_TABLE = [
    0, 94, 188, 226, 97, 63, 221, 131, 194, 156, 126, 32, 163, 253, 31, 65,
    157, 195, 33, 127, 252, 162, 64, 30, 95, 1, 227, 189, 62, 96, 130, 220,
    35, 125, 159, 193, 66, 28, 254, 160, 225, 191, 93, 3, 128, 222, 60, 98,
    190, 224, 2, 92, 223, 129, 99, 61, 124, 34, 192, 158, 29, 67, 161, 255,
    70, 24, 250, 164, 39, 121, 155, 197, 132, 218, 56, 102, 229, 187, 89, 7,
    219, 133, 103, 57, 186, 228, 6, 88, 25, 71, 165, 251, 120, 38, 196, 154,
    101, 59, 217, 135, 4, 90, 184, 230, 167, 249, 27, 69, 198, 152, 122, 36,
    248, 166, 68, 26, 153, 199, 37, 123, 58, 100, 134, 216, 91, 5, 231, 185,
    140, 210, 48, 110, 237, 179, 81, 15, 78, 16, 242, 172, 47, 113, 147, 205,
    17, 79, 173, 243, 112, 46, 204, 146, 211, 141, 111, 49, 178, 236, 14, 80,
    175, 241, 19, 77, 206, 144, 114, 44, 109, 51, 209, 143, 12, 82, 176, 238,
    50, 108, 142, 208, 83, 13, 239, 177, 240, 174, 76, 18, 145, 207, 45, 115,
    202, 148, 118, 40, 171, 245, 23, 73, 8, 86, 180, 234, 105, 55, 213, 139,
    87, 9, 235, 181, 54, 104, 138, 212, 149, 203, 41, 119, 244, 170, 72, 22,
    233, 183, 85, 11, 136, 214, 52, 106, 43, 117, 151, 201, 74, 20, 246, 168,
    116, 42, 200, 150, 21, 75, 169, 247, 182, 232, 10, 84, 215, 137, 107, 53
]


def crc8(data):
    check = 0
    for b in data:
        check = _CRC8_TABLE[check ^ b]
    return check & 0xFF


def send_packet(ser, func, data):
    buf = [0xAA, 0x55, func, len(data)] + data
    checksum = crc8(bytes(buf[2:]))
    buf.append(checksum)
    ser.write(bytes(buf))


def recv_packet(ser, timeout=1.0, expected_func=None):
    """
    接收一个完整的数据包。
    如果指定 expected_func，会跳过其他功能字的包，直到收到期望的包或超时。
    返回: (func, data) 或 None（超时/校验失败）
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        state = 0  # 0:AA, 1:55, 2:func, 3:len, 4:data, 5:crc
        frame = []
        data_len = 0
        recv_count = 0

        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                b = ord(ser.read(1))

                if state == 0:  # 等待 0xAA
                    if b == 0xAA:
                        state = 1
                elif state == 1:  # 等待 0x55
                    if b == 0x55:
                        state = 2
                    else:
                        state = 0
                elif state == 2:  # 功能码
                    frame = [b]
                    state = 3
                elif state == 3:  # 数据长度
                    data_len = b
                    frame.append(b)
                    recv_count = 0
                    if data_len == 0:
                        state = 5  # 无数据，直接等待CRC
                    else:
                        state = 4
                elif state == 4:  # 数据
                    frame.append(b)
                    recv_count += 1
                    if recv_count >= data_len:
                        state = 5
                elif state == 5:  # CRC校验
                    expected_crc = crc8(bytes(frame))
                    if expected_crc == b:
                        func = frame[0]
                        data = bytes(frame[2:]) if len(frame) > 2 else b''

                        # 如果指定了期望的功能字，且当前包不匹配，继续读取下一个包
                        if expected_func is not None and func != expected_func:
                            state = 0  # 重新开始，读取下一个包
                            continue

                        return func, data
                    # CRC失败，重新开始
                    state = 0
                    break
            else:
                time.sleep(0.001)

    return None


def move_servos(ser, positions, duration=2.0):
    """
    控制舵机位置。
    positions: [[servo_id, pwm], ...] pwm 范围 500~2500
    duration: 运动时间（秒）
    """
    duration_ms = int(duration * 1000)
    clamped = []
    for servo_id, pwm in positions:
        pwm = max(SERVO_MIN, min(SERVO_MAX, int(pwm)))
        clamped.append([servo_id, pwm])

    data = [0x01, duration_ms & 0xFF, (duration_ms >> 8) & 0xFF, len(clamped)]
    for servo_id, pwm in clamped:
        data.extend(struct.pack("<BH", servo_id, pwm))
    send_packet(ser, 0x05, data)

    print(f"  {'ID':<4} {'PWM':>6}")
    print(f"  {'-'*12}")
    for servo_id, pwm in clamped:
        print(f"  {servo_id:<4} {pwm:>6}")


def move_arm(ser, j1, j2, j3, j4, j5, duration=2.0):
    """控制5个关节，参数为PWM值，ID 0~4"""
    move_servos(ser, [[0, j1], [1, j2], [2, j3], [3, j4], [4, j5]], duration)


def set_gripper(ser, pwm, duration=1.0):
    """控制夹爪，ID=5"""
    move_servos(ser, [[5, pwm]], duration)


def read_servo_position(ser, servo_id, debug=False):
    """
    读取单个舵机的当前位置。
    返回: PWM值(500~2500) 或 None（失败）
    """
    # 清空接收缓冲区
    ser.reset_input_buffer()
    time.sleep(0.05)  # 等待缓冲区清空

    # 发送读取位置命令 (func=0x05, cmd=0x05, servo_id)
    send_packet(ser, 0x05, [0x05, servo_id])

    if debug:
        print(f"  [DEBUG] 已发送读取命令给舵机 {servo_id}")
        time.sleep(0.05)
        print(f"  [DEBUG] 缓冲区字节数: {ser.in_waiting}")

    # 接收响应，只接收功能字为0x05的包（过滤掉IMU等其他数据）
    result = recv_packet(ser, timeout=0.5, expected_func=0x05)

    if result:
        func, data = result
        if debug:
            print(f"  [DEBUG] 收到舵机数据包: func=0x{func:02X}, data_len={len(data)}, data={data.hex()}")

        if len(data) >= 4:
            # 格式: cmd(1) + servo_id(1) + status(1) + position(2)
            cmd, sid, status, pos = struct.unpack("<BBBH", data[:5])
            if debug:
                print(f"  [DEBUG] 解析: cmd=0x{cmd:02X}, servo_id={sid}, status={status}, pos={pos}")
            if status == 0:  # 0表示成功
                return pos
        elif debug:
            print(f"  [DEBUG] 数据长度不足")
    elif debug:
        print(f"  [DEBUG] 接收超时或未收到功能字0x05的响应")

    return None


def read_all_servos(ser, debug=False):
    """读取机械臂5个关节的位置（跳过夹爪ID=5）"""
    print("\n读取舵机位置...")
    print(f"  {'ID':<4} {'PWM':>6}")
    print(f"  {'-'*12}")

    positions = []
    for servo_id in range(5):  # 只读取0-4（机械臂5个关节）
        pos = read_servo_position(ser, servo_id, debug=debug)
        if pos is not None:
            positions.append((servo_id, pos))
            print(f"  {servo_id:<4} {pos:>6}")
        else:
            print(f"  {servo_id:<4} {'失败':>6}")
        time.sleep(0.05)

    return positions


def go_work(ser, duration=2.0):
    """移动到工作位置"""
    positions = [[i, pwm] for i, pwm in enumerate(WORK_POSITION)]
    move_servos(ser, positions, duration)


def go_home(ser, duration=2.0):
    """所有关节回中位"""
    move_servos(ser, [[0, 1500], [1, 1500], [2, 1500], [3, 1500], [4, 1500], [5, 1500]], duration)


# ============================================================
# 动作序列（在交互模式中调试好后粘贴到这里）
# ============================================================
ACTIONS = [
    ('home', None, '归零状态'),
    ('arm', [1500, 1100, 2200, 1850, 1500], '工作状态')
]


def interactive_mode(ser):
    """交互模式：手动输入PWM值调试动作"""
    print("=" * 50)
    print("=== 交互调试模式 ===")
    print("=" * 50)
    print("命令:")
    print("  j1 j2 j3 j4 j5   - 5个关节PWM值(500~2500)")
    print("  g <pwm>           - 夹爪PWM值")
    print("  s <id> <pwm>      - 单个舵机控制，如: s 2 1200")
    print("  r <id>            - 读取单个舵机位置，如: r 2")
    print("  r <id> -d         - 读取舵机位置（带调试信息），如: r 2 -d")
    print("  read              - 读取所有舵机位置")
    print("  read -d           - 读取所有舵机位置（带调试信息）")
    print("  home              - 全部回中位(1500)")
    print("  work              - 进入默认工作状态")
    print("  play              - 回放已保存的动作")
    print("  yaml              - 导出为YAML文件(action_player格式)")
    print("  list              - 查看已保存的动作")
    print("  del <n>           - 删除第n个已保存的动作")
    print("  quit              - 退出")
    print("-" * 50)

    actions = []

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        if cmd == 'quit':
            break
        elif cmd == 'home':
            go_home(ser, duration=2.0)
            time.sleep(2.5)
            name = input("  保存? 输入名称(回车跳过): ").strip()
            if name:
                actions.append(('home', None, name))
                print(f"  已保存: {name}")
        elif cmd == 'work':
            pos = [[i, pwm] for i, pwm in enumerate(WORK_POSITION)]
            move_servos(ser, pos, duration=2.0)
            time.sleep(2.5)
            name = input("  保存? 输入名称(回车跳过): ").strip()
            if name:
                actions.append(('arm', WORK_POSITION[:5], name))
                print(f"  已保存: {name}")
        elif cmd.startswith('g '):
            try:
                pwm = int(cmd[2:])
                set_gripper(ser, pwm)
                time.sleep(1.5)
                name = input("  保存? 输入名称(回车跳过): ").strip()
                if name:
                    actions.append(('gripper', pwm, name))
                    print(f"  已保存: {name}")
            except ValueError:
                print("  格式错误，示例: g 1800")
        elif cmd.startswith('s '):
            parts = cmd[2:].split()
            if len(parts) == 2:
                try:
                    sid = int(parts[0])
                    pwm = int(parts[1])
                    move_servos(ser, [[sid, pwm]], duration=1.0)
                    time.sleep(1.5)
                except ValueError:
                    print("  格式错误，示例: s 2 1200")
            else:
                print("  格式错误，示例: s 2 1200")
        elif cmd.startswith('r '):
            parts = cmd[2:].split()
            if len(parts) >= 1:
                try:
                    sid = int(parts[0])
                    debug = len(parts) > 1 and parts[1] == '-d'
                    pos = read_servo_position(ser, sid, debug=debug)
                    if pos is not None:
                        print(f"  舵机 {sid} 当前位置: {pos}")
                    else:
                        print(f"  读取舵机 {sid} 失败")
                except ValueError:
                    print("  格式错误，示例: r 2 或 r 2 -d")
            else:
                print("  格式错误，示例: r 2 或 r 2 -d")
        elif cmd == 'read' or cmd == 'read -d':
            debug = '-d' in cmd
            read_all_servos(ser, debug=debug)
        elif cmd == 'play':
            if not actions:
                print("  没有已保存的动作")
            else:
                print(f"  回放 {len(actions)} 个动作...")
                for act in actions:
                    print(f"  [{act[2]}]")
                    if act[0] == 'arm':
                        move_arm(ser, *act[1], duration=2.0)
                        time.sleep(3.0)
                    elif act[0] == 'gripper':
                        set_gripper(ser, act[1])
                        time.sleep(2.0)
                    elif act[0] == 'home':
                        go_home(ser, duration=2.0)
                        time.sleep(3.0)
                print("  回放完成")
        elif cmd == 'yaml':
            export_yaml(actions)
        elif cmd == 'list':
            if not actions:
                print("  没有已保存的动作")
            else:
                for i, act in enumerate(actions):
                    if act[0] == 'arm':
                        print(f"  {i+1}. [{act[2]}] arm: {act[1]}")
                    elif act[0] == 'gripper':
                        print(f"  {i+1}. [{act[2]}] gripper: {act[1]}")
                    elif act[0] == 'home':
                        print(f"  {i+1}. [{act[2]}] home")
        elif cmd.startswith('del '):
            try:
                idx = int(cmd[4:]) - 1
                if 0 <= idx < len(actions):
                    removed = actions.pop(idx)
                    print(f"  已删除: {removed[2]}")
                else:
                    print(f"  序号超出范围 (1~{len(actions)})")
            except ValueError:
                print("  格式错误，示例: del 2")
        else:
            parts = cmd.replace(',', ' ').split()
            if len(parts) == 5:
                try:
                    pwms = [int(x) for x in parts]
                    move_arm(ser, *pwms, duration=2.0)
                    time.sleep(2.5)
                    name = input("  保存? 输入名称(回车跳过): ").strip()
                    if name:
                        actions.append(('arm', pwms, name))
                        print(f"  已保存: {name}")
                except ValueError:
                    print("  格式错误，示例: 1500 1000 1000 900 1500")
            else:
                print("  无法识别，可用命令:")
                print("    1500 1000 1000 900 1500  (5个关节PWM)")
                print("    s 2 1200                 (单个舵机: ID PWM)")
                print("    r 2                      (读取舵机: ID)")
                print("    r 2 -d                   (读取舵机带调试)")
                print("    read                     (读取全部舵机)")
                print("    read -d                  (读取全部舵机带调试)")
                print("    g 1800                   (夹爪PWM)")
                print("    home / work / play / yaml / list / del / quit")

    return actions


def export_actions(actions):
    """将动作序列导出"""
    if not actions:
        return
    print("\n" + "=" * 50)
    print("=== 导出动作序列 ===")
    print("=" * 50)
    print("\n将以下内容替换脚本中的 ACTIONS:\n")
    print("ACTIONS = [")
    for act in actions:
        if act[0] == 'arm':
            print(f"    ('arm', {act[1]}, '{act[2]}'),")
        elif act[0] == 'gripper':
            print(f"    ('gripper', {act[1]}, '{act[2]}'),")
        elif act[0] == 'home':
            print(f"    ('home', None, '{act[2]}'),")
    print("]")


def export_yaml(actions, output_path=None):
    """将动作序列导出为 action_player 兼容的 YAML 文件"""
    if not actions:
        print("  没有已保存的动作，无法导出")
        return

    if not output_path:
        name = input("  动作组名称 (如 pick_front): ").strip()
        if not name:
            print("  取消导出")
            return
        desc = input("  描述 (回车跳过): ").strip() or f"{name} action"
        default_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'src/xflz_robot_car1/arm/car1_arm_controller/config/actions')
        output_path = os.path.join(default_dir, f'{name}.yaml')
    else:
        name = os.path.splitext(os.path.basename(output_path))[0]
        desc = f"{name} action"

    yaml_actions = []
    for act in actions:
        step = {'name': act[2], 'duration': 2.0}
        if act[0] == 'arm':
            step['servos'] = {i: act[1][i] for i in range(5)}
        elif act[0] == 'gripper':
            step['servos'] = {5: act[1]}
            step['duration'] = 1.0
        elif act[0] == 'home':
            step['servos'] = {i: 1500 for i in range(6)}
            step['duration'] = 3.0
        yaml_actions.append(step)

    data = {'name': name, 'description': desc, 'actions': yaml_actions}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\n  已导出到: {output_path}")
    print(f"  动作步数: {len(yaml_actions)}")
    print(f"\n  使用方法:")
    print(f"    ros2 run car1_arm_controller action_player --ros-args -p action_file:={name}")


def playback_mode(ser):
    """回放模式：执行 ACTIONS 列表"""
    print("=" * 50)
    print("=== 回放模式 ===")
    print("=" * 50)
    print(f"共 {len(ACTIONS)} 个动作\n")

    for i, act in enumerate(ACTIONS):
        print(f"[{i+1}/{len(ACTIONS)}] {act[2]}")
        if act[0] == 'arm':
            move_arm(ser, *act[1], duration=2.0)
            time.sleep(3.0)
        elif act[0] == 'gripper':
            set_gripper(ser, act[1])
            time.sleep(2.0)
        elif act[0] == 'home':
            go_home(ser, duration=2.0)
            time.sleep(3.0)

    print("\n=== 回放完成 ===")


def main():
    print(f"打开串口 {SERIAL_PORT} @ {BAUDRATE}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        ser.rts = False
        ser.dtr = False
    except Exception as e:
        print(f"串口打开失败: {e}")
        print("请确认：")
        print("  1. 已停止 bringup (Ctrl+C)")
        print("  2. 串口存在: ls -l /dev/ttyUSB* /dev/car1_board")
        print("  3. 有权限: sudo chmod 666 /dev/ttyUSB0")
        return

    print("串口已打开\n")
    time.sleep(0.2)

    print("选择模式:")
    print("  1. 交互模式 - 手动输入PWM值调试")
    print("  2. 回放模式 - 执行 ACTIONS 列表")
    choice = input("\n输入 1 或 2: ").strip()

    try:
        if choice == '1':
            actions = interactive_mode(ser)
            export_actions(actions)
        else:
            playback_mode(ser)
    except KeyboardInterrupt:
        print("\n\n中断，回到工作位置...")
        go_work(ser, duration=1.5)
        time.sleep(2.0)
    finally:
        ser.close()
        print("串口已关闭")


if __name__ == '__main__':
    main()
