#!/bin/bash

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install pre-commit
pip install pre-commit -q

# Install squad CLI
npm install -g @bradygaster/squad-cli

# Initialize Squad for multi-repo management
squad init

# Install git hooks (pre-commit + pre-push)
if [ -f ".pre-commit-config.yaml" ]; then
  chmod +x scripts/*.sh 2>/dev/null || true
  pre-commit install --install-hooks
  pre-commit install --hook-type pre-push
fi

# Install GitHub Copilot CLI extension (requires auth, may fail on first setup)
gh extension install github/gh-copilot 2>/dev/null || true

# Get versions
GIT_VER=$(git --version)
NODE_VER=$(node --version)
PYTHON_VER=$(python --version 2>&1)
UV_VER=$(uv --version 2>&1 || echo "not installed")

# Check if Copilot CLI is installed
if gh extension list 2>/dev/null | grep -q "gh-copilot"; then
  COPILOT_STATUS="✅ GitHub Copilot CLI installed"
else
  COPILOT_STATUS="⚠️  GitHub Copilot CLI not installed (run: gh auth login && gh extension install github/gh-copilot)"
fi

# Display welcome message
cat << EOF

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   🏠  Welcome to House Helper Pipeline!                        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

  ✅ $GIT_VER
  ✅ Node $NODE_VER
  ✅ $PYTHON_VER
  ✅ $UV_VER
  ✅ Squad CLI installed and initialized
  ✅ Pre-commit hooks installed
  $COPILOT_STATUS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 NEXT STEPS:

  1. Authenticate with GitHub:

     gh auth login

  Copilot CLI usage:
     gh copilot suggest "your question"
     gh copilot explain "command"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Environment ready! 🚀

EOF
