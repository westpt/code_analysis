@echo off
REM Compile script for timer project

REM Check if compiler exists
where clang >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Clang compiler not found in PATH
    echo Please install LLVM/Clang from https://releases.llvm.org/download.html
    echo Make sure to select "Add LLVM to the system PATH" during installation
    exit /b 1
)

REM Select compiler
SET COMPILER=clang

IF "%COMPILER%"=="gcc" (
    REM Using GCC compiler (if using MinGW)
    echo Compiling timer project with GCC...
    gcc -Wall -Wextra -I include src/timer.c src/timer_internal.c test_timer.c -o timer_test.exe
) ELSE IF "%COMPILER%"=="clang" (
    REM Using Clang compiler
    echo Compiling timer project with Clang...
    clang -Wall -Wextra -I include src/timer.c src/timer_internal.c test_timer.c -o timer_test.exe
) ELSE IF "%COMPILER%"=="msvc" (
    REM Using MSVC compiler (if using Visual Studio)
    echo Compiling timer project with MSVC...
    cl /W4 /I include src\timer.c src\timer_internal.c test_timer.c /Fe:timer_test.exe
)

REM If compilation is successful
if %ERRORLEVEL% EQU 0 (
    echo Compilation successful! You can run timer_test.exe
) else (
    echo Compilation failed, please check error messages.
)