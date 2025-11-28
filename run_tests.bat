@echo off
echo ========================================
echo RUNNING SYSTEM TESTS
echo ========================================
echo.

echo [1/3] Testing Backward Compatibility...
python tests/test_backward_compatibility.py
if %errorlevel% neq 0 (
    echo Backward compatibility test FAILED
    exit /b 1
)
echo.

echo [2/3] Testing End-to-End...
python tests/test_end_to_end.py
if %errorlevel% neq 0 (
    echo End-to-end test FAILED
    exit /b 1
)
echo.

echo [3/3] Testing SCADA Boundary...
python tests/test_scada_boundary.py
if %errorlevel% neq 0 (
    echo SCADA boundary test FAILED
    exit /b 1
)
echo.

echo ========================================
echo ALL TESTS PASSED!
echo ========================================



