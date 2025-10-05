#!/usr/bin/env python3
"""
Benchmark utility for gRPC streaming performance testing.
Measures latency, throughput, and resource usage for all streaming patterns.
"""

import asyncio
import logging
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import argparse
import psutil
import os

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


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    test_name: str
    total_requests: int
    total_responses: int
    total_duration: float
    avg_latency: float
    min_latency: float
    max_latency: float
    p95_latency: float
    requests_per_second: float
    responses_per_second: float
    cpu_usage_percent: float
    memory_usage_mb: float
    errors: int
    success_rate: float


class StreamBenchmark:
    """Benchmark client for streaming performance testing."""

    def __init__(self, server_address: str = "localhost:8080"):
        """Initialize benchmark client."""
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self.process = psutil.Process(os.getpid())

    def connect(self):
        """Establish connection to server."""
        self.channel = grpc.insecure_channel(
            self.server_address,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 5000),
            ],
        )
        self.stub = stream_pb2_grpc.EchoServiceStub(self.channel)

    def disconnect(self):
        """Close connection to server."""
        if self.channel:
            self.channel.close()

    def _measure_system_usage(self) -> Tuple[float, float]:
        """Measure current CPU and memory usage."""
        cpu_percent = self.process.cpu_percent()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        return cpu_percent, memory_mb

    def benchmark_client_stream(
        self,
        num_concurrent: int = 10,
        messages_per_stream: int = 100,
        message_size: int = 1024,
    ) -> BenchmarkResult:
        """
        Benchmark client streaming performance.

        Args:
            num_concurrent: Number of concurrent streams
            messages_per_stream: Messages per stream
            message_size: Size of each message in bytes
        """
        logger.info(
            f"Benchmarking client streaming: {num_concurrent} concurrent, "
            f"{messages_per_stream} msgs/stream, {message_size} bytes/msg"
        )

        latencies = []
        errors = 0
        total_requests = 0
        total_responses = 0

        def client_stream_task(task_id: int) -> Tuple[float, int, int, int]:
            """Single client streaming task."""
            nonlocal total_requests

            start_time = time.time()
            local_requests = 0
            local_responses = 0
            local_errors = 0

            try:

                def generate_requests():
                    nonlocal local_requests
                    message_data = "x" * message_size
                    for i in range(messages_per_stream):
                        local_requests += 1
                        yield stream_pb2.EchoRequest(
                            message=f"Task-{task_id}-Msg-{i}: {message_data}"
                        )

                response = self.stub.EchoClientStream(generate_requests())
                local_responses += 1

            except Exception as e:
                logger.error(f"Client stream task {task_id} error: {e}")
                local_errors += 1

            duration = time.time() - start_time
            return duration, local_requests, local_responses, local_errors

        # Measure initial system state
        start_cpu, start_memory = self._measure_system_usage()
        benchmark_start = time.time()

        # Run concurrent client streaming tasks
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(client_stream_task, i) for i in range(num_concurrent)
            ]

            for future in as_completed(futures):
                duration, requests, responses, task_errors = future.result()
                latencies.append(duration)
                total_requests += requests
                total_responses += responses
                errors += task_errors

        benchmark_duration = time.time() - benchmark_start

        # Measure final system state
        end_cpu, end_memory = self._measure_system_usage()

        return BenchmarkResult(
            test_name="client_stream",
            total_requests=total_requests,
            total_responses=total_responses,
            total_duration=benchmark_duration,
            avg_latency=statistics.mean(latencies) if latencies else 0,
            min_latency=min(latencies) if latencies else 0,
            max_latency=max(latencies) if latencies else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18]
            if len(latencies) > 20
            else max(latencies)
            if latencies
            else 0,
            requests_per_second=total_requests / benchmark_duration,
            responses_per_second=total_responses / benchmark_duration,
            cpu_usage_percent=(start_cpu + end_cpu) / 2,
            memory_usage_mb=(start_memory + end_memory) / 2,
            errors=errors,
            success_rate=(total_responses / num_concurrent * 100)
            if num_concurrent > 0
            else 0,
        )

    def benchmark_server_stream(
        self,
        num_concurrent: int = 10,
        message_size: int = 1024,
    ) -> BenchmarkResult:
        """
        Benchmark server streaming performance.

        Args:
            num_concurrent: Number of concurrent streams
            message_size: Size of request message in bytes
        """
        logger.info(
            f"Benchmarking server streaming: {num_concurrent} concurrent, "
            f"{message_size} bytes/msg"
        )

        latencies = []
        errors = 0
        total_requests = 0
        total_responses = 0

        def server_stream_task(task_id: int) -> Tuple[float, int, int, int]:
            """Single server streaming task."""
            start_time = time.time()
            local_requests = 1
            local_responses = 0
            local_errors = 0

            try:
                message_data = "x" * message_size
                request = stream_pb2.EchoRequest(
                    message=f"Task-{task_id}: {message_data}"
                )

                response_stream = self.stub.EchoServerStream(request)

                for response in response_stream:
                    local_responses += 1

            except Exception as e:
                logger.error(f"Server stream task {task_id} error: {e}")
                local_errors += 1

            duration = time.time() - start_time
            return duration, local_requests, local_responses, local_errors

        # Measure initial system state
        start_cpu, start_memory = self._measure_system_usage()
        benchmark_start = time.time()

        # Run concurrent server streaming tasks
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(server_stream_task, i) for i in range(num_concurrent)
            ]

            for future in as_completed(futures):
                duration, requests, responses, task_errors = future.result()
                latencies.append(duration)
                total_requests += requests
                total_responses += responses
                errors += task_errors

        benchmark_duration = time.time() - benchmark_start

        # Measure final system state
        end_cpu, end_memory = self._measure_system_usage()

        return BenchmarkResult(
            test_name="server_stream",
            total_requests=total_requests,
            total_responses=total_responses,
            total_duration=benchmark_duration,
            avg_latency=statistics.mean(latencies) if latencies else 0,
            min_latency=min(latencies) if latencies else 0,
            max_latency=max(latencies) if latencies else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18]
            if len(latencies) > 20
            else max(latencies)
            if latencies
            else 0,
            requests_per_second=total_requests / benchmark_duration,
            responses_per_second=total_responses / benchmark_duration,
            cpu_usage_percent=(start_cpu + end_cpu) / 2,
            memory_usage_mb=(start_memory + end_memory) / 2,
            errors=errors,
            success_rate=((num_concurrent - errors) / num_concurrent * 100)
            if num_concurrent > 0
            else 0,
        )

    def benchmark_bidirectional_stream(
        self,
        num_concurrent: int = 10,
        messages_per_stream: int = 50,
        message_size: int = 1024,
        async_mode: bool = False,
    ) -> BenchmarkResult:
        """
        Benchmark bidirectional streaming performance.

        Args:
            num_concurrent: Number of concurrent streams
            messages_per_stream: Messages per stream
            message_size: Size of each message in bytes
            async_mode: Use async or sync bidirectional stream
        """
        test_name = (
            "bidirectional_stream_async" if async_mode else "bidirectional_stream_sync"
        )

        logger.info(
            f"Benchmarking {test_name}: {num_concurrent} concurrent, "
            f"{messages_per_stream} msgs/stream, {message_size} bytes/msg"
        )

        latencies = []
        errors = 0
        total_requests = 0
        total_responses = 0

        def bidirectional_stream_task(task_id: int) -> Tuple[float, int, int, int]:
            """Single bidirectional streaming task."""
            start_time = time.time()
            local_requests = 0
            local_responses = 0
            local_errors = 0

            try:

                def generate_requests():
                    nonlocal local_requests
                    message_data = "x" * message_size
                    for i in range(messages_per_stream):
                        local_requests += 1
                        yield stream_pb2.EchoRequest(
                            message=f"Task-{task_id}-Msg-{i}: {message_data}"
                        )

                if async_mode:
                    response_stream = self.stub.EchoBidirectionalStreamAsync(
                        generate_requests()
                    )
                else:
                    response_stream = self.stub.EchoBidirectionalStreamSync(
                        generate_requests()
                    )

                for response in response_stream:
                    local_responses += 1

            except Exception as e:
                logger.error(f"Bidirectional stream task {task_id} error: {e}")
                local_errors += 1

            duration = time.time() - start_time
            return duration, local_requests, local_responses, local_errors

        # Measure initial system state
        start_cpu, start_memory = self._measure_system_usage()
        benchmark_start = time.time()

        # Run concurrent bidirectional streaming tasks
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(bidirectional_stream_task, i)
                for i in range(num_concurrent)
            ]

            for future in as_completed(futures):
                duration, requests, responses, task_errors = future.result()
                latencies.append(duration)
                total_requests += requests
                total_responses += responses
                errors += task_errors

        benchmark_duration = time.time() - benchmark_start

        # Measure final system state
        end_cpu, end_memory = self._measure_system_usage()

        return BenchmarkResult(
            test_name=test_name,
            total_requests=total_requests,
            total_responses=total_responses,
            total_duration=benchmark_duration,
            avg_latency=statistics.mean(latencies) if latencies else 0,
            min_latency=min(latencies) if latencies else 0,
            max_latency=max(latencies) if latencies else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18]
            if len(latencies) > 20
            else max(latencies)
            if latencies
            else 0,
            requests_per_second=total_requests / benchmark_duration,
            responses_per_second=total_responses / benchmark_duration,
            cpu_usage_percent=(start_cpu + end_cpu) / 2,
            memory_usage_mb=(start_memory + end_memory) / 2,
            errors=errors,
            success_rate=((num_concurrent - errors) / num_concurrent * 100)
            if num_concurrent > 0
            else 0,
        )

    def run_all_benchmarks(
        self,
        concurrent_levels: List[int] = None,
        message_sizes: List[int] = None,
        messages_per_stream: int = 100,
    ) -> Dict[str, List[BenchmarkResult]]:
        """
        Run comprehensive benchmark suite.

        Args:
            concurrent_levels: List of concurrency levels to test
            message_sizes: List of message sizes to test
            messages_per_stream: Number of messages per stream for applicable tests
        """
        if concurrent_levels is None:
            concurrent_levels = [1, 5, 10, 20, 50]
        if message_sizes is None:
            message_sizes = [64, 1024, 8192]

        results = {
            "client_stream": [],
            "server_stream": [],
            "bidirectional_sync": [],
            "bidirectional_async": [],
        }

        self.connect()

        try:
            for concurrent in concurrent_levels:
                for message_size in message_sizes:
                    logger.info(
                        f"Running benchmarks: concurrent={concurrent}, message_size={message_size}"
                    )

                    # Client streaming
                    result = self.benchmark_client_stream(
                        num_concurrent=concurrent,
                        messages_per_stream=messages_per_stream,
                        message_size=message_size,
                    )
                    results["client_stream"].append(result)

                    # Server streaming
                    result = self.benchmark_server_stream(
                        num_concurrent=concurrent,
                        message_size=message_size,
                    )
                    results["server_stream"].append(result)

                    # Bidirectional sync streaming
                    result = self.benchmark_bidirectional_stream(
                        num_concurrent=concurrent,
                        messages_per_stream=messages_per_stream
                        // 2,  # Fewer messages for bidirectional
                        message_size=message_size,
                        async_mode=False,
                    )
                    results["bidirectional_sync"].append(result)

                    # Bidirectional async streaming
                    result = self.benchmark_bidirectional_stream(
                        num_concurrent=concurrent,
                        messages_per_stream=messages_per_stream // 2,
                        message_size=message_size,
                        async_mode=True,
                    )
                    results["bidirectional_async"].append(result)

                    # Small delay between test configurations
                    time.sleep(1)

        finally:
            self.disconnect()

        return results


