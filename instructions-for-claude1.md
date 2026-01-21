# DevOps Tools Installation and Setup Guide

## 1. Local Installation on Ubuntu VM

### Gitea (Self-hosted Git Service)
**Installation via Package Manager**:
```bash
# Add Gitea repository
sudo apt update
sudo apt install git

# Install via binary (recommended method for Ubuntu)
wget -O gitea https://dl.gitea.io/gitea/1.21.0/gitea-1.21.0-linux-amd64
chmod +x gitea
sudo mv gitea /usr/local/bin/gitea

# Create gitea user
sudo adduser --system --shell /bin/bash --gecos 'Git Version Control' --group --disabled-password --home /home/git git

# Create directory structure
sudo mkdir -p /var/lib/gitea/{custom,data,log}
sudo chown -R git:git /var/lib/gitea/
sudo chmod -R 750 /var/lib/gitea/

# Run Gitea
sudo -u git gitea web --config /etc/gitea/app.ini
```

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

