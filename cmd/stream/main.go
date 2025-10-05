package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"

	"google.golang.org/grpc"

	stream "github.com/easyp-tech/course-grpc/pkg/api/stream/v1"
)

var _ stream.EchoServiceServer = &API{}

type API struct {
	stream.UnimplementedEchoServiceServer
}

// EchoClientStream handles client streaming - receives multiple messages from client, returns one response
func (a *API) EchoClientStream(streamServer stream.EchoService_EchoClientStreamServer) error {
	log.Println("EchoClientStream: Starting client stream")

	var messages []string

	for {
		req, err := streamServer.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("EchoClientStream: Error receiving message: %v", err)
			return err
		}

		log.Printf("EchoClientStream: Received message: %s", req.Message)
		messages = append(messages, req.Message)
	}

	response := &stream.EchoResponse{
		Message: fmt.Sprintf("Received %d messages: %v", len(messages), messages),
	}

	log.Printf("EchoClientStream: Sending response: %s", response.Message)
	return streamServer.SendAndClose(response)
}

// EchoServerStream handles server streaming - receives a message and sends back a stream of responses.
func (a *API) EchoServerStream(req *stream.EchoRequest, streamServer stream.EchoService_EchoServerStreamServer) error {
	log.Printf("EchoServerStream: Received message: %s", req.Message)

	for i := 1; i <= 5; i++ {
		response := &stream.EchoResponse{
			Message: fmt.Sprintf("Echo #%d: %s", i, req.Message),
		}

		log.Printf("EchoServerStream: Sending response #%d: %s", i, response.Message)

		if err := streamServer.Send(response); err != nil {
			log.Printf("EchoServerStream: Error sending response: %v", err)
			return err
		}

		time.Sleep(100 * time.Millisecond)
	}

	log.Println("EchoServerStream: Finished sending responses")
	return nil
}

// EchoBidirectionalStreamSync handles bidirectional streaming with synchronous processing
func (a *API) EchoBidirectionalStreamSync(streamServer stream.EchoService_EchoBidirectionalStreamSyncServer) error {
	log.Println("EchoBidirectionalStreamSync: Starting bidirectional stream (sync)")

	for {
		req, err := streamServer.Recv()
		if err == io.EOF {
			log.Println("EchoBidirectionalStreamSync: Client closed connection")
			return nil
		}
		if err != nil {
			log.Printf("EchoBidirectionalStreamSync: Error receiving message: %v", err)
			return err
		}

		log.Printf("EchoBidirectionalStreamSync: Received message: %s", req.Message)

		response := &stream.EchoResponse{
			Message: fmt.Sprintf("Sync Echo: %s", req.Message),
		}

		if err := streamServer.Send(response); err != nil {
			log.Printf("EchoBidirectionalStreamSync: Error sending response: %v", err)
			return err
		}

		log.Printf("EchoBidirectionalStreamSync: Sent response: %s", response.Message)
	}
}

// EchoBidirectionalStreamAsync handles bidirectional streaming with asynchronous processing
// func (a *API) EchoBidirectionalStreamAsync(streamServer grpc.BidiStreamingServer[stream.EchoRequest, stream.EchoResponse]) error {
func (a *API) EchoBidirectionalStreamAsync(streamServer stream.EchoService_EchoBidirectionalStreamAsyncServer) error {
	log.Println("EchoBidirectionalStreamAsync: Starting bidirectional stream (async)")

	ctx := streamServer.Context()
	requestCh := make(chan *stream.EchoRequest, 10)
	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		defer close(requestCh)

		for {
			req, err := streamServer.Recv()
			if err == io.EOF {
				log.Println("EchoBidirectionalStreamAsync: Client closed connection")
				return
			}
			if err != nil {
				log.Printf("EchoBidirectionalStreamAsync: Error receiving message: %v", err)
				return
			}

			log.Printf("EchoBidirectionalStreamAsync: Received message: %s", req.Message)

			select {
			case requestCh <- req:
			case <-ctx.Done():
				return
			}
		}
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()

		for {
			select {
			case req, ok := <-requestCh:
				if !ok {
					log.Println("EchoBidirectionalStreamAsync: Request channel closed")
					return
				}

				time.Sleep(200 * time.Millisecond)

				response := &stream.EchoResponse{
					Message: fmt.Sprintf("Async Echo (processed): %s", req.Message),
				}

				if err := streamServer.Send(response); err != nil {
					log.Printf("EchoBidirectionalStreamAsync: Error sending response: %v", err)
					return
				}

				log.Printf("EchoBidirectionalStreamAsync: Sent async response: %s", response.Message)

			case <-ctx.Done():
				log.Println("EchoBidirectionalStreamAsync: Context cancelled")
				return
			}
		}
	}()

	wg.Wait()
	log.Println("EchoBidirectionalStreamAsync: Stream finished")
	return nil
}

func main() {
	log.Println("Starting gRPC Echo Stream Server...")

	lis, err := net.Listen("tcp", ":8080")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	s := grpc.NewServer()
	api := &API{}

	stream.RegisterEchoServiceServer(s, api)

	log.Println("gRPC server listening on :8080")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
