# Time Streaming Microservices

This project consists of two microservices:
1. A Go client using the standard `net/rpc` library
2. A Python server implementing a compatible RPC interface

The primary functionality is a time service where the client makes a single request, and the server responds with a stream of time updates.

## Project Structure

```
.
├── client/             # Go client service
│   ├── go.mod          # Go module definition
│   └── main.go         # Client implementation
├── server/             # Python server service
│   ├── pyproject.toml  # Poetry configuration
│   └── time_service/   # Python package
│       ├── __init__.py
│       ├── main.py     # Server entry point
│       └── service.py  # Time service implementation
└── specs.md            # Project specifications
```

## Prerequisites

- Go 1.21 or later
- Python 3.9 or later
- Poetry (Python dependency management)

## Setup Instructions

### Go Client

1. Navigate to the client directory:
   ```bash
   cd client
   ```

2. Build the client:
   ```bash
   go build -o time-client
   ```

### Python Server

1. Navigate to the server directory:
   ```bash
   cd server
   ```

2. Install dependencies using Poetry:
   ```bash
   # Install Poetry if not already installed
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install
   ```

## Running the Services

### Start the Python Server

1. Navigate to the server directory:
   ```bash
   cd server
   ```

2. Run the server using Poetry:
   ```bash
   poetry run python -m time_service.main
   ```

   Optional arguments:
   - `--host`: Host to bind the server to (default: localhost)
   - `--port`: Port to bind the server to (default: 8080)

### Run the Go Client

1. Navigate to the client directory:
   ```bash
   cd client
   ```

2. Run the client:
   ```bash
   ./time-client
   ```

   Optional flags:
   - `-server`: RPC server address (default: localhost:8080)
   - `-interval`: Update interval in seconds (default: 1)
   - `-duration`: Total duration in seconds, 0 for indefinite (default: 60)

## Example Usage

1. Start the server in one terminal:
   ```bash
   cd server
   poetry run python -m time_service.main
   ```

2. Run the client in another terminal:
   ```bash
   cd client
   ./time-client -interval 2 -duration 30
   ```

   This will request time updates every 2 seconds for a total duration of 30 seconds.

## Docker Deployment

### Build and Run the Server

```bash
cd server
docker build -t time-service-server .
docker run -p 8080:8080 time-service-server
```

### Build and Run the Client

```bash
cd client
docker build -t time-service-client .
docker run --network="host" time-service-client
```

## License

This project is open source and available under the [MIT License](LICENSE).