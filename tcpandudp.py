import socket
import struct
import threading
import time

def get_host_port():
    while True:
        host = input("Enter the host IP (e.g., 127.0.0.1 for localhost): ")
        try:
            socket.gethostbyname(host)
            break
        except socket.gaierror:
            print("Invalid hostname or IP address. Please try again.")

    while True:
        try:
            port = int(input("Enter the port number (1024-65535): "))
            if 1024 <= port <= 65535:
                return host, port
            else:
                print("Port must be between 1024 and 65535.")
        except ValueError:
            print("Please enter a valid integer for the port.")

def get_protocol():
    while True:
        protocol = input("Choose protocol (tcp/udp): ").lower()
        if protocol in ['tcp', 'udp']:
            return protocol
        print("Invalid protocol. Please enter 'tcp' or 'udp'.")

def send_data(sock, target_host, target_port, protocol):
    data_types = {
        '1': ('int', 'i'),
        '2': ('float', 'f'),
        '3': ('unsigned int', 'I'),
        '4': ('char', 'c'),
        '5': ('unsigned short', 'H'),
        '6': ('signed short', 'h'),
        '7': ('complete string', 's')
    }
    
    print("\nChoose data type to send:")
    for key, value in data_types.items():
        print(f"{key}. {value[0]}")
    
    choice = input("Enter your choice (1-7): ")
    if choice not in data_types:
        print("Invalid choice. Please try again.")
        return
    
    data_type, format_char = data_types[choice]
    
    while True:
        value = input(f"Enter {data_type} value(s) (or 'q' to quit): ")
        if value.lower() == 'q':
            break
        
        values = value.split()
        
        try:
            for val in values:
                if data_type == 'complete string':
                    encoded_value = val.encode()
                    length = len(encoded_value)
                    packed_data = struct.pack(f'<cI{length}s', b's', length, encoded_value)
                elif data_type == 'char':
                    packed_data = struct.pack('<cc', b'c', val.encode())
                elif data_type == 'float':
                    packed_data = struct.pack('<cf', b'f', float(val))
                else:
                    packed_data = struct.pack(f'<c{format_char}', format_char.encode(), int(val))
                
                if protocol == 'udp':
                    sock.sendto(packed_data, (target_host, target_port))
                else:
                    sock.send(packed_data)
                print(f"Sent {data_type}: {val} to {target_host}:{target_port}")
        except struct.error as e:
            print(f"Error packing data: {e}")
        except ValueError:
            print("Invalid input for the chosen data type.")
        except OSError as e:
            print(f"Error sending data: {e}")
            break

def receive_data(sock, stop_event, protocol):
    print("Listening for incoming data...")
    while not stop_event.is_set():
        try:
            if protocol == 'udp':
                data, addr = sock.recvfrom(1024)
            else:
                data = sock.recv(1024)
                addr = sock.getpeername()
            
            if not data:
                break
            
            print(f"\nReceived raw data from {addr}")
            
            if len(data) < 2:
                print("Received data is too short to process.")
                continue

            data_type = data[0:1].decode()
            
            try:
                if data_type == 's':
                    length = struct.unpack('<I', data[1:5])[0]
                    value = data[5:5+length].decode()
                    print(f"Received complete string: {value}")
                elif data_type == 'c':
                    value = data[1:2].decode()
                    print(f"Received char: {value}")
                elif data_type == 'f':
                    value = struct.unpack('<f', data[1:5])[0]
                    print(f"Received float: {value}")
                elif data_type in 'iIHh':
                    format_char = data_type
                    value = struct.unpack(f'<{format_char}', data[1:])[0]
                    if data_type == 'i':
                        print(f"Received int: {value}")
                    elif data_type == 'I':
                        print(f"Received unsigned int: {value}")
                    elif data_type == 'H':
                        print(f"Received unsigned short: {value}")
                    elif data_type == 'h':
                        print(f"Received signed short: {value}")
                else:
                    print(f"Received unknown data type: {data_type}")
            except struct.error as e:
                print(f"Error unpacking data: {e}")
            except UnicodeDecodeError as e:
                print(f"Error decoding data: {e}")
            
        except socket.timeout:
            continue
        except OSError:
            break
    print("Receiving thread stopped.")

def main():
    stop_event = threading.Event()
    receive_thread = None
    sock = None
    role = None
    protocol = None
    target_host = None
    target_port = None

    while True:
        if role is None:
            print("Do you want to act as a sender or receiver?")
            role = input("Enter 's' for sender or 'r' for receiver: ").lower()
            if role not in ['s', 'r']:
                print("Invalid role. Please enter 's' or 'r'.")
                role = None
                continue

        if protocol is None:
            protocol = get_protocol()

        if role == 'r':
            while True:
                try:
                    host, port = get_host_port()
                    if protocol == 'udp':
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.bind((host, port))
                    else:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.bind((host, port))
                        sock.listen(1)
                        print(f"Waiting for TCP connection on {host}:{port}")
                        sock, addr = sock.accept()
                        print(f"Connected to {addr}")
                    sock.settimeout(0.1)
                    print(f"Receiver bound to {host}:{port}")
                    break
                except socket.gaierror:
                    print(f"Error: Invalid host address. Please enter a valid IP or hostname.")
                except OSError as e:
                    print(f"Error binding to {host}:{port}: {e}")
                    choice = input("Do you want to try a different port? (y/n): ")
                    if choice.lower() != 'y':
                        print("Exiting program.")
                        return

            receive_thread = threading.Thread(target=receive_data, args=(sock, stop_event, protocol))
            receive_thread.start()
        elif role == 's':
            target_host, target_port = get_host_port()
            if protocol == 'udp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.connect((target_host, target_port))
                except ConnectionRefusedError:
                    print(f"Connection to {target_host}:{target_port} was refused.")
                    print("Make sure the receiver is running and listening on the specified port.")
                    print("Also check for any firewall or antivirus software that might be blocking the connection.")
                    sock.close()
                    continue
                except Exception as e:
                    print(f"An error occurred while connecting: {e}")
                    sock.close()
                    continue
            sock.settimeout(0.1)
            print(f"Sender created. Will send to {target_host}:{target_port}")

        while True:
            print(f"\n{protocol.upper()} Communication Program")
            print("1. Send data" if role == 's' else "1. Receive data")
            print("2. Switch role")
            print("3. Switch protocol")
            print("4. Exit")

            choice = input("Enter your choice: ")

            if choice == '1':
                if role == 's':
                    send_data(sock, target_host, target_port, protocol)
                else:
                    input("Press Enter to return to main menu...\n")
            elif choice == '2':
                role = 's' if role == 'r' else 'r'
                stop_event.set()
                if receive_thread:
                    receive_thread.join()
                sock.close()
                sock = None
                receive_thread = None
                stop_event.clear()
                print(f"Switched to {'sender' if role == 's' else 'receiver'} mode.")
                break
            elif choice == '3':
                protocol = 'udp' if protocol == 'tcp' else 'tcp'
                stop_event.set()
                if receive_thread:
                    receive_thread.join()
                sock.close()
                sock = None
                receive_thread = None
                stop_event.clear()
                print(f"Switched to {protocol.upper()} protocol.")
                break
            elif choice == '4':
                stop_event.set()
                if sock:
                    sock.close()
                if receive_thread:
                    receive_thread.join()
                print("Program terminated.")
                return
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

