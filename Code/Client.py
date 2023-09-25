import argparse
import ipaddress
import json
import socket
import threading
from socket import *


# 客户端的启动参数
def parse_arguments():
    # 帮助参数 输出参数帮助
    parser = argparse.ArgumentParser(description='客户端启动参数帮助')
    # 添加 -i 参数，指定服务端 IP 地址,同时支持 IPv4 和 IPv6 不得为空
    parser.add_argument(
        '-i', '--ip',
        required=True,
        help='服务端 IP 地址,支持 IPv4 和 IPv6 ,不得为空。'
             '可以使用以下示例格式:'
             ' IPv4地址: 172.27.95.215'
             ' IPv6地址:fe80::3b35:c27e:d55b:4e88'
    )
    # 添加 -p 参数，指定服务端端口号 不得为空
    parser.add_argument(
        '-p', '--port',
        required=True,
        help='服务端端口号,不得为空'
    )
    return parser.parse_args()


class RPCClient:
    # 初始化RPC客户端
    def __init__(self, ip, port):
        # 服务器的IP地址
        self.ip = ip
        # 服务器端口号
        self.port = port

    # 发起RPC调用，将函数名和参数发送给服务器，然后接收服务器的响应
    def rpc_call(self, func_name, *args):
        try:
            # 创建客户套接字,同时支持IPv4和IPv6协议
            if ipaddress.ip_address(ip).version == 6:
                # IPv6地址加上括号后才能正常被绑定使用
                ip_address = ipaddress.IPv6Address(self.ip).compressed
                clientSocket = socket(AF_INET6, SOCK_STREAM)
                clientSocket.connect((ip_address, self.port))  # 建立TCP连接
            else:
                clientSocket = socket(AF_INET, SOCK_STREAM)
                clientSocket.connect((self.ip, self.port))  # 建立TCP连接
            # 设置端口重用，以便服务能迅速重启
            clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            clientSocket.settimeout(5)  # 设置超时时间为5秒
            print("成功连接到服务器 {}: {}".format(self.ip, self.port))
        except ConnectionError as e:
            print("无法连接到服务器 {}: {}: {}".format(self.ip, self.port, str(e)))  # 与服务器建立连接导致异常
            clientSocket.close()  # 关闭套接字
        except timeout as e:
            print("与服务端 {}:{} 建立连接超时: {}".format(self.ip, self.port, str(e)))  # 与服务器建立连接导致超时
            clientSocket.close()  # 关闭套接字

        # 客户端查看服务端支持调用的服务
        if func_name == 'get_supported_functions':
            request_data = json.dumps({'func': func_name}).encode()
            clientSocket.sendall(len(request_data).to_bytes(4, byteorder='big') + request_data)
            # 接收服务器返回内容
            data = clientSocket.recv(1024)

            # 未接收到数据
            if not data:
                clientSocket.close()
                return  # 退出当前函数
            # 获取数据长度 即头部
            message_length = int.from_bytes(data[:4], byteorder='big')

            if len(data) < 4 + message_length:
                print("请求数据不完整")
                clientSocket.close()  # 关闭套接字
                return  # 退出当前函数

            # 通过头部指示的长度截取字节流中的内容进行解析
            message = json.loads(data[4:4 + message_length].decode())
            print('Supported functions:', message)

        # 客户端进行函数调用
        else:
            try:
                # 创建RPC请求的JSON对象(包含函数名,位置参数) 将JSON对象编码为字节
                request_data = json.dumps({'func': func_name, 'args': args}).encode()
                # 发送 数据长度+数据内容
                clientSocket.sendall(len(request_data).to_bytes(4, byteorder='big') + request_data)
            except Exception as e:
                print("发送请求失败: {}".format(str(e)))  # 发送请求到服务端 写数据导致的异常/超时
                clientSocket.close()  # 关闭套接字

            try:
                # 接收服务器的返回内容
                data = clientSocket.recv(1024)
                # 未接收到数据
                if not data:
                    clientSocket.close()
                    return  # 退出当前函数
                # 获取数据长度 即头部
                message_length = int.from_bytes(data[:4], byteorder='big')
                if len(data) < 4 + message_length:
                    print("请求数据不完整")
                    clientSocket.close()  # 关闭套接字
                    return  # 退出当前函数
                # 通过头部指示的长度截取字节流中的内容进行解析
                result = json.loads(data[4:4 + message_length].decode())
                print(result)  # 打印调用结果(或相关错误信息)

            except timeout:
                print("等待处理超时: 从服务端接收响应时，等待处理导致的超时")  # 等待服务端处理时 读数据导致的异常/超时
                clientSocket.close()  # 关闭套接字
            except OSError as e:
                print("从服务端接收响应时发生错误: {}".format(str(e)))  # 从服务端接收响应时 读数据导致的异常
                clientSocket.close()  # 关闭套接字
            except Exception as e:
                print("从服务端接收响应时发生其他异常: {}".format(str(e)))  # 从服务端接收响应时 其他类型的异常
                clientSocket.close()  # 关闭套接字


if __name__ == '__main__':
    args = parse_arguments()
    ip = args.ip
    port = args.port
    # 客户端创建
    rpc_client = RPCClient(ip, int(port))

    # 客户端调用函数
    rpc_client.rpc_call('get_supported_functions')
    rpc_client.rpc_call('add', 1, 2)
    rpc_client.rpc_call('minus', 2, 1)
    rpc_client.rpc_call('isEven', 999)
    rpc_client.rpc_call('isOdd', 999)

    rpc_client.rpc_call('ad', 1, 2)
    rpc_client.rpc_call('add', 1)
    rpc_client.rpc_call('add', 1, "3")

    # # 创建多个线程模拟多个客户端并发请求 以测试服务器的并发处理性能
    # threads = []
    # num_threads = 10  # 设置线程数量
    # for _ in range(num_threads):
    #     rpc_client = RPCClient(ip, int(port))
    #     thread = threading.Thread(target=rpc_client.rpc_call, args=('add', 1, 2))
    #     threads.append(thread)
    #     thread.start()
    #     # 等待所有线程完成
    # for thread in threads:
    #     thread.join()
