# Python gRPC Streaming Implementation

Complete Python implementation of gRPC streaming patterns, ported and extended from the Go implementation in the easyp-demo project.

## 🚀 Features

This implementation demonstrates all four gRPC communication patterns:

- **Client Streaming** - Multiple client messages → Single server response
- **Server Streaming** - Single client message → Multiple server responses  
- **Bidirectional Streaming (Sync)** - Real-time synchronous message exchange
- **Bidirectional Streaming (Async)** - Asynchronous processing with separate threads

## 📁 Project Structure

```
python/
├── stream_server.py          # gRPC streaming server implementation
├── stream_client.py          # gRPC streaming client with tests
├── stream_benchmark.py       # Performance benchmarking utility
├── run_stream_tests.sh       # Bash script for automated testing
├── Makefile                  # Automation tasks
├── requirements.txt          # Python dependencies
├── README_STREAM.md          # Detailed streaming documentation
├── COMPARISON.md             # Go vs Python comparison
└── api/stream/v1/            # Generated protobuf/gRPC code
    ├── stream_pb2.py
    ├── stream_pb2.pyi
    └── stream_pb2_grpc.py
```

## 🛠️ Quick Start

### Prerequisites

- Python 3.7+
- pip package manager

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate protobuf code:**
   ```bash
   make proto
   ```

3. **Run tests:**
   ```bash
   make run-tests-once
   ```

### Using Make Commands

```bash
# Show all available commands
make help

# Install dependencies and setup
make all

# Start server only
make server

# Start client only (server must be running)
make client

# Run comprehensive tests
make run-tests

# Run performance benchmarks
make benchmark-quick
```

## 🎯 Usage Examples

### Start the Server

```bash
# Basic server
python stream_server.py

# Custom port with verbose logging
python stream_server.py --port 9090 --verbose --workers 20
```

### Run Client Tests

```bash
# All streaming patterns
python stream_client.py

# Specific pattern
python stream_client.py --test client
python stream_client.py --test server
python stream_client.py --test sync
python stream_client.py --test async

# Single run (not continuous)
python stream_client.py --once

# Custom server
python stream_client.py --server localhost:9090
```

### Performance Benchmarking

```bash
# Quick benchmark
python stream_benchmark.py --concurrent 1 5 --message-size 1024

# Comprehensive benchmark
python stream_benchmark.py --concurrent 1 5 10 20 --message-size 64 1024 8192

# Export results to CSV
python stream_benchmark.py --output results.csv
```

## 🔧 Server Configuration

The server supports various configuration options:

```python
# Default configuration
server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[StreamServerInterceptor()],
    options=[
        ("grpc.max_send_message_length", 50 * 1024 * 1024),
        ("grpc.max_receive_message_length", 50 * 1024 * 1024),
    ],
)
```

### Command Line Options

- `--port PORT` - Server port (default: 8080)
- `--workers N` - Max worker threads (default: 10)
- `--verbose` - Enable debug logging

## 🧪 Testing

### Automated Testing

```bash
# Run all tests with automatic server startup
./run_stream_tests.sh

# Run once and exit
./run_stream_tests.sh --once

# Custom configuration
./run_stream_tests.sh --port 9090 --verbose
```

### Manual Testing

```bash
# Terminal 1: Start server
python stream_server.py --verbose

# Terminal 2: Run specific tests
python stream_client.py --test client --once
python stream_client.py --test server --once
python stream_client.py --test sync --once
python stream_client.py --test async --once
```

## 📊 Performance

### Benchmark Results (Local Testing)

| Pattern | Concurrent Clients | Requests/sec | Avg Latency | 
|---------|-------------------|--------------|-------------|
| Client Streaming | 5 | ~5,400 | ~15ms |
| Server Streaming | 5 | ~48 | ~520ms |
| Bidirectional Sync | 5 | ~3,200 | ~14ms |
| Bidirectional Async | 5 | ~240 | ~208ms |

*Results vary based on hardware and system configuration*

### Performance Tuning

1. **Adjust worker threads:**
   ```bash
   python stream_server.py --workers 50
   ```

2. **Message size limits:**
   ```python
   options=[
       ("grpc.max_send_message_length", 100 * 1024 * 1024),
       ("grpc.max_receive_message_length", 100 * 1024 * 1024),
   ]
   ```

3. **Connection settings:**
   ```python
   options=[
       ("grpc.keepalive_time_ms", 30000),
       ("grpc.keepalive_timeout_ms", 5000),
   ]
   ```

## 🏗️ Implementation Details

### Key Features

- **Thread-safe streaming** using `threading` and `Queue`
- **Graceful shutdown** with signal handling
- **Comprehensive error handling** with proper cleanup
- **Performance monitoring** with CPU/memory tracking
- **Interceptors** for logging and monitoring
- **Type hints** for better code quality

### Threading Architecture

```python
# Async bidirectional streaming uses separate threads
receiver_thread = threading.Thread(target=receive_messages, daemon=True)
processor_thread = threading.Thread(target=process_messages, daemon=True)

# Queue-based communication
request_queue = Queue(maxsize=10)
response_queue = Queue(maxsize=10)
```

### Error Handling

```python
try:
    for request in request_iterator:
        # Process request
        yield response
except grpc.RpcError as e:
    logger.error(f"RPC error: {e}")
    context.abort(grpc.StatusCode.INTERNAL, str(e))
```

## 🔍 Debugging

### Enable Verbose Logging

```bash
python stream_server.py --verbose
python stream_client.py --verbose
```

### Common Issues

1. **Connection refused:**
   - Ensure server is running: `make check-server`
   - Check port availability: `lsof -i :8080`

2. **Import errors:**
   - Regenerate protobuf: `make proto`
   - Check Python path: `export PYTHONPATH=$PWD:$PYTHONPATH`

3. **Performance issues:**
   - Monitor system resources
   - Adjust worker thread count
   - Check network latency

## 🆚 Go vs Python Comparison

| Aspect | Go | Python |
|--------|----|---------| 
| **Performance** | ~3-4x faster | Baseline |
| **Memory Usage** | ~50% less | Baseline |
| **Development Speed** | Moderate | Fast |
| **Ecosystem** | Growing | Rich |
| **Type Safety** | Strong | Optional |
| **Deployment Size** | ~15-25MB | ~80-120MB |

See [COMPARISON.md](COMPARISON.md) for detailed analysis.

## 📚 Documentation

- [README_STREAM.md](README_STREAM.md) - Detailed streaming patterns documentation
- [COMPARISON.md](COMPARISON.md) - Go vs Python implementation comparison

## 🛠️ Development

### Code Formatting

```bash
# Install formatting tools
pip install black isort flake8

# Format code
make format

# Lint code  
make lint
```

### Adding New Features

1. Update the server implementation in `stream_server.py`
2. Add client tests in `stream_client.py`  
3. Update benchmarks in `stream_benchmark.py`
4. Add tests and documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is part of the easyp-demo repository. See the main repository for license information.

## 🔗 Related Projects

- [Go Implementation](../cmd/stream/) - Original Go streaming implementation
- [easyp-demo](../) - Main project repository
- [gRPC Python](https://grpc.io/docs/languages/python/) - Official gRPC Python documentation

---

**Happy Streaming!** 🚀

For questions or issues, please check the documentation or open an issue in the main repository.