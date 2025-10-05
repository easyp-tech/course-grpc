#!/usr/bin/env python3
"""
gRPC Stream Client implementation in Python.
Tests all streaming patterns: client streaming, server streaming, and bidirectional streaming.
"""

import asyncio
import logging
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator, List, Optional
import random

import grpc

# Import generated protobuf/grpc code
from api.stream.v1 import stream_pb2
from api.stream.v1 import stream_pb2_grpc


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class StreamClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor,
):
    """Client interceptor for logging all types of RPC calls."""

    def intercept_unary_unary(self, continuation, client_call_details, request):
        start_time = time.time()
        response = continuation(client_call_details, request)
        duration = time.time() - start_time
        logger.info(
            f"[INTERCEPTOR] {client_call_details.method} (unary-unary) completed in {duration:.3f}s"
        )
        return response

    def intercept_unary_stream(self, continuation, client_call_details, request):
        logger.info(
            f"[INTERCEPTOR] Starting {client_call_details.method} (unary-stream)"
        )
        return continuation(client_call_details, request)

    def intercept_stream_unary(
        self, continuation, client_call_details, request_iterator
    ):
        start_time = time.time()
        response = continuation(client_call_details, request_iterator)
        duration = time.time() - start_time
        logger.info(
            f"[INTERCEPTOR] {client_call_details.method} (stream-unary) completed in {duration:.3f}s"
        )
        return response

    def intercept_stream_stream(
        self, continuation, client_call_details, request_iterator
    ):
        logger.info(
            f"[INTERCEPTOR] Starting {client_call_details.method} (stream-stream)"
        )
        return continuation(client_call_details, request_iterator)


