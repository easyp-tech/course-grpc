import time

import grpc
from grpc_status import rpc_status

from api import service_pb2_grpc
from api import service_pb2

def run():
    # Создаем канал и клиент
    channel = grpc.intercept_channel(
        grpc.insecure_channel('localhost:5001'),
    )
    client = service_pb2_grpc.EchoServiceStub(channel)

    try:
        # Отправляем первый запрос
        resp_hello_world = client.HelloWorld(service_pb2.EchoRequest(message="[PYTHON} Ping"))
        print(f'Response hello world: {resp_hello_world}')

        # Отправляем второй запрос, в котором будет кастомная ошибка
        resp_with_error = client.WithError(service_pb2.EchoRequest(message="[PYTHON} Ping"))
    except grpc.RpcError as rpc_error:
        # полученная ошибка это ошибка сообщение от сервера gRPC, а не, например, сетевая ошибка
        status = rpc_status.from_call(rpc_error)
        print(f'Code: {status.code}')

        for detail in status.details:
            error_message = service_pb2.CustomError()
            detail.Unpack(error_message)
            print(f'Reason: {error_message.reason}')

    except Exception as e:
        print(f"Generic error: {e}")


if __name__ == '__main__':
    run()
