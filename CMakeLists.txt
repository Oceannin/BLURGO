cmake_minimum_required(VERSION 3.28...3.30)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/common/bootstrap.cmake" NO_POLICY_SCOPE)

project(${_name} VERSION ${_version})

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(ENABLE_FRONTEND_API "Use obs-frontend-api for UI functionality" OFF)
option(ENABLE_QT "Use Qt functionality" OFF)

include(compilerconfig)
include(defaults)
include(helpers)

add_library(${CMAKE_PROJECT_NAME} MODULE)

find_package(libobs REQUIRED)
target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE OBS::libobs)

if(ENABLE_FRONTEND_API)
  find_package(obs-frontend-api REQUIRED)
  target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE OBS::obs-frontend-api)
endif()

if(ENABLE_QT)
  find_package(Qt6 COMPONENTS Widgets Core)
  target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE Qt6::Core Qt6::Widgets)
  target_compile_options(
    ${CMAKE_PROJECT_NAME}
    PRIVATE $<$<C_COMPILER_ID:Clang,AppleClang>:-Wno-quoted-include-in-framework-header -Wno-comma>
  )
  set_target_properties(
    ${CMAKE_PROJECT_NAME}
    PROPERTIES AUTOMOC ON AUTOUIC ON AUTORCC ON
  )
endif()

target_sources(
  ${CMAKE_PROJECT_NAME}
  PRIVATE
    src/blurgo-filter.c
    src/blurgo-settings.c
    src/blurgo-settings.h
    src/plugin-main.c
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE src)

set_target_properties_plugin(${CMAKE_PROJECT_NAME} PROPERTIES OUTPUT_NAME ${_name})

if(OS_MACOS)
  target_add_resource(${CMAKE_PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
  target_add_resource(${CMAKE_PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/README.md")
  target_add_resource(${CMAKE_PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/SECURITY.md")
  target_add_resource(${CMAKE_PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/CONTRIBUTING.md")
elseif(OS_WINDOWS)
  install(
    FILES LICENSE README.md SECURITY.md CONTRIBUTING.md
    DESTINATION "${CMAKE_PROJECT_NAME}"
    COMPONENT Runtime
  )
else()
  install(
    FILES LICENSE README.md SECURITY.md CONTRIBUTING.md
    DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/doc/${CMAKE_PROJECT_NAME}"
    COMPONENT Runtime
  )
endif()

include(CTest)

if(BUILD_TESTING)
  add_executable(blurgo-settings-tests tests/blurgo-settings-test.c src/blurgo-settings.c)
  target_include_directories(blurgo-settings-tests PRIVATE src)
  add_test(NAME blurgo-settings COMMAND blurgo-settings-tests)
endif()
