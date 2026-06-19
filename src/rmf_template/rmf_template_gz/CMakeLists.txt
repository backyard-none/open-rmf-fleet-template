cmake_minimum_required(VERSION 3.5)
project(rmf_template_gz)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  launch/
  config/
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
