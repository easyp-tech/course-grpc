package main

import (
	"context"
	"log"
	"time"

	"github.com/google/uuid"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	pb "github.com/easyp-tech/course-grpc/pkg/api/v1"
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
		"nginx-proxy:5001",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithChainUnaryInterceptor(interceptorStat),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                10 * time.Second,
			Timeout:             3 * time.Second,
			PermitWithoutStream: true,
		}),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(16*1024*1024),
			grpc.MaxCallSendMsgSize(8*1024*1024),
			grpc.WaitForReady(false),
		),
		grpc.WithReadBufferSize(64*1024),
		grpc.WithWriteBufferSize(64*1024),
	)
	if err != nil {
		log.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()

	c := pb.NewEchoAPIClient(conn)

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*2)
	defer cancel()

	// Отправляем первый запрос
	respHelloWorld, err := c.HelloWorld(ctx, &pb.EchoRequest{Message: "ping123456789"})
	if err != nil {
		log.Fatalf("could not greet: %v", err)
	}
	log.Printf("Response Hello World: %s", respHelloWorld.Message)

	// create request 1
	createOrder1 := &pb.CreateOrder{
		ProductId: uuid.NewString(),
		Count:     15,
	}
	// create request 2
	createOrder2 := &pb.CreateOrder{
		ProductId: uuid.NewString(),
		//ProductId: "dsfsdf",
		Count: 15,
	}
	orders := []*pb.CreateOrder{createOrder1, createOrder2}
	_ = orders

	userEmail := "user@mail.loc"
	_ = userEmail

	userID := uuid.New().String()
	_ = userID

	createOrderRequest := &pb.CreateOrdersRequest{
		CreateOrder: []*pb.CreateOrder{createOrder1, createOrder2},
		UserEmail:   &userEmail,
		//UserId:      &userID,
	}

	resp, err := c.CreateOrder(ctx, createOrderRequest)
	if err != nil {
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
	log.Printf("resp: %v", resp)
}
