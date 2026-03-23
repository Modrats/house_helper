#!/bin/bash
# Pre-commit wrapper that auto-fixes formatting and provides clear feedback
# Formatters auto-fix issues; only real errors block the commit

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🔍 Running pre-commit checks (auto-fix enabled)...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Capture files that were staged before running hooks
STAGED_FILES=$(git diff --cached --name-only)

# Run pre-commit
if pre-commit run "$@" 2>&1; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    EXIT_CODE=$?
    
    # Check if formatters made changes to staged files
    MODIFIED_STAGED=$(git diff --name-only $STAGED_FILES 2>/dev/null | head -20)
    
    if [ -n "$MODIFIED_STAGED" ]; then
        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}🔧 Auto-fixed formatting in:${NC}"
        echo "$MODIFIED_STAGED" | while read f; do echo -e "   ${BLUE}$f${NC}"; done
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${BOLD}To include the fixes in your commit:${NC}"
        echo -e "  ${BLUE}git add -u && git commit${NC}"
        echo ""
        echo -e "${YELLOW}💡 Or review changes first: ${BLUE}git diff${NC}"
    else
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ Pre-commit checks failed (not a formatting issue)${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${BOLD}Check the errors above and fix manually.${NC}"
        echo -e "  ${BLUE}make lint${NC}   - See all lint errors"
        echo -e "  ${BLUE}make test${NC}   - Run tests"
        echo ""
    fi
    
    echo -e "${YELLOW}Bypass (use sparingly): ${BLUE}git commit --no-verify${NC}"
    echo ""
    exit $EXIT_CODE
fi
