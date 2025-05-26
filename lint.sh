#!/bin/bash

set -e  # 에러 발생 시 즉시 중단

echo "🧹 Running black (format check)..."
black --check .

echo "🧪 Running mypy (type check)..."
mypy --explicit-package-bases src/

echo "🔍 Running flake8 (style lint)..."
flake8 src/

echo "✅ All checks passed."