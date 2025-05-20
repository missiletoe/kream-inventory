@echo off
echo 🧹 Running black (format check)...
black --check .
if %errorlevel% neq 0 exit /b %errorlevel%

echo 🧪 Running mypy (type check)...
mypy --explicit-package-bases src/
if %errorlevel% neq 0 exit /b %errorlevel%

echo 🔍 Running flake8 (style lint)...
flake8 src/
if %errorlevel% neq 0 exit /b %errorlevel%

echo ✅ All checks passed.
exit /b 0 