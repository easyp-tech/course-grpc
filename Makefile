LOCAL_BIN:=$(CURDIR)/bin

.PHONY: bin-deps
bin-deps:
	$(info Installing binary dependencies...)
	mkdir -p $(LOCAL_BIN)
	GOBIN=$(LOCAL_BIN) go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.31.0 && \
    GOBIN=$(LOCAL_BIN) go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0 && \
    GOBIN=$(LOCAL_BIN) go install github.com/easyp-tech/easyp/cmd/easyp@v0.7.15 && \
    GOBIN=$(LOCAL_BIN) go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest && \
    GOBIN=$(LOCAL_BIN) go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2

.PHONY: gen-protoc
gen-protoc:
	protoc -I . -I api \
	--plugin=protoc-gen-go=$(LOCAL_BIN)/protoc-gen-go --go_out=./pkg --go_opt=paths=source_relative \
    --plugin=protoc-gen-go-grpc=$(LOCAL_BIN)/protoc-gen-go-grpc --go-grpc_out=./pkg --go-grpc_opt=paths=source_relative \
	api/v1/service.proto

# Docker commands
.PHONY: docker-build-server
docker-build-server:
	docker build -f ./cmd/server/Dockerfile -t grpc-server:latest .

.PHONY: docker-build-stream
docker-build-stream:
	docker build -f ./cmd/stream/Dockerfile -t stream-server:latest .

.PHONY: docker-build-client
docker-build-client:
	docker build -f ./cmd/client/Dockerfile -t grpc-client:latest .

.PHONY: docker-build-stream-client
docker-build-stream-client:
	docker build -f ./cmd/stream/client/Dockerfile -t stream-client:latest .



.PHONY: docker-run-server
docker-run-server:
	docker run --rm -p 5001:5001 --name grpc-server grpc-server:latest

.PHONY: docker-run-stream
docker-run-stream:
	docker run --rm -p 8080:8080 --name stream-server stream-server:latest

.PHONY: docker-run-client
docker-run-client:
	docker run --rm --network host --name grpc-client grpc-client:latest

.PHONY: docker-run-stream-client
docker-run-stream-client:
	docker run --rm --network host --name stream-client stream-client:latest

.PHONY: compose-up
compose-up:
	docker-compose up --build -d

.PHONY: compose-up-with-clients
compose-up-with-clients:
	docker-compose --profile clients up --build -d

.PHONY: compose-down
compose-down:
	docker-compose down

.PHONY: compose-logs
compose-logs:
	docker-compose logs -f

.PHONY: docker-build-nginx
docker-build-nginx:
	docker build -f ./nginx/Dockerfile -t nginx-proxy:latest ./nginx

.PHONY: docker-build-all
docker-build-all: docker-build-server docker-build-stream docker-build-client docker-build-stream-client docker-build-nginx

.PHONY: compose-up-servers
compose-up-servers:
	docker-compose up --build -d nginx-proxy grpc-server-1 grpc-server-2 stream-server-1 stream-server-2

.PHONY: compose-up-with-clients
compose-up-with-clients:
	docker-compose --profile clients up --build -d

.PHONY: compose-scale-grpc
compose-scale-grpc:
	docker-compose up --scale grpc-server-1=2 --scale grpc-server-2=2 -d

.PHONY: compose-scale-stream
compose-scale-stream:
	docker-compose up --scale stream-server-1=2 --scale stream-server-2=2 -d

.PHONY: nginx-logs
nginx-logs:
	docker-compose logs -f nginx-proxy

.PHONY: test-nginx-health
test-nginx-health:
	curl -f http://localhost:80/health

.PHONY: test-load-balancing
test-load-balancing:
	./test-load-balancing.sh



.PHONY: docker-clean
docker-clean:
	docker-compose down --rmi all --volumes --remove-orphans
	docker image prune -f
