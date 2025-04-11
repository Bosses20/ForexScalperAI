@echo off
echo Running API endpoint tests...
python -m pytest tests\api\test_api_endpoints.py -v
if %ERRORLEVEL% EQU 0 (
    echo All API tests passed successfully!
) else (
    echo Some tests failed. Please check the output above for details.
)
pause
