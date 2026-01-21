#!/bin/bash
# Helper script to push commits to GitHub

echo "========================================="
echo "GitHub Push Helper"
echo "========================================="
echo ""
echo "You have 47 commits ready to push to GitHub."
echo ""
echo "Choose an option:"
echo ""
echo "1. Push with username/password (or token)"
echo "2. Push with token in URL (no prompt)"
echo "3. Setup gh auth first"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Running: git push origin master"
        echo "You'll be prompted for username and password/token"
        echo ""
        git push origin master
        ;;
    2)
        echo ""
        read -p "Enter your GitHub Personal Access Token: " token
        echo ""
        echo "Pushing with token..."
        git push https://$token@github.com/kareemmohamed2024/12-extractor.git master

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Push successful!"
            echo ""
            echo "Updating remote to use stored credentials..."
            git remote set-url origin https://$token@github.com/kareemmohamed2024/12-extractor.git
            echo "✅ Future pushes will use stored credentials"
        fi
        ;;
    3)
        echo ""
        echo "Setting up GitHub CLI authentication..."
        echo ""
        echo "Choose authentication method:"
        echo "1. Device code (recommended for WSL)"
        echo "2. Paste token directly"
        echo ""
        read -p "Enter choice (1-2): " auth_choice

        case $auth_choice in
            1)
                gh auth login --hostname github.com --git-protocol https --web
                ;;
            2)
                echo ""
                echo "Create a token at: https://github.com/settings/tokens/new"
                echo "Required scopes: repo"
                echo ""
                read -p "Paste your token and press Enter: " gh_token
                echo $gh_token | gh auth login --hostname github.com --git-protocol https --with-token
                ;;
        esac

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Authentication successful!"
            echo "Now running: git push origin master"
            echo ""
            git push origin master
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "Done!"
echo "========================================="
