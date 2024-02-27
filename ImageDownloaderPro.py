import os
import requests
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from threading import Thread, Event
from PIL import Image, ImageTk  # Certifique-se de ter a biblioteca Pillow instalada

class ImageDownloader:
    def __init__(self, urls, folder_path, folder_name, progress_callback, status_callback, cancel_event):
        self.urls = urls
        self.folder_path = folder_path
        self.folder_name = folder_name
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.cancel_event = cancel_event

    def download_images(self):
        try:
            if self.folder_name:
                self.folder_path = os.path.join(self.folder_path, self.folder_name)

            if not os.path.exists(self.folder_path):
                os.makedirs(self.folder_path)

            total_images = 0
            current_image = 0

            for url in self.urls:
                if self.cancel_event.is_set():
                    self.status_callback("Download cancelado.")
                    return False, "Download cancelado."

                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                img_tags = soup.find_all('img')
                total_images += len(img_tags)

                for img_tag in img_tags:
                    img_url = img_tag.get('src')

                    if img_url:
                        img_url = urljoin(url, img_url)
                        img_data = requests.get(img_url).content
                        img_name = os.path.join(self.folder_path, os.path.basename(img_url))

                        with open(img_name, 'wb') as img_file:
                            img_file.write(img_data)

                        current_image += 1
                        progress_percent = (current_image / total_images) * 100
                        self.progress_callback(int(progress_percent))

            self.status_callback("Download de imagens concluído com sucesso!")
            return True, "Download de imagens concluído com sucesso."

        except requests.exceptions.RequestException as e:
            error_message = f"Erro de requisição: {str(e)}"
            self.status_callback(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Ocorreu um erro: {str(e)}"
            self.status_callback(error_message)
            return False, error_message

class ImageDownloaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Downloader")
        self.master.geometry("600x500")
        self.cancel_event = Event()
        self.download_thread = None

        self.urls_var = tk.StringVar()
        self.save_folder = tk.StringVar()
        self.folder_name_var = tk.StringVar()

        tk.Label(self.master, text="URLs para Baixar (separe por vírgula ou insira em linhas separadas):").pack(pady=5)
        self.entry_urls = tk.Text(self.master, wrap=tk.WORD, height=5, width=70)
        self.entry_urls.pack(pady=5, padx=10)

        tk.Label(self.master, text="Caminho de Destino:").pack(pady=5)
        self.entry_save_folder = tk.Entry(self.master, textvariable=self.save_folder, width=70)
        self.entry_save_folder.pack(pady=5, padx=10)
        tk.Button(self.master, text="Procurar", command=self.browse_save_folder).pack(pady=5)

        tk.Label(self.master, text="Nome da Pasta (opcional):").pack(pady=5)
        self.entry_folder_name = tk.Entry(self.master, textvariable=self.folder_name_var, width=70)
        self.entry_folder_name.pack(pady=5, padx=10)

        tk.Button(self.master, text="Baixar Imagens", command=self.download_images_threaded).pack(pady=10)
        self.cancel_button = tk.Button(self.master, text="Cancelar Download", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_button.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self.master, orient='horizontal', length=550, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.status_bar = tk.Label(self.master, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(self.master, text="Limpar URLs", command=self.clear_urls).pack(pady=5)

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def browse_save_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.save_folder.set(folder_selected)

    def download_images_threaded(self):
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo("Informação", "Um download já está em andamento.")
            return

        urls = [url.strip() for url in self.entry_urls.get("1.0", tk.END).splitlines() if url.strip()]
        folder_path = self.save_folder.get()
        folder_name = self.folder_name_var.get()

        if not urls:
            messagebox.showerror("Erro", "Insira pelo menos uma URL para baixar.")
            return

        if not all(self.is_valid_url(url) for url in urls):
            messagebox.showerror("Erro", "Uma ou mais URLs são inválidas.")
            return

        if not folder_path:
            messagebox.showerror("Erro", "Selecione um caminho de destino válido.")
            return

        self.progress_bar["value"] = 0
        self.cancel_event.clear()

        self.status_bar["text"] = "Baixando imagens..."
        self.cancel_button["state"] = tk.NORMAL  # Ativar o botão "Cancelar Download"
        self.download_thread = Thread(target=self.download_images, args=(urls, folder_path, folder_name), daemon=True)
        self.download_thread.start()

    def download_images(self, urls, folder_path, folder_name):
        self.update_ui(cancel_button_state=tk.DISABLED)  # Desativar o botão "Cancelar Download" durante o download
        image_downloader = ImageDownloader(urls, folder_path, folder_name, self.update_progress, self.update_status, self.cancel_event)
        success, message = image_downloader.download_images()
        self.show_message(success, message)
        self.update_ui(cancel_button_state=tk.DISABLED)  # Manter o botão "Cancelar Download" desativado após o download

    def update_progress(self, value):
        self.progress_bar["value"] = value
        self.master.update_idletasks()

    def update_status(self, message):
        self.status_bar["text"] = message
        self.master.update_idletasks()

    def show_message(self, success, message):
        self.status_bar["text"] = ""
        if success:
            messagebox.showinfo("Concluído", message)
        else:
            messagebox.showerror("Erro", message)
            # Adiciona uma caixa de diálogo de detalhes de erro
            self.show_error_details(message)

    def show_error_details(self, error_message):
        error_details_window = tk.Toplevel(self.master)
        error_details_window.title("Detalhes do Erro")
        tk.Label(error_details_window, text="Detalhes do Erro:").pack(pady=5)
        text_widget = tk.Text(error_details_window, wrap=tk.WORD, height=10, width=60)
        text_widget.insert(tk.END, error_message)
        text_widget.pack(pady=5, padx=10)
        text_widget.config(state=tk.DISABLED)

    def cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            if messagebox.askyesno("Cancelar Download", "Tem certeza de que deseja cancelar o download?"):
                self.cancel_event.set()
                self.status_bar["text"] = "Cancelando download..."
        else:
            messagebox.showinfo("Informação", "Nenhum download em andamento.")

    def on_close(self):
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo("Informação", "Aguarde o término do download antes de fechar a aplicação.")
        else:
            self.master.destroy()

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def update_ui(self, cancel_button_state):
        self.cancel_button["state"] = cancel_button_state

    def clear_urls(self):
        self.entry_urls.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageDownloaderApp(root)
    root.mainloop()
