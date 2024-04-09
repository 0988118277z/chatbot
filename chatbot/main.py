import socketio
import time

sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=1, reconnection_delay_max=5)

@sio.event
def connect():
    print("Connected to the server.")
    sio.emit("message", "Hello, WebSocket!")

@sio.event
def message(data):
    print('Received message:', data)

@sio.event
def disconnect():
    print("Disconnected from server.")

def attempt_connect(url):
    while True:
        try:
            sio.connect(url)
            print("Connection successful!")
            break  # 连接成功后跳出循环
        except socketio.exceptions.ConnectionError as err:
            print("Connection failed, retrying...", err)
            time.sleep(5)  # 等待5秒后再次尝试连接

if __name__ == '__main__':
    attempt_connect('http://127.0.0.1:5000')
