#!/bin/bash
# Install git hooks
# Usually run automatically by devcontainer, but can be run manually

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}🔧 Installing git hooks...${NC}"

# Check if pre-commit is available
if ! command -v pre-commit &> /dev/null; then
    echo -e "${YELLOW}Installing pre-commit...${NC}"
    pip install pre-commit -q
fi

# Install the hooks
pre-commit install --install-hooks
pre-commit install --hook-type pre-push

echo ""
echo -e "${GREEN}✅ Git hooks installed!${NC}"
echo ""
echo -e "${BOLD}What happens now:${NC}"
echo -e "  • ${BLUE}On commit:${NC} Linting runs, formatting auto-fixes"
echo -e "  • ${BLUE}On push:${NC}   Tests run"
echo ""
echo -e "${BOLD}Commands:${NC}"
echo -e "  ${BLUE}make pre-commit${NC}  - Run checks manually"
echo -e "  ${BLUE}make format${NC}      - Auto-fix all formatting"
echo -e "  ${BLUE}make lint${NC}        - Run linters"
echo -e "  ${BLUE}make test${NC}        - Run tests"
echo ""
echo -e "${YELLOW}Bypass: git commit --no-verify${NC}"