class EchoStreamClient:
    """Client for testing all streaming patterns."""

    def __init__(self, server_address: str = "localhost:8080"):
        """
        Initialize the client.

        Args:
            server_address: Server address in format "host:port"
        """
        self.server_address = server_address

        # Create intercepted channel
        channel = grpc.insecure_channel(
            server_address,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
            ],
        )

        self.channel = grpc.intercept_channel(channel, StreamClientInterceptor())
        self.stub = stream_pb2_grpc.EchoServiceStub(self.channel)
        self.client_id = None

    def close(self):
        """Close the client connection."""
        self.channel.close()

    def test_client_stream(self, client_id: int, num_messages: int = 3) -> bool:
        """
        Test client streaming - send multiple messages, receive one response.

        Args:
            client_id: Client identifier
            num_messages: Number of messages to send

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[Client-{client_id}] Starting client stream test")

        def generate_requests():
            """Generator function for client requests."""
            for i in range(1, num_messages + 1):
                message = f"Hello from client-{client_id} message-{i}"
                logger.info(f"[Client-{client_id}] Sending: {message}")
                yield stream_pb2.EchoRequest(message=message)
                time.sleep(0.5)  # Small delay between messages

        try:
            # Call client streaming RPC
            response = self.stub.EchoClientStream(generate_requests())
            logger.info(
                f"[Client-{client_id}] Client stream response: {response.message}"
            )
            return True

        except grpc.RpcError as e:
            logger.error(
                f"[Client-{client_id}] Client stream error: {e.code()}: {e.details()}"
            )
            return False

    def test_server_stream(self, client_id: int) -> bool:
        """
        Test server streaming - send one message, receive multiple responses.

        Args:
            client_id: Client identifier

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[Client-{client_id}] Starting server stream test")

        request = stream_pb2.EchoRequest(
            message=f"Hello from client-{client_id} for server stream"
        )

        try:
            logger.info(f"[Client-{client_id}] Sent request: {request.message}")

            # Call server streaming RPC
            response_stream = self.stub.EchoServerStream(request)

            # Receive all responses
            response_count = 0
            for response in response_stream:
                response_count += 1
                logger.info(
                    f"[Client-{client_id}] Server stream response #{response_count}: {response.message}"
                )

            logger.info(
                f"[Client-{client_id}] Server stream finished, received {response_count} responses"
            )
            return True

        except grpc.RpcError as e:
            logger.error(
                f"[Client-{client_id}] Server stream error: {e.code()}: {e.details()}"
            )
            return False

    def test_bidirectional_stream_sync(
        self, client_id: int, num_messages: int = 3
    ) -> bool:
        """
        Test bidirectional streaming with synchronous pattern.

        Args:
            client_id: Client identifier
            num_messages: Number of messages to send

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[Client-{client_id}] Starting bidirectional stream sync test")

        def generate_requests():
            """Generator function for client requests."""
            for i in range(1, num_messages + 1):
                message = f"Sync message {i} from client-{client_id}"
                logger.info(f"[Client-{client_id}] Sending sync: {message}")
                yield stream_pb2.EchoRequest(message=message)
                time.sleep(1.0)  # Delay between messages

        try:
            # Call bidirectional streaming RPC
            response_stream = self.stub.EchoBidirectionalStreamSync(generate_requests())

            # Receive all responses
            response_count = 0
            for response in response_stream:
                response_count += 1
                logger.info(
                    f"[Client-{client_id}] Sync response #{response_count}: {response.message}"
                )

            logger.info(f"[Client-{client_id}] Bidirectional sync stream finished")
            return True

        except grpc.RpcError as e:
            logger.error(
                f"[Client-{client_id}] Bidirectional sync error: {e.code()}: {e.details()}"
            )
            return False

    def test_bidirectional_stream_async(
        self, client_id: int, num_messages: int = 3
    ) -> bool:
        """
        Test bidirectional streaming with asynchronous pattern.
        Uses separate threads for sending and receiving.

        Args:
            client_id: Client identifier
            num_messages: Number of messages to send

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[Client-{client_id}] Starting bidirectional stream async test")

        # Event to coordinate threads
        stop_event = threading.Event()
        send_complete = threading.Event()
        success = True

        def send_requests():
            """Thread function for sending requests."""
            try:
                for i in range(1, num_messages + 1):
                    if stop_event.is_set():
                        break

                    message = f"Async message {i} from client-{client_id}"
                    logger.info(f"[Client-{client_id}] Sending async: {message}")
                    yield stream_pb2.EchoRequest(message=message)
                    time.sleep(0.8)  # Delay between messages

            except Exception as e:
                logger.error(f"[Client-{client_id}] Error sending async requests: {e}")
            finally:
                send_complete.set()
                logger.info(f"[Client-{client_id}] Finished sending async requests")

        def receive_responses(response_stream):
            """Thread function for receiving responses."""
            nonlocal success
            try:
                response_count = 0
                for response in response_stream:
                    if stop_event.is_set():
                        break
                    response_count += 1
                    logger.info(
                        f"[Client-{client_id}] Async response #{response_count}: {response.message}"
                    )

                logger.info(f"[Client-{client_id}] Finished receiving async responses")

            except grpc.RpcError as e:
                logger.error(
                    f"[Client-{client_id}] Error receiving async responses: {e.code()}: {e.details()}"
                )
                success = False
            except Exception as e:
                logger.error(
                    f"[Client-{client_id}] Unexpected error receiving async responses: {e}"
                )
                success = False

        try:
            # Start bidirectional stream
            response_stream = self.stub.EchoBidirectionalStreamAsync(send_requests())

            # Start receiver thread
            receiver_thread = threading.Thread(
                target=receive_responses, args=(response_stream,), daemon=True
            )
            receiver_thread.start()

            # Wait for sending to complete
            send_complete.wait(timeout=10)

            # Wait a bit more for responses
            time.sleep(2)

            # Signal stop and wait for receiver
            stop_event.set()
            receiver_thread.join(timeout=5)

            logger.info(f"[Client-{client_id}] Bidirectional async stream finished")
            return success

        except grpc.RpcError as e:
            logger.error(
                f"[Client-{client_id}] Bidirectional async error: {e.code()}: {e.details()}"
            )
            return False
        except Exception as e:
            logger.error(f"[Client-{client_id}] Unexpected error in async stream: {e}")
            return False


