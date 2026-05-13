import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD


class M4SProcessorApp(TkinterDnD.Tk):
    CHUNK_SIZE = 8 * 1024 * 1024  # 每次处理 8MB，适合大文件

    def __init__(self):
        super().__init__()
        self.title("M4S文件处理器")
        self.geometry("600x360")

        self.target_folder = tk.StringVar()
        self.is_processing = False

        self.total_bytes = 0
        self.copied_bytes = 0

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(
            self,
            text="拖放文件夹到此处 或 点击选择文件夹",
            font=("微软雅黑", 12)
        ).pack(pady=10)

        self.drop_frame = ttk.Frame(self, relief="solid", borderwidth=2)
        self.drop_frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)

        ttk.Button(
            self.drop_frame,
            text="选择视频文件夹",
            command=self.choose_folder,
            width=15
        ).place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(self, text="视频文件夹路径：").pack(pady=(10, 0), padx=20, anchor="w")

        self.path_entry = ttk.Entry(self, textvariable=self.target_folder, width=70)
        self.path_entry.pack(padx=20, fill="x")

        self.start_button = ttk.Button(
            self,
            text="开始处理",
            command=self.start_processing,
            style="Accent.TButton"
        )
        self.start_button.pack(pady=15)

        self.progress_bar = ttk.Progressbar(
            self,
            orient="horizontal",
            length=520,
            mode="determinate"
        )
        self.progress_bar.pack(pady=5)

        self.status_label = ttk.Label(self, text="", foreground="blue")
        self.status_label.pack(pady=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Accent.TButton",
            foreground="white",
            background="#4CAF50",
            font=("微软雅黑", 10)
        )

    def on_drop(self, event):
        """处理拖放文件夹事件，支持路径中有空格"""
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = event.data.strip().split()

        folders = []
        for path in paths:
            path = os.path.normpath(path.strip("{}").strip('"'))
            if os.path.isdir(path):
                folders.append(path)

        if folders:
            self.target_folder.set(folders[0])
            self.status_label.config(text=f"已检测到文件夹：{folders[0]}")
        else:
            messagebox.showwarning("提示", "拖放的内容不是有效文件夹！")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="选择包含 .m4s 文件的文件夹")
        if folder:
            self.target_folder.set(folder)
            self.status_label.config(text=f"已选择文件夹：{folder}")

    def start_processing(self):
        """点击按钮后启动后台线程"""
        if self.is_processing:
            return

        target_dir = self.target_folder.get()

        if not target_dir or not os.path.isdir(target_dir):
            messagebox.showerror("错误", "请选择有效的文件夹路径！")
            return

        self.is_processing = True
        self.start_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.status_label.config(text="准备处理中...")

        thread = threading.Thread(
            target=self.process_files,
            args=(target_dir,),
            daemon=True
        )
        thread.start()

    def process_files(self, target_dir):
        """后台处理文件，避免窗口未响应"""
        try:
            current_dir = os.path.normpath(target_dir)

            m4s_files = [
                os.path.join(current_dir, f)
                for f in os.listdir(current_dir)
                if f.lower().endswith(".m4s")
            ]

            if len(m4s_files) != 2:
                raise RuntimeError(
                    f"当前文件夹下需要恰好两个 .m4s 文件！当前找到 {len(m4s_files)} 个"
                )

            m4s_files.sort(key=lambda x: os.path.getsize(x))

            small_file = m4s_files[0]
            large_file = m4s_files[1]

            ending_dir = os.path.join(current_dir, "ending")
            ending_dir = os.path.normpath(ending_dir)
            os.makedirs(ending_dir, exist_ok=True)

            small_dest = os.path.join(ending_dir, "audio.mp3")
            large_dest = os.path.join(ending_dir, "video.mp4")

            self.total_bytes = (
                max(os.path.getsize(small_file) - 9, 0)
                + max(os.path.getsize(large_file) - 9, 0)
            )
            self.copied_bytes = 0

            self.set_status("正在处理音频文件...")
            self.copy_without_first_n_bytes(
                small_file,
                small_dest,
                n=9,
                progress_callback=self.update_progress
            )

            self.set_status("正在处理视频文件，文件较大请耐心等待...")
            self.copy_without_first_n_bytes(
                large_file,
                large_dest,
                n=9,
                progress_callback=self.update_progress
            )

            self.set_progress(100)
            self.set_status("处理完成！")

            self.after(0, lambda: messagebox.showinfo(
                "成功",
                f"所有文件处理完成！\n\n处理后的文件保存在：\n{ending_dir}"
            ))

        except Exception:
            error_msg = traceback.format_exc()
            self.set_status("处理失败")

            self.after(0, lambda: messagebox.showerror(
                "处理失败",
                f"错误详情：\n{error_msg}"
            ))

        finally:
            self.after(0, self.finish_processing)

    def finish_processing(self):
        self.is_processing = False
        self.start_button.config(state="normal")

    def set_status(self, text):
        self.after(0, lambda: self.status_label.config(text=text))

    def set_progress(self, value):
        self.after(0, lambda: self.progress_bar.config(value=value))

    def update_progress(self, copied_size):
        self.copied_bytes += copied_size

        if self.total_bytes <= 0:
            return

        percent = self.copied_bytes / self.total_bytes * 100
        self.set_progress(percent)

        copied_gb = self.copied_bytes / 1024 / 1024 / 1024
        total_gb = self.total_bytes / 1024 / 1024 / 1024

        self.set_status(f"处理中... {percent:.1f}%  ({copied_gb:.2f} GB / {total_gb:.2f} GB)")

    @classmethod
    def copy_without_first_n_bytes(cls, src, dst, n=9, progress_callback=None):
        """
        复制文件时跳过前 n 个字节。
        不会一次性读取整个文件，适合几十 GB 的大文件。
        """
        if not os.path.isfile(src):
            raise FileNotFoundError(f"文件不存在：{src}")

        file_size = os.path.getsize(src)

        if file_size <= n:
            raise ValueError(f"文件太小，无法删除前 {n} 个字节：{src}")

        temp_dst = dst + ".tmp"

        try:
            with open(src, "rb") as f_in:
                f_in.seek(n)

                with open(temp_dst, "wb") as f_out:
                    while True:
                        chunk = f_in.read(cls.CHUNK_SIZE)

                        if not chunk:
                            break

                        f_out.write(chunk)

                        if progress_callback:
                            progress_callback(len(chunk))

            os.replace(temp_dst, dst)

        except Exception:
            if os.path.exists(temp_dst):
                try:
                    os.remove(temp_dst)
                except Exception:
                    pass

            raise


if __name__ == "__main__":
    app = M4SProcessorApp()
    app.mainloop()