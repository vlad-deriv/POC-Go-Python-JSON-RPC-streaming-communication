# Microservices Application Specification

## 1. System Overview

This document specifies an application consisting of two microservices:
- **Client Service**: Written in Go, using the standard `net/rpc` library
- **Server Service**: Written in Python, implementing a compatible RPC interface

The primary functionality is a time service where the client makes a single request, and the server responds with a stream of time updates.

## 2. Client Service Specification (Go)

### 2.1 Technology Stack
- **Language**: Go (1.21+)
- **RPC Library**: Standard `net/rpc` package
- **Configuration**: Environment variables and/or config files (YAML/JSON)
- **Logging**: Standard Go `log` package or structured logging with `zap`/`logrus`

### 2.2 Responsibilities
- Establish and maintain RPC connection to the server service
- Make a remote procedure call to request time updates
- Process the streaming response from the server
- Handle connection errors and implement reconnection logic
- Provide clean shutdown mechanism

### 2.3 Implementation Details

#### Connection Management
```go
// Example connection code
import "net/rpc"

func connectToServer(serverAddr string) (*rpc.Client, error) {
    client, err := rpc.DialHTTP("tcp", serverAddr)
    if err != nil {
        return nil, fmt.Errorf("failed to connect to server: %w", err)
    }
    return client, nil
}
```

#### Making RPC Call for Time Stream
Since Go's standard `net/rpc` library doesn't natively support streaming responses, we'll implement a workaround using channels:

```go
// TimeRequest represents the request for time updates
type TimeRequest struct {
    UpdateInterval int // Interval in seconds between updates
    Duration       int // Total duration in seconds to receive updates (0 for indefinite)
}

// TimeResponse represents a single time update in the stream
type TimeResponse struct {
    Timestamp   int64  // Unix timestamp
    TimeString  string // Formatted time string
    SequenceNum int    // Sequence number in the stream
    IsFinal     bool   // Indicates if this is the final message in the stream
}

// TimeStream represents the streaming response channel
type TimeStream struct {
    Updates chan TimeResponse
    Error   error
}

// RequestTimeStream initiates a streaming time request
func RequestTimeStream(client *rpc.Client, interval, duration int) (*TimeStream, error) {
    args := &TimeRequest{
        UpdateInterval: interval,
        Duration:       duration,
    }
    
    stream := &TimeStream{
        Updates: make(chan TimeResponse, 10), // Buffered channel
    }
    
    // Start a goroutine to handle the streaming response
    go func() {
        defer close(stream.Updates)
        
        var response TimeResponse
        for {
            // Call the RPC method to get the next update
            err := client.Call("TimeService.GetNextUpdate", args, &response)
            if err != nil {
                stream.Error = err
                return
            }
            
            // Send the update to the channel
            stream.Updates <- response
            
            // Check if this is the final update
            if response.IsFinal {
                return
            }
        }
    }()
    
    return stream, nil
}
```

#### Client Usage Example
```go
func main() {
    client, err := connectToServer("localhost:8080")
    if err != nil {
        log.Fatalf("Failed to connect: %v", err)
    }
    defer client.Close()
    
    // Request time updates every 1 second for 60 seconds
    stream, err := RequestTimeStream(client, 1, 60)
    if err != nil {
        log.Fatalf("Failed to request time stream: %v", err)
    }
    
    // Process the streaming updates
    for update := range stream.Updates {
        fmt.Printf("Time update #%d: %s\n", update.SequenceNum, update.TimeString)
        
        if update.IsFinal {
            fmt.Println("Stream completed")
            break
        }
    }
    
    if stream.Error != nil {
        log.Fatalf("Stream error: %v", stream.Error)
    }
}
```

## 3. Server Service Specification (Python)

### 3.1 Technology Stack
- **Language**: Python (3.9+)
- **Dependency Management**: Poetry
- **RPC Library**: Custom implementation compatible with Go's `net/rpc` or `jsonrpclib-pelix`
- **Web Framework**: FastAPI or Flask (for additional HTTP endpoints)
- **Configuration**: Environment variables and/or config files (YAML/JSON)
- **Logging**: Standard Python `logging` module or structured logging with `structlog`

### 3.1.1 Poetry Configuration
Poetry will be used for dependency management and packaging. A sample `pyproject.toml` file:

```toml
[tool.poetry]
name = "time-service"
version = "0.1.0"
description = "Python RPC server providing time streaming service"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
jsonrpclib-pelix = "^0.4.2"
structlog = "^23.1.0"
pydantic = "^2.0.0"
python-dotenv = "^1.0.0"

[tool.poetry.dev-dependencies]
pytest = "^7.3.1"
black = "^23.3.0"
isort = "^5.12.0"
mypy = "^1.3.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry.scripts]
start = "time_service.main:main"
```

### 3.2 Responsibilities
- Expose RPC methods that can be called by the Go client
- Implement a time service that provides streaming updates
- Handle client connections and disconnections gracefully
- Provide proper error handling and validation
- Include health check endpoints for monitoring

### 3.3 Implementation Options

