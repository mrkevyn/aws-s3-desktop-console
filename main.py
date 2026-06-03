import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import boto3
from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import threading
import os
from datetime import datetime
import humanize

# CONFIG
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("AWS_BUCKET")

# APP
class S3ModernApp:

    def __init__(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = TkinterDnD.Tk()
        self.root.title("AWS S3 Desktop Console")
        self.root.geometry("1400x850")
        self.root.configure(bg="#0f172a")

        self.selected_file = None

        # AWS CLIENT
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )

        # Multipart config
        self.transfer_config = TransferConfig(
            multipart_threshold=25 * 1024 * 1024,
            multipart_chunksize=25 * 1024 * 1024,
            max_concurrency=10,
            use_threads=True
        )

        self.setup_ui()

        self.list_files()

        self.root.mainloop()

    # UI
    def setup_ui(self):

        # SIDEBAR
        sidebar = ctk.CTkFrame(
            self.root,
            width=250,
            corner_radius=0,
            fg_color="#111827"
        )

        sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(
            sidebar,
            text="☁ AWS S3",
            font=("Segoe UI", 28, "bold")
        ).pack(pady=30)

        self.btn_upload = ctk.CTkButton(
            sidebar,
            text="📤 Upload",
            height=45,
            command=self.upload_file
        )

        self.btn_upload.pack(fill="x", padx=20, pady=10)

        self.btn_download = ctk.CTkButton(
            sidebar,
            text="⬇ Download",
            height=45,
            command=self.download_file
        )

        self.btn_download.pack(fill="x", padx=20, pady=10)

        self.btn_delete = ctk.CTkButton(
            sidebar,
            text="🗑 Delete",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=45,
            command=self.delete_file
        )

        self.btn_delete.pack(fill="x", padx=20, pady=10)

        self.btn_refresh = ctk.CTkButton(
            sidebar,
            text="🔄 Refresh",
            height=45,
            command=self.list_files
        )

        self.btn_refresh.pack(fill="x", padx=20, pady=10)

        # =========================================
        # STATUS
        # =========================================
        self.status_label = ctk.CTkLabel(
            sidebar,
            text="🟢 Online",
            text_color="#4ade80",
            font=("Segoe UI", 12, "bold")
        )

        self.status_label.pack(side="bottom", pady=20)

        # =========================================
        # MAIN AREA
        # =========================================
        main = ctk.CTkFrame(
            self.root,
            fg_color="#0f172a"
        )

        main.pack(side="left", fill="both", expand=True)

        # HEADER
        header = ctk.CTkFrame(
            main,
            fg_color="#0f172a"
        )

        header.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            header,
            text="AWS S3 CLOUD CONSOLE",
            font=("Segoe UI", 32, "bold")
        ).pack(anchor="w")

        # SEARCH
        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="Buscar arquivos...",
            width=400,
            height=40
        )

        self.search_entry.pack(anchor="w", pady=15)

        self.search_entry.bind("<KeyRelease>", lambda e: self.search_files())

        # STATS
        stats_frame = ctk.CTkFrame(
            main,
            fg_color="transparent"
        )

        stats_frame.pack(fill="x", padx=20)

        self.total_card = self.make_card(stats_frame, "📦 Arquivos", "0")
        self.total_card.pack(side="left", padx=10)

        self.size_card = self.make_card(stats_frame, "💾 Espaço", "0 GB")
        self.size_card.pack(side="left", padx=10)

        self.glacier_card = self.make_card(stats_frame, "🧊 Glacier", "0")
        self.glacier_card.pack(side="left", padx=10)

        self.standard_card = self.make_card(stats_frame, "⚡ Standard", "0")
        self.standard_card.pack(side="left", padx=10)

        # TABLE
        table_frame = ctk.CTkFrame(
            main,
            fg_color="#111827"
        )

        table_frame.pack(fill="both", expand=True, padx=20, pady=20)

        columns = (
            "icon",
            "name",
            "storage",
            "status",
            "size",
            "date"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=22
        )

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#111827",
            foreground="white",
            fieldbackground="#111827",
            rowheight=38,
            borderwidth=0,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Treeview.Heading",
            background="#1f2937",
            foreground="white",
            font=("Segoe UI", 10, "bold")
        )

        style.map(
            "Treeview",
            background=[("selected", "#2563eb")]
        )

        self.tree.heading("icon", text="")
        self.tree.heading("name", text="Arquivo")
        self.tree.heading("storage", text="Storage")
        self.tree.heading("status", text="Status")
        self.tree.heading("size", text="Tamanho")
        self.tree.heading("date", text="Upload")

        self.tree.column("icon", width=60, anchor="center")
        self.tree.column("name", width=500)
        self.tree.column("storage", width=130, anchor="center")
        self.tree.column("status", width=180, anchor="center")
        self.tree.column("size", width=120, anchor="center")
        self.tree.column("date", width=180, anchor="center")

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # DRAG DROP
        self.tree.drop_target_register(DND_FILES)
        self.tree.dnd_bind("<<Drop>>", self.drop_file)

        # PROGRESS
        progress_frame = ctk.CTkFrame(
            main,
            fg_color="#111827",
            height=90
        )

        progress_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.progress = ctk.CTkProgressBar(
            progress_frame,
            width=1000,
            height=25
        )

        self.progress.pack(pady=15)

        self.progress.set(0)

        self.progress_text = ctk.CTkLabel(
            progress_frame,
            text="0%"
        )

        self.progress_text.pack()

    # CARD
    def make_card(self, parent, title, value):

        card = ctk.CTkFrame(
            parent,
            width=220,
            height=100,
            fg_color="#111827"
        )

        card.pack_propagate(False)

        label1 = ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 13)
        )

        label1.pack(pady=(15, 5))

        label2 = ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 24, "bold")
        )

        label2.pack()

        card.value_label = label2

        return card

    # ICONS
    def get_icon(self, filename):

        ext = filename.split(".")[-1].lower()

        icons = {
            "jpg": "🖼",
            "png": "🖼",
            "jpeg": "🖼",
            "mp4": "🎥",
            "mkv": "🎥",
            "mp3": "🎵",
            "zip": "📦",
            "rar": "📦",
            "pdf": "📕",
            "exe": "⚙"
        }

        return icons.get(ext, "📄")

    # LIST FILES
    def list_files(self):

        self.tree.delete(*self.tree.get_children())

        total_size = 0
        glacier_count = 0
        standard_count = 0

        try:

            response = self.s3.list_objects_v2(
                Bucket=BUCKET_NAME
            )

            contents = response.get("Contents", [])

            for obj in contents:

                key = obj["Key"]

                meta = self.s3.head_object(
                    Bucket=BUCKET_NAME,
                    Key=key
                )

                storage = meta.get(
                    "StorageClass",
                    "STANDARD"
                )

                restore = meta.get("Restore", "")

                if storage == "STANDARD":
                    badge = "⚡ STANDARD"
                    standard_count += 1
                else:
                    badge = "🧊 GLACIER"
                    glacier_count += 1

                if 'ongoing-request="false"' in restore:
                    status = "🟢 Restaurado"
                elif 'ongoing-request="true"' in restore:
                    status = "🔄 Restaurando"
                else:
                    status = "🟢 Disponível"

                size = humanize.naturalsize(obj["Size"])

                total_size += obj["Size"]

                date = obj["LastModified"].strftime(
                    "%d/%m/%Y %H:%M"
                )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        self.get_icon(key),
                        key,
                        badge,
                        status,
                        size,
                        date
                    )
                )

            self.total_card.value_label.configure(
                text=str(len(contents))
            )

            self.size_card.value_label.configure(
                text=humanize.naturalsize(total_size)
            )

            self.glacier_card.value_label.configure(
                text=str(glacier_count)
            )

            self.standard_card.value_label.configure(
                text=str(standard_count)
            )

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # SEARCH
    def search_files(self):

        query = self.search_entry.get().lower()

        for item in self.tree.get_children():

            values = self.tree.item(item)["values"]

            filename = str(values[1]).lower()

            if query in filename:
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    # SELECT
    def on_select(self, event):

        try:
            item = self.tree.selection()[0]

            values = self.tree.item(item)["values"]

            self.selected_file = values[1]

            self.status_label.configure(
                text=f"📄 {self.selected_file}",
                text_color="white"
            )

        except:
            pass

    # UPLOAD
    def upload_file(self):

        file_path = filedialog.askopenfilename()

        if not file_path:
            return

        self.start_upload(file_path)

    # DRAG DROP
    def drop_file(self, event):

        file_path = event.data.replace("{", "").replace("}", "")

        self.start_upload(file_path)

    # START UPLOAD
    def start_upload(self, file_path):

        file_name = os.path.basename(file_path)

        def task():

            try:

                total = os.path.getsize(file_path)

                uploaded = 0

                start_time = datetime.now()

                # =========================
                # STORAGE CLASS
                # =========================
                gb_size = total / (1024 * 1024 * 1024)

                if gb_size > 5:
                    storage_class = "STANDARD"
                    storage_badge = "⚡ STANDARD"
                else:
                    storage_class = "GLACIER"
                    storage_badge = "🧊 GLACIER"

                # RESET UI
                self.root.after(
                    0,
                    lambda: self.progress.set(0)
                )

                self.root.after(
                    0,
                    lambda: self.progress_text.configure(
                        text="0%"
                    )
                )

                self.root.after(
                    0,
                    lambda: self.status_label.configure(
                        text=f"🚀 Upload iniciado ({storage_badge})",
                        text_color="#60a5fa"
                    )
                )

                # =========================
                # CALLBACK
                # =========================
                def callback(bytes_amount):

                    nonlocal uploaded

                    uploaded += bytes_amount

                    percent = uploaded / total

                    elapsed = (
                        datetime.now() - start_time
                    ).total_seconds()

                    speed = uploaded / elapsed if elapsed > 0 else 0

                    remaining = (
                        (total - uploaded) / speed
                        if speed > 0 else 0
                    )

                    uploaded_text = humanize.naturalsize(uploaded)
                    total_text = humanize.naturalsize(total)

                    speed_text = humanize.naturalsize(speed) + "/s"

                    remaining_text = humanize.precisedelta(
                        remaining
                    )

                    # UPDATE UI
                    self.root.after(
                        0,
                        lambda: self.progress.set(percent)
                    )

                    self.root.after(
                        0,
                        lambda: self.progress_text.configure(
                            text=(
                                f"{int(percent * 100)}%  •  "
                                f"{uploaded_text} / {total_text}  •  "
                                f"{speed_text}  •  "
                                f"⏱ {remaining_text}"
                            )
                        )
                    )

                # =========================
                # UPLOAD
                # =========================
                self.s3.upload_file(
                    file_path,
                    BUCKET_NAME,
                    file_name,

                    Config=self.transfer_config,

                    ExtraArgs={
                        "StorageClass": storage_class
                    },

                    Callback=callback
                )

                # COMPLETE
                self.root.after(
                    0,
                    lambda: self.progress.set(1)
                )

                self.root.after(
                    0,
                    lambda: self.progress_text.configure(
                        text="✅ Upload concluído"
                    )
                )

                self.root.after(
                    0,
                    lambda: self.status_label.configure(
                        text=f"✔ Upload finalizado ({storage_badge})",
                        text_color="#4ade80"
                    )
                )

                self.root.after(
                    0,
                    self.list_files
                )

            except Exception as e:

                self.root.after(
                    0,
                    lambda: self.status_label.configure(
                        text="❌ Erro no upload",
                        text_color="#ef4444"
                    )
                )

                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Erro",
                        str(e)
                    )
                )

        threading.Thread(
            target=task,
            daemon=True
        ).start()

    # DOWNLOAD
    def download_file(self):

        if not self.selected_file:
            return

        path = filedialog.asksaveasfilename(
            initialfile=self.selected_file
        )

        if not path:
            return

        def task():

            try:

                self.s3.download_file(
                    BUCKET_NAME,
                    self.selected_file,
                    path
                )

                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "OK",
                        "Download concluído"
                    )
                )

            except Exception as e:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Erro",
                        str(e)
                    )
                )

        threading.Thread(
            target=task,
            daemon=True
        ).start()

    # DELETE
    def delete_file(self):

        if not self.selected_file:
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            f"Deletar {self.selected_file}?"
        )

        if not confirm:
            return

        try:

            self.s3.delete_object(
                Bucket=BUCKET_NAME,
                Key=self.selected_file
            )

            self.list_files()

        except Exception as e:
            messagebox.showerror("Erro", str(e))

# START
if __name__ == "__main__":
    S3ModernApp()