#!/usr/bin/env python3
"""
gRPC Stream Server implementation in Python.
Implements all streaming patterns: client streaming, server streaming, and bidirectional streaming.
"""

import asyncio
import logging
import signal
import sys
from concurrent import futures
from typing import Iterator, Optional
import time
import threading
from queue import Queue, Empty

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


class EchoStreamService(stream_pb2_grpc.EchoServiceServicer):
    """Implementation of the EchoService with all streaming patterns."""

    def EchoClientStream(
        self,
        request_iterator: Iterator[stream_pb2.EchoRequest],
        context: grpc.ServicerContext,
    ) -> stream_pb2.EchoResponse:
        """
        Client streaming RPC - receives multiple messages from client, returns one response.

        Args:
            request_iterator: Iterator of client requests
            context: RPC context

        Returns:
            Single EchoResponse with summary of received messages
        """
        logger.info("EchoClientStream: Starting client stream")

        messages = []
        try:
            for request in request_iterator:
                logger.info(f"EchoClientStream: Received message: {request.message}")
                messages.append(request.message)

                # Check if client cancelled
                if context.is_active() is False:
                    logger.warning("EchoClientStream: Client cancelled the stream")
                    break

        except grpc.RpcError as e:
            logger.error(f"EchoClientStream: Error receiving message: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

        response_message = f"Received {len(messages)} messages: {messages}"
        logger.info(f"EchoClientStream: Sending response: {response_message}")

        return stream_pb2.EchoResponse(message=response_message)

    def EchoServerStream(
        self, request: stream_pb2.EchoRequest, context: grpc.ServicerContext
    ) -> Iterator[stream_pb2.EchoResponse]:
        """
        Server streaming RPC - receives one message and sends back a stream of responses.

        Args:
            request: Single client request
            context: RPC context

        Yields:
            Multiple EchoResponse messages
        """
        logger.info(f"EchoServerStream: Received message: {request.message}")

        for i in range(1, 6):
            # Check if client is still connected
            if not context.is_active():
                logger.warning("EchoServerStream: Client disconnected")
                break

            response_message = f"Echo #{i}: {request.message}"
            logger.info(f"EchoServerStream: Sending response #{i}: {response_message}")

            yield stream_pb2.EchoResponse(message=response_message)

            # Small delay between messages
            time.sleep(0.1)

        logger.info("EchoServerStream: Finished sending responses")

    def EchoBidirectionalStreamSync(
        self,
        request_iterator: Iterator[stream_pb2.EchoRequest],
        context: grpc.ServicerContext,
    ) -> Iterator[stream_pb2.EchoResponse]:
        """
        Bidirectional streaming RPC with synchronous processing.
        Processes each request immediately and sends a response.

        Args:
            request_iterator: Iterator of client requests
            context: RPC context

        Yields:
            EchoResponse messages as they are processed
        """
        logger.info("EchoBidirectionalStreamSync: Starting bidirectional stream (sync)")

        try:
            for request in request_iterator:
                # Check if client is still connected
                if not context.is_active():
                    logger.warning("EchoBidirectionalStreamSync: Client disconnected")
                    break

                logger.info(
                    f"EchoBidirectionalStreamSync: Received message: {request.message}"
                )

                # Process and respond immediately (synchronous)
                response_message = f"Sync Echo: {request.message}"
                logger.info(
                    f"EchoBidirectionalStreamSync: Sent response: {response_message}"
                )

                yield stream_pb2.EchoResponse(message=response_message)

        except grpc.RpcError as e:
            logger.error(f"EchoBidirectionalStreamSync: Error in stream: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

        logger.info("EchoBidirectionalStreamSync: Stream finished")

    def EchoBidirectionalStreamAsync(
        self,
        request_iterator: Iterator[stream_pb2.EchoRequest],
        context: grpc.ServicerContext,
    ) -> Iterator[stream_pb2.EchoResponse]:
        """
        Bidirectional streaming RPC with asynchronous processing.
        Uses separate threads for receiving and processing messages.

        Args:
            request_iterator: Iterator of client requests
            context: RPC context

        Yields:
            EchoResponse messages as they are processed asynchronously
        """
        logger.info(
            "EchoBidirectionalStreamAsync: Starting bidirectional stream (async)"
        )

        # Queue for passing messages between receiver and processor threads
        request_queue = Queue(maxsize=10)
        response_queue = Queue(maxsize=10)
        stop_event = threading.Event()

        def receive_messages():
            """Thread function for receiving messages from client."""
            try:
                for request in request_iterator:
                    if stop_event.is_set() or not context.is_active():
                        break

                    logger.info(
                        f"EchoBidirectionalStreamAsync: Received message: {request.message}"
                    )
                    request_queue.put(request)

            except Exception as e:
                logger.error(f"EchoBidirectionalStreamAsync: Error receiving: {e}")
            finally:
                # Signal end of stream
                request_queue.put(None)
                stop_event.set()

        def process_messages():
            """Thread function for processing messages asynchronously."""
            try:
                while not stop_event.is_set():
                    try:
                        # Get request with timeout to check stop event periodically
                        request = request_queue.get(timeout=0.1)

                        if request is None:  # End of stream signal
                            break

                        # Simulate async processing with delay
                        time.sleep(0.2)

                        response_message = f"Async Echo (processed): {request.message}"
                        response = stream_pb2.EchoResponse(message=response_message)

                        response_queue.put(response)
                        logger.info(
                            f"EchoBidirectionalStreamAsync: Processed async response: {response_message}"
                        )

                    except Empty:
                        continue
                    except Exception as e:
                        logger.error(
                            f"EchoBidirectionalStreamAsync: Error processing: {e}"
                        )

            finally:
                # Signal end of processing
                response_queue.put(None)

        # Start receiver and processor threads
        receiver_thread = threading.Thread(target=receive_messages, daemon=True)
        processor_thread = threading.Thread(target=process_messages, daemon=True)

        receiver_thread.start()
        processor_thread.start()

        # Yield responses as they become available
        try:
            while True:
                if not context.is_active():
                    stop_event.set()
                    break

                try:
                    response = response_queue.get(timeout=0.1)

                    if response is None:  # End of processing signal
                        break

                    logger.info(
                        f"EchoBidirectionalStreamAsync: Sent async response: {response.message}"
                    )
                    yield response

                except Empty:
                    continue

        except Exception as e:
            logger.error(f"EchoBidirectionalStreamAsync: Error sending responses: {e}")
        finally:
            stop_event.set()

        # Wait for threads to finish
        receiver_thread.join(timeout=1.0)
        processor_thread.join(timeout=1.0)

        logger.info("EchoBidirectionalStreamAsync: Stream finished")


class StreamServerInterceptor(grpc.ServerInterceptor):
    """Server interceptor for logging and monitoring."""

    def intercept_service(self, continuation, handler_call_details):
        """Intercept and log service calls."""
        start_time = time.time()

        logger.info(f"[INTERCEPTOR] Starting call to {handler_call_details.method}")

        # Call the actual handler
        response = continuation(handler_call_details)

        duration = time.time() - start_time
        logger.info(
            f"[INTERCEPTOR] {handler_call_details.method} setup completed in {duration:.3f}s"
        )

        return response


def serve(port: int = 8080, max_workers: int = 10):
    """
    Start the gRPC server.

    Args:
        port: Port to listen on
        max_workers: Maximum number of worker threads
    """
    # Create server with thread pool
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        interceptors=[StreamServerInterceptor()],
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
        ],
    )

    # Add service to server
    stream_pb2_grpc.add_EchoServiceServicer_to_server(EchoStreamService(), server)

    # Add insecure port
    server_address = f"[::]:{port}"
    server.add_insecure_port(server_address)

    # Start server
    server.start()
    logger.info(f"gRPC Echo Stream Server listening on {server_address}")

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        server.stop(grace=5.0)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Keep server running
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        server.stop(grace=5.0)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="gRPC Echo Stream Server")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to listen on (default: 8080)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Maximum number of worker threads (default: 10)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting gRPC Echo Stream Server...")
    serve(port=args.port, max_workers=args.workers)


if __name__ == "__main__":
    main()