#### Option 1: Custom Implementation with Socket Server
```python
# Example custom RPC server compatible with Go's net/rpc
import socket
import json
import threading
import time
import datetime

class TimeService:
    def __init__(self):
        self.sequence_counter = {}  # Track sequence numbers per client
    
    def GetNextUpdate(self, request, client_id):
        # Get or initialize sequence counter for this client
        if client_id not in self.sequence_counter:
            self.sequence_counter[client_id] = 0
        
        # Extract parameters
        interval = request.get('UpdateInterval', 1)
        duration = request.get('Duration', 0)
        
        # Calculate if this should be the final update
        sequence_num = self.sequence_counter[client_id]
        self.sequence_counter[client_id] += 1
        
        is_final = False
        if duration > 0 and sequence_num * interval >= duration:
            is_final = True
        
        # Create the time update
        now = datetime.datetime.now()
        response = {
            'Timestamp': int(time.time()),
            'TimeString': now.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'SequenceNum': sequence_num,
            'IsFinal': is_final
        }
        
        # Simulate the interval (in a real implementation, this would be handled differently)
        time.sleep(interval)
        
        return response

class RPCServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.services = {}
        self.client_counter = 0
        
    def register_service(self, name, service):
        self.services[name] = service
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        
        while True:
            client, addr = server.accept()
            client_id = self.client_counter
            self.client_counter += 1
            print(f"Client {client_id} connected from {addr}")
            threading.Thread(target=self.handle_client, args=(client, client_id)).start()
            
    def handle_client(self, client, client_id):
        # Implementation details to handle Go's net/rpc wire protocol
        # This is a simplified example and would need to be expanded
        # to properly implement the Go net/rpc wire protocol
        try:
            while True:
                # Read request
                data = client.recv(4096)
                if not data:
                    break
                
                # Parse request (simplified)
                request = json.loads(data.decode('utf-8'))
                service_method = request.get('method', '').split('.')
                if len(service_method) != 2:
                    response = {'error': 'Invalid method format'}
                else:
                    service_name, method_name = service_method
                    if service_name not in self.services:
                        response = {'error': f'Service {service_name} not found'}
                    else:
                        service = self.services[service_name]
                        if not hasattr(service, method_name):
                            response = {'error': f'Method {method_name} not found'}
                        else:
                            method = getattr(service, method_name)
                            try:
                                result = method(request.get('params', {}), client_id)
                                response = {'result': result, 'error': None}
                            except Exception as e:
                                response = {'error': str(e)}
                
                # Send response
                client.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
        finally:
            client.close()
            print(f"Client {client_id} disconnected")

# Usage
if __name__ == "__main__":
    server = RPCServer('localhost', 8080)
    time_service = TimeService()
    server.register_service('TimeService', time_service)
    server.start()
```

#### Option 2: Using jsonrpclib-pelix with Custom Streaming
```python
# Example using jsonrpclib-pelix with custom streaming support
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import time
import datetime
import threading

class TimeService:
    def __init__(self):
        self.clients = {}  # Store client state
        self.lock = threading.Lock()
    
    def RequestTimeStream(self, client_id, interval=1, duration=0):
        """
        Initialize a time stream for a client.
        Returns the initial response and stores client state for subsequent calls.
        """
        with self.lock:
            self.clients[client_id] = {
                'sequence': 0,
                'interval': interval,
                'duration': duration,
                'start_time': time.time()
            }
        
        # Return the first update immediately
        return self._generate_update(client_id)
    
    def GetNextUpdate(self, client_id):
        """
        Get the next update in the stream for a client.
        """
        if client_id not in self.clients:
            return {'error': 'Stream not initialized'}
        
        # Simulate waiting for the next interval
        client_data = self.clients[client_id]
        time.sleep(client_data['interval'])
        
        return self._generate_update(client_id)
    
    def _generate_update(self, client_id):
        """
        Generate a time update for a client.
        """
        with self.lock:
            if client_id not in self.clients:
                return {'error': 'Client not found'}
            
            client_data = self.clients[client_id]
            sequence = client_data['sequence']
            client_data['sequence'] += 1
            
            # Check if this should be the final update
            is_final = False
            elapsed_time = time.time() - client_data['start_time']
            if client_data['duration'] > 0 and elapsed_time >= client_data['duration']:
                is_final = True
                # Clean up client data if this is the final update
                if is_final:
                    del self.clients[client_id]
            
            # Create the time update
            now = datetime.datetime.now()
            return {
                'Timestamp': int(time.time()),
                'TimeString': now.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'SequenceNum': sequence,
                'IsFinal': is_final
            }

# Server setup
server = SimpleJSONRPCServer(('localhost', 8080))
time_service = TimeService()

# Register functions
server.register_function(time_service.RequestTimeStream, 'TimeService.RequestTimeStream')
server.register_function(time_service.GetNextUpdate, 'TimeService.GetNextUpdate')

print("Starting server on localhost:8080...")
server.serve_forever()
```

## 4. Communication Protocol