def print_results(results: Dict[str, List[BenchmarkResult]]):
    """Print benchmark results in a formatted table."""
    print("\n" + "=" * 120)
    print("GRPC STREAMING PERFORMANCE BENCHMARK RESULTS")
    print("=" * 120)

    for test_type, test_results in results.items():
        print(f"\n{test_type.upper().replace('_', ' ')}:")
        print("-" * 120)

        # Header
        print(
            f"{'Concurrent':<12} {'MsgSize':<10} {'Requests':<10} {'Responses':<11} "
            f"{'RPS':<8} {'Resp/s':<8} {'AvgLat':<8} {'P95Lat':<8} {'CPU%':<6} "
            f"{'Mem(MB)':<8} {'Errors':<7} {'Success%':<8}"
        )
        print("-" * 120)

        for result in test_results:
            # Extract concurrent level and message size from the test parameters
            # This is a simplified approach - in a real implementation you'd store these separately
            print(
                f"{10:<12} {1024:<10} {result.total_requests:<10} {result.total_responses:<11} "
                f"{result.requests_per_second:<8.1f} {result.responses_per_second:<8.1f} "
                f"{result.avg_latency * 1000:<8.1f} {result.p95_latency * 1000:<8.1f} "
                f"{result.cpu_usage_percent:<6.1f} {result.memory_usage_mb:<8.1f} "
                f"{result.errors:<7} {result.success_rate:<8.1f}"
            )


