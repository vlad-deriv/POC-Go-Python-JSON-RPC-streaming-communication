"""
Time Service implementation.

This module provides the TimeService class that handles time update requests
and maintains client state for streaming updates.
"""

import datetime
import threading
import time
from typing import Dict, Any, Optional


class TimeService:
    """
    Time Service that provides streaming time updates to clients.
    
    This service maintains client state to track sequence numbers and
    stream durations for each connected client.
    """
    
    def __init__(self):
        """Initialize the TimeService."""
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def request_time_stream(self, client_id: str, interval: int = 1, duration: int = 0) -> Dict[str, Any]:
        """
        Initialize a time stream for a client.
        
        Args:
            client_id: Unique identifier for the client
            interval: Update interval in seconds
            duration: Total duration in seconds (0 for indefinite)
            
        Returns:
            The initial time update
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
    
    def get_next_update(self, client_id: str) -> Dict[str, Any]:
        """
        Get the next update in the stream for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            The next time update or an error if the stream is not initialized
        """
        if client_id not in self.clients:
            return {'error': 'Stream not initialized'}
        
        return self._generate_update(client_id)
    
    def _generate_update(self, client_id: str) -> Dict[str, Any]:
        """
        Generate a time update for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            A time update dictionary
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