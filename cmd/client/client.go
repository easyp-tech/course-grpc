package main

import (
	"context"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"

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

	// Отправляем второй запрос, в котором будет кастомная ошибка
	respWithError, err := c.WithError(ctx, &pb.EchoRequest{Message: "hello world"})
	if err != nil {
		// проверяем что полученная ошибка это ошибка сообщение от сервера gRPC, а не, например, сетевая ошибка
		st, ok := status.FromError(err)
		if !ok {
			log.Fatalf("status.FromError: %v", err)
		}
		log.Printf("Code: %s", st.Code().String())

		for _, d := range st.Details() {
			switch t := d.(type) {
			case *pb.CustomError:
				log.Printf("Reason: %v", t.Reason)
			}
		}
	}

	// тут ожидаемо будет nil, т.к запрос вернул ошибку
	log.Printf("Response WithError: %v", respWithError)
}
