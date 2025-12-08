"""
Interface graphique Tkinter pour exécuter les commandes make.ps1
Permet aux utilisateurs non techniques d'exécuter les commandes facilement
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import subprocess
import threading
import sys
from pathlib import Path
import os

# Essayer d'importer PIL pour gérer les images
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class MakeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MPPEEP Dashboard - Interface de Configuration")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Couleurs MPPEEP : orange, blanc, vert
        self.colors = {
            'bg': '#FFFFFF',  # Blanc
            'primary': '#FF8C00',  # Orange foncé (DarkOrange)
            'secondary': '#FFA500',  # Orange standard
            'success': '#22C55E',  # Vert (success)
            'warning': '#FF9500',  # Orange clair
            'danger': '#EF4444',  # Rouge (erreur)
            'text': '#1E293B',  # Texte foncé
            'header_text': '#FFFFFF',  # Texte blanc sur header orange
            'accent_green': '#16A34A'  # Vert accent
        }
        
        # Charger le logo
        self.setup_logo()
        
        self.setup_ui()
        self.current_process = None
        self.is_running = False
        
        # Vérifier que make.ps1 est accessible au démarrage
        self.verify_make_ps1()
    
    def setup_logo(self):
        """Charge le logo comme icône de fenêtre et pour l'en-tête"""
        base_dir = Path(__file__).parent
        project_root = base_dir.parent
        
        # Chercher le logo dans plusieurs emplacements
        logo_paths = [
            project_root / "app" / "static" / "images" / "logo.webp",
            project_root / "app" / "static" / "images" / "logo_default.png",
            project_root / "app" / "static" / "favicon.ico",
            project_root / "icon.ico",
            base_dir / "icon.ico",
        ]
        
        logo_path = None
        for path in logo_paths:
            if path.exists():
                logo_path = path
                break
        
        if logo_path:
            try:
                if PIL_AVAILABLE and logo_path.suffix.lower() in ['.webp', '.png', '.jpg', '.jpeg']:
                    # Charger avec PIL pour supporter webp
                    img = Image.open(logo_path)
                    
                    # Créer l'icône de fenêtre (32x32)
                    img_icon = img.resize((32, 32), Image.Resampling.LANCZOS)
                    self.logo_icon = ImageTk.PhotoImage(img_icon)
                    self.root.iconphoto(True, self.logo_icon)
                    
                    # Créer le logo pour l'en-tête (64x64)
                    img_header = img.resize((64, 64), Image.Resampling.LANCZOS)
                    self.logo_header = ImageTk.PhotoImage(img_header)
                else:
                    # Utiliser iconbitmap pour .ico
                    if logo_path.suffix.lower() == '.ico':
                        self.root.iconbitmap(str(logo_path))
                        # Pour .ico, utiliser aussi comme logo header si possible
                        if PIL_AVAILABLE:
                            try:
                                img = Image.open(logo_path)
                                img_header = img.resize((64, 64), Image.Resampling.LANCZOS)
                                self.logo_header = ImageTk.PhotoImage(img_header)
                            except:
                                pass
            except Exception as e:
                print(f"⚠️  Impossible de charger le logo: {e}")
        else:
            print("ℹ️  Aucun logo trouvé, utilisation de l'icône par défaut")
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header avec logo
        header_frame = tk.Frame(main_frame, bg=self.colors['primary'], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Conteneur pour logo et titre
        header_content = tk.Frame(header_frame, bg=self.colors['primary'])
        header_content.pack(expand=True)
        
        # Logo dans le header (si disponible)
        if hasattr(self, 'logo_header'):
            try:
                logo_label = tk.Label(
                    header_content,
                    image=self.logo_header,
                    bg=self.colors['primary']
                )
                logo_label.pack(side=tk.LEFT, padx=(0, 15))
            except:
                pass
        
        title_label = tk.Label(
            header_content,
            text="🚀 MPPEEP Dashboard",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['primary'],
            fg=self.colors['header_text']
        )
        title_label.pack(side=tk.LEFT)
        
        # Notebook pour les onglets
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Créer les onglets
        self.create_quick_start_tab(notebook)
        self.create_environment_tab(notebook)
        self.create_database_tab(notebook)
        self.create_docker_tab(notebook)
        self.create_tests_tab(notebook)
        self.create_quality_tab(notebook)
        self.create_git_tab(notebook)
        self.create_maintenance_tab(notebook)
        
        # Zone de sortie
        output_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        output_header = tk.Frame(output_frame, bg=self.colors['bg'])
        output_header.pack(fill=tk.X, pady=(0, 5))
        
        output_label = tk.Label(
            output_header,
            text="Sortie de la commande:",
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        output_label.pack(side=tk.LEFT)
        
        self.stop_btn = tk.Button(
            output_header,
            text="⏹️ Arrêter",
            command=self.stop_command,
            font=('Segoe UI', 9),
            bg=self.colors['danger'],
            fg='white',
            activebackground='#DC2626',  # Rouge plus foncé pour danger
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        clear_btn = tk.Button(
            output_header,
            text="🗑️ Effacer",
            command=self.clear_output,
            font=('Segoe UI', 9),
            bg=self.colors['secondary'],
            fg='white',
            activebackground='#FF7F00',  # Orange au survol pour secondary
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        clear_btn.pack(side=tk.RIGHT)
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            height=15,
            font=('Consolas', 9),
            bg='#1e293b',
            fg='#e2e8f0',
            insertbackground='white',
            wrap=tk.WORD
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Barre de statut
        self.status_label = tk.Label(
            main_frame,
            text="Prêt",
            font=('Segoe UI', 9),
            bg=self.colors['bg'],
            fg=self.colors['secondary'],
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
    def create_quick_start_tab(self, notebook):
        """Onglet Démarrage rapide"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="🚀 Démarrage")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Titre
        title = tk.Label(
            content,
            text="Démarrage Rapide",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        # Boutons
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("🔧 Installation Complète", "setup", "Installe l'environnement et les dépendances", self.setup_with_python),
            ("▶️ Démarrer", "start", "Démarrer l'application", lambda: self.run_command("start")),
            ("⏹️ Arrêter", "stop", "Arrêter l'application", lambda: self.run_command("stop")),
            ("🔄 Redémarrer", "restart", "Redémarrer l'application", lambda: self.run_command("restart")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_environment_tab(self, notebook):
        """Onglet Environnement"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="⚙️ Environnement")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Gestion de l'Environnement",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("📦 Installer Dépendances", "install", "Installer les dépendances avec uv", lambda: self.run_command("install")),
            ("✅ Vérifier Environnement", "env-check", "Vérifier la configuration", lambda: self.run_command("env-check")),
            ("ℹ️ Infos Environnement", "env-info", "Afficher les informations", lambda: self.run_command("env-info")),
            ("🔄 Synchroniser UV", "uv-sync", "Synchroniser les dépendances", lambda: self.run_command("uv-sync")),
            ("➕ Ajouter Package", "uv-add", "Ajouter un package", self.uv_add_package),
            ("➖ Supprimer Package", "uv-remove", "Supprimer un package", self.uv_remove_package),
            ("📋 Lister Packages", "uv-list", "Lister les packages installés", lambda: self.run_command("uv-list")),
            ("🔄 Mettre à jour", "uv-update", "Mettre à jour les packages", lambda: self.run_command("uv-update")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_database_tab(self, notebook):
        """Onglet Base de données"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="💾 Base de Données")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Gestion de la Base de Données",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("🔧 Initialiser DB", "db-init", "Initialiser la base de données", lambda: self.run_command("db-init", confirm=True)),
            ("🔄 Réinitialiser DB", "db-reset", "Réinitialiser la base de données", lambda: self.run_command("db-reset", confirm=True)),
            ("💾 Sauvegarder DB", "db-backup", "Sauvegarder la base de données", lambda: self.run_command("db-backup")),
            ("👤 Créer Admin", "create-admin", "Créer un utilisateur administrateur", lambda: self.run_command("create-admin")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_docker_tab(self, notebook):
        """Onglet Docker"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="🐳 Docker")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Gestion Docker",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        # Sous-sections
        dev_frame = tk.LabelFrame(
            content,
            text="Développement",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            padx=10,
            pady=10
        )
        dev_frame.pack(fill=tk.X, pady=(0, 10))
        
        dev_buttons = tk.Frame(dev_frame, bg=self.colors['bg'])
        dev_buttons.pack(fill=tk.X)
        
        dev_commands = [
            ("▶️ Démarrer Dev", "docker-dev", None, lambda: self.run_command("docker-dev")),
            ("⏹️ Arrêter Dev", "docker-stop-dev", None, lambda: self.run_command("docker-stop-dev")),
            ("🔄 Redémarrer Dev", "docker-restart-dev", None, lambda: self.run_command("docker-restart-dev")),
            ("📋 Logs Dev", "docker-logs-dev", None, lambda: self.run_command("docker-logs-dev")),
        ]
        
        self.create_buttons_row(dev_buttons, dev_commands)
        
        prod_frame = tk.LabelFrame(
            content,
            text="Production",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            padx=10,
            pady=10
        )
        prod_frame.pack(fill=tk.X, pady=(0, 10))
        
        prod_buttons = tk.Frame(prod_frame, bg=self.colors['bg'])
        prod_buttons.pack(fill=tk.X)
        
        prod_commands = [
            ("▶️ Démarrer Prod", "docker-prod", None, lambda: self.run_command("docker-prod")),
            ("🔨 Rebuild Prod", "docker-rebuild-prod", None, lambda: self.run_command("docker-rebuild-prod", confirm=True)),
            ("⏹️ Arrêter Prod", "docker-stop-prod", None, lambda: self.run_command("docker-stop-prod")),
            ("🔄 Redémarrer Prod", "docker-restart-prod", None, lambda: self.run_command("docker-restart-prod")),
            ("📋 Logs Prod", "docker-logs-prod", None, lambda: self.run_command("docker-logs-prod")),
            ("📊 Statut", "docker-status", None, lambda: self.run_command("docker-status")),
        ]
        
        self.create_buttons_row(prod_buttons, prod_commands)
        
        other_frame = tk.LabelFrame(
            content,
            text="Autres",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            padx=10,
            pady=10
        )
        other_frame.pack(fill=tk.X)
        
        other_buttons = tk.Frame(other_frame, bg=self.colors['bg'])
        other_buttons.pack(fill=tk.X)
        
        other_commands = [
            ("💾 Exporter Image", "docker-save", None, lambda: self.run_command("docker-save")),
            ("📥 Importer Image", "docker-load", None, lambda: self.run_command("docker-load")),
            ("📦 Package", "docker-package", None, lambda: self.run_command("docker-package")),
            ("🧹 Nettoyer", "docker-prune", None, lambda: self.run_command("docker-prune", confirm=True)),
        ]
        
        self.create_buttons_row(other_buttons, other_commands)
        
    def create_tests_tab(self, notebook):
        """Onglet Tests"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="🧪 Tests")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Tests",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("▶️ Tous les Tests", "test", "Lancer tous les tests", lambda: self.run_command("test")),
            ("🔬 Tests Unitaires", "test-unit", "Tests unitaires uniquement", lambda: self.run_command("test-unit")),
            ("📊 Couverture", "test-cov", "Tests avec couverture", lambda: self.run_command("test-cov")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_quality_tab(self, notebook):
        """Onglet Qualité du code"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="✨ Qualité")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Qualité du Code",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("🔍 Linter", "lint", "Vérifier le code", lambda: self.run_command("lint")),
            ("🔧 Corriger Lint", "lint-fix", "Corriger automatiquement", lambda: self.run_command("lint-fix")),
            ("📝 Formater", "format", "Formater le code", lambda: self.run_command("format")),
            ("🧹 Nettoyer Code", "clean-code", "Nettoyage complet", lambda: self.run_command("clean-code")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_git_tab(self, notebook):
        """Onglet Git"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="📂 Git")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Gestion Git",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("📊 Statut", "git-status", "Statut Git", lambda: self.run_command("git-status")),
            ("📜 Log", "git-log", "Historique Git", lambda: self.run_command("git-log")),
            ("🔄 Pré-commit", "pre-commit", "Préparer commit", lambda: self.run_command("pre-commit")),
            ("⬆️ Push", "push", "Push vers origin", lambda: self.run_command("push")),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_maintenance_tab(self, notebook):
        """Onglet Maintenance"""
        frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(frame, text="🔧 Maintenance")
        
        content = tk.Frame(frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title = tk.Label(
            content,
            text="Maintenance",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(anchor=tk.W, pady=(0, 20))
        
        buttons_frame = tk.Frame(content, bg=self.colors['bg'])
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        commands = [
            ("📋 Logs", "logs", "Voir les logs", lambda: self.run_command("logs")),
            ("🧹 Nettoyer", "clean", "Nettoyer fichiers temporaires", lambda: self.run_command("clean")),
            ("🗑️ Nettoyer Tout", "clean-all", "Nettoyage complet", lambda: self.run_command("clean-all", confirm=True)),
        ]
        
        self.create_buttons_grid(buttons_frame, commands)
        
    def create_buttons_grid(self, parent, commands):
        """Crée une grille de boutons"""
        row = 0
        col = 0
        max_cols = 3
        
        for label, cmd, tooltip, action in commands:
            btn = tk.Button(
                parent,
                text=label,
                command=action,
                font=('Segoe UI', 10),
                bg=self.colors['primary'],
                fg='white',
                activebackground='#FF7F00',  # Orange plus foncé au survol
                activeforeground='white',
                relief=tk.FLAT,
                padx=15,
                pady=10,
                cursor='hand2',
                width=20
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky='ew')
            
            if tooltip:
                self.create_tooltip(btn, tooltip)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Configurer les colonnes pour qu'elles s'étendent
        for i in range(max_cols):
            parent.grid_columnconfigure(i, weight=1)
    
    def create_buttons_row(self, parent, commands):
        """Crée une ligne de boutons"""
        for i, (label, cmd, tooltip, action) in enumerate(commands):
            btn = tk.Button(
                parent,
                text=label,
                command=action,
                font=('Segoe UI', 9),
                bg=self.colors['primary'],
                fg='white',
                activebackground='#FF7F00',  # Orange plus foncé au survol
                activeforeground='white',
                relief=tk.FLAT,
                padx=10,
                pady=8,
                cursor='hand2'
            )
            btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            if tooltip:
                self.create_tooltip(btn, tooltip)
    
    def create_tooltip(self, widget, text):
        """Crée un tooltip pour un widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(
                tooltip,
                text=text,
                bg='#1e293b',
                fg='white',
                font=('Segoe UI', 9),
                padx=8,
                pady=4,
                relief=tk.SOLID,
                borderwidth=1
            )
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
    
    def setup_with_python(self):
        """Setup avec sélection de version Python"""
        python_version = simpledialog.askstring(
            "Version Python",
            "Version Python (ex: 3.11, python3.12, ou laissez vide pour défaut):",
            parent=self.root
        )
        
        if python_version is None:
            return
        
        if python_version.strip():
            self.run_command("setup", args=[f"-Python {python_version}"])
        else:
            self.run_command("setup")
    
    def uv_add_package(self):
        """Ajouter un package avec uv"""
        package = simpledialog.askstring(
            "Ajouter Package",
            "Nom du package à ajouter:",
            parent=self.root
        )
        
        if package and package.strip():
            self.run_command("uv-add", args=[f"-PKG {package.strip()}"])
    
    def uv_remove_package(self):
        """Supprimer un package avec uv"""
        package = simpledialog.askstring(
            "Supprimer Package",
            "Nom du package à supprimer:",
            parent=self.root
        )
        
        if package and package.strip():
            self.run_command("uv-remove", args=[f"-PKG {package.strip()}"])
    
    def run_command(self, command, args=None, confirm=False):
        """Exécute une commande make.ps1"""
        if confirm:
            if not messagebox.askyesno(
                "Confirmation",
                f"Êtes-vous sûr de vouloir exécuter '{command}' ?\n\nCette action peut être irréversible.",
                parent=self.root
            ):
                return
        
        # Arrêter la commande précédente si elle est en cours
        if self.is_running:
            if not messagebox.askyesno(
                "Commande en cours",
                "Une commande est déjà en cours d'exécution. Voulez-vous l'arrêter ?",
                parent=self.root
            ):
                return
            self.stop_command()
        
        # Construire la commande
        # Chercher make.ps1 dans plusieurs emplacements
        script_path = self.find_make_ps1()
        
        if not script_path:
            # Détecter si on est dans un exécutable PyInstaller pour le message d'erreur
            if getattr(sys, 'frozen', False):
                exe_path = Path(sys.executable)
                exe_dir = exe_path.parent
                project_root = exe_dir.parent.parent
            else:
                base_dir = Path(__file__).parent
                project_root = base_dir.parent
            
            self.append_output(f"\n[ERREUR] make.ps1 introuvable dans les emplacements suivants:\n")
            possible_paths = [
                project_root / "make.ps1",
                Path.cwd() / "make.ps1",
                Path.cwd().parent / "make.ps1",
            ]
            for path in possible_paths:
                status = "✓" if path.exists() else "✗"
                self.append_output(f"  {status} {path}\n")
            self.update_status("[ERREUR] make.ps1 introuvable")
            messagebox.showerror(
                "Erreur",
                f"Le fichier make.ps1 est introuvable.\n\n"
                f"Emplacements recherchés:\n"
                f"  • {project_root / 'make.ps1'}\n"
                f"  • {Path.cwd() / 'make.ps1'}\n\n"
                f"Veuillez vous assurer que make.ps1 est à la racine du projet\n"
                f"ou dans le même répertoire que l'application.",
                parent=self.root
            )
            return
        
        # Afficher où make.ps1 a été trouvé
        self.append_output(f"[INFO] make.ps1 trouvé: {script_path}\n")
        
        cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path), command]
        
        if args:
            cmd.extend(args)
        
        # Afficher dans la sortie
        self.append_output(f"\n{'='*60}\n")
        self.append_output(f"Commande: .\\make.ps1 {command} {' '.join(args) if args else ''}\n")
        self.append_output(f"{'='*60}\n\n")
        
        self.update_status(f"Exécution de: {command}...")
        self.is_running = True
        self.stop_btn.config(state=tk.NORMAL)
        
        # Exécuter dans un thread séparé
        thread = threading.Thread(target=self.execute_command, args=(cmd, command, script_path))
        thread.daemon = True
        thread.start()
    
    def execute_command(self, cmd, command_name, script_path):
        """Exécute la commande dans un thread séparé"""
        output_lines = []  # Stocker toutes les lignes pour analyse
        
        try:
            # Déterminer le répertoire de travail
            # Utiliser le répertoire parent de make.ps1 (racine du projet)
            work_dir = script_path.parent if script_path else Path.cwd()
            
            # S'assurer que le répertoire de travail existe
            if not work_dir.exists():
                work_dir = Path.cwd()
            
            self.append_output(f"[INFO] Répertoire de travail: {work_dir}\n")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=str(work_dir)  # Convertir en string pour compatibilité
            )
            
            # Lire la sortie en temps réel
            for line in iter(self.current_process.stdout.readline, ''):
                if line:
                    output_lines.append(line)
                    self.root.after(0, self.append_output, line)
            
            self.current_process.wait()
            
            # Analyser la sortie pour détecter erreurs et avertissements
            output_text = ''.join(output_lines).lower()
            has_warnings = any(keyword in output_text for keyword in ["warning", "avertissement", "warn"])
            has_errors = any(keyword in output_text for keyword in ["error:", "erreur:", "failed", "échec", "accès refusé", "access denied"])
            
            if self.current_process.returncode == 0:
                # Détecter spécifiquement les erreurs OneDrive
                has_onedrive_error = "accès refusé" in output_text or "access denied" in output_text or "os error 5" in output_text
                
                if has_errors:
                    if has_onedrive_error:
                        self.root.after(0, self.update_status, f"[ATTENTION] {command_name} termine avec des erreurs OneDrive (code: {self.current_process.returncode})")
                        self.root.after(0, self.append_output, f"\n[TERMINE] Code de sortie: {self.current_process.returncode} (avec erreurs)\n")
                        self.root.after(0, self.append_output, f"[INFO] Les erreurs 'Accès refusé' sont souvent causées par OneDrive qui verrouille les fichiers.\n")
                        self.root.after(0, self.append_output, f"[INFO] Solution: Pausez temporairement la synchronisation OneDrive avant d'exécuter la commande.\n")
                    else:
                        self.root.after(0, self.update_status, f"[ATTENTION] {command_name} termine avec des erreurs (code: {self.current_process.returncode})")
                        self.root.after(0, self.append_output, f"\n[TERMINE] Code de sortie: {self.current_process.returncode} (avec erreurs)\n")
                elif has_warnings:
                    self.root.after(0, self.update_status, f"[OK] {command_name} termine avec succes (avec avertissements)")
                    self.root.after(0, self.append_output, f"\n[TERMINE] Code de sortie: {self.current_process.returncode} (avec avertissements)\n")
                else:
                    self.root.after(0, self.update_status, f"[OK] {command_name} termine avec succes")
                    self.root.after(0, self.append_output, f"\n[TERMINE] Code de sortie: {self.current_process.returncode}\n")
            else:
                self.root.after(0, self.update_status, f"[ERROR] {command_name} termine avec erreur")
                self.root.after(0, self.append_output, f"\n[ERREUR] Code de sortie: {self.current_process.returncode}\n")
                
        except Exception as e:
            self.root.after(0, self.update_status, f"[ERROR] Erreur: {str(e)}")
            self.root.after(0, self.append_output, f"\n[ERREUR] {str(e)}\n")
        finally:
            self.current_process = None
            self.is_running = False
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
    
    def stop_command(self):
        """Arrête la commande en cours"""
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.append_output("\n[ARRETE] Commande interrompue par l'utilisateur\n")
            self.update_status("Commande arretee")
            self.is_running = False
            self.stop_btn.config(state=tk.DISABLED)
    
    def append_output(self, text):
        """Ajoute du texte à la zone de sortie avec coloration syntaxique"""
        # Détecter les erreurs, avertissements et infos pour la coloration
        text_lower = text.lower()
        
        # Tags pour la coloration
        if not hasattr(self, 'tags_configured'):
            self.output_text.tag_configure("error", foreground="#ef4444", font=('Consolas', 9, 'bold'))
            self.output_text.tag_configure("warning", foreground=self.colors['warning'], font=('Consolas', 9))
            self.output_text.tag_configure("success", foreground=self.colors['success'], font=('Consolas', 9))
            self.output_text.tag_configure("info", foreground=self.colors['primary'], font=('Consolas', 9))
            self.tags_configured = True
        
        # Insérer le texte
        start_pos = self.output_text.index(tk.END + "-1c")
        self.output_text.insert(tk.END, text)
        end_pos = self.output_text.index(tk.END + "-1c")
        
        # Appliquer les tags selon le contenu
        if any(keyword in text_lower for keyword in ["error", "erreur", "failed", "échec", "accès refusé", "access denied"]):
            self.output_text.tag_add("error", start_pos, end_pos)
        elif any(keyword in text_lower for keyword in ["warning", "avertissement", "warn"]):
            self.output_text.tag_add("warning", start_pos, end_pos)
        elif any(keyword in text_lower for keyword in ["[ok]", "[success]", "succès", "réussi", "terminé"]):
            self.output_text.tag_add("success", start_pos, end_pos)
        elif any(keyword in text_lower for keyword in ["[info]", "info:", "information"]):
            self.output_text.tag_add("info", start_pos, end_pos)
        
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, text):
        """Met à jour le statut"""
        self.status_label.config(text=text)
    
    def clear_output(self):
        """Efface la zone de sortie"""
        self.output_text.delete(1.0, tk.END)
    
    def verify_make_ps1(self):
        """Vérifie que make.ps1 est accessible au démarrage"""
        script_path = self.find_make_ps1()
        if script_path:
            self.update_status(f"Prêt - make.ps1 trouvé: {script_path.name}")
        else:
            self.update_status("[ATTENTION] make.ps1 introuvable - certaines commandes peuvent échouer")
    
    def find_make_ps1(self):
        """Trouve le fichier make.ps1 dans les emplacements possibles"""
        # Détecter si on est dans un exécutable PyInstaller
        if getattr(sys, 'frozen', False):
            # On est dans un exécutable PyInstaller
            exe_path = Path(sys.executable)
            exe_dir = exe_path.parent
            # L'exécutable est dans build_exe/dist/, donc la racine est 2 niveaux au-dessus
            project_root = exe_dir.parent.parent
        else:
            # On est dans le script Python normal
            base_dir = Path(__file__).parent  # config_tkinter
            project_root = base_dir.parent  # Racine du projet
        
        # Liste exhaustive des emplacements possibles pour make.ps1
        possible_paths = [
            project_root / "make.ps1",  # À la racine du projet (recommandé)
            Path.cwd() / "make.ps1",  # Répertoire de travail actuel
            Path.cwd().parent / "make.ps1",  # Parent du répertoire de travail
        ]
        
        # Si on n'est pas dans un exécutable, ajouter config_tkinter
        if not getattr(sys, 'frozen', False):
            base_dir = Path(__file__).parent
            possible_paths.insert(1, base_dir / "make.ps1")  # Dans config_tkinter
        
        # Si on est dans un exécutable, chercher aussi près de l'exécutable
        if getattr(sys, 'frozen', False):
            exe_path = Path(sys.executable)
            exe_dir = exe_path.parent
            # Chercher dans le même dossier que l'exécutable
            possible_paths.insert(1, exe_dir / "make.ps1")
            # Chercher dans le parent de l'exécutable
            possible_paths.insert(2, exe_dir.parent / "make.ps1")
        
        # Chercher make.ps1 dans tous les emplacements possibles
        for path in possible_paths:
            try:
                if path.exists() and path.is_file():
                    return path.resolve()  # Normaliser le chemin
            except Exception:
                # Ignorer les erreurs de chemin (permissions, etc.)
                continue
        
        return None

def main():
    root = tk.Tk()
    app = MakeGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


