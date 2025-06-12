import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import socket
import os
import threading

class FileClientApp:
    def __init__(self, master):
        self.master = master
        master.title("Two-Way TCP File Client")

        # Configure grid to center and expand
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(9, weight=1)

        # Server IP input
        tk.Label(master, text="Server IP:").grid(row=0, column=0, sticky="e", padx=10, pady=5)
        self.ip_entry = tk.Entry(master)
        self.ip_entry.grid(row=0, column=1, sticky="we", padx=10, pady=5)
        self.ip_entry.insert(0, "127.0.0.1")

        # Server Port input
        tk.Label(master, text="Port:").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.port_entry = tk.Entry(master)
        self.port_entry.grid(row=1, column=1, sticky="we", padx=10, pady=5)
        self.port_entry.insert(0, "5001")

        # Upload button
        self.upload_btn = tk.Button(master, text="Upload File", command=self.upload_file)
        self.upload_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        # Download input
        tk.Label(master, text="Download Filename:").grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.download_entry = tk.Entry(master)
        self.download_entry.grid(row=3, column=1, sticky="we", padx=10, pady=5)

        self.download_btn = tk.Button(master, text="Download File", command=self.download_file)
        self.download_btn.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        # Upload progress bar
        tk.Label(master, text="Upload Progress:").grid(row=5, column=0, sticky="e", padx=10, pady=5)
        self.upload_progress = ttk.Progressbar(master, orient='horizontal', length=200, mode='determinate')
        self.upload_progress.grid(row=5, column=1, sticky="we", padx=10, pady=5)

        # Download progress bar
        tk.Label(master, text="Download Progress:").grid(row=6, column=0, sticky="e", padx=10, pady=5)
        self.download_progress = ttk.Progressbar(master, orient='horizontal', length=200, mode='determinate')
        self.download_progress.grid(row=6, column=1, sticky="we", padx=10, pady=5)

        # Connection status label
        self.status_label = tk.Label(master, text="Status: not connected", fg="red")
        self.status_label.grid(row=7, column=0, columnspan=2, pady=5)

        # Status log
        self.status_text = tk.Text(master, height=10, width=50)
        self.status_text.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

    def log(self, message):
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)

    def set_status(self, message, color="blue"):
        self.status_label.config(text=f"Status: {message}", fg=color)
        self.log(message)

    def toggle_buttons(self, state="normal"):
        self.upload_btn.config(state=state)
        self.download_btn.config(state=state)

    def download_file(self):
        filename = self.download_entry.get()
        if not filename:
            messagebox.showwarning("Input Missing", "Please enter a filename to download.")
            return

        def download_thread():
            try:
                self.set_status("Downloading...", "orange")
                self.toggle_buttons("disabled")
                self.download_progress['value'] = 0

                server_ip = self.ip_entry.get()
                port = int(self.port_entry.get())

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((server_ip, port))
                    s.sendall(f"DOWNLOAD|{filename}\n".encode('utf-8'))

                    header = s.recv(1024).decode('utf-8')
                    if header.startswith("NOTFOUND"):
                        self.set_status(f"File '{filename}' not found.", "red")
                        self.toggle_buttons("normal")
                        return
                    elif header.startswith("SIZE|"):
                        filesize = int(header.split('|')[1])
                    else:
                        self.set_status("Unexpected server response.", "red")
                        self.toggle_buttons("normal")
                        return

                    save_path = filedialog.asksaveasfilename(initialfile=filename)
                    if not save_path:
                        self.set_status("Download cancelled.", "blue")
                        self.toggle_buttons("normal")
                        return

                    with open(save_path, "wb") as file:
                        received = 0
                        while received < filesize:
                            chunk = s.recv(min(4096, filesize - received))
                            if not chunk:
                                break
                            file.write(chunk)
                            received += len(chunk)
                            self.download_progress['value'] = (received / filesize) * 100
                            self.master.update_idletasks()

                    if received == filesize:
                        self.set_status(f"Downloaded '{filename}' successfully.", "green")
                    else:
                        self.set_status(f"Download incomplete.", "red")

            except Exception as e:
                self.set_status(f"Download failed: {e}", "red")
            finally:
                self.toggle_buttons("normal")
                self.download_progress['value'] = 0

        threading.Thread(target=download_thread, daemon=True).start()

    def upload_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        def upload_thread():
            try:
                self.set_status("Uploading...", "orange")
                self.toggle_buttons("disabled")
                self.upload_progress['value'] = 0

                server_ip = self.ip_entry.get()
                port = int(self.port_entry.get())
                filename = os.path.basename(filepath)
                filesize = os.path.getsize(filepath)

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((server_ip, port))
                    header = f"UPLOAD|{filename}|{filesize}\n".encode('utf-8')
                    s.sendall(header)

                    ack = s.recv(1024).decode('utf-8')
                    if ack != "READY":
                        self.set_status("Server not ready for upload.", "red")
                        self.toggle_buttons("normal")
                        return

                    sent = 0
                    with open(filepath, "rb") as file:
                        while chunk := file.read(4096):
                            s.sendall(chunk)
                            sent += len(chunk)
                            self.upload_progress['value'] = (sent / filesize) * 100
                            self.master.update_idletasks()

                self.set_status(f"Uploaded '{filename}' successfully.", "green")

            except Exception as e:
                self.set_status(f"Upload failed: {e}", "red")
            finally:
                self.toggle_buttons("normal")
                self.upload_progress['value'] = 0

        threading.Thread(target=upload_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileClientApp(root)

    # Center the window after it's fully laid out
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()
