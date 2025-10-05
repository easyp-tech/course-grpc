# gRPC Echo Stream Demo

This demo showcases all 4 types of gRPC streaming:

1. **Client Streaming** - Client sends multiple messages, server responds with one
2. **Server Streaming** - Client sends one message, server responds with multiple
3. **Bidirectional Streaming (Sync)** - Both sides stream, processing messages synchronously
4. **Bidirectional Streaming (Async)** - Both sides stream, processing messages asynchronously

## Project Structure

- `main.go` - gRPC server implementation
- `client.go` - gRPC client that tests all streaming methods
- `Makefile` - Convenient build and run targets

## Quick Start

### Option 1: Using Makefile (Recommended)

```bash
# Build and run both server and client
make start-all

# Or run them separately:
# Terminal 1: Start server
make run-server

# Terminal 2: Start client
make run-client
```

### Option 2: Manual Setup

```bash
# Terminal 1: Start the server
go run main.go

# Terminal 2: Start the client
go run client.go
```

### Option 3: Using Built Binaries

```bash
# Build binaries
make build-server build-client

# Terminal 1: Start server
./stream-server

# Terminal 2: Start client  
./stream-client
```

## What You'll See

### Server Output
```
Starting gRPC Echo Stream Server...
gRPC server listening on :8080
EchoClientStream: Starting client stream
EchoClientStream: Received message: Hello from client-1 message-1
EchoServerStream: Received message: Hello from client-2 for server stream
...
```

### Client Output
```
Starting gRPC Echo Stream Client...
All streaming clients started. Press Ctrl+C to stop...
[Client-1] Starting client stream test
[Client-1] Sent: Hello from client-1 message-1
[Client-2] Starting server stream test
[Client-2] Server stream response: Echo #1: Hello from client-2 for server stream
...
```

## Streaming Methods Explained

### 1. Client Streaming (`EchoClientStream`)
- **Client**: Sends 3 messages with delays
- **Server**: Accumulates all messages and responds with a summary
- **Use Case**: Uploading files, batch operations

### 2. Server Streaming (`EchoServerStream`)
- **Client**: Sends 1 request message
- **Server**: Responds with 5 echo messages with delays
- **Use Case**: Real-time notifications, data feeds

### 3. Bidirectional Sync (`EchoBidirectionalStreamSync`)
- **Both**: Exchange messages in real-time
- **Processing**: Each message is processed and responded to immediately
- **Use Case**: Chat applications, real-time collaboration

### 4. Bidirectional Async (`EchoBidirectionalStreamAsync`)
- **Both**: Exchange messages asynchronously
- **Processing**: Uses separate goroutines for sending/receiving with processing delays
- **Use Case**: Complex processing pipelines, background tasks

## Signal Handling

Both server and client handle graceful shutdown:

```bash
# Press Ctrl+C to stop
^C
Received signal: interrupt, initiating graceful shutdown...
Shutdown signal received, waiting for all goroutines to finish...
All goroutines finished gracefully
Client shutdown completed
```

## Client Behavior

The client runs 4 concurrent goroutines, each testing a different streaming method:

- **Client-1**: Tests client streaming (repeats every 5s)
- **Client-2**: Tests server streaming (repeats every 4s) 
- **Client-3**: Tests bidirectional sync (repeats every 6s)
- **Client-4**: Tests bidirectional async (repeats every 7s)

Each client has different timing to demonstrate concurrent streaming.

## Development

### Available Make Targets

```bash
make help                 # Show available commands
make build-server        # Build server binary
make build-client        # Build client binary  
make run-server          # Build and run server
make run-client          # Build and run client
make dev-server          # Run server with go run
make dev-client          # Run client with go run
make start-all           # Start server in background + client
make test                # Quick 30-second test
make clean               # Remove binaries
```

### Testing Individual Methods

You can modify the client to test specific streaming methods by commenting out unwanted goroutines in `main()`.

## Requirements

- Go 1.21+
- gRPC dependencies (automatically downloaded)

## Troubleshooting

### Connection Issues
```bash
# Check if server is running
netstat -ln | grep 8080

# Check server logs
make dev-server
```

### Build Issues
```bash
# Clean and rebuild
make clean
go mod tidy
make build-server build-client
```

## Protocol Buffer Definition

The service is defined in `api/v1/stream/stream.proto`:

```protobuf
service EchoService {
  rpc EchoClientStream(stream EchoRequest) returns (EchoResponse);
  rpc EchoServerStream(EchoRequest) returns (stream EchoResponse);
  rpc EchoBidirectionalStreamSync(stream EchoRequest) returns (stream EchoResponse);
  rpc EchoBidirectionalStreamAsync(stream EchoRequest) returns (stream EchoResponse);
}
```

This demo provides a comprehensive example of gRPC streaming patterns in Go!