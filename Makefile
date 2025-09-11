LOCAL_BIN:=$(CURDIR)/bin

.PHONY: bin-deps
bin-deps:
	$(info Installing binary dependencies...)
	mkdir -p $(LOCAL_BIN)
	GOBIN=$(LOCAL_BIN) go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.31.0 && \
    GOBIN=$(LOCAL_BIN) go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0 && \
    GOBIN=$(LOCAL_BIN) go install github.com/easyp-tech/easyp/cmd/easyp@v0.7.15
