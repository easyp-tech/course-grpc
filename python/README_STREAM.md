# Python gRPC Streaming Implementation

This directory contains a complete Python implementation of gRPC streaming patterns, ported from the Go implementation.

## Overview

The implementation demonstrates all four gRPC communication patterns:
1. **Client Streaming** - Multiple client messages, single server response
2. **Server Streaming** - Single client message, multiple server responses
3. **Bidirectional Streaming (Sync)** - Synchronous message exchange
4. **Bidirectional Streaming (Async)** - Asynchronous message exchange with separate threads

## Files

- `stream_server.py` - Server implementation with all streaming handlers
- `stream_client.py` - Client implementation with tests for all streaming patterns
- `api/stream/v1/` - Generated protobuf/gRPC code from the proto definition

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Generate protobuf code (if needed):
```bash
python -m grpc_tools.protoc -I../api \
    --python_out=api/stream/v1 \
    --pyi_out=api/stream/v1 \
    --grpc_python_out=api/stream/v1 \
    ../api/stream/v1/stream.proto
```

## Running the Server

Start the streaming server:
```bash
python stream_server.py
```

Server options:
- `--port PORT` - Port to listen on (default: 8080)
- `--workers N` - Maximum worker threads (default: 10)
- `--verbose` - Enable verbose logging

Example with custom settings:
```bash
python stream_server.py --port 9090 --workers 20 --verbose
```

## Running the Client

Run all streaming tests continuously:
```bash
python stream_client.py
```

Client options:
- `--server ADDRESS` - Server address (default: localhost:8080)
- `--test TYPE` - Test type: client, server, sync, async, or all (default: all)
- `--once` - Run tests once instead of continuously
- `--verbose` - Enable verbose logging

Examples:
```bash
# Run only client streaming test
python stream_client.py --test client

# Run all tests once
python stream_client.py --once

# Connect to different server
python stream_client.py --server localhost:9090
```

## Implementation Details

### Server Features

1. **Client Streaming Handler** (`EchoClientStream`)
   - Collects all messages from client
   - Returns summary of received messages

2. **Server Streaming Handler** (`EchoServerStream`)
   - Receives one message
   - Sends back 5 echo responses with delays

3. **Bidirectional Sync Handler** (`EchoBidirectionalStreamSync`)
   - Processes each message immediately
   - Sends response right after receiving

4. **Bidirectional Async Handler** (`EchoBidirectionalStreamAsync`)
   - Uses separate threads for receiving and processing
   - Simulates asynchronous processing with delays
   - Queue-based message passing between threads

### Client Features

1. **Concurrent Testing**
   - Runs 4 parallel test clients
   - Each client tests different streaming pattern
   - Configurable test intervals

2. **Error Handling**
   - Graceful handling of connection errors
   - Proper cleanup on shutdown
   - Timeout management

3. **Logging & Monitoring**
   - Detailed logging for all operations
   - Interceptor for monitoring RPC calls
   - Performance timing

### Key Differences from Go Implementation

1. **Threading vs Goroutines**
   - Python uses `threading` module instead of goroutines
   - Queue-based communication between threads
   - Thread synchronization with Events

2. **Generator Functions**
   - Python uses generator functions for streaming
   - `yield` statements for producing stream elements
   - Iterator protocol for consuming streams

3. **Context Handling**
   - gRPC context for checking connection status
   - Manual thread coordination with Events
   - Timeout handling with thread joins

## Testing

Run both server and client in separate terminals:

Terminal 1:
```bash
python stream_server.py --verbose
```

Terminal 2:
```bash
python stream_client.py --verbose
```

You should see:
- Client-1 performing client streaming (sending 3 messages, receiving 1)
- Client-2 performing server streaming (sending 1 message, receiving 5)
- Client-3 performing bidirectional sync streaming
- Client-4 performing bidirectional async streaming

## Graceful Shutdown

Both server and client support graceful shutdown:
- Press `Ctrl+C` to initiate shutdown
- Server waits up to 5 seconds for active connections to finish
- Client waits for all test threads to complete

## Performance Considerations

1. **Message Size Limits**
   - Configured to support up to 50MB messages
   - Adjustable via gRPC channel options

2. **Thread Pool Size**
   - Server uses ThreadPoolExecutor with configurable workers
   - Default: 10 worker threads

3. **Queue Sizes**
   - Async streaming uses bounded queues (size 10)
   - Prevents memory issues with slow consumers

## Troubleshooting

1. **Connection Refused**
   - Ensure server is running before starting client
   - Check port availability

2. **Import Errors**
   - Verify protobuf code is generated
   - Check Python path includes project directory

3. **Performance Issues**
   - Adjust worker thread count
   - Monitor system resources
   - Check network latency

## Comparison with Go Implementation

| Feature | Go | Python |
|---------|----|---------| 
| Concurrency | Goroutines | Threads |
| Channels | Go channels | Queue module |
| Context | context.Context | grpc.ServicerContext |
| Error Handling | error interface | Exceptions |
| Performance | Higher | Lower (GIL) |
| Memory Usage | Lower | Higher |

Both implementations provide the same functionality and demonstrate all gRPC streaming patterns effectively.