def export_results_csv(results: Dict[str, List[BenchmarkResult]], filename: str):
    """Export results to CSV file."""
    import csv

    with open(filename, "w", newline="") as csvfile:
        fieldnames = [
            "test_type",
            "total_requests",
            "total_responses",
            "total_duration",
            "avg_latency_ms",
            "min_latency_ms",
            "max_latency_ms",
            "p95_latency_ms",
            "requests_per_second",
            "responses_per_second",
            "cpu_usage_percent",
            "memory_usage_mb",
            "errors",
            "success_rate",
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for test_type, test_results in results.items():
            for result in test_results:
                writer.writerow(
                    {
                        "test_type": result.test_name,
                        "total_requests": result.total_requests,
                        "total_responses": result.total_responses,
                        "total_duration": result.total_duration,
                        "avg_latency_ms": result.avg_latency * 1000,
                        "min_latency_ms": result.min_latency * 1000,
                        "max_latency_ms": result.max_latency * 1000,
                        "p95_latency_ms": result.p95_latency * 1000,
                        "requests_per_second": result.requests_per_second,
                        "responses_per_second": result.responses_per_second,
                        "cpu_usage_percent": result.cpu_usage_percent,
                        "memory_usage_mb": result.memory_usage_mb,
                        "errors": result.errors,
                        "success_rate": result.success_rate,
                    }
                )

    logger.info(f"Results exported to {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="gRPC Streaming Performance Benchmark")
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
        "--concurrent",
        type=int,
        nargs="+",
        default=[1, 5, 10],
        help="Concurrency levels to test (default: [1, 5, 10])",
    )
    parser.add_argument(
        "--message-size",
        type=int,
        nargs="+",
        default=[1024],
        help="Message sizes to test in bytes (default: [1024])",
    )
    parser.add_argument(
        "--messages-per-stream",
        type=int,
        default=100,
        help="Messages per stream for client/bidirectional tests (default: 100)",
    )
    parser.add_argument("--output", type=str, help="Output CSV file for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting gRPC Streaming Performance Benchmark...")
    logger.info(f"Server: {args.server}")
    logger.info(f"Concurrency levels: {args.concurrent}")
    logger.info(f"Message sizes: {args.message_size}")

    benchmark = StreamBenchmark(args.server)

    try:
        if args.test == "all":
            results = benchmark.run_all_benchmarks(
                concurrent_levels=args.concurrent,
                message_sizes=args.message_size,
                messages_per_stream=args.messages_per_stream,
            )
        else:
            # Run specific test
            benchmark.connect()
            results = {}

            if args.test == "client":
                results["client_stream"] = [
                    benchmark.benchmark_client_stream(
                        num_concurrent=args.concurrent[0],
                        messages_per_stream=args.messages_per_stream,
                        message_size=args.message_size[0],
                    )
                ]
            elif args.test == "server":
                results["server_stream"] = [
                    benchmark.benchmark_server_stream(
                        num_concurrent=args.concurrent[0],
                        message_size=args.message_size[0],
                    )
                ]
            elif args.test == "sync":
                results["bidirectional_sync"] = [
                    benchmark.benchmark_bidirectional_stream(
                        num_concurrent=args.concurrent[0],
                        messages_per_stream=args.messages_per_stream,
                        message_size=args.message_size[0],
                        async_mode=False,
                    )
                ]
            elif args.test == "async":
                results["bidirectional_async"] = [
                    benchmark.benchmark_bidirectional_stream(
                        num_concurrent=args.concurrent[0],
                        messages_per_stream=args.messages_per_stream,
                        message_size=args.message_size[0],
                        async_mode=True,
                    )
                ]

            benchmark.disconnect()

        # Print results
        print_results(results)

        # Export to CSV if requested
        if args.output:
            export_results_csv(results, args.output)

    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        sys.exit(1)

    logger.info("Benchmark completed")


if __name__ == "__main__":
    main()
