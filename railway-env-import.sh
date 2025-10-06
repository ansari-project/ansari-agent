#!/bin/bash

# Script to import environment variables from .env file to Railway
# Usage: ./railway-env-import.sh [service-name] [environment-name]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}Error: Railway CLI not installed. Install it with: npm install -g @railway/cli${NC}"
    exit 1
fi

# Parse command line arguments
SERVICE=""
ENVIRONMENT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-s service-name] [-e environment-name]"
            echo "  -s, --service     Service name (optional)"
            echo "  -e, --environment Environment name (optional)"
            echo ""
            echo "If not specified, will use the currently linked project/service/environment"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}🚂 Importing environment variables from .env to Railway...${NC}"

# Build railway command base
RAILWAY_CMD="railway variables"
if [ -n "$SERVICE" ]; then
    RAILWAY_CMD="$RAILWAY_CMD --service $SERVICE"
fi
if [ -n "$ENVIRONMENT" ]; then
    RAILWAY_CMD="$RAILWAY_CMD --environment $ENVIRONMENT"
fi

# Read .env file and set variables
COUNT=0
SKIPPED=0

while IFS='=' read -r key value; do
    # Skip empty lines and comments
    if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
        continue
    fi

    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)

    # Remove quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    # Skip if key is empty
    if [ -z "$key" ]; then
        continue
    fi

    # Set the variable in Railway
    echo -n "  Setting $key..."
    if $RAILWAY_CMD --set "$key=$value" &> /dev/null; then
        echo -e " ${GREEN}✓${NC}"
        ((COUNT++))
    else
        echo -e " ${RED}✗${NC}"
        ((SKIPPED++))
    fi
done < .env

echo ""
echo -e "${GREEN}✅ Import complete!${NC}"
echo "  Variables set: $COUNT"
if [ $SKIPPED -gt 0 ]; then
    echo "  Variables failed: $SKIPPED"
fi

echo ""
echo -e "${YELLOW}To verify your variables, run:${NC}"
echo "  railway variables"