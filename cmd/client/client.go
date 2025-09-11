package main

import (
	"context"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/easyp-tech/course-grpc/pkg/api"
)

func main() {
	conn, err := grpc.NewClient(
		"127.0.0.1:5001",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		log.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()

	c := pb.NewEchoServiceClient(conn)

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*2)
	defer cancel()

	// Отправляем первый запрос
	respHelloWorld, err := c.HelloWorld(ctx, &pb.EchoRequest{Message: "ping"})
	if err != nil {
		log.Fatalf("could not greet: %v", err)
	}
	log.Printf("Response Hello World: %s", respHelloWorld.Message)
}
