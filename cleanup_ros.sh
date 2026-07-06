#!/bin/bash
# ROS2 进程清理脚本
# 用于清理残留的 ROS2 节点、话题、服务

echo "======================================"
echo "ROS2 进程清理工具"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计残留进程
count=0

echo "1. 检查 ROS2 相关进程..."
echo "--------------------------------------"

# 常见的 ROS2 进程名称
ROS_PROCESSES=(
    "ros2"
    "rviz2"
    "gazebo"
    "gz"
    "slam_toolbox"
    "amcl"
    "map_server"
    "planner_server"
    "controller_server"
    "bt_navigator"
    "behavior_server"
    "velocity_smoother"
    "lifecycle_manager"
    "robot_state_publisher"
    "joint_state_publisher"
    "base_driver"
    "arm_controller"
    "visual_grasp"
    "teleop"
    "m1ct_d2"
    "ascamera"
)

# 检查并列出残留进程
for proc in "${ROS_PROCESSES[@]}"; do
    pids=$(pgrep -f "$proc" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}发现残留进程: $proc${NC}"
        ps aux | grep "$proc" | grep -v grep | awk '{printf "  PID: %s, CMD: %s\n", $2, $11}'
        count=$((count + $(echo "$pids" | wc -l)))
    fi
done

echo ""
if [ $count -eq 0 ]; then
    echo -e "${GREEN}✓ 没有发现残留的 ROS2 进程${NC}"
    echo ""
    echo "======================================"
    exit 0
fi

echo -e "${RED}共发现 $count 个残留进程${NC}"
echo ""

# 询问是否清理
read -p "是否清理这些进程？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消清理"
    exit 0
fi

echo ""
echo "2. 清理残留进程..."
echo "--------------------------------------"

# 清理进程（先尝试 SIGTERM，再用 SIGKILL）
for proc in "${ROS_PROCESSES[@]}"; do
    pids=$(pgrep -f "$proc" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "正在清理: $proc"
        for pid in $pids; do
            # 先尝试温和的 SIGTERM
            kill -15 "$pid" 2>/dev/null && echo "  发送 SIGTERM 到 PID $pid"
        done
    fi
done

# 等待 2 秒让进程优雅退出
sleep 2

# 强制清理仍然存在的进程
killed=0
for proc in "${ROS_PROCESSES[@]}"; do
    pids=$(pgrep -f "$proc" 2>/dev/null)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null && echo "  强制结束 PID $pid (SIGKILL)" && killed=$((killed + 1))
        done
    fi
done

echo ""
if [ $killed -gt 0 ]; then
    echo -e "${YELLOW}强制结束了 $killed 个顽固进程${NC}"
fi

echo ""
echo "3. 清理共享内存（DDS）..."
echo "--------------------------------------"

# 清理 FastDDS 共享内存
if [ -d "/dev/shm" ]; then
    shm_files=$(ls /dev/shm/ 2>/dev/null | grep -E "fastrtps|ros" | wc -l)
    if [ $shm_files -gt 0 ]; then
        echo "发现 $shm_files 个共享内存文件"
        sudo rm -f /dev/shm/fastrtps* /dev/shm/ros* 2>/dev/null && echo "  ✓ 已清理"
    else
        echo "  ✓ 无需清理"
    fi
else
    echo "  - 跳过（/dev/shm 不存在）"
fi

echo ""
echo "4. 验证清理结果..."
echo "--------------------------------------"

# 再次检查
remaining=0
for proc in "${ROS_PROCESSES[@]}"; do
    pids=$(pgrep -f "$proc" 2>/dev/null)
    if [ -n "$pids" ]; then
        remaining=$((remaining + $(echo "$pids" | wc -l)))
    fi
done

if [ $remaining -eq 0 ]; then
    echo -e "${GREEN}✓ 所有 ROS2 进程已清理${NC}"
else
    echo -e "${RED}⚠ 仍有 $remaining 个进程未清理${NC}"
    echo "请检查以下进程："
    ps aux | grep -E "$(IFS="|"; echo "${ROS_PROCESSES[*]}")" | grep -v grep
fi

echo ""
echo "======================================"
echo "清理完成"
echo "======================================"
