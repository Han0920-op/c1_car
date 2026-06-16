#!/usr/bin/env python3
"""
PWM to FK Demo - Validation Tool for Level 3

This script validates the PWM → Angle → FK → tcp_link position calculation chain.
User provides PWM values, script calculates tcp_link position, user verifies visually.

Usage:
    ros2 run car1_kinematics pwm_to_fk_demo
    or
    python3 pwm_to_fk_demo.py

Author: Level 3 Implementation
Date: 2026-06-04
"""

import sys
import math
from transform import pwm_array_to_angles, TCP_OFFSET_Z, print_servo_config
from fk_demo import compute_fk


def demo_pwm_to_tcp_link(pwm_values, description=""):
    """
    Calculate tcp_link position from PWM values.

    Args:
        pwm_values (list): [ID0_pwm, ID1_pwm, ID2_pwm, ID3_pwm, ID4_pwm]
        description (str): Description of this test case
    """
    print("\n" + "=" * 80)
    if description:
        print(f"Test: {description}")
    print("=" * 80)

    print(f"\n输入 PWM 值: {pwm_values}")
    print(f"  ID 0 (底座旋转): {pwm_values[0]}")
    print(f"  ID 1 (大臂):     {pwm_values[1]}")
    print(f"  ID 2 (小臂):     {pwm_values[2]}")
    print(f"  ID 3 (腕部):     {pwm_values[3]}")
    print(f"  ID 4 (末端旋转): {pwm_values[4]}")

    # Step 1: PWM → Angles
    print("\n" + "-" * 80)
    print("步骤 1: PWM → 关节角度")
    print("-" * 80)

    try:
        joint_angles = pwm_array_to_angles(pwm_values)

        for i, (pwm, angle) in enumerate(zip(pwm_values, joint_angles)):
            angle_deg = math.degrees(angle)
            print(f"  ID {i}: PWM {pwm:4d} → {angle:7.4f} rad ({angle_deg:6.2f}°)")

        # Step 2: FK calculation (to arm_link5)
        print("\n" + "-" * 80)
        print("步骤 2: 正运动学计算 (FK → arm_link5)")
        print("-" * 80)

        arm_link5_pos = compute_fk(joint_angles)

        print(f"\narm_link5 位置:")
        print(f"  x = {arm_link5_pos[0]:.4f} m ({arm_link5_pos[0]*100:.2f} cm)")
        print(f"  y = {arm_link5_pos[1]:.4f} m ({arm_link5_pos[1]*100:.2f} cm)")
        print(f"  z = {arm_link5_pos[2]:.4f} m ({arm_link5_pos[2]*100:.2f} cm)")

        # Step 3: Add tcp offset
        print("\n" + "-" * 80)
        print("步骤 3: 添加 tcp_link 偏移")
        print("-" * 80)

        print(f"\ntcp_link 偏移: [0, 0, {TCP_OFFSET_Z:.4f}] m")

        tcp_link_pos = [
            arm_link5_pos[0],
            arm_link5_pos[1],
            arm_link5_pos[2] + TCP_OFFSET_Z
        ]

        print(f"\ntcp_link 位置 (最终结果):")
        print(f"  x = {tcp_link_pos[0]:.4f} m ({tcp_link_pos[0]*100:.2f} cm)")
        print(f"  y = {tcp_link_pos[1]:.4f} m ({tcp_link_pos[1]*100:.2f} cm)")
        print(f"  z = {tcp_link_pos[2]:.4f} m ({tcp_link_pos[2]*100:.2f} cm)")

        # Calculate reach distance
        reach = math.sqrt(tcp_link_pos[0]**2 + tcp_link_pos[1]**2)
        print(f"\n水平伸展距离: {reach:.4f} m ({reach*100:.2f} cm)")

        print("\n" + "=" * 80)
        print("请目测验证：计算的 tcp_link 位置是否与实际机械臂位置一致？")
        print("（允许误差：< 2cm）")
        print("=" * 80)

        return tcp_link_pos

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function."""
    print("\n" + "=" * 80)
    print("PWM → FK → tcp_link 位置验证工具")
    print("Level 3 Implementation")
    print("=" * 80)

    # Print configuration
    print("\n" + "-" * 80)
    print("当前配置参数")
    print("-" * 80)
    print_servo_config()

    # Test case 1: All centered (vertical up)
    print("\n\n" + "▶" * 40)
    demo_pwm_to_tcp_link(
        [1500, 1500, 1500, 1500, 1500],
        "全部 1500（垂直向上）"
    )

    # Test case 2: User's test posture
    print("\n\n" + "▶" * 40)
    demo_pwm_to_tcp_link(
        [1500, 1850, 2109, 1850, 1500],
        "用户测试姿态（向前伸出）"
    )

    # Test case 3: Custom input
    print("\n\n" + "▶" * 40)
    print("\n自定义测试")
    print("-" * 80)
    print("输入格式: ID0 ID1 ID2 ID3 ID4 (空格分隔)")
    print("例如: 1500 1850 2109 1850 1500")
    print("按 Ctrl+C 退出")

    try:
        while True:
            print("\n" + "-" * 80)
            user_input = input("请输入 PWM 值 (或直接回车跳过): ").strip()

            if not user_input:
                break

            try:
                pwm_values = [int(x) for x in user_input.split()]
                if len(pwm_values) != 5:
                    print(f"错误: 需要 5 个 PWM 值，您输入了 {len(pwm_values)} 个")
                    continue

                demo_pwm_to_tcp_link(pwm_values, "自定义姿态")

            except ValueError as e:
                print(f"错误: 输入格式不正确 - {e}")
                continue

    except KeyboardInterrupt:
        print("\n\n程序退出")

    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)
    print("\n验证要点:")
    print("  1. PWM [1500]*5 → tcp_link 应该在 [~0, ~0, ~0.506] m（垂直向上）")
    print("  2. 计算位置与实际机械臂 tcp_link 位置误差应 < 2cm")
    print("  3. 如果误差较大，需要调整 transform.py 中的 direction/offset 参数")
    print("\n下一步: 如果验证通过，继续实现 safe_arm_controller.py")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
