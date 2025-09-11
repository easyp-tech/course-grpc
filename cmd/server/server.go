package main

import (
	"context"
	"log"
	"net"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"

	pb "github.com/easyp-tech/course-grpc/pkg/api"
)

const (
	keepaliveTime    = 50 * time.Second
	keepaliveTimeout = 10 * time.Second
	keepaliveMinTime = 30 * time.Second
)

type server struct {
	pb.UnimplementedEchoServiceServer
}

func (s *server) HelloWorld(ctx context.Context, req *pb.EchoRequest) (*pb.EchoResponse, error) {
	log.Printf("Request: %s", req.GetMessage())
	return &pb.EchoResponse{Message: "pong"}, nil
}

func (s *server) WithError(ctx context.Context, in *pb.EchoRequest) (*pb.EchoResponse, error) {
	// формируем кастомную ошибку
	st := status.New(codes.FailedPrecondition, "Custom error")
	errMsg := &pb.CustomError{Reason: "some reason"}

	var err error
	// дополняем ее деталями: которые содержат структуру сообщения из proto файла.
	st, err = st.WithDetails(errMsg)
	if err != nil {
		return nil, err
	}

	return nil, st.Err()
}

func main() {
	l, err := net.Listen("tcp", ":5001")
	if err != nil {
		log.Fatal(err)
	}

	// Создание gRPC сервера с параметрами
	s := grpc.NewServer(
		grpc.Creds(insecure.NewCredentials()),
		grpc.KeepaliveParams(
			keepalive.ServerParameters{ //nolint:exhaustruct
				Time:    keepaliveTime,
				Timeout: keepaliveTimeout,
			},
		),
		grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
			MinTime:             keepaliveMinTime,
			PermitWithoutStream: true,
		}),
	)

	// Регистрируем наш обработчик
	pb.RegisterEchoServiceServer(s, &server{})

	// Создаем healthcheck
	healthServer := health.NewServer()
	// Регистрируем healthcheck
	healthpb.RegisterHealthServer(s, healthServer)

	// Выставляем статус хелсчека
	healthServer.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)

	// Подключаем рефлексию для возможности использовать grpcurl и прочие утилиты для запросов
	reflection.Register(s)

	wg := sync.WaitGroup{}
	// запускаем сам сервер в отдельной горутина
	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Println("Starting server...")

		if err := s.Serve(l); err != nil {
			log.Fatalf("start: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	// ждем сигнал о завершении работы сервера
	<-quit
	log.Println("Shutting down server...")

	// после получения сигнала останавливаем сервер
	s.GracefulStop()
	wg.Wait()
}
