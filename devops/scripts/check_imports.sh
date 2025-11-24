#!/bin/bash
set -e

echo "=== Import Boundaries Check ==="
echo ""

echo "1. Testing core imports in isolation..."
python3 -c "import sibyl.core" 2>&1 || {
    echo "❌ FAILED: Cannot import sibyl.core"
    exit 1
}
echo "✅ Core imports successfully"
echo ""

echo "2. Verifying core doesn't depend on examples at import time..."
python3 -c "
import pkgutil
import sys

import sibyl.core

loaded_examples = [m for m in sys.modules if m and m.startswith('examples')]
if loaded_examples:
    print('ERROR: Found example modules loaded:', loaded_examples)
    sys.exit(1)

# Walk sibyl.core submodules to catch late imports
prefix = sibyl.core.__name__ + '.'
for module in pkgutil.walk_packages(sibyl.core.__path__, prefix):
    try:
        __import__(module.name)
    except Exception as exc:
        # Still fail fast but show which module caused it
        print(f'ERROR: Failed importing {module.name}: {exc}')
        sys.exit(1)

if any(m for m in sys.modules if m.startswith('examples')):
    print('ERROR: Loading sibyl.core pulled in examples modules')
    sys.exit(1)

print('OK: No example modules loaded')
" || {
    echo "❌ FAILED: Core depends on examples at import time"
    exit 1
}
echo "✅ Core is independent of examples"
echo ""

echo "3. Testing example imports..."
SIBYL_PROFILE=retailflow python3 -c "import examples.retailflow" 2>&1 || {
    echo "❌ FAILED: Cannot import examples.retailflow"
    exit 1
}
echo "✅ Examples import successfully"
echo ""

echo "=== All Import Boundary Checks Passed ==="
