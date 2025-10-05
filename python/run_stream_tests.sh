#!/bin/bash

# Bash script for running Python gRPC streaming tests
# This script starts the server and client, and handles cleanup on exit

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
SERVER_PORT=8080
VERBOSE=""
TEST_TYPE="all"
RUN_ONCE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            SERVER_PORT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --test)
            TEST_TYPE="$2"
            shift 2
            ;;
        --once)
            RUN_ONCE="--once"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --port PORT    Server port (default: 8080)"
            echo "  --verbose      Enable verbose logging"
            echo "  --test TYPE    Test type: client, server, sync, async, or all (default: all)"
            echo "  --once         Run tests once instead of continuously"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"

    # Kill server and client processes
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill -TERM $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi

    if [ ! -z "$CLIENT_PID" ]; then
        echo "Stopping client (PID: $CLIENT_PID)..."
        kill -TERM $CLIENT_PID 2>/dev/null
        wait $CLIENT_PID 2>/dev/null
    fi

    echo -e "${GREEN}Cleanup complete${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM EXIT

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if required files exist
if [ ! -f "stream_server.py" ]; then
    echo -e "${RED}Error: stream_server.py not found${NC}"
    echo "Please run this script from the python directory"
    exit 1
fi

if [ ! -f "stream_client.py" ]; then
    echo -e "${RED}Error: stream_client.py not found${NC}"
    echo "Please run this script from the python directory"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import grpc" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        exit 1
    fi
fi

# Start the server
echo -e "${GREEN}Starting gRPC streaming server on port $SERVER_PORT...${NC}"
python3 stream_server.py --port $SERVER_PORT $VERBOSE &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 2

# Check if server is running
if ! ps -p $SERVER_PID > /dev/null; then
    echo -e "${RED}Error: Server failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}Server started successfully (PID: $SERVER_PID)${NC}"

# Start the client
echo -e "${GREEN}Starting gRPC streaming client...${NC}"
python3 stream_client.py --server localhost:$SERVER_PORT --test $TEST_TYPE $VERBOSE $RUN_ONCE &
CLIENT_PID=$!

# Wait for client to start
sleep 1

# Check if client is running
if ! ps -p $CLIENT_PID > /dev/null; then
    echo -e "${RED}Error: Client failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}Client started successfully (PID: $CLIENT_PID)${NC}"

if [ ! -z "$RUN_ONCE" ]; then
    # If running once, wait for client to finish
    echo "Running tests once..."
    wait $CLIENT_PID
    echo -e "${GREEN}Tests completed${NC}"
else
    # If running continuously, show instructions
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Streaming tests are running continuously${NC}"
    echo -e "${GREEN}Press Ctrl+C to stop${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Wait indefinitely
    while true; do
        # Check if processes are still running
        if ! ps -p $SERVER_PID > /dev/null; then
            echo -e "${RED}Server stopped unexpectedly${NC}"
            break
        fi

        if ! ps -p $CLIENT_PID > /dev/null; then
            echo -e "${RED}Client stopped unexpectedly${NC}"
            break
        fi

        sleep 5
    done
fi
