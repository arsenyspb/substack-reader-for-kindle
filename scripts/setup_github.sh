#!/bin/bash

# Substack RFK: GitHub Setup Helper
# This script automates the creation of GitHub Secrets and Variables.

echo "------------------------------------------------"
echo "Substack RFK: GitHub Actions Setup"
echo "------------------------------------------------"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null
then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null
then
    echo "Error: You are not logged in to GitHub CLI."
    echo "Please run: gh auth login"
    exit 1
fi

echo "Please enter the following values (they will be saved to your GitHub Fork):"

# Secrets (Hidden in UI)
read -p "GMAIL_APP_PASSWORD: " gmail_pass
read -p "WEB_APP_SECRET (the UUID from your sheet): " web_secret

# Secrets & Config (All saved as Secrets to mask from logs)
read -p "GMAIL_USER: " gmail_user
read -p "KINDLE_EMAIL: " kindle_email
read -p "WEB_APP_URL: " web_url
read -p "ALLOWLISTED_SENDERS (optional, comma-separated): " allowlisted

echo ""
echo "Updating GitHub Secrets..."
gh secret set GMAIL_APP_PASSWORD --body "$gmail_pass"
gh secret set WEB_APP_SECRET --body "$web_secret"
gh secret set GMAIL_USER --body "$gmail_user"
gh secret set KINDLE_EMAIL --body "$kindle_email"
gh secret set WEB_APP_URL --body "$web_url"
gh secret set ALLOWLISTED_SENDERS --body "$allowlisted"

echo "Cleaning up any legacy GitHub Variables..."
gh variable delete GMAIL_USER &> /dev/null || true
gh variable delete KINDLE_EMAIL &> /dev/null || true
gh variable delete WEB_APP_URL &> /dev/null || true
gh variable delete ALLOWLISTED_SENDERS &> /dev/null || true

echo "------------------------------------------------"
echo "Setup Complete! You can now run your first Sync."
echo "------------------------------------------------"
