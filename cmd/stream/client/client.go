package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	stream "github.com/easyp-tech/course-grpc/pkg/api/stream/v1"
)

type Client struct {
	conn   *grpc.ClientConn
	client stream.EchoServiceClient
}

func NewClient(addr string) (*Client, error) {
	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("failed to connect: %w", err)
	}

	client := stream.NewEchoServiceClient(conn)

	return &Client{
		conn:   conn,
		client: client,
	}, nil
}

func (c *Client) Close() error {
	return c.conn.Close()
}

// testClientStream tests client streaming
func (c *Client) testClientStream(ctx context.Context, clientID int) error {
	log.Printf("[Client-%d] Starting client stream test", clientID)

	streamClient, err := c.client.EchoClientStream(ctx)
	if err != nil {
		return fmt.Errorf("failed to create client stream: %w", err)
	}

	// Send multiple messages
	messages := []string{
		fmt.Sprintf("Hello from client-%d message-1", clientID),
		fmt.Sprintf("Hello from client-%d message-2", clientID),
		fmt.Sprintf("Hello from client-%d message-3", clientID),
	}

	for i, msg := range messages {
		select {
		case <-ctx.Done():
			log.Printf("[Client-%d] Context cancelled during client stream send", clientID)
			return ctx.Err()
		default:
		}

		if err := streamClient.Send(&stream.EchoRequest{Message: msg}); err != nil {
			return fmt.Errorf("failed to send message %d: %w", i, err)
		}
		log.Printf("[Client-%d] Sent: %s", clientID, msg)
		time.Sleep(500 * time.Millisecond)
	}

	// Close and receive response
	resp, err := streamClient.CloseAndRecv()
	if err != nil {
		return fmt.Errorf("failed to close and receive: %w", err)
	}

	log.Printf("[Client-%d] Client stream response: %s", clientID, resp.Message)
	return nil
}

// testServerStream tests server streaming
func (c *Client) testServerStream(ctx context.Context, clientID int) error {
	log.Printf("[Client-%d] Starting server stream test", clientID)

	req := &stream.EchoRequest{
		Message: fmt.Sprintf("Hello from client-%d for server stream", clientID),
	}

	streamClient, err := c.client.EchoServerStream(ctx, req)
	if err != nil {
		return fmt.Errorf("failed to create server stream: %w", err)
	}

	log.Printf("[Client-%d] Sent request: %s", clientID, req.Message)

	// Receive multiple responses
	for {
		select {
		case <-ctx.Done():
			log.Printf("[Client-%d] Context cancelled during server stream receive", clientID)
			return ctx.Err()
		default:
		}

		resp, err := streamClient.Recv()
		if err == io.EOF {
			log.Printf("[Client-%d] Server stream finished", clientID)
			break
		}
		if err != nil {
			return fmt.Errorf("failed to receive from server stream: %w", err)
		}

		log.Printf("[Client-%d] Server stream response: %s", clientID, resp.Message)
	}

	return nil
}

// testBidirectionalStreamSync tests bidirectional streaming (sync)
func (c *Client) testBidirectionalStreamSync(ctx context.Context, clientID int) error {
	log.Printf("[Client-%d] Starting bidirectional stream sync test", clientID)

	streamClient, err := c.client.EchoBidirectionalStreamSync(ctx)
	if err != nil {
		return fmt.Errorf("failed to create bidirectional stream: %w", err)
	}

	// Send messages and receive responses concurrently
	var wg sync.WaitGroup
	errCh := make(chan error, 2)

	// Sender goroutine
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer streamClient.CloseSend()

		messages := []string{
			fmt.Sprintf("Sync message 1 from client-%d", clientID),
			fmt.Sprintf("Sync message 2 from client-%d", clientID),
			fmt.Sprintf("Sync message 3 from client-%d", clientID),
		}

		for i, msg := range messages {
			select {
			case <-ctx.Done():
				errCh <- ctx.Err()
				return
			default:
			}

			if err := streamClient.Send(&stream.EchoRequest{Message: msg}); err != nil {
				errCh <- fmt.Errorf("failed to send sync message %d: %w", i, err)
				return
			}
			log.Printf("[Client-%d] Sent sync: %s", clientID, msg)
			time.Sleep(1 * time.Second)
		}
	}()

	// Receiver goroutine
	wg.Add(1)
	go func() {
		defer wg.Done()

		for {
			select {
			case <-ctx.Done():
				errCh <- ctx.Err()
				return
			default:
			}

			resp, err := streamClient.Recv()
			if err == io.EOF {
				log.Printf("[Client-%d] Bidirectional sync stream finished", clientID)
				return
			}
			if err != nil {
				errCh <- fmt.Errorf("failed to receive from sync stream: %w", err)
				return
			}

			log.Printf("[Client-%d] Sync response: %s", clientID, resp.Message)
		}
	}()

	// Wait for completion or error
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		return nil
	case err := <-errCh:
		return err
	case <-ctx.Done():
		return ctx.Err()
	}
}

