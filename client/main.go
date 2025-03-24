package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// TimeRequest represents the request for time updates
type TimeRequest struct {
	UpdateInterval int `json:"UpdateInterval"` // Interval in seconds between updates
	Duration       int `json:"Duration"`       // Total duration in seconds to receive updates (0 for indefinite)
}

// TimeResponse represents a single time update in the stream
type TimeResponse struct {
	Timestamp   int64  `json:"Timestamp"`   // Unix timestamp
	TimeString  string `json:"TimeString"`  // Formatted time string
	SequenceNum int    `json:"SequenceNum"` // Sequence number in the stream
	IsFinal     bool   `json:"IsFinal"`     // Indicates if this is the final message in the stream
}

// connectToServer establishes a connection to the RPC server
func connectToServer(serverAddr string) (net.Conn, error) {
	conn, err := net.Dial("tcp", serverAddr)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to server: %w", err)
	}
	return conn, nil
}

// requestTimeStream initiates a streaming time request
func requestTimeStream(conn net.Conn, interval, duration int) error {
	// Create the request
	request := TimeRequest{
		UpdateInterval: interval,
		Duration:       duration,
	}

	// Encode the request as JSON
	requestBytes, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	// Send the request
	_, err = conn.Write(requestBytes)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}

	return nil
}

func main() {
	// Parse command line flags
	serverAddr := flag.String("server", "localhost:8080", "RPC server address")
	interval := flag.Int("interval", 1, "Update interval in seconds")
	duration := flag.Int("duration", 60, "Total duration in seconds (0 for indefinite)")
	flag.Parse()

	log.Printf("Connecting to server at %s...", *serverAddr)

	// Connect to the server with retry logic
	var conn net.Conn
	var err error
	maxRetries := 5
	retryDelay := time.Second

	for i := 0; i < maxRetries; i++ {
		conn, err = connectToServer(*serverAddr)
		if err == nil {
			break
		}
		log.Printf("Connection attempt %d failed: %v", i+1, err)
		if i < maxRetries-1 {
			log.Printf("Retrying in %v...", retryDelay)
			time.Sleep(retryDelay)
			retryDelay *= 2 // Exponential backoff
		}
	}

	if err != nil {
		log.Fatalf("Failed to connect after %d attempts: %v", maxRetries, err)
	}
	defer conn.Close()

	log.Printf("Connected to server. Requesting time updates every %d second(s) for %d second(s)...", *interval, *duration)

	// Request time updates
	err = requestTimeStream(conn, *interval, *duration)
	if err != nil {
		log.Fatalf("Failed to request time stream: %v", err)
	}

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Process the streaming updates
	updateCount := 0
	done := make(chan struct{})

	// Start a goroutine to read updates from the connection
	go func() {
		defer close(done)
		scanner := bufio.NewScanner(conn)
		for scanner.Scan() {
			// Parse the update
			var update TimeResponse
			err := json.Unmarshal(scanner.Bytes(), &update)
			if err != nil {
				log.Printf("Error parsing update: %v", err)
				continue
			}

			updateCount++
			log.Printf("Time update #%d: %s (Unix timestamp: %d)",
				update.SequenceNum, update.TimeString, update.Timestamp)

			if update.IsFinal {
				log.Println("Stream completed")
				return
			}
		}

		if err := scanner.Err(); err != nil {
			log.Printf("Error reading from server: %v", err)
		}
	}()

	// Wait for completion or interrupt
	select {
	case <-done:
		log.Printf("Received %d time updates", updateCount)
	case sig := <-sigChan:
		log.Printf("Received signal %v, shutting down...", sig)
	}

	log.Println("Client terminated")
}
