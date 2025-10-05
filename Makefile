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