def run_client_tests(client_id: int, server_address: str, stop_event: threading.Event):
    """
    Run all streaming tests for a single client.

    Args:
        client_id: Client identifier
        server_address: Server address
        stop_event: Event to signal stop
    """
    client = EchoStreamClient(server_address)

    try:
        while not stop_event.is_set():
            # Determine which test to run based on client_id
            if client_id == 1:
                # Client Stream Test
                success = client.test_client_stream(client_id)
                if not success:
                    logger.warning(f"[Client-{client_id}] Client stream test failed")
                time.sleep(5)  # Wait before next iteration

            elif client_id == 2:
                # Server Stream Test
                success = client.test_server_stream(client_id)
                if not success:
                    logger.warning(f"[Client-{client_id}] Server stream test failed")
                time.sleep(4)  # Wait before next iteration

            elif client_id == 3:
                # Bidirectional Sync Test
                success = client.test_bidirectional_stream_sync(client_id)
                if not success:
                    logger.warning(
                        f"[Client-{client_id}] Bidirectional sync test failed"
                    )
                time.sleep(6)  # Wait before next iteration

            elif client_id == 4:
                # Bidirectional Async Test
                success = client.test_bidirectional_stream_async(client_id)
                if not success:
                    logger.warning(
                        f"[Client-{client_id}] Bidirectional async test failed"
                    )
                time.sleep(7)  # Wait before next iteration

            # Check stop event during sleep
            if stop_event.wait(timeout=0.1):
                break

    except Exception as e:
        logger.error(f"[Client-{client_id}] Unexpected error: {e}")
    finally:
        client.close()
        logger.info(f"[Client-{client_id}] Client stopped")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="gRPC Echo Stream Client")
    parser.add_argument(
        "--server",
        type=str,
        default="localhost:8080",
        help="Server address (default: localhost:8080)",
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["client", "server", "sync", "async", "all"],
        default="all",
        help="Which test to run (default: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run tests only once instead of continuously",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting gRPC Echo Stream Client...")

    # Setup signal handling
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.test == "all":
        # Run all tests in parallel threads
        threads = []
        for client_id in range(1, 5):
            if args.once:
                # For single run, create client and run test once
                client = EchoStreamClient(args.server)
                if client_id == 1:
                    client.test_client_stream(client_id)
                elif client_id == 2:
                    client.test_server_stream(client_id)
                elif client_id == 3:
                    client.test_bidirectional_stream_sync(client_id)
                elif client_id == 4:
                    client.test_bidirectional_stream_async(client_id)
                client.close()
            else:
                # For continuous run, start threads
                thread = threading.Thread(
                    target=run_client_tests,
                    args=(client_id, args.server, stop_event),
                    daemon=True,
                )
                thread.start()
                threads.append(thread)

        if not args.once:
            logger.info("All streaming clients started. Press Ctrl+C to stop...")

            # Wait for stop signal
            stop_event.wait()

            # Wait for all threads to finish
            for thread in threads:
                thread.join(timeout=5)

    else:
        # Run specific test
        client = EchoStreamClient(args.server)
        client_id = 1

        try:
            if args.test == "client":
                while not stop_event.is_set():
                    client.test_client_stream(client_id)
                    if args.once:
                        break
                    time.sleep(5)

            elif args.test == "server":
                while not stop_event.is_set():
                    client.test_server_stream(client_id)
                    if args.once:
                        break
                    time.sleep(4)

            elif args.test == "sync":
                while not stop_event.is_set():
                    client.test_bidirectional_stream_sync(client_id)
                    if args.once:
                        break
                    time.sleep(6)

            elif args.test == "async":
                while not stop_event.is_set():
                    client.test_bidirectional_stream_async(client_id)
                    if args.once:
                        break
                    time.sleep(7)

        finally:
            client.close()

    logger.info("Client shutdown completed")


if __name__ == "__main__":
    main()
