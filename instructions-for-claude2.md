# DevOps Tools Installation and Setup Guide

## 1. Local Installation on Ubuntu VM

### Git and GitHub CLI (gh)
**Installation via Package Manager**:
```bash
# Update package list
sudo apt update

# Install Git
sudo apt install git

# Install GitHub CLI
sudo apt install gh
```

**Initial Git Configuration**:
```bash
# Set your git identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Optional: Set default branch name
git config --global init.defaultBranch main
```

**GitHub CLI Authentication**:
```bash
# Authenticate with GitHub (optional - only needed for cloud sync)
gh auth login

# Follow the interactive prompts to authenticate
```

**Basic Workflow**:
```bash
# 1. Initialize a local repository
cd your-project
git init

# 2. Work locally with standard git commands
git add .
git commit -m "Initial commit"

# 3. (Optional) Create remote repository and push when ready to sync to cloud
gh repo create your-repo-name --private --source=. --push

# Or for public repository
gh repo create your-repo-name --public --source=. --push
```

**Benefits of this approach**:
- Lightweight with no server maintenance
- Work locally without any services running
- Optional cloud sync when needed
- Direct GitHub integration via gh CLI
- Low resource usage
- Simple setup and configuration

### Selenium (Browser Automation Tool)
**Installation via pip (Python)**:
```bash
pip install selenium
```

**Installation via npm (Node.js)**:
```bash
npm install selenium-webdriver
```


### Jest (JavaScript Testing Framework)
**Installation via npm**:
```bash
npm install --save-dev jest
```


---
**Basic Project Structure**:
```
your-project/
├── src/                    # Source code
├── tests/
│   ├── selenium/          # Selenium tests
│   └── jest/              # Jest tests
├── .gitignore
├── package.json           # For Node.js/Jest dependencies
└── README.md
```

**Recommended .gitignore**:
```
# Dependencies
node_modules/
__pycache__/
*.pyc

# Test artifacts
*.log
screenshots/

# IDE
.vscode/
.idea/

# Environment variables
.env
```
