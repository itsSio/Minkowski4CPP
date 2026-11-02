# Temporary out-of-tree equivalent of PR #5 (fork branch fix/cpu-only-build, commit 0e169ba).
# mink-build.ps1 -Cpu injects it via -DCMAKE_PROJECT_INCLUDE only when the checkout lacks the fix.
# The autograd sources and coordinate_manager.cu carry both backends (CUDA paths are guarded by
# CPU_ONLY); without them a CPU_ONLY build has unresolved symbols. They are compiled as C++.
if(CPU_ONLY)
    cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL _mink_cpu_only_fix)
    function(_mink_cpu_only_fix)
        set(_dual "${CMAKE_SOURCE_DIR}/MinkowskiEngine/coordinate_manager.cu")
        file(GLOB _ag "${CMAKE_SOURCE_DIR}/MinkowskiEngine/autograd/*.cu")
        list(APPEND _dual ${_ag})
        set_source_files_properties(${_dual} DIRECTORY "${CMAKE_SOURCE_DIR}"
            PROPERTIES LANGUAGE CXX COMPILE_OPTIONS "/TP")
        target_sources(minkowski_cpp PRIVATE ${_dual})
        message(STATUS "mink-build: applied temporary CPU_ONLY fix (PR #5) to minkowski_cpp")
    endfunction()
endif()
