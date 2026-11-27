cmake_minimum_required(VERSION 3.8)
project(car1_kinematics)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(car1_description REQUIRED)

ament_python_install_package(kinematics)

install(FILES package.xml
  DESTINATION share/${PROJECT_NAME}
)

# 按 launch 使用的可执行名安装现有 FK 演示脚本。
install(PROGRAMS kinematics/fk_demo.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME fk_demo
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
