# Python gRPC Streaming Makefile
# Automation tasks for building, testing, and running the streaming implementation

.PHONY: help install clean proto server client test benchmark all

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install Python dependencies"
	@echo "  clean       - Clean generated files and cache"
	@echo "  proto       - Generate protobuf/gRPC code"
	@echo "  server      - Start the streaming server"
	@echo "  client      - Start the streaming client"
	@echo "  test        - Run all streaming tests once"
	@echo "  benchmark   - Run performance benchmarks"
	@echo "  all         - Install dependencies and generate proto files"
	@echo "  help        - Show this help message"

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	pip3 install -r requirements.txt

# Clean generated files and cache
clean:
	@echo "Cleaning generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f api/stream/v1/stream_pb2.py
	rm -f api/stream/v1/stream_pb2.pyi
	rm -f api/stream/v1/stream_pb2_grpc.py
	@echo "Cleanup complete"

# Generate protobuf/gRPC code
proto:
	@echo "Generating protobuf/gRPC code..."
	mkdir -p api/stream/v1
	python3 -m grpc_tools.protoc \
		-I../api \
		--python_out=api/stream/v1 \
		--pyi_out=api/stream/v1 \
		--grpc_python_out=api/stream/v1 \
		../api/stream/v1/stream.proto
	# Fix import in generated gRPC file
	sed -i.bak 's/from stream\.v1 import stream_pb2/from . import stream_pb2/' api/stream/v1/stream_pb2_grpc.py
	rm -f api/stream/v1/stream_pb2_grpc.py.bak
	@echo "Protobuf generation complete"

# Start the streaming server
server: proto
	@echo "Starting gRPC streaming server..."
	python3 stream_server.py --verbose

# Start the streaming client
client: proto
	@echo "Starting gRPC streaming client..."
	python3 stream_client.py --verbose

# Run all streaming tests once
test: proto
	@echo "Running streaming tests..."
	python3 stream_client.py --once --verbose

# Run performance benchmarks
benchmark: proto
	@echo "Running performance benchmarks..."
	python3 stream_benchmark.py --verbose

# Quick benchmark with limited scope
benchmark-quick: proto
	@echo "Running quick performance benchmark..."
	python3 stream_benchmark.py --concurrent 1 5 --message-size 1024 --messages-per-stream 50 --verbose

# Run server and client together using the bash script
run-tests: proto
	@echo "Running server and client tests..."
	chmod +x run_stream_tests.sh
	./run_stream_tests.sh --verbose

# Run tests once using the bash script
run-tests-once: proto
	@echo "Running server and client tests once..."
	chmod +x run_stream_tests.sh
	./run_stream_tests.sh --once --verbose

# Install and setup everything
all: install proto
	@echo "Setup complete"

# Development targets
dev-server: proto
	@echo "Starting development server with auto-reload..."
	python3 stream_server.py --verbose --port 8080

dev-client: proto
	@echo "Starting development client..."
	python3 stream_client.py --server localhost:8080 --verbose

# Test specific streaming patterns
test-client: proto
	python3 stream_client.py --test client --once --verbose

test-server: proto
	python3 stream_client.py --test server --once --verbose

test-sync: proto
	python3 stream_client.py --test sync --once --verbose

test-async: proto
	python3 stream_client.py --test async --once --verbose

# Benchmark specific patterns
benchmark-client: proto
	python3 stream_benchmark.py --test client --concurrent 5 --message-size 1024 --verbose

benchmark-server: proto
	python3 stream_benchmark.py --test server --concurrent 5 --message-size 1024 --verbose

benchmark-sync: proto
	python3 stream_benchmark.py --test sync --concurrent 5 --message-size 1024 --verbose

benchmark-async: proto
	python3 stream_benchmark.py --test async --concurrent 5 --message-size 1024 --verbose

# Format code (requires black and isort)
format:
	@echo "Formatting Python code..."
	python3 -m black --line-length 88 *.py
	python3 -m isort *.py

# Lint code (requires flake8)
lint:
	@echo "Linting Python code..."
	python3 -m flake8 --max-line-length 88 --ignore E203,W503 *.py

# Check if server is running
check-server:
	@echo "Checking if server is running..."
	@python3 -c "import grpc; channel = grpc.insecure_channel('localhost:8080'); print('Server is running' if channel else 'Server not found')" 2>/dev/null || echo "Server is not running"

# Show system information
info:
	@echo "System Information:"
	@echo "Python version: $(shell python3 --version)"
	@echo "Pip version: $(shell pip3 --version)"
	@echo "gRPC version: $(shell python3 -c 'import grpc; print(grpc.__version__)' 2>/dev/null || echo 'Not installed')"
	@echo "Working directory: $(PWD)"
	@echo "Available Python modules:"
	@python3 -c "import grpc, google.protobuf; print('✓ gRPC and protobuf are available')" 2>/dev/null || echo "✗ Missing dependencies"
