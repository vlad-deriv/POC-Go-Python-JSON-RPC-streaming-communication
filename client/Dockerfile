FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go.mod
COPY go.mod ./

# Copy the source code
COPY main.go .

# Build the application
RUN go build -o time-client .

# Use a smaller image for the final container
FROM alpine:latest

WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/time-client .

# Set the entrypoint
ENTRYPOINT ["./time-client"]

# Default command line arguments
CMD ["-server", "host.docker.internal:8080"]