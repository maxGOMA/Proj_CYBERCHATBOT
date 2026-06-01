import tkinter as tk


class CyberBotGUI:
    def __init__(self, bot):
        self.bot = bot
        self.root = tk.Tk()
        self.root.title("CyberBot")
        self.root.geometry("1180x760")
        self.root.minsize(920, 640)
        self.root.configure(bg="#08111f")

        self.colors = {
            "bg": "#08111f",
            "panel": "#0d1727",
            "panel_alt": "#111f35",
            "card": "#15243c",
            "text": "#e8eef9",
            "muted": "#9db0ca",
            "accent": "#39c0a8",
            "accent_dark": "#1e8f7b",
            "danger": "#ef4444",
            "user": "#1d4ed8",
            "bot": "#17263f",
            "border": "#223552",
        }

        self.status_vars = {
            "threat": tk.StringVar(value="Sin diagnostico"),
            "confidence": tk.StringVar(value="-"),
            "turns": tk.StringVar(value="0"),
            "facts": tk.StringVar(value="0"),
        }

        self._build_layout()
        self._update_status()
        self.add_message("bot", self.bot.get_welcome_message())

    def _build_layout(self):
        shell = tk.Frame(self.root, bg=self.colors["bg"])
        shell.pack(fill="both", expand=True, padx=20, pady=20)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(
            shell,
            bg=self.colors["panel"],
            width=290,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 18))
        self.sidebar.pack_propagate(False)

        self.main_panel = tk.Frame(
            shell,
            bg=self.colors["panel_alt"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.main_panel.grid(row=0, column=1, sticky="nsew")
        self.main_panel.grid_rowconfigure(1, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        header = tk.Frame(self.sidebar, bg=self.colors["panel"])
        header.pack(fill="x", padx=18, pady=(20, 14))

        tk.Label(
            header,
            text="CyberBot",
            font=("Bahnschrift", 24, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["text"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Asistente guiado para diagnosticar incidentes de ciberseguridad.",
            font=("Segoe UI", 10),
            justify="left",
            wraplength=250,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
        ).pack(anchor="w", pady=(8, 0))

        status_card = tk.Frame(
            self.sidebar,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        status_card.pack(fill="x", padx=18, pady=(6, 16))

        tk.Label(
            status_card,
            text="Estado de la sesion",
            font=("Segoe UI Semibold", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
        ).pack(anchor="w", padx=14, pady=(12, 10))

        self._status_row(status_card, "Amenaza", self.status_vars["threat"])
        self._status_row(status_card, "Confianza", self.status_vars["confidence"])
        self._status_row(status_card, "Turnos", self.status_vars["turns"])
        self._status_row(status_card, "Hechos", self.status_vars["facts"], bottom=14)

        actions = tk.Frame(self.sidebar, bg=self.colors["panel"])
        actions.pack(fill="x", padx=18)

        self._action_button(actions, "Ayuda", "ayuda")
        self._action_button(actions, "Buenas practicas", "buenas practicas")
        self._action_button(actions, "Amenazas", "amenazas")
        self._action_button(actions, "Reiniciar sesion", "reset", danger=True)

        prompt_card = tk.Frame(
            self.sidebar,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        prompt_card.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            prompt_card,
            text="Ideas para empezar",
            font=("Segoe UI Semibold", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
        ).pack(anchor="w", padx=14, pady=(12, 10))

        for prompt in self.bot.get_quick_prompts():
            button = tk.Button(
                prompt_card,
                text=prompt,
                command=lambda value=prompt: self._send_preset(value),
                anchor="w",
                justify="left",
                wraplength=230,
                padx=12,
                pady=10,
                relief="flat",
                bd=0,
                font=("Segoe UI", 10),
                bg=self.colors["panel"],
                fg=self.colors["text"],
                activebackground=self.colors["accent_dark"],
                activeforeground="white",
                cursor="hand2",
            )
            button.pack(fill="x", padx=14, pady=(0, 10))

    def _build_main_area(self):
        hero = tk.Frame(self.main_panel, bg=self.colors["panel_alt"])
        hero.grid(row=0, column=0, sticky="ew", padx=22, pady=22)
        hero.grid_columnconfigure(0, weight=1)

        tk.Label(
            hero,
            text="Diagnostico conversacional con contexto",
            font=("Bahnschrift", 21, "bold"),
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            hero,
            text="Modelos hibridos con CountVectorizer, TF-IDF y reglas por sintomas.",
            font=("Segoe UI", 10),
            bg=self.colors["panel_alt"],
            fg=self.colors["muted"],
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.chat_wrapper = tk.Frame(
            self.main_panel,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.chat_wrapper.grid(row=1, column=0, sticky="nsew", padx=22)
        self.chat_wrapper.grid_rowconfigure(0, weight=1)
        self.chat_wrapper.grid_columnconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(
            self.chat_wrapper,
            bg=self.colors["panel"],
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(
            self.chat_wrapper,
            orient="vertical",
            command=self.chat_canvas.yview,
            bg=self.colors["panel_alt"],
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_inner = tk.Frame(self.chat_canvas, bg=self.colors["panel"])
        self.chat_window = self.chat_canvas.create_window(
            (0, 0),
            window=self.chat_inner,
            anchor="nw",
        )

        self.chat_inner.bind("<Configure>", self._on_chat_configure)
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        composer = tk.Frame(self.main_panel, bg=self.colors["panel_alt"])
        composer.grid(row=2, column=0, sticky="ew", padx=22, pady=22)
        composer.grid_columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            composer,
            textvariable=self.input_var,
            font=("Segoe UI", 11),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            bd=0,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", ipady=14)
        self.input_entry.bind("<Return>", self._submit_event)

        entry_shell = tk.Frame(
            composer,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        entry_shell.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        entry_shell.grid_columnconfigure(0, weight=1)
        self.input_entry.grid_forget()
        self.input_entry = tk.Entry(
            entry_shell,
            textvariable=self.input_var,
            font=("Segoe UI", 11),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            bd=0,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=14, pady=12, ipady=2)
        self.input_entry.bind("<Return>", self._submit_event)

        send_button = tk.Button(
            composer,
            text="Enviar",
            command=self.submit_message,
            padx=22,
            pady=12,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 11),
            bg=self.colors["accent"],
            fg="#03211c",
            activebackground="#52d2bc",
            activeforeground="#02110e",
            cursor="hand2",
        )
        send_button.grid(row=0, column=1, sticky="e")

        self.input_entry.focus_set()

    def _status_row(self, parent, label, variable, bottom=8):
        row = tk.Frame(parent, bg=self.colors["card"])
        row.pack(fill="x", padx=14, pady=(0, bottom))
        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["muted"],
        ).pack(anchor="w")
        tk.Label(
            row,
            textvariable=variable,
            font=("Segoe UI Semibold", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
        ).pack(anchor="w", pady=(2, 0))

    def _action_button(self, parent, label, prompt, danger=False):
        bg_color = self.colors["danger"] if danger else self.colors["accent"]
        fg_color = "white" if danger else "#03211c"
        active_bg = "#f87171" if danger else "#52d2bc"

        button = tk.Button(
            parent,
            text=label,
            command=lambda value=prompt: self._send_preset(value),
            padx=14,
            pady=10,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            bg=bg_color,
            fg=fg_color,
            activebackground=active_bg,
            activeforeground=fg_color,
            cursor="hand2",
        )
        button.pack(fill="x", pady=(0, 10))

    def _send_preset(self, text):
        self.input_var.set(text)
        self.submit_message()

    def _submit_event(self, _event):
        self.submit_message()
        return "break"

    def submit_message(self):
        text = self.input_var.get().strip()
        if not text:
            return

        self.input_var.set("")
        self.add_message("user", text)

        try:
            response = self.bot.process_input(text)
        except Exception as error:
            response = f"Error inesperado: {error}"

        self.add_message("bot", response)
        self._update_status()
        self.input_entry.focus_set()

    def add_message(self, role, text):
        row = tk.Frame(self.chat_inner, bg=self.colors["panel"])
        row.pack(fill="x", pady=8, padx=18)

        is_user = role == "user"
        anchor = "e" if is_user else "w"
        bubble_bg = self.colors["user"] if is_user else self.colors["bot"]
        bubble_fg = "white" if is_user else self.colors["text"]
        name = "Tu" if is_user else "CyberBot"

        content = tk.Frame(row, bg=self.colors["panel"])
        content.pack(anchor=anchor)

        tk.Label(
            content,
            text=name,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["muted"],
        ).pack(anchor=anchor, padx=4, pady=(0, 4))

        bubble = tk.Label(
            content,
            text=text,
            font=("Segoe UI", 11),
            justify="left",
            wraplength=700,
            padx=16,
            pady=12,
            bg=bubble_bg,
            fg=bubble_fg,
            bd=0,
            relief="flat",
        )
        bubble.pack(anchor=anchor)

        self.root.after(10, self._scroll_to_bottom)

    def _update_status(self):
        status = self.bot.get_status()
        self.status_vars["threat"].set(status["threat"])
        self.status_vars["confidence"].set(status["confidence"])
        self.status_vars["turns"].set(str(status["turns"]))
        self.status_vars["facts"].set(str(status["facts"]))

    def _on_chat_configure(self, _event):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfigure(self.chat_window, width=event.width)

    def _scroll_to_bottom(self):
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def run(self):
        self.root.mainloop()
