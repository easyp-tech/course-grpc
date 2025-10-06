FROM golang:1.24-alpine AS go-builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /bin/stream-server ./cmd/stream

FROM alpine:3.20.3 AS builder

RUN apk update && apk add --no-cache ca-certificates

FROM scratch

WORKDIR /bin

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=go-builder /bin/stream-server stream-server

EXPOSE 8080

ENTRYPOINT ["./stream-server"]
