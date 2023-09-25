import inspect
import ipaddress
import json
import socket
import argparse
from socket import *
import select


# 加法
def add(a, b):
    return a + b


# 减法
def minus(a, b):
    return a - b


# 乘法
def multiply(a, b):
    return a * b


# 除法
def divide(a, b):
    if b != 0:
        return a / b
    else:
        return "Error: 除数为0"


# 取模
def modulus(a, b):
    if b != 0:
        return a % b
    else:
        return "Error: 除数为0"


# 计算幂次方
def power(base, exponent):
    return base ** exponent


# 计算平方根
def square_root(number):
    if number >= 0:
        return number ** 0.5
    else:
        return "Error: 无法计算负数的平方根"


# 求列表中的最大值
def maximum(numbers):
    if len(numbers) > 0:
        return max(numbers)
    else:
        return "Error: 列表为空"


# 求列表中的最小值
def minimum(numbers):
    if len(numbers) > 0:
        return min(numbers)
    else:
        return "Error: 列表为空"


# 计算平方数
def square(a):
    return a * a


# 计算立方数
def cube(a):
    return a * a * a


# 服务端的启动参数
def parse_arguments():
    # 帮助参数 输出参数帮助
    parser = argparse.ArgumentParser(description='服务端启动参数帮助')
    # 添加 -l 参数,指定服务端监听的 IP 地址,同时支持 IPv4 和 IPv6,可以为空,默认监听所有 ip 地址,即 0.0.0.0
    parser.add_argument(
        '-l', '--listen',
        default='0.0.0.0',
        help='服务端监听的 IP 地址,支持 IPv4 和 IPv6, 默认为 0.0.0.0 '
             '可以使用以下示例格式:'
             ' IPv4地址: 172.27.95.215'
             ' IPv6地址:fe80::3b35:c27e:d55b:4e88'
    )
    # 添加 -p 参数,指定服务端监听的端口号 不得为空
    parser.add_argument(
        '-p', '--port',
        required=True,
        help='服务端监听的端口号,不能为空'
    )
    return parser.parse_args()


