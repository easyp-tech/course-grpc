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
    except Exception as e:
        print(f"Generic error: {e}")

if __name__ == '__main__':
    run()
