# Sources
file(GLOB SOURCES_PY "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
set(MANIFEST_FILE "${CMAKE_CURRENT_SOURCE_DIR}/MANIFEST.in")

# find all the python modules
file(GLOB_RECURSE __INIT__PYS "${CMAKE_CURRENT_SOURCE_DIR}/**/__init__.py")
string(LENGTH "${CMAKE_CURRENT_SOURCE_DIR}" CMAKE_CURRENT_SOURCE_DIR_LEN)
foreach (init_py ${__INIT__PYS})
  string(SUBSTRING "${init_py}"
      ${CMAKE_CURRENT_SOURCE_DIR_LEN}
      -1
      path)
  string(LENGTH ${path} path_len)
  math(EXPR path_len "${path_len} - 13")
  string(SUBSTRING "${path}"
      1
      ${path_len}
      path)
  list(APPEND PY_MODULES "${path}")
endforeach ()
message(STATUS "Python modules: ${PY_MODULES}")

foreach(module_name ${PY_MODULES})
  file(GLOB SOURCES_PY_${module_name}
            "${CMAKE_CURRENT_SOURCE_DIR}/${module_name}/*.py")
endforeach()
file(GLOB TESTS_TASKS "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_*")
set(REQUIREMENTS_TXT "${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt")

# Install directories
set(SOURCES_MODULE "${CMAKE_CURRENT_BINARY_DIR}/task_maker")
foreach(module_name ${PY_MODULES})
  set(SOURCES_${module_name}_MODULE "${SOURCES_MODULE}/${module_name}")
endforeach()
set(BIN_DIRECTORY "${SOURCES_MODULE}/bin")

# Create the install directories
file(MAKE_DIRECTORY ${SOURCES_MODULE})
foreach(module_name ${PY_MODULES})
  file(MAKE_DIRECTORY ${SOURCES_${module_name}_MODULE})
endforeach()
file(MAKE_DIRECTORY ${BIN_DIRECTORY})
file(WRITE "${BIN_DIRECTORY}/__init__.py" "")

# Compute the target file paths
set(MANIFEST_FILE_TGT "${CMAKE_CURRENT_BINARY_DIR}/MANIFEST.in")
string(REGEX
       REPLACE "${CMAKE_CURRENT_SOURCE_DIR}"
               "${SOURCES_MODULE}"
               SOURCES_PY_TGT
               "${SOURCES_PY}")
foreach(module_name ${PY_MODULES})
  string(REGEX
         REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/${module_name}"
                 "${SOURCES_${module_name}_MODULE}"
                 SOURCES_PY_${module_name}_TGT
                 "SOURCES_PY_${module_name}")
  file(MAKE_DIRECTORY ${SOURCES_${module_name}_MODULE})
  list(APPEND MODULES_TGT ${SOURCES_PY_${module_name}_TGT})
endforeach()
string(REGEX
       REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests"
               "${SOURCES_tests_MODULE}"
               TESTS_TASKS_TGT
               "${TESTS_TASKS}")
set(SETUP_PY ${CMAKE_CURRENT_BINARY_DIR}/setup.py)
set(VERSION_PY ${SOURCES_MODULE}/version.py)
set(REQUIREMENTS_TXT_TGT "${CMAKE_CURRENT_BINARY_DIR}/requirements.txt")
set(CPP_EXECUTABLES "${BIN_DIRECTORY}/task-maker")
set(FRONTEND_LIB "${SOURCES_MODULE}/task_maker_frontend.so")

# Copy all the files
add_custom_command(OUTPUT ${MANIFEST_FILE_TGT}
    COMMAND ${CMAKE_COMMAND} -E copy ${MANIFEST_FILE}
    ${MANIFEST_FILE_TGT}
    DEPENDS "${MANIFEST_FILE}")
add_custom_command(OUTPUT ${SOURCES_PY_TGT}
                   COMMAND ${CMAKE_COMMAND} -E copy ${SOURCES_PY}
                           ${SOURCES_MODULE}
                   DEPENDS "${SOURCES_PY}")

foreach(module_name ${PY_MODULES})
  add_custom_command(OUTPUT ${SOURCES_PY_${module_name}_TGT}
                     COMMAND ${CMAKE_COMMAND} -E copy
                             ${SOURCES_PY_${module_name}}
                             ${SOURCES_${module_name}_MODULE}
                     DEPENDS "${SOURCES_PY_${module_name}}")
endforeach()

# copy the statement templates
set(STATEMENTS_TEMPLATES_SRC_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/statements/templates")
set(STATEMENTS_TEMPLATES_DST_DIR "${SOURCES_statements_MODULE}/templates")
add_custom_command(OUTPUT ${STATEMENTS_TEMPLATES_DST_DIR}
    COMMAND ${CMAKE_COMMAND} -E copy_directory
    ${STATEMENTS_TEMPLATES_SRC_DIR}
    ${STATEMENTS_TEMPLATES_DST_DIR}
    DEPENDS ${STATEMENTS_TEMPLATES_SRC_DIR})

add_custom_command(OUTPUT ${REQUIREMENTS_TXT_TGT}
                   COMMAND ${CMAKE_COMMAND} -E copy ${REQUIREMENTS_TXT}
                           ${REQUIREMENTS_TXT_TGT}
                   DEPENDS ${REQUIREMENTS_TXT})

add_custom_command(OUTPUT "${FRONTEND_LIB}"
                   COMMAND ${CMAKE_COMMAND} -E copy
                           $<TARGET_FILE:task_maker_frontend> ${FRONTEND_LIB}
                   DEPENDS task_maker_frontend)

foreach(task ${TESTS_TASKS})
  string(REGEX
         REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_"
                 ""
                 task_name
                 "${task}")
  set(TEST_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/tests")
  set(TEST_DST_DIR "${SOURCES_tests_MODULE}")

  add_custom_command(OUTPUT ${TEST_DST_DIR}/task_${task_name}
                     COMMAND ${CMAKE_COMMAND} -E copy_directory
                             ${TEST_SRC_DIR}/task_${task_name}
                             ${TEST_DST_DIR}/task_${task_name}
                     DEPENDS "${TEST_SRC_DIR}/task_${task_name}")

  file(COPY
       ${TEST_SRC_DIR}/${task_name}.py
       DESTINATION
       ${TEST_DST_DIR}
       FILE_PERMISSIONS
       OWNER_EXECUTE
       OWNER_READ
       GROUP_EXECUTE
       GROUP_READ
       WORLD_READ
       WORLD_EXECUTE)

  if(ADDRESSSANITIZER)
    set(ASAN_EXTRA_ENV ASAN_OPTIONS=detect_leaks=0
        LD_PRELOAD=/usr/lib/libasan.so)
  endif()

  add_test(NAME pytest.${task_name}
           COMMAND env PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR} ${ASAN_EXTRA_ENV}
                   "${TEST_DST_DIR}/${task_name}.py")
endforeach(task)

add_custom_command(OUTPUT ${BIN_DIRECTORY}/task-maker
                   COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:task-maker>
                           ${BIN_DIRECTORY}
                   DEPENDS task-maker)

# generate setup.py
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in ${SETUP_PY})
execute_process(COMMAND chmod 555 ${SETUP_PY})

# generate version.py
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/version.py.in ${VERSION_PY})

add_custom_target(module_files ALL
                  DEPENDS ${MODULES_TGT}
    ${MANIFEST_FILE_TGT}
    ${STATEMENTS_TEMPLATES_DST_DIR}
                          ${REQUIREMENTS_TXT_TGT}
                          "${TESTS_TASKS_TGT}"
                          ${SOURCES_PY_TGT}
                          ${CPP_EXECUTABLES}
                          ${FRONTEND_LIB})

add_custom_target(develop
                  COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} develop
                  DEPENDS module_files)

install(CODE
        "execute_process(COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} install)")
