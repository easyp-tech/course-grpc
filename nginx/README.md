# Nginx Reverse Proxy Configuration

This directory contains the nginx configuration for load balancing and reverse proxying gRPC services.

## Architecture

```
Client -> Nginx Proxy -> Load Balanced gRPC Servers
```

- **Nginx Proxy**: Handles incoming requests and distributes them across multiple server instances
- **Main gRPC Servers**: 2 instances of the main gRPC service (port 5001)
- **Stream gRPC Servers**: 2 instances of the streaming gRPC service (port 8080)

## Configuration Details

### Load Balancing

The nginx configuration includes two upstream groups:

1. **grpc_backend**: Load balances between `grpc-server-1` and `grpc-server-2`
2. **stream_backend**: Load balances between `stream-server-1` and `stream-server-2`

Both use round-robin load balancing by default with keepalive connections.

### Ports

- **5001**: Main gRPC service proxy (HTTP/2)
- **8080**: Stream gRPC service proxy (HTTP/2)
- **80**: Health check endpoint (HTTP/1.1)

### Features

- **HTTP/2 Support**: Required for gRPC communication
- **Keepalive Connections**: Maintains persistent connections to backend servers
- **Error Handling**: Custom gRPC error responses for 502, 503, 504 errors
- **Health Checks**: Simple HTTP health endpoint at `/health`
- **Streaming Support**: Optimized for gRPC streaming with disabled buffering
- **Proper Headers**: Forwards client information to backend servers

## Files

- `nginx.conf`: Main nginx configuration with gRPC load balancing
- `Dockerfile`: Container build configuration for nginx
- `README.md`: This documentation file

## Usage with Docker Compose

### Start all servers with load balancing:
```bash
make compose-up-servers
# or
docker-compose up --build -d nginx-proxy grpc-server-1 grpc-server-2 stream-server-1 stream-server-2
```

### Start with clients:
```bash
make compose-up-with-clients
# or
docker-compose --profile clients up --build -d
```

### Check nginx logs:
```bash
make nginx-logs
# or
docker-compose logs -f nginx-proxy
```

### Test health endpoint:
```bash
make test-nginx-health
# or
curl -f http://localhost:80/health
```

## Testing Load Balancing

You can verify load balancing is working by:

1. **Checking nginx logs**: Each request should show which backend server handled it
2. **Server identification**: Each server instance has a `SERVER_ID` environment variable
3. **Multiple requests**: Send several requests and observe distribution

### Example gRPC client test:
```bash
# Multiple requests will be distributed across backend servers
for i in {1..10}; do
  grpcurl -plaintext -d '{"message": "test '$i'"}' localhost:5001 easyp.tech.course_grpc.v1.EchoAPI/HelloWorld
done
```

## Error Handling

The configuration includes proper gRPC error handling:

- **502 (Bad Gateway)**: Returns gRPC status 14 (UNAVAILABLE)
- **503 (Service Unavailable)**: Returns gRPC status 14 (UNAVAILABLE)  
- **504 (Gateway Timeout)**: Returns gRPC status 4 (DEADLINE_EXCEEDED)

## Performance Tuning

### Connection Settings:
- `keepalive 32`: Maintains 32 idle connections per upstream
- `grpc_connect_timeout 60s`: Connection timeout to backend
- `grpc_send_timeout 60s`: Send timeout to backend
- `grpc_read_timeout 60s`: Read timeout from backend

### Streaming Optimizations:
- `proxy_buffering off`: Disables response buffering for real-time streaming
- `proxy_request_buffering off`: Disables request buffering for streaming uploads

## Monitoring

### Health Check:
```bash
curl http://localhost:80/health
# Should return: healthy
```

### Access Logs:
Nginx logs all requests with timestamps, response codes, and backend information.

### Error Logs:
Any nginx-level errors are logged to `/var/log/nginx/error.log` inside the container.

## Security Considerations

Current configuration is for development/testing. For production:

1. **Enable TLS**: Add SSL certificates and configure HTTPS
2. **Authentication**: Add JWT or basic auth if needed
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **IP Filtering**: Restrict access to specific IP ranges if required

## Scaling

To scale the backend servers:

```bash
# Scale main gRPC servers
docker-compose up --scale grpc-server-1=3 --scale grpc-server-2=3 -d

# Scale stream servers  
docker-compose up --scale stream-server-1=3 --scale stream-server-2=3 -d
```

Note: You'll need to update the nginx configuration to include additional upstream servers when scaling beyond the current 2 instances per service.

## Troubleshooting

### Common Issues:

1. **Connection refused**: Check if backend servers are running
2. **502 errors**: Backend servers may be down or unreachable
3. **Timeouts**: Increase timeout values in nginx.conf if needed

### Debug Commands:
```bash
# Check nginx configuration
docker-compose exec nginx-proxy nginx -t

# Reload nginx configuration
docker-compose exec nginx-proxy nginx -s reload

# View real-time logs
docker-compose logs -f nginx-proxy
```
