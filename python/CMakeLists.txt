# Python

file(GLOB SOURCES_PY "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
file(GLOB UIS_PY "${CMAKE_CURRENT_SOURCE_DIR}/uis/*.py")

SET(SOURCES_MODULE "${CMAKE_CURRENT_BINARY_DIR}/task_maker")
SET(UIS_MODULE "${SOURCES_MODULE}/uis")
SET(PROTOS_MODULE "${SOURCES_MODULE}/proto")
SET(BIN_DIRECTORY "${SOURCES_MODULE}/bin")

file(MAKE_DIRECTORY ${SOURCES_MODULE})
file(MAKE_DIRECTORY ${UIS_MODULE})
file(MAKE_DIRECTORY ${PROTOS_MODULE})
file(MAKE_DIRECTORY ${BIN_DIRECTORY})
file(WRITE "${PROTOS_MODULE}/__init__.py" "")
file(WRITE "${BIN_DIRECTORY}/__init__.py" "")

string(REGEX REPLACE "[^;]*/" "${PROTOS_MODULE}/" PROTOS_PY_TGT "${PROTOS_PY}")
string(REGEX REPLACE "[^;]*/" "${PROTOS_MODULE}/" GRPC_PY_TGT "${GRPC_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}" "${SOURCES_MODULE}" SOURCES_PY_TGT "${SOURCES_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/uis" "${UIS_MODULE}" UIS_PY_TGT "${UIS_PY}")

add_custom_command(OUTPUT ${PROTOS_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${PROTOS_PY} ${PROTOS_MODULE}
  DEPENDS protos_py
)

add_custom_command(OUTPUT ${GRPC_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${GRPC_PY} ${PROTOS_MODULE}
  DEPENDS grpc_py
)

add_custom_command(OUTPUT ${SOURCES_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${SOURCES_PY} ${SOURCES_MODULE}
  DEPENDS "${SOURCES_PY}"
)

add_custom_command(OUTPUT ${UIS_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${UIS_PY} ${UIS_MODULE}
  DEPENDS "${UIS_PY}"
)

add_custom_command(OUTPUT ${BIN_DIRECTORY}/server ${BIN_DIRECTORY}/worker ${BIN_DIRECTORY}/manager
  COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:server> $<TARGET_FILE:worker> $<TARGET_FILE:manager> ${BIN_DIRECTORY}
  DEPENDS server worker manager
)

SET(SETUP_PY ${CMAKE_CURRENT_BINARY_DIR}/setup.py)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in ${SETUP_PY})

SET(CPP_EXECUTABLES
  "${BIN_DIRECTORY}/manager"
  "${BIN_DIRECTORY}/server"
  "${BIN_DIRECTORY}/worker"
)

add_custom_target(module_files ALL
  DEPENDS ${PROTOS_PY_TGT} ${GRPC_PY_TGT} ${UIS_PY_TGT} ${SOURCES_PY_TGT} ${CPP_EXECUTABLES}
)

add_custom_target(develop
  COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} develop
  DEPENDS module_files
)

install(CODE "execute_process(COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} install)")