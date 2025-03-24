"""
Main entry point for the Time Service server.

This module sets up and runs a custom TCP server that provides
time streaming functionality to Go clients.
"""

import argparse
import json
import logging
import os
import signal
import socket
import socketserver
import sys
import threading
import time
from typing import Dict, Any, Optional

import structlog

from time_service.service import TimeService


# Configure structured logging
def configure_logging():
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler)


class TimeStreamHandler(socketserver.BaseRequestHandler):
    """
    Handler for time streaming connections.
    
    This handler reads a single request from the client and then
    sends periodic time updates until the specified duration is reached.
    """
    
    time_service = None
    client_counter = 0
    client_ids = {}
    log = None
    
    def handle(self):
        """Handle a client connection."""
        # Get client ID
        client_addr = self.client_address[0]
        client_id = self.get_client_id(client_addr)
        
        self.log.info("Client connected", client_id=client_id, address=client_addr)
        
        try:
            # Read the request
            data = self.request.recv(1024)
            if not data:
                self.log.warning("Empty request received", client_id=client_id)
                return
            
            # Parse the request
            try:
                request = json.loads(data.decode('utf-8'))
                interval = request.get('UpdateInterval', 1)
                duration = request.get('Duration', 0)
                self.log.info("Received time stream request", 
                             client_id=client_id, 
                             interval=interval, 
                             duration=duration)
            except json.JSONDecodeError:
                self.log.error("Invalid JSON request", client_id=client_id)
                return
            
            # Initialize the time stream
            self.time_service.request_time_stream(client_id, interval, duration)
            
            # Send periodic updates
            start_time = time.time()
            sequence = 0
            
            while True:
                # Check if we've reached the duration
                elapsed_time = time.time() - start_time
                if duration > 0 and elapsed_time >= duration:
                    # Send final update
                    update = {
                        'Timestamp': int(time.time()),
                        'TimeString': time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                        'SequenceNum': sequence,
                        'IsFinal': True
                    }
                    self.send_update(update, client_id)
                    break
                
                # Generate and send update
                update = self.time_service.get_next_update(client_id)
                self.send_update(update, client_id)
                
                # Increment sequence and wait for next interval
                sequence += 1
                time.sleep(interval)
                
        except ConnectionError as e:
            self.log.error("Connection error", client_id=client_id, error=str(e))
        except Exception as e:
            self.log.error("Error handling client", client_id=client_id, error=str(e))
        finally:
            self.log.info("Client disconnected", client_id=client_id)
    
    def send_update(self, update: Dict[str, Any], client_id: str):
        """Send a time update to the client."""
        try:
            # Convert update to JSON and send
            update_json = json.dumps(update)
            self.request.sendall((update_json + '\n').encode('utf-8'))
            self.log.info("Sent update", client_id=client_id, update=update)
        except Exception as e:
            self.log.error("Error sending update", client_id=client_id, error=str(e))
            raise
    
    def get_client_id(self, client_addr: str) -> str:
        """
        Get or create a client ID for the given address.
        
        Args:
            client_addr: Client address string
            
        Returns:
            A unique client ID
        """
        if client_addr not in self.client_ids:
            self.client_ids[client_addr] = self.client_counter
            self.client_counter += 1
        
        return f"client_{self.client_ids[client_addr]}"


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP server to handle multiple clients."""
    allow_reuse_address = True


def main():
    """Run the Time Service server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Time Service TCP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind the server to')
    args = parser.parse_args()
    
    # Configure logging
    configure_logging()
    log = structlog.get_logger()
    
    # Create the time service
    time_service = TimeService()
    
    # Set up the handler class with the time service
    TimeStreamHandler.time_service = time_service
    TimeStreamHandler.log = log
    
    # Create and start the server
    server = ThreadedTCPServer((args.host, args.port), TimeStreamHandler)
    
    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        log.info("Shutting down server...")
        server.shutdown()
        log.info("Server shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    log.info(f"Starting Time Service server on {args.host}:{args.port}...")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Server stopped by keyboard interrupt")
    except Exception as e:
        log.error("Server error", error=str(e))
    finally:
        server.shutdown()
        log.info("Server shutdown complete")


if __name__ == "__main__":
    main()