#!/bin/bash

# Simple API test script
# Tests the Web API endpoints

BASE_URL="http://localhost:3000"

echo "==================================="
echo "Testing Web API Endpoints"
echo "==================================="
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
echo "GET /health"
echo ""

# Test 2: Get leaderboard
echo "Test 2: Get Leaderboard"
echo "GET /api/leaderboard"
echo ""

# Test 3: Get stats
echo "Test 3: Get Global Stats"
echo "GET /api/stats"
echo ""

# Test 4: Get character details
echo "Test 4: Get Character Details (ID=1)"
echo "GET /api/character/1"
echo ""

# Test 5: Get battle details
echo "Test 5: Get Battle Details (ID=1)"
echo "GET /api/battle/1"
echo ""

echo "==================================="
echo "Manual testing:"
echo "  curl http://localhost:3000/health"
echo "  curl http://localhost:3000/api/leaderboard"
echo "  curl http://localhost:3000/api/stats"
echo "  curl http://localhost:3000/api/character/1"
echo "  curl http://localhost:3000/api/battle/1"
echo "==================================="
