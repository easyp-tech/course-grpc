package main

import (
	"context"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	pb "github.com/easyp-tech/course-grpc/pkg/api"
)

func interceptorStat(
	ctx context.Context,
	method string,
	req, reply interface{},
	cc *grpc.ClientConn,
	invoker grpc.UnaryInvoker,
	opts ...grpc.CallOption,
) error {
	// Pre-processing
	start := time.Now()
	log.Printf("[INTERCEPTOR STAT] Calling: %s", method)

	// Добавляем кастомные заголовки
	ctx = metadata.AppendToOutgoingContext(ctx,
		"client-timestamp", time.Now().Format(time.RFC3339),
		"user-agent", "my-grpc-client/1.0",
	)

	// Вызов сервера
	err := invoker(ctx, method, req, reply, cc, opts...)

	// Post-processing
	duration := time.Since(start)
	if err != nil {
		if st, ok := status.FromError(err); ok {
			log.Printf("[INTERCEPTOR STAT] %s failed after %v: code=%s, message=%s",
				method, duration, st.Code(), st.Message())
		} else {
			log.Printf("[INTERCEPTOR STAT] %s failed after %v: %v", method, duration, err)
		}
	} else {
		log.Printf("[INTERCEPTOR STAT] %s completed in %v", method, duration)
	}

	return err
}

func main() {
	conn, err := grpc.NewClient(
		"127.0.0.1:5001",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithChainUnaryInterceptor(interceptorStat),
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
