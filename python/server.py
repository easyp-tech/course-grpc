from concurrent import futures
import time

import grpc
from grpc_status import rpc_status
from google.protobuf import any_pb2

from api import service_pb2_grpc
from api import service_pb2

class Service(service_pb2_grpc.EchoServiceServicer):
    def HelloWorld(self, request, context):
        print('called: ', request)
        return service_pb2.EchoResponse(message='pong')

def serve():
    # https://grpc.github.io/grpc/python/grpc.html#grpc.server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        maximum_concurrent_rpcs=10,
    )
    service_pb2_grpc.add_EchoServiceServicer_to_server(
        Service(), server
    )
    server.add_insecure_port('[::]:5001')
    server.start()
    print("Starting server...")

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()