import os
import io
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, UnidentifiedImageError
from datetime import datetime

# --- Drag & Drop Setup ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
    class CustomTkRoot(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
except ImportError:
    HAS_DND = False
    class CustomTkRoot(ctk.CTk):
        pass

# --- Application Configuration ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')

# --- Image Processing Logic ---
def process_image(input_path, output_path, max_size_kb, scale_percent, force_format="Auto"):
    try:
        img = Image.open(input_path)
        img_format = img.format if img.format else "JPEG"
        
        if force_format != "Auto":
            img_format = force_format
            output_path = os.path.splitext(output_path)[0] + f".{force_format.lower()}"
            if img_format in ["JPEG", "WEBP"]:
                img = img.convert("RGB")

        elif img_format == "PNG" and max_size_kb > 0:
            img_format = "JPEG"
            img = img.convert("RGB")
            output_path = os.path.splitext(output_path)[0] + ".jpg"

        if scale_percent < 100:
            new_width = int(img.width * (scale_percent / 100))
            new_height = int(img.height * (scale_percent / 100))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        if max_size_kb > 0:
            quality = 95
            while quality >= 10:
                buffer = io.BytesIO()
                img.save(buffer, format=img_format, quality=quality)
                size_kb = len(buffer.getvalue()) / 1024

                if size_kb <= max_size_kb:
                    with open(output_path, "wb") as f:
                        f.write(buffer.getvalue())
                    return True, f"Optimized to {size_kb:.1f}KB", output_path
                quality -= 5
            return False, "Could not compress below target size", None
            
        else:
            img.save(output_path, format=img_format, quality=95)
            return True, "Dimensions resized successfully", output_path

    except UnidentifiedImageError:
        return False, "Invalid or corrupted image file", None
    except Exception as e:
        return False, str(e), None


# --- UI Class ---
class SmartSizerPro(CustomTkRoot):
    def __init__(self):
        super().__init__()

        self.title("SmartSizer")
        self.geometry("950x750")
        self.minsize(900, 700)

        # --- 1. Fix: Load PNG Icon Safely ---
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "icon.png")
            icon_image = tk.PhotoImage(file=icon_path)
            self.iconphoto(False, icon_image)
        except Exception as e:
            print(f"⚠️ Could not load icon. Error: {e}")

        self.file_list = []
        self.output_folder = tk.StringVar()
        self.target_kb = tk.IntVar(value=1024)
        self.scale_percent = tk.IntVar(value=100)
        self.force_format = tk.StringVar(value="Auto")
        self.is_processing = False
        self.cancel_flag = False

        self.setup_navbar() # Replaced setup_menu()
        self.setup_ui()
        
        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_drop)
        else:
            self.log("⚠️ Drag-and-Drop disabled. Please 'pip install tkinterdnd2'", "error")

    # --- 2. Fix: Custom Modern Navigation Bar ---
    def setup_navbar(self):
        # Frame that sits at the very top
        self.nav_frame = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=("gray85", "gray15"))
        self.nav_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.nav_frame.grid_propagate(False) # Keep fixed height

        # Navigation Buttons
        self.btn_file = ctk.CTkButton(self.nav_frame, text="File", width=60, fg_color="transparent", 
                                      text_color=("black", "white"), hover_color=("gray75", "gray25"),
                                      command=lambda: self.show_file_menu(self.btn_file))
        self.btn_file.pack(side="left", padx=(5, 0), pady=4)

        self.btn_view = ctk.CTkButton(self.nav_frame, text="View", width=60, fg_color="transparent", 
                                      text_color=("black", "white"), hover_color=("gray75", "gray25"),
                                      command=lambda: self.show_view_menu(self.btn_view))
        self.btn_view.pack(side="left", padx=5, pady=4)

        self.btn_help = ctk.CTkButton(self.nav_frame, text="Help", width=60, fg_color="transparent", 
                                      text_color=("black", "white"), hover_color=("gray75", "gray25"),
                                      command=lambda: self.show_help_menu(self.btn_help))
        self.btn_help.pack(side="left", padx=5, pady=4)

    def _get_menu_colors(self):
        if ctk.get_appearance_mode() == "Dark":
            return {"bg": "#2b2b2b", "fg": "white", "abg": "#1f538d", "afg": "white"}
        else:
            return {"bg": "#f0f0f0", "fg": "black", "abg": "#3a7ebf", "afg": "white"}

    def show_file_menu(self, btn):
        colors = self._get_menu_colors()
        menu = tk.Menu(self, tearoff=0, bg=colors["bg"], fg=colors["fg"], activebackground=colors["abg"], activeforeground=colors["afg"], relief="flat", borderwidth=1)
        menu.add_command(label="Add Images...", command=self.select_image)
        menu.add_command(label="Add Folder...", command=self.select_folder)
        menu.add_separator()
        menu.add_command(label="Open Output Directory", command=self.open_output_dir_menu)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.quit)
        # Position dropdown right below the button
        menu.post(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())

    def show_view_menu(self, btn):
        colors = self._get_menu_colors()
        menu = tk.Menu(self, tearoff=0, bg=colors["bg"], fg=colors["fg"], activebackground=colors["abg"], activeforeground=colors["afg"], relief="flat", borderwidth=1)
        menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme_mode)
        menu.add_command(label="Show/Hide Advanced Settings", command=self.toggle_advanced)
        menu.post(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())

    def show_help_menu(self, btn):
        colors = self._get_menu_colors()
        menu = tk.Menu(self, tearoff=0, bg=colors["bg"], fg=colors["fg"], activebackground=colors["abg"], activeforeground=colors["afg"], relief="flat", borderwidth=1)
        menu.add_command(label="View Documentation", command=lambda: messagebox.showinfo("Documentation", "1. Select input images or drag and drop them.\n2. Adjust max size and dimensions.\n3. Click Start Optimization."))
        menu.add_command(label="About SmartSizer", command=lambda: messagebox.showinfo("About", "SmartSizer\n\nA professional batch image optimization utility.\n\n@2026 Parakrama Welipitiya"))
        menu.post(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())


    def setup_ui(self):
        # Adjusted rows to account for Navbar
        self.grid_rowconfigure(0, weight=0) # Navbar row
        self.grid_rowconfigure(1, weight=1) # Content row
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        # --- Left Panel ---
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        title_text = "SmartSizer" if HAS_DND else "SmartSizer (No DND)"
        ctk.CTkLabel(self.controls_frame, text=title_text, font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self.controls_frame, text="Drag & Drop images anywhere!", text_color="#1f6aa5").pack(pady=(0, 20))

        self.btn_select_folder = ctk.CTkButton(self.controls_frame, text="📁 Select Folder", command=self.select_folder)
        self.btn_select_folder.pack(pady=5, padx=20, fill="x")
        
        self.btn_select_image = ctk.CTkButton(self.controls_frame, text="🖼️ Select Images", fg_color="transparent", border_width=1, command=self.select_image)
        self.btn_select_image.pack(pady=5, padx=20, fill="x")

        self.lbl_selected_files = ctk.CTkLabel(self.controls_frame, text="No files selected", text_color="gray")
        self.lbl_selected_files.pack(pady=(0, 15))

        ctk.CTkLabel(self.controls_frame, text="Max File Size (KB):", anchor="w").pack(padx=20, fill="x")
        self.slider_kb = ctk.CTkSlider(self.controls_frame, from_=0, to=5000, variable=self.target_kb, command=self.update_labels)
        self.slider_kb.pack(padx=20, pady=5, fill="x")
        self.lbl_kb_val = ctk.CTkLabel(self.controls_frame, text="1024 KB (0 = Ignore)")
        self.lbl_kb_val.pack()

        ctk.CTkLabel(self.controls_frame, text="Scale Dimensions (%):", anchor="w").pack(padx=20, fill="x", pady=(10, 0))
        self.slider_scale = ctk.CTkSlider(self.controls_frame, from_=10, to=100, variable=self.scale_percent, command=self.update_labels)
        self.slider_scale.pack(padx=20, pady=5, fill="x")
        self.lbl_scale_val = ctk.CTkLabel(self.controls_frame, text="100% (Original Size)")
        self.lbl_scale_val.pack()

        self.btn_adv = ctk.CTkButton(self.controls_frame, text="⚙️ Advanced Settings", fg_color="transparent", text_color="gray", command=self.toggle_advanced)
        self.btn_adv.pack(pady=(10, 0))
        
        self.adv_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        ctk.CTkLabel(self.adv_frame, text="Force Output Format:").pack(anchor="w", padx=20)
        ctk.CTkOptionMenu(self.adv_frame, variable=self.force_format, values=["Auto", "JPEG", "WEBP", "PNG"]).pack(padx=20, fill="x")

        self.btn_output = ctk.CTkButton(self.controls_frame, text="💾 Choose Output Folder", command=self.select_output)
        self.btn_output.pack(pady=(20, 5), padx=20, fill="x")
        self.lbl_output = ctk.CTkLabel(self.controls_frame, text="Waiting for input...", text_color="gray", wraplength=200)
        self.lbl_output.pack(padx=20)

        self.btn_start = ctk.CTkButton(self.controls_frame, text="🚀 Start Optimization", height=40, font=ctk.CTkFont(weight="bold"), command=self.start_processing_thread)
        self.btn_start.pack(pady=20, padx=20, fill="x", side="bottom")


        # --- Right Panel ---
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(1, weight=3) 
        self.log_frame.grid_rowconfigure(4, weight=2) 
        self.log_frame.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(log_header, text="Activity Log", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        ctk.CTkButton(log_header, text="🗑️ Clear", width=60, height=24, fg_color="#333333", hover_color="#555555", command=self.clear_log).pack(side="right", padx=2)
        ctk.CTkButton(log_header, text="💾 Save", width=60, height=24, fg_color="#333333", hover_color="#555555", command=self.save_log).pack(side="right", padx=2)
        ctk.CTkButton(log_header, text="📋 Copy", width=60, height=24, fg_color="#333333", hover_color="#555555", command=self.copy_log).pack(side="right", padx=2)

        self.log_box = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.log_box.configure(state="disabled")
        
        self.log_box.tag_config("timestamp", foreground="#f39c12")
        self.log_box.tag_config("success", foreground="#2ecc71")
        self.log_box.tag_config("error", foreground="#e74c3c")
        self.log_box.tag_config("info", foreground="#cccccc")

        self.progress_bar = ctk.CTkProgressBar(self.log_frame)
        self.progress_bar.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)

        ctk.CTkLabel(self.log_frame, text="Live Preview Gallery", font=ctk.CTkFont(size=16, weight="bold")).grid(row=3, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.gallery_frame = ctk.CTkScrollableFrame(self.log_frame, orientation="horizontal", height=150)
        self.gallery_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

    # --- Utility Methods ---
    def open_output_dir_menu(self):
        out = self.output_folder.get()
        if out and os.path.exists(out):
            os.startfile(out)
        else:
            messagebox.showinfo("Not Found", "Output directory has not been set or created yet.")

    def toggle_theme_mode(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Light" if current == "Dark" else "Dark")

    def update_labels(self, _=None):
        self.lbl_kb_val.configure(text=f"{int(self.target_kb.get())} KB" if self.target_kb.get() > 0 else "0 (Ignore Limit)")
        self.lbl_scale_val.configure(text=f"{int(self.scale_percent.get())}%" if self.scale_percent.get() < 100 else "100% (Original)")

    def toggle_advanced(self):
        if self.adv_frame.winfo_ismapped():
            self.adv_frame.pack_forget()
        else:
            self.adv_frame.pack(fill="x", pady=10, before=self.btn_output)

    def log(self, message, level="info"):
        def append_text():
            now = datetime.now().strftime("%I:%M:%S %p")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{now}] ", "timestamp")
            self.log_box.insert("end", f"{message}\n", level)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, append_text)

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_box.get("1.0", "end"))
        self.update()
        messagebox.showinfo("Copied", "Log copied to clipboard!")

    def save_log(self):
        file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], title="Save Log")
        if file:
            with open(file, "w", encoding="utf-8") as f:
                f.write(self.log_box.get("1.0", "end"))
            self.log(f"💾 Log saved to {file}", "info")


    # --- File Handlers ---
    def set_default_output(self, source_path):
        out = os.path.join(os.path.dirname(source_path), "Optimized")
        self.output_folder.set(out)
        self.lbl_output.configure(text=out, text_color="white")

    def handle_drop(self, event):
        raw_files = self.tk.splitlist(event.data)
        valid_files = [f for f in raw_files if f.lower().endswith(SUPPORTED_FORMATS)]
        
        if valid_files:
            self.file_list.extend(valid_files)
            self.file_list = list(set(self.file_list))
            self.lbl_selected_files.configure(text=f"{len(self.file_list)} images loaded via Drop.", text_color="white")
            self.log(f"📥 Dropped {len(valid_files)} valid images.")
            self.set_default_output(self.file_list[0])

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(SUPPORTED_FORMATS)]
            self.file_list = files
            self.lbl_selected_files.configure(text=f"{len(self.file_list)} images found.", text_color="white")
            self.log(f"📂 Selected folder with {len(files)} images.")
            if files: self.set_default_output(files[0])

    def select_image(self):
        files = filedialog.askopenfilenames(title="Select Images", filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff")])
        if files:
            self.file_list = list(files)
            self.lbl_selected_files.configure(text=f"{len(self.file_list)} images selected.", text_color="white")
            self.log(f"🖼️ Selected {len(files)} image(s).")
            self.set_default_output(files[0])

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.lbl_output.configure(text=folder, text_color="white")

    def clear_gallery(self):
        for w in self.gallery_frame.winfo_children(): 
            w.destroy()

    def add_preview_image(self, img_path):
        try:
            img = Image.open(img_path)
            img.thumbnail((120, 120))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            lbl = ctk.CTkLabel(self.gallery_frame, image=ctk_img, text="")
            lbl.pack(side="left", padx=10, pady=5)
            self.gallery_frame._parent_canvas.xview_moveto(1.0)
        except Exception: pass

    # --- Interactive Retry Popup ---
    def prompt_retry_single(self):
        self.is_processing = False
        self.btn_start.configure(state="normal", text="🚀 Start Optimization", fg_color=["#3a7ebf", "#1f538d"])
        self.progress_bar.set(0)

        retry_win = ctk.CTkToplevel(self)
        retry_win.title("Optimization Failed")
        retry_win.geometry("400x300")
        retry_win.attributes("-topmost", True)
        retry_win.grab_set()

        ctk.CTkLabel(retry_win, text="⚠️ Target Size Too Small", font=("Arial", 18, "bold"), text_color="#e74c3c").pack(pady=(20, 5))
        ctk.CTkLabel(retry_win, text="This image cannot be compressed further.\nPlease choose a higher target limit.").pack(pady=(0, 20))

        suggested_kb = self.target_kb.get() + 500
        new_kb_var = tk.IntVar(value=suggested_kb)

        ctk.CTkLabel(retry_win, text="Adjust Target Size (KB):").pack()
        slider = ctk.CTkSlider(retry_win, from_=self.target_kb.get(), to=5000, variable=new_kb_var)
        slider.pack(pady=5)
        
        val_lbl = ctk.CTkLabel(retry_win, text=f"{suggested_kb} KB", font=("Arial", 14, "bold"))
        val_lbl.pack()

        def update_lbl(_):
            val_lbl.configure(text=f"{int(new_kb_var.get())} KB")
        slider.configure(command=update_lbl)

        def try_again():
            self.target_kb.set(int(new_kb_var.get()))
            self.update_labels()
            retry_win.destroy()
            self.start_processing_thread()

        btn_frame = ctk.CTkFrame(retry_win, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=retry_win.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Optimize Again", font=ctk.CTkFont(weight="bold"), command=try_again).pack(side="right", padx=10)

    # --- Threading & Processing ---
    def start_processing_thread(self):
        if not self.file_list or not self.output_folder.get():
            messagebox.showwarning("Warning", "Ensure inputs and output folder are set.")
            return

        if self.is_processing:
            self.cancel_flag = True
            self.btn_start.configure(text="Canceling...", state="disabled")
            self.log("🛑 Cancel requested! Finishing current file...", "error")
            return

        self.is_processing = True
        self.cancel_flag = False
        self.btn_start.configure(text="🛑 Cancel Processing", fg_color="darkred", hover_color="red")
        
        self.progress_bar.set(0)
        self.clear_gallery()

        threading.Thread(target=self.process_images, daemon=True).start()

    def process_images(self):
        self.log(f"🚀 Optimization started for {self.target_kb.get()} KB...", "info")
        out_dir = self.output_folder.get()
        os.makedirs(out_dir, exist_ok=True)
        
        target_kb = self.target_kb.get()
        scale_pct = self.scale_percent.get()
        fmt = self.force_format.get()
        
        success_count = 0
        orig_bytes, new_bytes = 0, 0
        total = len(self.file_list)

        for i, filepath in enumerate(self.file_list):
            if self.cancel_flag: break 

            filename = os.path.basename(filepath)
            temp_out_path = os.path.join(out_dir, filename)

            try: orig_bytes += os.path.getsize(filepath)
            except: pass

            success, msg, final_out_path = process_image(filepath, temp_out_path, target_kb, scale_pct, fmt)
            
            if success and final_out_path:
                self.log(f"✅ {os.path.basename(final_out_path)} -> {msg}", "success")
                success_count += 1
                try: new_bytes += os.path.getsize(final_out_path)
                except: pass
                self.after(0, lambda p=final_out_path: self.add_preview_image(p))
            else:
                self.log(f"❌ {filename} -> Error: {msg}", "error")

            self.after(0, self.progress_bar.set, (i + 1) / total)

        if total == 1 and success_count == 0 and not self.cancel_flag:
            self.after(0, self.prompt_retry_single)
        else:
            saved_mb = (orig_bytes - new_bytes) / (1024 * 1024)
            pct_saved = ((orig_bytes - new_bytes) / orig_bytes * 100) if orig_bytes > 0 else 0
            analytics = f"Space Saved: {saved_mb:.2f} MB ({pct_saved:.1f}%)" if saved_mb > 0 else "No significant space saved."
            self.after(0, lambda: self.reset_ui(success_count, total, out_dir, analytics))

    def reset_ui(self, success_count, total, out_dir, analytics_text):
        self.is_processing = False
        self.btn_start.configure(state="normal", text="🚀 Start Optimization", fg_color=["#3a7ebf", "#1f538d"])
        
        if self.cancel_flag:
            msg = f"Task Canceled.\n\nProcessed {success_count} images before canceling.\n{analytics_text}"
        else:
            self.progress_bar.set(1.0)
            msg = f"Task Finished!\n\nSuccessfully processed {success_count} of {total} images.\n\n📉 {analytics_text}"
            
        messagebox.showinfo("Optimization Complete", msg)
        
        try:
            if os.name == 'nt' and success_count > 0: os.startfile(out_dir)
        except: pass

        self.file_list = []
        self.lbl_selected_files.configure(text="No files selected", text_color="gray")
        self.output_folder.set("")
        self.lbl_output.configure(text="Waiting for input...", text_color="gray")
        self.progress_bar.set(0)
        self.clear_log()
        self.clear_gallery()

if __name__ == "__main__":
    app = SmartSizerPro()
    app.mainloop()