class RPCServer:
    # 初始化
    def __init__(self):
        # 初始化一个字典来保存注册的函数
        self.func_map = {}

    # 服务注册 服务端注册能支持的函数
    def register_func(self, func):
        # 注册函数,将函数名作为键,函数本身作为值保存到字典中
        self.func_map[func.__name__] = func

    # 服务发现 返回给客户端已注册的函数列表
    def get_registered_functions(self):
        return list(self.func_map.keys())

    # RPC请求的处理 解析请求消息,调用相应的函数,并将结果发送回客户端
    def handle_rpc(self, conn):
        conn.settimeout(5)  # 设置超时时间为5s
        try:
            data = conn.recv(1024)  # 从与客户端连接的套接字中接收数据
        except timeout:
            # 处理超时异常
            print("请求超时")  # 读取客户端请求数据时 读数据导致的超时
            conn.close()  # 关闭套接字
        except Exception as e:
            print("读取请求数据失败: {}".format(str(e)))  # 读取客户端请求数据时 读数据导致的异常
            conn.close()  # 关闭套接字
        if not data:
            conn.close()  # 关闭套接字
            return  # 退出当前函数
        # 获取数据长度 即数据头部
        message_length = int.from_bytes(data[:4], byteorder='big')
        if len(data) < 4 + message_length:
            print("请求数据不完整")
            conn.close()  # 关闭套接字
            return  # 退出当前函数

        # 通过长度截取字节流中的数据进行解析
        message = json.loads(data[4:4 + message_length].decode())
        # 从解析后的对象中获取函数名和位置参数
        func_name = message['func']
        if func_name == 'get_supported_functions':
            # 处理获取支持的函数列表的请求
            result = self.get_registered_functions()
        elif func_name in self.func_map:
            # 处理已注册的函数的请求
            args = message['args']  # 从解析后的对象中获取位置参数

            # 对于客户端调用函数时参数数量不一致的检测
            expected_params = inspect.signature(self.func_map[func_name]).parameters.values()  # 获取注册函数的参数字典中的值部分
            if len(args) != len(expected_params):
                # 参数数量不一致
                result = '调用的函数 {} 的参数数量不正确,需要输入{}个参数'.format(func_name, len(expected_params))
            else:
                try:
                    for arg, param in zip(args, expected_params):
                        # 获取函数参数的预期类型 ,检查参数的注解是否存在,并将其赋值给expected_type变量 如果参数没有注解或注解为空,expected_type被设置为None
                        expected_type = param.annotation if param.annotation != inspect.Parameter.empty else None
                        # 这获取实际参数的类型 检查expected_type是否存在
                        # 如果expected_type为None,arg_type将被设置为None
                        arg_type = type(arg) if expected_type is not None else None
                        # 检查实际参数的类型是否与预期类型匹配
                        if expected_type is not None and arg_type != expected_type:
                            # 参数类型不匹配，抛出类型错误异常
                            raise TypeError(
                                "参数类型不匹配: 期望 {} 类型, 实际 {} 类型".format(expected_type.__name__, arg_type.__name__))
                    # 正确调用函数 返回给客户端的调用结果
                    result = '{}的调用结果: {}({}) = {}'.format(func_name, func_name,
                                                           ', '.join(str(arg) for arg in args),
                                                           self.func_map[func_name](*args))

                except TypeError as e:
                    # 处理参数类型错误的异常
                    error_message = str(e)
                    result = {'error': '参数类型错误: {}'.format(error_message)}  # 返回错误信息给客户端
                    print("处理数据时出现异常: {}".format(error_message))  # 调用映射服务的方法时 处理数据导致的异常/超时
                except Exception as e:
                    # 处理其他异常
                    error_message = str(e)
                    result = {'error': '处理数据时出现异常: {}'.format(error_message)}  # 返回错误信息给客户端
                    print("处理数据时出现异常: {}".format(error_message))  # 调用映射服务的方法时 处理数据导致的异常/超时

        else:
            # 处理未注册的函数的请求
            result = '调用的函数 {} 并不存在'.format(func_name)
        # 将前面判断得到的result封装后发送给客户端

        try:
            # 将结果封装为JSON格式 编码为字节后发送给客户端
            response_data = json.dumps({'result': result}).encode()
            # 打包发送数据长度 + 数据内容
            conn.sendall(len(response_data).to_bytes(4, byteorder='big') + response_data)

        except timeout:
            # 处理发送超时异常
            print("发送响应数据超时")  # 发送响应数据时 写数据导致的超时
            conn.close()  # 关闭套接字
        except Exception as e:
            print("发送响应数据失败: {}".format(str(e)))  # 发送响应数据时 写数据导致的异常
            conn.close()  # 关闭套接字

    # 服务端启动函数
    def runserver(self, ip, port):
        # 运行RPC服务器,监听指定的IP地址和端口，接受客户端的连接 同时支持IPv4和IPv6协议
        if ipaddress.ip_address(ip).version == 6:
            ip = "[" + ip + "]"  # IPv6地址加上括号后才能正常被绑定使用
            serverSocket = socket(AF_INET6, SOCK_STREAM)
        else:
            serverSocket = socket(AF_INET, SOCK_STREAM)
        # 设置端口重用，以便服务能迅速重启
        serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # 绑定端口号和套接字
        serverSocket.bind((ip, port))
        # 变为被动
        serverSocket.listen(1024)
        # 设置套接字为非阻塞模式
        serverSocket.setblocking(False)
        # 创建一个epoll对象
        epoll = select.epoll()
        # 为服务器端套接字server_socket的文件描述符注册事件
        epoll.register(serverSocket.fileno(), select.EPOLLIN)
        print("RPC服务器运行于于{}:{}...".format(ip, port))
        # 维护字典 存储套接字和客户端地址信息
        new_socket_list = {}
        client_address_list = {}
        while True:
            try:
                # 循环等待数据到达
                while True:
                    # 检测并获取epoll监控的已触发事件
                    epoll_list = epoll.poll()
                    # 对事件进行处理
                    for fd, events in epoll_list:
                        # 如果有新的连接请求递达
                        if fd == serverSocket.fileno():
                            new_socket, client_address = serverSocket.accept()
                            new_socket.setblocking(False)  # 设置新连接为非阻塞模式
                            print('有新的客户端到来:%s' % str(client_address))
                            # 为新套接字的文件描述符注册读事件
                            epoll.register(new_socket.fileno(), select.EPOLLIN)
                            # 将新套接字和客户端地址保存到字典中
                            new_socket_list[new_socket.fileno()] = new_socket
                            client_address_list[new_socket.fileno()] = client_address
                        # 如果监听到 EPOLLIN 事件, 表示对应的文件描述符可以读
                        elif events & select.EPOLLIN:
                            # 处理逻辑
                            # 从字典中获取与该文件描述符相关的套接字
                            conn = new_socket_list[fd]
                            # 调用rpc处理函数
                            self.handle_rpc(conn)
                        elif events & select.EPOLLHUP:
                            print(f"Client {fd} disconnected")
                            # 取消注册
                            epoll.unregister(fd)
                            conn = new_socket_list[fd]
                            print('客户端断开连接：%s' % str(conn.getpeername()))
                            conn.close()
                            del new_socket_list[fd]
                            del client_address_list[fd]
            except KeyboardInterrupt:
                # 处理键盘中断
                print("RPC服务器已关闭")
            finally:
                epoll.unregister(serverSocket.fileno())
                epoll.close()
                serverSocket.close()


if __name__ == '__main__':
    args = parse_arguments()
    listen_ip = args.listen
    port = args.port

    # 初始化服务器
    rpc_server = RPCServer()
    # 服务端注册其能支持的函数 可以同时注册多个函数
    rpc_server.register_func(add)
    rpc_server.register_func(minus)
    rpc_server.register_func(multiply)
    rpc_server.register_func(divide)
    rpc_server.register_func(modulus)
    rpc_server.register_func(power)
    rpc_server.register_func(square_root)
    rpc_server.register_func(maximum)
    rpc_server.register_func(minimum)
    rpc_server.register_func(square)
    rpc_server.register_func(cube)

    # 运行服务器监听IP地址和端口 处理连接
    rpc_server.runserver(listen_ip, int(port))
