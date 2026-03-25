# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'main.py'
# Bytecode version: 3.13.0rc3 (3571)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from ttkthemes import ThemedTk
    HAS_THEMES = True
except ImportError:
    HAS_THEMES = False
from PIL import Image, ImageTk, ImageSequence
from editor_app import XMLConfigEditor
from tools_app import ConfigToolsApp
from analyses_tab import AnalysesTab
from patterns_tab import PatternsTab
from search_tab import SearchTab
class ImpactConfigSuite:
    # ***<module>.ImpactConfigSuite: Failure detected at line number 89 and instruction offset 42: Different bytecode
    def __init__(self, root):
        self.root = root
        self.root.title('IMPACT Configuration Suite v3.0')
        self.root.geometry('1150x900')
        self.root.minsize(1050, 800)
        self.dark_mode = True
        self.dark_theme = 'equilux'
        self.light_theme = 'arc'
        self.load_branding_images()
        self.style = ttk.Style()
        self.apply_theme()
        self.header_frame = ttk.Frame(self.root, padding='10')
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        if hasattr(self, 'logo_img'):
            ttk.Label(self.header_frame, image=self.logo_img).pack(side=tk.LEFT)
        self.title_frame = ttk.Frame(self.header_frame)
        self.title_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(self.title_frame, text='IMPACT CONFIGURATION SUITE', font=('Segoe UI', 18, 'bold')).pack(anchor=tk.W)
        ttk.Label(self.title_frame, text='Unified Management & Workflow Engineering', font=('Segoe UI', 10)).pack(anchor=tk.W)
        if hasattr(self, 'newgen_img'):
            ttk.Label(self.header_frame, image=self.newgen_img).pack(side=tk.RIGHT)
        self.theme_btn = ttk.Button(self.header_frame, text=' 🌙 ', command=self.toggle_theme, width=3)
        self.theme_btn.pack(side=tk.RIGHT, padx=10)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_frame, text=' 📝 XML Editor ')
        self.editor_app = XMLConfigEditor(self.editor_frame, is_tab=True, root_win=self.root)
        self.tools_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tools_frame, text=' ⚙️ Validation & Workflow ')
        self.tools_app = ConfigToolsApp(self.tools_frame, is_tab=True, root_win=self.root)
        self.analyses_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analyses_frame, text=' 🔍 XML Analysis ')
        self.analyses_app = AnalysesTab(self.analyses_frame, root_win=self.root)
        self.analyses_app.pack(fill=tk.BOTH, expand=True)
        self.patterns_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.patterns_frame, text=' 📈 Pattern Report ')
        self.patterns_app = PatternsTab(self.patterns_frame, root_win=self.root)
        self.patterns_app.pack(fill=tk.BOTH, expand=True)
        self.search_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.search_frame, text=' 🌐 Global Search ')
        self.search_app = SearchTab(self.search_frame, root_win=self.root)
        self.search_app.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value='IMPACT Config Suite v3.0 Ready')
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
    def on_closing(self):
        """Cleanup on application exit"""
        if hasattr(self, 'search_app'):
            self.search_app.on_closing()
        self.root.destroy()
    def load_branding_images(self):
        # irreducible cflow, using cdg fallback
        """Load global logos and application icon"""
        # ***<module>.ImpactConfigSuite.load_branding_images: Failure: Compilation Error
        logo_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images_logo')
        impact_path = os.path.join(logo_folder, 'IMPACT.png')
        if os.path.exists(impact_path):
            img = Image.open(impact_path).resize((100, 40), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
        newgen_path = os.path.join(logo_folder, 'newgen.png')
        if os.path.exists(newgen_path):
            img = Image.open(newgen_path).resize((120, 30), Image.LANCZOS)
            self.newgen_img = ImageTk.PhotoImage(img)
        icon_path = os.path.join(logo_folder, 'newgen_logo_sm.png')
        if os.path.exists(icon_path):
            icon_img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(icon_img)
            self.root.wm_iconphoto(True, photo)
            self.app_icon = photo
                except Exception as e:
                        print(f'Error loading branding: {e}')
    def apply_theme(self):
        """Apply the current theme to the application"""
        if HAS_THEMES:
            available = self.root.get_themes()
            target = self.dark_theme if self.dark_mode else self.light_theme
            if target in available:
                self.root.set_theme(target)
            else:
                fallback = 'black' if self.dark_mode else 'clam'
                self.style.theme_use(fallback)
        else:
            self.style.theme_use('clam')
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        for app_name in ['editor_app', 'tools_app', 'analyses_app', 'patterns_app', 'search_app']:
            if hasattr(self, app_name):
                sub_app = getattr(self, app_name)
                if hasattr(sub_app, 'refresh_theme'):
                    sub_app.refresh_theme()
        if self.dark_mode:
            self.theme_btn.config(text=' 🌙 ')
            self.status_var.set('Dark mode activated')
        else:
            self.theme_btn.config(text=' ☀️ ')
            self.status_var.set('Light mode activated')
def main():
    if HAS_THEMES:
        root = ThemedTk(theme='equilux')
    else:
        root = tk.Tk()
    app = ImpactConfigSuite(root)
    root.mainloop()
if __name__ == '__main__':
    main()