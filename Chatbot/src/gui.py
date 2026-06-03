import tkinter as tk
from tkinter import messagebox


class CyberBotGUI:
    def __init__(self, bot):
        self.bot = bot

        self.window = tk.Tk()
        self.window.title("CyberBot")
        self.window.geometry("900x600")

        # Frame principal
        self.main_frame = tk.Frame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Parte izquierda
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True)

        # Parte derecha
        self.right_frame = tk.Frame(self.main_frame, width=220)
        self.right_frame.pack(side="right", fill="y", padx=(10, 0))
        self.right_frame.pack_propagate(False)

        # Titulo
        self.title_label = tk.Label(
            self.left_frame,
            text="CyberBot - Asistente de ciberseguridad",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=(0, 10))

        # Area del chat
        self.chat_area = tk.Text(self.left_frame, wrap="word", state="disabled")
        self.chat_area.pack(fill="both", expand=True)

        # Frame de entrada
        self.input_frame = tk.Frame(self.left_frame)
        self.input_frame.pack(fill="x", pady=(10, 0))

        self.entry = tk.Entry(self.input_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(
            self.input_frame,
            text="Enviar",
            command=self.send_message
        )
        self.send_button.pack(side="left", padx=(10, 0))

        # Botones extra
        self.buttons_frame = tk.Frame(self.left_frame)
        self.buttons_frame.pack(fill="x", pady=(10, 0))

        self.reset_button = tk.Button(
            self.buttons_frame,
            text="Reiniciar",
            command=self.reset_chat
        )
        self.reset_button.pack(side="left")

        self.clear_button = tk.Button(
            self.buttons_frame,
            text="Limpiar",
            command=self.clear_chat
        )
        self.clear_button.pack(side="left", padx=(10, 0))

        # Estado
        self.status_title = tk.Label(
            self.right_frame,
            text="Estado",
            font=("Arial", 13, "bold")
        )
        self.status_title.pack(anchor="w", pady=(0, 10))

        self.status_text = tk.Text(self.right_frame, height=8, width=25, state="disabled")
        self.status_text.pack(fill="x")

        # Mensajes rapidos
        self.quick_title = tk.Label(
            self.right_frame,
            text="Mensajes rapidos",
            font=("Arial", 13, "bold")
        )
        self.quick_title.pack(anchor="w", pady=(15, 10))

        self.quick_buttons_frame = tk.Frame(self.right_frame)
        self.quick_buttons_frame.pack(fill="x")

        self.button_1 = tk.Button(
            self.quick_buttons_frame,
            text="Me han hackeado",
            command=lambda: self.put_quick_message("Me han hackeado")
        )
        self.button_1.pack(fill="x", pady=2)

        self.button_2 = tk.Button(
            self.quick_buttons_frame,
            text="He recibido un correo sospechoso",
            command=lambda: self.put_quick_message("He recibido un correo sospechoso")
        )
        self.button_2.pack(fill="x", pady=2)

        self.button_3 = tk.Button(
            self.quick_buttons_frame,
            text="Mis archivos estan cifrados",
            command=lambda: self.put_quick_message("Mis archivos estan cifrados")
        )
        self.button_3.pack(fill="x", pady=2)

        self.button_4 = tk.Button(
            self.quick_buttons_frame,
            text="Que es el phishing",
            command=lambda: self.put_quick_message("Que es el phishing")
        )
        self.button_4.pack(fill="x", pady=2)

        self.button_5 = tk.Button(
            self.quick_buttons_frame,
            text="Buenas practicas",
            command=lambda: self.put_quick_message("Buenas practicas")
        )
        self.button_5.pack(fill="x", pady=2)

        # Mensaje inicial
        welcome = self.bot.get_welcome_message()
        self.add_message("CyberBot", welcome)
        self.update_status()

    def add_message(self, role, text):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", role + ": " + text + "\n\n")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def send_message_event(self, event):
        self.send_message()

    def send_message(self):
        user_text = self.entry.get().strip()

        if user_text == "":
            messagebox.showinfo("CyberBot", "Escribe un mensaje.")
        else:
            self.add_message("Tu", user_text)
            self.entry.delete(0, "end")

            response = self.bot.process_input(user_text)

            self.add_message("CyberBot", response)
            self.update_status()

    def put_quick_message(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def update_status(self):
        status = self.bot.get_status()

        text = ""
        text = text + "Amenaza: " + str(status["threat"]) + "\n"
        text = text + "Confianza: " + str(status["confidence"]) + "\n"
        text = text + "Turnos: " + str(status["turns"]) + "\n"
        text = text + "Hechos: " + str(status["facts"])

        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.config(state="disabled")

    def clear_chat(self):
        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.config(state="disabled")

        welcome = self.bot.get_welcome_message()
        self.add_message("CyberBot", welcome)
        self.update_status()

    def reset_chat(self):
        response = self.bot.reset_session()

        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.config(state="disabled")

        self.add_message("CyberBot", response)
        self.add_message("CyberBot", self.bot.get_welcome_message())
        self.update_status()

    def run(self):
        self.window.mainloop()