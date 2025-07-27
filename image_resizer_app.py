import os
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Menu
from PIL import Image, ImageTk

MAX_SIZE_KB_DEFAULT = 1024
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')


def compress_image_to_size(input_path, output_path, max_size_kb=MAX_SIZE_KB_DEFAULT):
    try:
        image = Image.open(input_path)
        image_format = image.format if image.format != "PNG" else "JPEG"
        quality = 95

        while quality >= 10:
            buffer = io.BytesIO()
            image.save(buffer, format=image_format, quality=quality)
            size_kb = len(buffer.getvalue()) / 1024

            if size_kb <= max_size_kb:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(buffer.getvalue())
                return True, image
            quality -= 5

        return False, image
    except Exception as e:
        print(f"Error compressing image {input_path}: {e}")
        return False, None


class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartSizer - Resize Images Under Target Size")
        self.root.geometry("700x560")
        self.root.resizable(False, False)
        self.file_list = []
        self.output_folder = tk.StringVar()
        self.dark_mode = tk.BooleanVar(value=False)
        self.show_preview = tk.BooleanVar(value=False)
        self.target_size_kb = tk.IntVar(value=MAX_SIZE_KB_DEFAULT)

        self.setup_menu()
        self.setup_ui()
        self.set_theme()

    def setup_menu(self):
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        # File menu
        file_menu = Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu.add_cascade(label="File", menu=file_menu)

        # FAQ menu
        faq_menu = Menu(self.menu, tearoff=0)
        faq_menu.add_command(label="Help", command=self.show_faq)
        self.menu.add_cascade(label="Help", menu=faq_menu)

        # Contact menu
        contact_menu = Menu(self.menu, tearoff=0)
        contact_menu.add_command(label="Contact Us", command=self.show_contact)
        self.menu.add_cascade(label="Contact", menu=contact_menu)

        # Settings menu
        settings_menu = Menu(self.menu, tearoff=0)
        settings_menu.add_command(label="Change Output Folder", command=self.change_output_folder)
        settings_menu.add_checkbutton(label="Toggle Dark Mode", onvalue=True, offvalue=False,
                                      variable=self.dark_mode, command=self.toggle_dark_mode)
        self.menu.add_cascade(label="Settings", menu=settings_menu)

    def setup_ui(self):
        ttk.Label(self.root, text="SmartSizer Image Converter", font=("Segoe UI", 16, "bold")).pack(pady=10)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="📁 Select Folder", command=self.select_folder).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="🖼️ Select Image", command=self.select_image).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="💾 Output Folder", command=self.select_output_folder).grid(row=0, column=2, padx=5)

        ttk.Label(self.root, text="Target File Size (KB):").pack()
        size_slider = ttk.Scale(self.root, from_=100, to=5120, orient='horizontal', variable=self.target_size_kb)
        size_slider.pack(pady=5)
        ttk.Label(self.root, textvariable=self.target_size_kb).pack()

        ttk.Entry(self.root, textvariable=self.output_folder, width=80).pack(pady=5)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(pady=5)

        self.status_box = tk.Text(self.root, height=10, width=85, state='disabled', font=("Consolas", 9))
        self.status_box.pack(pady=10)

        ttk.Checkbutton(self.root, text="Show Image Preview", variable=self.show_preview).pack()

        ttk.Button(self.root, text="🚀 Start Resizing", command=self.start_resizing).pack(pady=10)

        self.preview_frame = ttk.Frame(self.root)
        self.preview_frame.pack()

    def log(self, message):
        self.status_box.configure(state='normal')
        self.status_box.insert(tk.END, f"{message}\n")
        self.status_box.see(tk.END)
        self.status_box.configure(state='disabled')

    def clear_log(self):
        self.status_box.configure(state='normal')
        self.status_box.delete('1.0', tk.END)
        self.status_box.configure(state='disabled')

    def clear_previews(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder with Images")
        if folder_path:
            self.file_list = [os.path.join(folder_path, f)
                              for f in os.listdir(folder_path)
                              if f.lower().endswith(SUPPORTED_FORMATS)]
            self.clear_log()
            self.log(f"📂 Selected folder with {len(self.file_list)} supported image(s).")
            self.clear_previews()

    def select_image(self):
        file_path = filedialog.askopenfilename(title="Select Image",
                                               filetypes=[("Supported Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff")])
        if file_path:
            self.file_list = [file_path]
            self.clear_log()
            self.log("🖼️ Selected single image.")
            self.clear_previews()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.log(f"💾 Output will be saved in: {folder}")

    def change_output_folder(self):
        self.select_output_folder()

    def toggle_dark_mode(self):
        self.set_theme()

    def set_theme(self):
        dark = self.dark_mode.get()
        bg_color = "#1e1e1e" if dark else "#ffffff"
        fg_color = "#ffffff" if dark else "#000000"
        entry_bg = "#2e2e2e" if dark else "#f0f0f0"
        entry_fg = fg_color

        self.root.configure(bg=bg_color)

        # Apply colors to all children widgets recursively
        def recursive_color(widget):
            try:
                if isinstance(widget, (tk.Text, ttk.Entry, ttk.Scale)):
                    widget.configure(background=entry_bg, foreground=entry_fg)
                else:
                    widget.configure(bg=bg_color, fg=fg_color)
            except Exception:
                pass
            for child in widget.winfo_children():
                recursive_color(child)

        recursive_color(self.root)

    def show_faq(self):
        messagebox.showinfo("Help", "This app allows you to resize images under a target size.\n\n"
                                   "1. Add images.\n"
                                   "2. Choose target size.\n"
                                   "3. Select output folder.\n"
                                   "4. Click Resize.\n\n"
                                   "Supported formats: jpg, jpeg, png, webp, bmp, tiff.")

    def show_contact(self):
        messagebox.showinfo("Contact", "For support, email: parakramawelipitiya00@gmail.com\n"
                                      "Phone: +94 75 435 7288")

    def start_resizing(self):
        out_folder = self.output_folder.get().strip()
        if not self.file_list:
            messagebox.showwarning("No Images", "Please select an image or folder first.")
            return
        if not out_folder:
            messagebox.showwarning("No Output Folder", "Please select an output folder.")
            return

        self.clear_log()
        self.clear_previews()
        self.log("🚀 Resizing started...")
        resized_count = 0

        self.progress["maximum"] = len(self.file_list)
        self.progress["value"] = 0

        target_size_kb = self.target_size_kb.get()

        self.root.config(cursor="wait")
        self.root.update()

        for i, img_path in enumerate(self.file_list):
            file_name = os.path.basename(img_path)
            output_path = os.path.join(out_folder, file_name)

            # Skip already optimized
            if os.path.exists(output_path) and os.path.getsize(output_path) <= target_size_kb * 1024:
                self.log(f"⏩ {file_name} already optimized. Skipped.")
                self.progress["value"] += 1
                self.root.update_idletasks()
                continue

            success, image = compress_image_to_size(img_path, output_path, max_size_kb=target_size_kb)
            if success:
                self.log(f"✅ {file_name} resized successfully.")
                resized_count += 1

                if self.show_preview.get() and image:
                    preview_img = image.copy()
                    preview_img.thumbnail((120, 120))
                    photo = ImageTk.PhotoImage(preview_img)
                    label = ttk.Label(self.preview_frame, image=photo)
                    label.image = photo
                    label.pack(side="left", padx=5, pady=5)
            else:
                self.log(f"❌ {file_name} could not be resized under {target_size_kb}KB.")

            self.progress["value"] += 1
            self.root.update_idletasks()

        self.root.config(cursor="")
        self.log(f"\n🎉 Done! {resized_count}/{len(self.file_list)} images resized.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()
