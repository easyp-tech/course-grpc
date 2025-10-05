from concurrent import futures
import time

import grpc
from grpc_status import rpc_status
from google.protobuf import any_pb2

from api import service_pb2_grpc
from api import service_pb2

class InterceptorStat(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details: grpc.HandlerCallDetails) -> grpc.RpcMethodHandler:
        """Базовый интерсептор для униарных вызовов"""
        method_handler = continuation(handler_call_details)

        start_time = time.time()
        res = method_handler
        duration = time.time() - start_time
        print(f"[INTERCEPTOR STAT] {handler_call_details.method} completed in {duration:.3f}s")

        return res


class Service(service_pb2_grpc.EchoServiceServicer):
    def HelloWorld(self, request, context):
        print('called: ', request)
        return service_pb2.EchoResponse(message='pong')

    def WithError(self, request, context):
        print('Called with error')

        # формируем кастомную ошибку
        error_message = service_pb2.CustomError(reason='[PYTHON] some reason')

        detail = any_pb2.Any()
        detail.Pack(error_message)

        # Создаем статус
        # дополняем ее деталями: которые содержат структуру сообщения из proto файла.
        status = rpc_status.status_pb2.Status(
            code=grpc.StatusCode.FAILED_PRECONDITION.value[0],
            message='[PYTHON] Custom error',
            details=[detail]
        )
        context.abort_with_status(rpc_status.to_status(status))

def serve():
    # https://grpc.github.io/grpc/python/grpc.html#grpc.server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        maximum_concurrent_rpcs=10,
        interceptors=[InterceptorStat()],
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