### 4.1 Protocol Details
The Go `net/rpc` package uses a specific wire protocol for communication. To ensure compatibility, the Python server must implement this protocol or use a library that does.

Key aspects of the protocol:
- **Transport**: TCP or HTTP
- **Encoding**: Go's `encoding/gob` by default (binary format)
- **Message Format**: Request/Response with method name, sequence ID, and arguments

### 4.2 Alternative Approach: JSON-RPC
If implementing the exact Go `net/rpc` protocol proves challenging, an alternative is to use JSON-RPC:

1. On the Go side, use `net/rpc/jsonrpc` instead of `net/rpc`
2. On the Python side, use a JSON-RPC library like `jsonrpclib-pelix`

This approach provides better interoperability between the languages.

### 4.3 Streaming Implementation
Since Go's `net/rpc` doesn't natively support streaming, we implement streaming as a series of individual RPC calls:

1. Client makes an initial request to start the stream
2. Server responds with the first update and maintains client state
3. Client makes subsequent calls to get the next update in the stream
4. Server indicates when the stream is complete via the `IsFinal` flag

## 5. API Definition

### 5.1 Time Service Methods

| Method Name | Input Parameters | Return Value | Description |
|-------------|-----------------|--------------|-------------|
| TimeService.RequestTimeStream | {UpdateInterval: int, Duration: int} | TimeResponse | Initiates a time stream and returns the first update |
| TimeService.GetNextUpdate | {} | TimeResponse | Gets the next update in the stream |

### 5.2 Data Structures

#### TimeRequest
```
{
  "UpdateInterval": int,  // Interval in seconds between updates
  "Duration": int         // Total duration in seconds (0 for indefinite)
}
```

#### TimeResponse
```
{
  "Timestamp": int64,    // Unix timestamp
  "TimeString": string,  // Formatted time string
  "SequenceNum": int,    // Sequence number in the stream
  "IsFinal": bool        // Indicates if this is the final message
}
```

## 6. Error Handling

### 6.1 Client-Side Error Handling
The Go client should implement robust error handling:
- Connection errors: Implement reconnection logic with exponential backoff
- RPC call errors: Log errors and potentially retry based on error type
- Stream termination: Handle unexpected stream termination gracefully

### 6.2 Server-Side Error Handling
The Python server should implement proper error handling:
- Invalid requests: Return appropriate error responses
- Resource management: Clean up resources for disconnected clients
- Exception handling: Catch and log exceptions, return error responses to clients

### 6.3 Error Codes and Messages
Define standard error codes and messages for common error scenarios:
- 1001: Connection error
- 1002: Invalid request parameters
- 1003: Stream initialization failed
- 1004: Stream terminated unexpectedly

## 7. Deployment Considerations

### 7.1 Client Service Deployment
- **Containerization**: Package the Go client in a Docker container
- **Configuration**: Use environment variables for server address, update interval, etc.
- **Monitoring**: Implement health checks and metrics for monitoring

### 7.2 Server Service Deployment
- **Dependency Management**: Use Poetry to manage dependencies and create reproducible builds
- **Containerization**: Package the Python server in a Docker container with Poetry
- **Scalability**: Consider using a load balancer for multiple server instances
- **State Management**: Use Redis or similar for shared state in a multi-instance setup
- **Monitoring**: Implement health checks and metrics for monitoring

#### 7.2.1 Poetry-based Deployment
For deploying the Python server with Poetry:

1. **Development Setup**:
   ```bash
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Navigate to the server directory
   cd server
   
   # Install dependencies
   poetry install
   
   # Run the server
   poetry run start
   ```

2. **Docker Deployment**:
   ```dockerfile
   FROM python:3.9-slim

   # Install Poetry
   RUN pip install poetry==1.5.1

   # Configure Poetry to not create a virtual environment inside the container
   RUN poetry config virtualenvs.create false

   # Set working directory
   WORKDIR /app

   # Copy Poetry configuration files
   COPY pyproject.toml poetry.lock* ./

   # Install dependencies
   RUN poetry install --no-dev --no-interaction --no-ansi

   # Copy application code
   COPY . .

   # Expose the port
   EXPOSE 8080

   # Run the application
   CMD ["python", "-m", "time_service.main"]
   ```

### 7.3 Network Configuration
- Ensure proper network configuration to allow communication between services
- Consider using service discovery for dynamic service addressing
- Implement proper security measures (TLS, authentication, etc.)

## 8. Testing Strategy

### 8.1 Unit Testing
- Test individual components in isolation
- Mock external dependencies

### 8.2 Integration Testing
- Test the interaction between client and server
- Verify streaming behavior works as expected

### 8.3 Load Testing
- Test the system under high load
- Verify performance and resource usage

## 9. Implementation Roadmap

### 9.1 Phase 1: Basic Implementation
- Implement basic client and server with single request/response
- Establish communication between Go and Python services

### 9.2 Phase 2: Streaming Implementation
- Implement streaming time updates
- Add error handling and reconnection logic

### 9.3 Phase 3: Production Readiness
- Add monitoring and metrics
- Implement containerization and deployment scripts
- Complete documentation