// testBidirectionalStreamAsync tests bidirectional streaming (async)
func (c *Client) testBidirectionalStreamAsync(ctx context.Context, clientID int) error {
	log.Printf("[Client-%d] Starting bidirectional stream async test", clientID)

	streamClient, err := c.client.EchoBidirectionalStreamAsync(ctx)
	if err != nil {
		return fmt.Errorf("failed to create async bidirectional stream: %w", err)
	}

	var wg sync.WaitGroup
	errCh := make(chan error, 2)

	// Sender goroutine
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer streamClient.CloseSend()

		messages := []string{
			fmt.Sprintf("Async message 1 from client-%d", clientID),
			fmt.Sprintf("Async message 2 from client-%d", clientID),
			fmt.Sprintf("Async message 3 from client-%d", clientID),
		}

		for i, msg := range messages {
			select {
			case <-ctx.Done():
				errCh <- ctx.Err()
				return
			default:
			}

			if err := streamClient.Send(&stream.EchoRequest{Message: msg}); err != nil {
				errCh <- fmt.Errorf("failed to send async message %d: %w", i, err)
				return
			}
			log.Printf("[Client-%d] Sent async: %s", clientID, msg)
			time.Sleep(800 * time.Millisecond)
		}
	}()

	// Receiver goroutine
	wg.Add(1)
	go func() {
		defer wg.Done()

		for {
			select {
			case <-ctx.Done():
				errCh <- ctx.Err()
				return
			default:
			}

			resp, err := streamClient.Recv()
			if err == io.EOF {
				log.Printf("[Client-%d] Bidirectional async stream finished", clientID)
				return
			}
			if err != nil {
				errCh <- fmt.Errorf("failed to receive from async stream: %w", err)
				return
			}

			log.Printf("[Client-%d] Async response: %s", clientID, resp.Message)
		}
	}()

	// Wait for completion or error
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		return nil
	case err := <-errCh:
		return err
	case <-ctx.Done():
		return ctx.Err()
	}
}

func main() {
	log.Println("Starting gRPC Echo Stream Client...")

	// Create client
	client, err := NewClient("localhost:8080")
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer func() {
		if err := client.Close(); err != nil {
			log.Printf("Failed to close client connection: %v", err)
		}
	}()

	// Setup signal handling
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		log.Printf("Received signal: %v, initiating graceful shutdown...", sig)
		cancel()
	}()

	// Start all streaming methods in separate goroutines
	var wg sync.WaitGroup
	clientID := 1

	// Test Client Stream
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			select {
			case <-ctx.Done():
				log.Printf("[Client-%d] Client stream test cancelled", clientID)
				return
			default:
			}

			if err := client.testClientStream(ctx, clientID); err != nil {
				if ctx.Err() != nil {
					return // Context was cancelled
				}
				log.Printf("[Client-%d] Client stream error: %v", clientID, err)
			}

			// Wait before next iteration
			select {
			case <-ctx.Done():
				return
			case <-time.After(5 * time.Second):
			}
		}
	}()

	// Test Server Stream
	wg.Add(1)
	go func() {
		defer wg.Done()
		clientID := 2
		for {
			select {
			case <-ctx.Done():
				log.Printf("[Client-%d] Server stream test cancelled", clientID)
				return
			default:
			}

			if err := client.testServerStream(ctx, clientID); err != nil {
				if ctx.Err() != nil {
					return // Context was cancelled
				}
				log.Printf("[Client-%d] Server stream error: %v", clientID, err)
			}

			// Wait before next iteration
			select {
			case <-ctx.Done():
				return
			case <-time.After(4 * time.Second):
			}
		}
	}()

	// Test Bidirectional Stream Sync
	wg.Add(1)
	go func() {
		defer wg.Done()
		clientID := 3
		for {
			select {
			case <-ctx.Done():
				log.Printf("[Client-%d] Bidirectional sync test cancelled", clientID)
				return
			default:
			}

			if err := client.testBidirectionalStreamSync(ctx, clientID); err != nil {
				if ctx.Err() != nil {
					return // Context was cancelled
				}
				log.Printf("[Client-%d] Bidirectional sync error: %v", clientID, err)
			}

			// Wait before next iteration
			select {
			case <-ctx.Done():
				return
			case <-time.After(6 * time.Second):
			}
		}
	}()

	// Test Bidirectional Stream Async
	wg.Add(1)
	go func() {
		defer wg.Done()
		clientID := 4
		for {
			select {
			case <-ctx.Done():
				log.Printf("[Client-%d] Bidirectional async test cancelled", clientID)
				return
			default:
			}

			if err := client.testBidirectionalStreamAsync(ctx, clientID); err != nil {
				if ctx.Err() != nil {
					return // Context was cancelled
				}
				log.Printf("[Client-%d] Bidirectional async error: %v", clientID, err)
			}

			// Wait before next iteration
			select {
			case <-ctx.Done():
				return
			case <-time.After(7 * time.Second):
			}
		}
	}()

	log.Println("All streaming clients started. Press Ctrl+C to stop...")

	// Wait for cancellation
	<-ctx.Done()
	log.Println("Shutdown signal received, waiting for all goroutines to finish...")

	// Wait for all goroutines to finish with timeout
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Println("All goroutines finished gracefully")
	case <-time.After(10 * time.Second):
		log.Println("Timeout waiting for goroutines to finish")
	}

	log.Println("Client shutdown completed")
}
