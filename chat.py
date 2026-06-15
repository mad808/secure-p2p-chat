import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket
import threading
import os
import json
import base64
from datetime import datetime
import struct
import time
import sys
import webbrowser

# --- Constants & Theme ---
HOST_IP_TO_BIND = "0.0.0.0"
DEFAULT_PORT = 65432
HEADER_LENGTH = 8

# Sophisticated dark color palette
COLOR_BACKGROUND = "#1e1e1e"       # Very dark grey, almost black
COLOR_FRAME = "#2d2d2d"           # Dark grey for frames and panels
COLOR_INPUT_BG = "#3c3c3c"         # Lighter grey for input fields
COLOR_TEXT = "#e0e0e0"             # Soft white for text
COLOR_SYSTEM = "#8e8e8e"           # Muted grey for system messages and timestamps
COLOR_ACCENT = "#007acc"           # A vibrant blue for highlights and buttons
COLOR_BUBBLE_SELF = "#005a9e"      # A deeper blue for the user's own message bubbles
COLOR_BUBBLE_OTHER = "#3c3c3c"     # Same as input, for other users' messages

# Font configuration
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_BOLD = (FONT_FAMILY, 11, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_TITLE = (FONT_FAMILY, 18, "bold")


# --- Helper Functions ---
def get_local_ip():
    """Gets the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# --- Server Logic ---
class ServerThread(threading.Thread):
    def __init__(self, port):
        super().__init__(daemon=True, name="ServerThread")
        self.port = port
        self.clients = {}
        self.server_socket = None

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((HOST_IP_TO_BIND, self.port))
            self.server_socket.listen()
            print(f"[SERVER] Started on: {get_local_ip()}:{self.port}")
        except Exception as e:
            print(f"[SERVER ERROR] Could not start server: {e}")
            return
        while True:
            try:
                client_socket, _ = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except OSError:
                break

    def handle_client(self, client_socket):
        username = None
        try:
            message = self._receive(client_socket)
            if message and message.get('type') == 'username':
                username = message['payload']
                self.clients[client_socket] = username
                self.broadcast({'type': 'system', 'payload': f"'{username}' has joined."})
                self.broadcast_user_list()
            else:
                client_socket.close()
                return
            while True:
                message = self._receive(client_socket)
                if message is None:
                    break
                self.broadcast(message)
        except (ConnectionResetError, struct.error, EOFError, KeyError) as e:
            print(f"[SERVER] Connection lost with '{username or 'Unknown'}': {e}")
        except Exception as e:
            print(f"[SERVER] Error ({username}): {e}")
        finally:
            self.remove_client(client_socket)

    def broadcast(self, message):
        for client_socket in list(self.clients.keys()):
            try:
                self._send(client_socket, message)
            except:
                self.remove_client(client_socket)

    def broadcast_user_list(self):
        self.broadcast({'type': 'user_list', 'payload': list(self.clients.values())})

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            username = self.clients.pop(client_socket)
            client_socket.close()
            self.broadcast({'type': 'system', 'payload': f"'{username}' has left."})
            self.broadcast_user_list()

    def _send(self, sock, message):
        data = json.dumps(message).encode('utf-8')
        sock.sendall(struct.pack('!Q', len(data)) + data)

    def _receive(self, sock):
        header = sock.recv(HEADER_LENGTH)
        if not header:
            return None
        length = struct.unpack('!Q', header)[0]
        data = b''
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return json.loads(data.decode('utf-8'))


# --- App Launcher ---
class AppLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P2P Chat")
        self.geometry("400x480")
        self.resizable(False, False)
        self.configure(bg=COLOR_BACKGROUND)

        # Custom TTK styling
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=COLOR_BACKGROUND, foreground=COLOR_TEXT, font=FONT_NORMAL)
        style.configure("TFrame", background=COLOR_BACKGROUND)
        style.configure("TEntry", fieldbackground=COLOR_INPUT_BG, foreground=COLOR_TEXT, insertcolor=COLOR_TEXT, bordercolor=COLOR_FRAME, lightcolor=COLOR_FRAME, darkcolor=COLOR_FRAME, font=FONT_NORMAL)
        style.map("TEntry", bordercolor=[("focus", COLOR_ACCENT)])

        # Button styling
        style.configure("TButton", font=FONT_BOLD, background=COLOR_INPUT_BG, foreground=COLOR_TEXT, borderwidth=0, focusthickness=0, padding=10)
        style.map("TButton", background=[("active", COLOR_FRAME)])
        style.configure("Accent.TButton", background=COLOR_ACCENT, foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#005a9e")])

        main_frame = ttk.Frame(self, padding=40)
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(main_frame, text="P2P Chat", font=FONT_TITLE).pack(pady=(0, 30))

        ttk.Label(main_frame, text="Display Name").pack(fill=tk.X, pady=(0, 5))
        self.username_entry = ttk.Entry(main_frame, font=FONT_NORMAL)
        self.username_entry.pack(fill=tk.X, ipady=8, pady=(0, 20))
        self.username_entry.focus()

        ttk.Label(main_frame, text="Server IP to Join").pack(fill=tk.X, pady=(0, 5))
        self.ip_entry = ttk.Entry(main_frame, font=FONT_NORMAL)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(fill=tk.X, ipady=8)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=30, fill=tk.X)
        button_frame.columnconfigure((0, 1), weight=1)

        ttk.Button(button_frame, text="Join", command=self.join_chat).grid(row=0, column=1, sticky="ew", padx=(5, 0))
        ttk.Button(button_frame, text="Host", command=self.host_chat, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Clickable Signature Link
        github_label = tk.Label(main_frame, text="Developed by mad808", font=FONT_SMALL, fg=COLOR_SYSTEM, bg=COLOR_BACKGROUND, cursor="hand2")
        github_label.pack(side=tk.BOTTOM, pady=(10, 0))
        github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/mad808"))
        github_label.bind("<Enter>", lambda e: github_label.config(fg=COLOR_ACCENT))
        github_label.bind("<Leave>", lambda e: github_label.config(fg=COLOR_SYSTEM))

    def start_chat(self, ip, username, is_host=False):
        if not username.strip():
            messagebox.showwarning("Username Required", "Please enter a display name.")
            return
        self.destroy()
        if is_host:
            ServerThread(DEFAULT_PORT).start()
            time.sleep(0.5)
        ChatClientGUI(ip, username).mainloop()

    def join_chat(self):
        self.start_chat(self.ip_entry.get(), self.username_entry.get())

    def host_chat(self):
        self.start_chat(get_local_ip(), self.username_entry.get(), is_host=True)


# --- Chat Window ---
class ChatClientGUI(tk.Tk):
    def __init__(self, server_ip, username):
        super().__init__()
        self.title(f"P2P Chat - {username}")
        self.geometry("950x700")
        self.minsize(600, 500)
        self.configure(bg=COLOR_BACKGROUND)

        self.username = username
        self.server_ip = server_ip
        self.client_socket = None
        self.socket_lock = threading.Lock()
        
        self._setup_styles()
        self._setup_ui()

        if not self._connect_to_server():
            return
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TFrame", background=COLOR_FRAME)
        style.configure("Vertical.TScrollbar", background=COLOR_FRAME, troughcolor=COLOR_BACKGROUND, bordercolor=COLOR_FRAME, arrowcolor=COLOR_TEXT)
        style.configure("Chat.TFrame", background=COLOR_BACKGROUND)
        style.configure("Input.TFrame", background=COLOR_FRAME)
        style.configure("TEntry", fieldbackground=COLOR_INPUT_BG, foreground=COLOR_TEXT, insertcolor=COLOR_TEXT, bordercolor=COLOR_FRAME, font=FONT_NORMAL)
        style.map("TEntry", bordercolor=[("focus", COLOR_ACCENT)])

    def _setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        user_list_frame = ttk.Frame(main_pane, width=220)
        main_pane.add(user_list_frame, weight=1)
        ttk.Label(user_list_frame, text="Participants", font=FONT_BOLD, foreground=COLOR_TEXT, background=COLOR_FRAME).pack(pady=10, padx=10)
        
        self.user_listbox = tk.Listbox(user_list_frame, font=FONT_NORMAL, bg=COLOR_FRAME, fg=COLOR_TEXT, relief=tk.FLAT, borderwidth=0, highlightthickness=0, selectbackground=COLOR_ACCENT)
        self.user_listbox.pack(expand=True, fill=tk.BOTH, padx=10, pady=(0, 10))

        # Clickable Signature Link in Chat UI
        github_label = tk.Label(user_list_frame, text="Developed by mad808", font=FONT_SMALL, fg=COLOR_SYSTEM, bg=COLOR_FRAME, cursor="hand2")
        github_label.pack(side=tk.BOTTOM, pady=10)
        github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/mad808"))
        github_label.bind("<Enter>", lambda e: github_label.config(fg=COLOR_ACCENT))
        github_label.bind("<Leave>", lambda e: github_label.config(fg=COLOR_SYSTEM))

        chat_container = ttk.Frame(main_pane, style="Chat.TFrame")
        main_pane.add(chat_container, weight=5)
        chat_container.columnconfigure(0, weight=1)
        chat_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(chat_container, bg=COLOR_BACKGROUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(chat_container, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.chat_frame = tk.Frame(self.canvas, bg=COLOR_BACKGROUND)
        self.canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        input_frame = ttk.Frame(chat_container, style="Input.TFrame", padding=(10, 15))
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.message_entry = ttk.Entry(input_frame, font=FONT_NORMAL)
        self.message_entry.grid(row=0, column=0, sticky="ew", ipady=10, padx=(0, 10))
        self.message_entry.bind("<Return>", self.send_text_message)
        self.message_entry.focus()
        
        attach_button = tk.Button(input_frame, text="📎", font=(FONT_FAMILY, 14), bg=COLOR_INPUT_BG, fg=COLOR_TEXT, relief="flat", command=self.send_file)
        attach_button.grid(row=0, column=1, padx=(0, 10))
        send_button = tk.Button(input_frame, text="➤", font=(FONT_FAMILY, 16), bg=COLOR_ACCENT, fg="#ffffff", relief="flat", command=self.send_text_message)
        send_button.grid(row=0, column=2)

    def _connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, DEFAULT_PORT))
            self._send_message_safe({'type': 'username', 'payload': self.username})
            threading.Thread(target=self.receive_messages, daemon=True).start()
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")
            self.destroy()
            return False

    def receive_messages(self):
        while self.client_socket:
            try:
                message = self._receive_message_safe()
                if message is None: break
                
                msg_type = message.get('type')
                if msg_type == 'text':
                    self.display_message(message['sender'], message['payload'])
                elif msg_type == 'system':
                    self.display_system_message(message['payload'])
                elif msg_type == 'user_list':
                    self.update_user_list(message['payload'])
                elif msg_type == 'file':
                    self.handle_incoming_file(message)
            except:
                self.handle_disconnection()
                break

    def display_message(self, sender, message_text):
        if not self.winfo_exists(): return
        
        is_self = sender == self.username
        align = 'e' if is_self else 'w'
        bubble_color = COLOR_BUBBLE_SELF if is_self else COLOR_BUBBLE_OTHER
        
        msg_frame = tk.Frame(self.chat_frame, bg=COLOR_BACKGROUND)
        msg_frame.pack(fill=tk.X, padx=20, pady=5, anchor=align)
        
        sender_label = tk.Label(msg_frame, text=sender, font=FONT_BOLD, bg=COLOR_BACKGROUND, fg=COLOR_ACCENT if is_self else COLOR_SYSTEM)
        sender_label.pack(anchor=align, padx=5)
        
        bubble = tk.Label(msg_frame, text=message_text, font=FONT_NORMAL, wraplength=600, justify=tk.LEFT,
                          bg=bubble_color, fg=COLOR_TEXT, padx=12, pady=8)
        bubble.pack(anchor=align, pady=(2, 4))
        
        time_label = tk.Label(msg_frame, text=datetime.now().strftime('%H:%M'), font=FONT_SMALL, bg=COLOR_BACKGROUND, fg=COLOR_SYSTEM)
        time_label.pack(anchor=align, padx=5)

        self.after(50, lambda: self.canvas.yview_moveto(1.0))

    def display_system_message(self, text):
        if not self.winfo_exists(): return
        label = tk.Label(self.chat_frame, text=text, font=(FONT_FAMILY, 10, "italic"), fg=COLOR_SYSTEM, bg=COLOR_BACKGROUND)
        label.pack(fill=tk.X, pady=10, padx=20)
        self.after(50, lambda: self.canvas.yview_moveto(1.0))

    def update_user_list(self, users):
        if not self.winfo_exists(): return
        self.after(0, lambda: [
            self.user_listbox.delete(0, tk.END),
            *[self.user_listbox.insert(tk.END, f" {u}{' (You)' if u == self.username else ''}") for u in sorted(users)]
        ])

    def send_text_message(self, event=None):
        text = self.message_entry.get()
        if text.strip():
            self._send_message_safe({'type': 'text', 'payload': text, 'sender': self.username})
            self.message_entry.delete(0, tk.END)

    def send_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            filename = os.path.basename(filepath)
            # Prevent potential crash with excessively large files
            if os.path.getsize(filepath) > 15 * 1024 * 1024:
                messagebox.showwarning("File Size Limit", "To prevent network lag, please select a file under 15MB.")
                return
            try:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                # Safe JSON transfer: Convert bytes to Base64 String
                encoded_data = base64.b64encode(file_data).decode('utf-8')
                self._send_message_safe({'type': 'file', 'filename': filename, 'payload': encoded_data, 'sender': self.username})
                self.display_system_message(f"You sent the file '{filename}'.")
            except Exception as e:
                self.display_system_message(f"Error sending file: {e}")

    def handle_incoming_file(self, msg):
        sender = msg.get('sender', 'Unknown')
        if sender == self.username: return

        filename = msg.get('filename', 'file.dat')
        payload_b64 = msg.get('payload')
        if payload_b64 and messagebox.askyesno("Incoming File", f"'{sender}' wants to send you '{filename}'. Accept?"):
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                try:
                    # Convert Base64 String back to raw bytes
                    file_data = base64.b64decode(payload_b64.encode('utf-8'))
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    self.display_system_message(f"File '{filename}' from '{sender}' was saved.")
                except Exception as e:
                    self.display_system_message(f"Error saving file: {e}")

    def handle_disconnection(self):
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
            if self.winfo_exists():
                self.after(0, lambda: self.display_system_message("Connection to the server has been lost."))

    def on_closing(self):
        if self.client_socket:
            try:
                self._send_message_safe({'type': 'disconnect'})
                self.client_socket.close()
            except: pass
        self.destroy()

    def _send_message_safe(self, message):
        with self.socket_lock:
            if self.client_socket:
                try:
                    data = json.dumps(message).encode('utf-8')
                    self.client_socket.sendall(struct.pack('!Q', len(data)) + data)
                except (ConnectionResetError, BrokenPipeError):
                    self.handle_disconnection()

    def _receive_message_safe(self):
        header = self.client_socket.recv(HEADER_LENGTH)
        if not header: return None
        length = struct.unpack('!Q', header)[0]
        data = bytearray(length)
        view = memoryview(data)
        while length > 0:
            bytes_recvd = self.client_socket.recv_into(view, length)
            if bytes_recvd == 0: return None
            view = view[bytes_recvd:]
            length -= bytes_recvd
        return json.loads(data.decode('utf-8'))


if __name__ == "__main__":
    AppLauncher().mainloop()