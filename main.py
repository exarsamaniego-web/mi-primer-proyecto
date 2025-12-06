import customtkinter as ctk
import threading
import pyttsx3
import speech_recognition as sr
from groq import Groq
import os
from PIL import Image
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import queue
# === IMPORTACIONES DE TUS MOTORES ===
from motores.fisica import MotorFisica
from motores.finanzas import MotorFinanzas
from motores.reportes import MotorReportes
#from traducciones import Traductor  # ← NUEVA IMPORTACIÓN
# ==========================================
# ⚙️ CONFIGURACIÓN GLOBAL
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

API_KEY_GROQ = "CLAVE_API"
CARGO_FIJO_MENSUAL = 4.50

CATALOGO_ELECTRO = {
    "Selecciona un aparato...": 0, "💡 CONSULTAR IA...": -1,
    "Refrigeradora (Convencional)": 350, "Refrigeradora (Inverter A+)": 120,
    "Lavadora (Solo lavado)": 500, "Lavaseca": 2500, "Microondas": 1200,
    "TV Smart 55''": 140, "Laptop": 60, "PC Gamer": 450, "Foco LED": 9,
    "Aire Acondicionado": 2000, "Ventilador": 70, "Plancha": 1500,
    "Olla Arrocera": 700, "Terma Eléctrica": 1500, "Ducha Rapiducha": 4500,
    "Hervidor": 1800, "Cargador Celular": 5, "Licuadora": 400
}


# ==========================================
# 🎈 CLASE TOOLTIP
# ==========================================
class ToolTip:
    def __init__(self, widget, text, app_ref):
        self.widget = widget
        self.text = text
        self.app_ref = app_ref
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.mostrar)
        self.widget.bind("<Leave>", self.ocultar)

    def mostrar(self, event=None):
        if not self.app_ref.ayuda_activa: return
        if self.tooltip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        frame = ctk.CTkFrame(self.tooltip_window, fg_color="#FFFFE0", corner_radius=10, border_color="#F1C40F",
                             border_width=1)
        frame.pack()
        ctk.CTkLabel(frame, text=self.text, text_color="#333333", font=("Arial", 12)).pack(padx=10, pady=5)

    def ocultar(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


# ==========================================
# 🧠 CEREBRO DE FOPE (IA + VOZ)
# ==========================================
class CerebroFope:
    def __init__(self):
        self.cliente = None
        self.hay_conexion = False
        self.voz_activada = True
        self.cache_respuestas = {}  # Nuevo: cache para respuestas frecuentes
        self.errores_conexion = 0
        self.max_errores = 3

        try:
            self.cliente = Groq(api_key=API_KEY_GROQ)
            # Test rápido de conexión
            test_response = self.cliente.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model="llama-3.1-8b-instant",
                max_tokens=10
            )
            self.hay_conexion = True
            self.errores_conexion = 0
        except Exception as e:
            print(f"⚠️ Error inicial Groq: {e}")
            self.hay_conexion = False
            self.errores_conexion += 1

        try:
            self.motor_voz = pyttsx3.init()
            self.motor_voz.setProperty('rate', 160)
            # Configurar voz en español si está disponible
            voices = self.motor_voz.getProperty('voices')
            for voice in voices:
                if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                    self.motor_voz.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"⚠️ Error voz: {e}")

        self.oido = sr.Recognizer()
        self.microfono = sr.Microphone()

    def set_voz(self, estado: bool):
        self.voz_activada = estado

    def hablar(self, texto):
        if not self.voz_activada or not texto:
            return

        def _speak():
            try:
                # Verificar si el motor de voz está ocupado
                if hasattr(self.motor_voz, '_inLoop') and self.motor_voz._inLoop:
                    self.motor_voz.endLoop()
                self.motor_voz.say(texto)
                self.motor_voz.runAndWait()
            except Exception as e:
                print(f"⚠️ Error al hablar: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def escuchar(self):
        """Escucha y transcribe voz con manejo de errores mejorado"""
        if not self.microfono:
            try:
                self.microfono = sr.Microphone()
            except:
                return None

        try:
            with self.microfono as fuente:
                self.oido.adjust_for_ambient_noise(fuente, duration=0.8)
                # ELIMINA esta línea: self.after(0, lambda: print("🎙️ Escuchando..."))

                try:
                    audio = self.oido.listen(fuente, timeout=5, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    return None

                try:
                    texto = self.oido.recognize_google(audio, language="es-PE")
                    return texto
                except sr.UnknownValueError:
                    return None
                except sr.RequestError as e:
                    print(f"⚠️ Error de reconocimiento: {e}")
                    return None
        except Exception as e:
            print(f"⚠️ Error de micrófono: {e}")
            return None

    def pensar(self, mensaje, contexto_datos, region_usuario, tarifa_actual, modo_breve=False):
        """Procesa la consulta con cache y manejo de errores"""
        # 1. Verificar cache primero (solo para modo breve)
        if modo_breve and mensaje in self.cache_respuestas:
            return self.cache_respuestas[mensaje]

        # 2. Verificar conexión
        if not self.hay_conexion or self.errores_conexion >= self.max_errores:
            # Modo offline - respuestas predefinidas
            return self.respuesta_offline(mensaje, contexto_datos, modo_breve)

        # 3. Construir prompt
        if modo_breve:
            prompt = f"Usuario pregunta sobre: '{mensaje}'. Dame UN consejo muy breve de ahorro energético para hogares peruanos (máximo 10 palabras). Responde en español."
            cache_key = mensaje
        else:
            prompt = (
                f"Eres Fope, experto eléctrico peruano.\n"
                f"Contexto del hogar: {contexto_datos}\n"
                f"Región: {region_usuario}. Tarifa: S/ {tarifa_actual}/kWh\n"
                f"Pregunta del usuario: {mensaje}\n"
                f"Responde de forma clara, educativa y breve (máximo 3 párrafos). "
                f"Incluye fundamentos científicos si es relevante."
            )
            cache_key = None

        # 4. Intentar conexión con Groq
        try:
            chat = self.cliente.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=300 if modo_breve else 500
            )

            respuesta = chat.choices[0].message.content.strip()

            # 5. Actualizar cache si es modo breve
            if modo_breve and cache_key:
                self.cache_respuestas[cache_key] = respuesta
                # Limitar tamaño del cache (últimas 50 respuestas)
                if len(self.cache_respuestas) > 50:
                    self.cache_respuestas.pop(next(iter(self.cache_respuestas)))

            self.errores_conexion = 0  # Resetear contador de errores
            return respuesta

        except Exception as e:
            print(f"⚠️ Error Groq: {e}")
            self.errores_conexion += 1

            # Si hay muchos errores, desactivar conexión temporalmente
            if self.errores_conexion >= self.max_errores:
                print("⚠️ Desactivando conexión Groq temporalmente")

            # Modo offline
            return self.respuesta_offline(mensaje, contexto_datos, modo_breve)

    def respuesta_offline(self, mensaje, contexto_datos, modo_breve):
        """Respuestas predefinidas para modo offline"""
        # Diccionario de respuestas frecuentes
        respuestas_frecuentes = {
            "hola": "¡Hola! Soy Fope, tu asistente eléctrico. Estoy en modo offline pero puedo ayudarte con consejos de ahorro.",
            "ahorro": "Para ahorrar energía: 1) Usa focos LED, 2) Desconecta cargadores, 3) Mantén bajo 140 kWh para subsidio FOSE.",
            "campo magnético": "Los electrodomésticos generan campos magnéticos seguros (<100 µT según OMS). La ducha eléctrica es el que más genera (10-15 µT).",
            "tarifa": "El Perú tiene tarifas diferenciadas por región. Lima: S/0.67-0.69. Mantente bajo 140 kWh para subsidio FOSE.",
            "refrigeradora": "Las refrigeradoras consumen más si están cerca de fuentes de calor. Mantén la puerta cerrada y limpia los condensadores.",
            "ducha eléctrica": "La ducha de 4500W consume 20.5A. Úsala máximo 10 minutos y no la uses con otros aparatos de alta potencia.",
            "aire acondicionado": "El aire acondicionado consume 2000W (9A). Úsalo a 24°C, cierra ventanas y limpia los filtros mensualmente.",
        }

        # Buscar palabras clave en el mensaje
        mensaje_lower = mensaje.lower()

        for keyword, respuesta in respuestas_frecuentes.items():
            if keyword in mensaje_lower:
                if modo_breve:
                    return respuesta.split(". ")[0] + "."  # Solo primera oración
                return respuesta

        # Respuesta genérica
        if modo_breve:
            return "Para ahorrar energía, usa electrodomésticos eficientes y mantén bajo consumo."

        return (
            "Estoy en modo offline temporalmente. Como experto eléctrico, te recomiendo:\n"
            "1. Revisa que tus aparatos sean eficientes energéticamente (clase A+)\n"
            "2. Mantén tu consumo bajo 140 kWh/mes para conservar el subsidio FOSE\n"
            "3. Los campos magnéticos domésticos son seguros (<100 µT según OMS)\n"
            "Intenta conectarte a internet para respuestas más específicas."
        )


# ==========================================
# 💬 VENTANA DE CHAT (CON CONTROL DE VOZ MEJORADO)
# ==========================================
class VentanaChatFope(ctk.CTkToplevel):
    def __init__(self, parent, cerebro, callback_datos, region, tarifa, mensaje_inicial=None):
        super().__init__(parent)
        self.title(f"Consultas Fope - {region}")
        self.geometry("500x700")
        self.cerebro = cerebro
        self.obtener_datos = callback_datos
        self.region = region
        self.tarifa = tarifa

        # Frame del Chat (Scroll)
        self.chat_frame = ctk.CTkScrollableFrame(self, fg_color="#1B2631")
        self.chat_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Mensaje de bienvenida
        saludo = mensaje_inicial if mensaje_inicial else f"Hola. Soy Fope. Veo que estás en {region}. ¿En qué te ayudo?"
        self.agregar_burbuja("Fope AI", saludo, "left")

        # --- CAMBIO 1: Hablar SIEMPRE el saludo al entrar ---
        # Usamos un delay de 500ms para asegurar que la ventana cargue visualmente antes de hablar
        self.after(500, lambda: self.cerebro.hablar(saludo))
        # ----------------------------------------------------

        # Área de Input (Abajo)
        input_frame = ctk.CTkFrame(self, fg_color="#212F3C")
        input_frame.pack(fill="x", padx=10, pady=10)

        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Escribe tu consulta aquí...", height=40)
        self.entry.pack(side="left", fill="x", expand=True, padx=5)
        self.entry.bind("<Return>", lambda e: self.enviar())

        # --- CAMBIO 2: BOTÓN (CHECKBOX) PARA SILENCIAR/ACTIVAR VOZ ---
        # Variable para controlar el audio SOLO de esta ventana
        self.chat_voz_activa = ctk.BooleanVar(value=True)

        # Checkbox con icono de parlante
        self.check_voz = ctk.CTkCheckBox(input_frame, text="🔊", variable=self.chat_voz_activa,
                                         width=40, onvalue=True, offvalue=False,
                                         fg_color="#E67E22", hover_color="#D35400")
        self.check_voz.pack(side="left", padx=5)

        # Tooltip para explicar qué hace el botón
        ToolTip(self.check_voz, "Activar/Desactivar lectura de voz en el chat", parent)
        # -------------------------------------------------------------

        ctk.CTkButton(input_frame, text="➤", width=50, command=self.enviar).pack(side="left")
        ctk.CTkButton(input_frame, text="🎙️", width=40, fg_color="#E67E22", command=self.voz).pack(side="left", padx=2)

    def agregar_burbuja(self, autor, texto, lado):
        color = "#27AE60" if lado == "right" else "#2874A6"
        alineacion = "e" if lado == "right" else "w"

        fila = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        fila.pack(fill="x", pady=5)

        lbl = ctk.CTkLabel(fila, text=f"{autor}:\n{texto}", fg_color=color, text_color="white", corner_radius=12,
                           wraplength=350, justify="left")
        lbl.pack(anchor=alineacion, padx=10, pady=2, ipadx=10, ipady=8)

        # Auto-scroll hacia abajo
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def enviar(self):
        msg = self.entry.get()
        if msg:
            self.agregar_burbuja("Usuario", msg, "right")
            self.entry.delete(0, 'end')
            threading.Thread(target=self.proc_resp, args=(msg,), daemon=True).start()

    def voz(self):
        self.entry.configure(placeholder_text="Escuchando...")
        threading.Thread(target=self._voz_hilo, daemon=True).start()

    def _voz_hilo(self):
        txt = self.cerebro.escuchar()
        self.after(0, lambda: self.entry.configure(placeholder_text="..."))
        if txt:
            self.after(0, lambda: self.agregar_burbuja("Voz", txt, "right"))
            self.after(0, lambda: threading.Thread(target=self.proc_resp, args=(txt,), daemon=True).start())

    def proc_resp(self, msg):
        contexto_actual = self.obtener_datos()

        # Mostrar indicador de carga
        self.agregar_burbuja("Fope AI", "🤔 Pensando...", "left")

        # Llamada a la IA
        resp = self.cerebro.pensar(msg, contexto_actual, self.region, self.tarifa)

        # Reemplazar el mensaje "Pensando..." con la respuesta real
        # Eliminar el último mensaje (el de "Pensando...")
        for widget in self.chat_frame.winfo_children()[-1:]:
            widget.destroy()

        # Agregar la respuesta real
        self.agregar_burbuja("Fope AI", resp, "left")

        # Leer respuesta si está activado el audio del chat
        if self.chat_voz_activa.get():
            self.cerebro.hablar(resp)
        # ------------------------------------------------------------------
# ==========================================
# 📊 VENTANA DE GRÁFICOS
# ==========================================
class VentanaGraficos(ctk.CTkToplevel):
    def __init__(self, parent, items):
        super().__init__(parent)
        self.title("Análisis Científico de Datos")
        self.geometry("900x700")
        nombres = [x['nombre'] for x in items]
        consumos = [x['kwh'] for x in items]
        campos_mag = [x['fisica']['B'] for x in items]
        fig = plt.Figure(figsize=(8, 6), dpi=100, facecolor='#2b2b2b')

        ax1 = fig.add_subplot(211)
        ax1.set_facecolor('#2b2b2b')
        ax1.bar(nombres, consumos, color='#2ECC71')
        ax1.set_title('Consumo Energético (kWh)', color='white')
        ax1.tick_params(axis='x', colors='white', rotation=15)
        ax1.tick_params(axis='y', colors='white')

        ax2 = fig.add_subplot(212)
        ax2.set_facecolor('#2b2b2b')
        ax2.plot(nombres, campos_mag, marker='o', color='#F1C40F', linewidth=2)
        ax2.fill_between(nombres, campos_mag, color='#F1C40F', alpha=0.3)
        ax2.set_title('Campo Magnético Emitido (µT)', color='white')
        ax2.tick_params(colors='white')

        fig.tight_layout(pad=3.0)
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


# ==========================================
# 🏠 APP PRINCIPAL (INTEGRACIÓN)
# ==========================================
class LuzSmartFusion(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LuzSmart Pro 🇵🇪 - v14.0 Ultimate Grid")
        self.geometry("1250x850")
        self.ayuda_activa = True
        self.cerebro = CerebroFope()
        self.lista_items = []
        self.tarifa_actual_valor = 0.67
        self.nombre_tarifa_actual = "Inicial"

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.pagina_actual = 0
        self.items_por_pagina = 10

        # === SIDEBAR ===
        sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#17202A")
        sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(sidebar, text="⚡ LUZ SMART PERÚ", font=("Roboto", 18, "bold"), text_color="#AED6F1").pack(
            pady=(30, 20))

        self.switch_voz = ctk.CTkSwitch(sidebar, text="Voz Fope", command=self.toggle_voz, onvalue=True, offvalue=False,
                                        progress_color="#2ECC71")
        self.switch_voz.select()
        self.switch_voz.pack(pady=5)

        self.switch_ayuda = ctk.CTkSwitch(sidebar, text="Modo Explicación", command=self.toggle_ayuda, onvalue=True,
                                          offvalue=False, progress_color="#F1C40F")
        self.switch_ayuda.select()
        self.switch_ayuda.pack(pady=5)

        f_region = ctk.CTkFrame(sidebar, fg_color="#2C3E50")
        f_region.pack(fill="x", padx=10, pady=15)
        ctk.CTkLabel(f_region, text="Ubicación:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5)
        self.combo_region = ctk.CTkComboBox(f_region, values=MotorFinanzas.obtener_lista_regiones(),
                                            command=self.al_cambiar_region)
        self.combo_region.set("Lima y Callao")
        self.combo_region.pack(fill="x", padx=5, pady=5)

        f_tarifa = ctk.CTkFrame(sidebar, fg_color="transparent")
        f_tarifa.pack(fill="x", padx=10)
        self.lbl_tarifa_valor = ctk.CTkLabel(f_tarifa, text="S/ 0.67", font=("Arial", 12, "bold"), text_color="#2ECC71")
        self.lbl_tarifa_valor.pack(side="right", padx=5)
        ctk.CTkLabel(f_tarifa, text="Tarifa Aplicada:").pack(side="left", padx=5)

        f_form = ctk.CTkFrame(sidebar, fg_color="transparent")
        f_form.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(f_form, text="1. Dispositivo:", anchor="w").pack(fill="x")
        self.combo_aparatos = ctk.CTkComboBox(f_form, values=list(CATALOGO_ELECTRO.keys()), command=self.al_seleccionar)
        self.combo_aparatos.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(f_form, text="2. Potencia (Watts):", anchor="w").pack(fill="x")
        self.entry_watts = ctk.CTkEntry(f_form, placeholder_text="Ej: 500")
        self.entry_watts.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(sidebar, text="Horas de uso diario:", anchor="w", font=("Arial", 12, "bold")).pack(padx=20,
                                                                                                        fill="x",
                                                                                                        pady=(10, 0))

        # Este label (lbl_horas_txt) es el que cambia el numero
        self.lbl_horas_txt = ctk.CTkLabel(sidebar, text="1.0 horas", text_color="#AED6F1")
        self.lbl_horas_txt.pack()

        self.slider_horas = ctk.CTkSlider(sidebar, from_=0, to=24, number_of_steps=48,
                                          command=lambda v: self.lbl_horas_txt.configure(text=f"{float(v):.1f} horas"))
        self.slider_horas.set(1)
        self.slider_horas.pack(padx=20, fill="x")

        # 4. SLIDER DÍAS (Aquí estaba el problema)
        ctk.CTkLabel(sidebar, text="Días al mes:", anchor="w", font=("Arial", 12, "bold")).pack(padx=20, fill="x",
                                                                                                pady=(10, 0))

        # Este label (lbl_dias_txt) mostrará el número cambiante
        self.lbl_dias_txt = ctk.CTkLabel(sidebar, text="30 días", text_color="#AED6F1")
        self.lbl_dias_txt.pack()

        self.slider_dias = ctk.CTkSlider(sidebar, from_=1, to=31, number_of_steps=30,
                                         command=lambda v: self.lbl_dias_txt.configure(text=f"{int(v)} días"))
        self.slider_dias.set(30)  # Valor por defecto
        self.slider_dias.pack(padx=20, fill="x", pady=(0, 20))

        btn_add = ctk.CTkButton(sidebar, text="➕ AGREGAR", height=40, font=("Arial", 13, "bold"), fg_color="#2874A6",
                                command=self.agregar_item)
        btn_add.pack(padx=20, pady=(10, 5), fill="x")

        f_tools = ctk.CTkFrame(sidebar, fg_color="transparent")
        f_tools.pack(fill="x", padx=20)
        ctk.CTkButton(f_tools, text="📈 Gráficos", width=130, fg_color="#27AE60", command=self.abrir_graficos).pack(
            side="left", padx=2)
        ctk.CTkButton(f_tools, text="📄 PDF", width=130, fg_color="#C0392B", command=self.generar_pdf).pack(side="right",
                                                                                                           padx=2)

        btn_chat = ctk.CTkButton(sidebar, text="🤖 Chat IA", fg_color="#8E44AD", command=self.abrir_chat_manual)
        btn_chat.pack(pady=20, padx=20, side="bottom")

        btn_limpiar = ctk.CTkButton(sidebar, text="🗑️ Reiniciar", fg_color="#922B21", command=self.limpiar)
        btn_limpiar.pack(pady=5, padx=20, side="bottom")

        # === AREA PRINCIPAL ===
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # KPIs
        kpi_frame = ctk.CTkFrame(main_area, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        self.lbl_total_mes = self.crear_tarjeta(kpi_frame, "RECIBO MENSUAL (S/)", "#2E86C1")
        self.lbl_kwh_mes = self.crear_tarjeta(kpi_frame, "CONSUMO (kWh)", "#D68910")
        self.lbl_cargo_fijo = self.crear_tarjeta(kpi_frame, "CARGO FIJO", "#7F8C8D")
        self.lbl_cargo_fijo.configure(text=f"S/ {CARGO_FIJO_MENSUAL:.2f}")

        # === BOTÓN DE ANÁLISIS DE CIRCUITO (PRIORIDAD 3) ===
        self.btn_circuito = ctk.CTkButton(main_area,
                                          text="⚡ ANALIZAR CIRCUITO COMPLETO",
                                          font=("Arial", 14, "bold"),
                                          fg_color="#8E44AD",
                                          height=40,
                                          command=self.analizar_circuito_total)
        self.btn_circuito.pack(fill="x", pady=(10, 20))

        # --- LISTA DETALLADA MEJORADA ---
        ctk.CTkLabel(main_area, text="📋 Detalle Completo:", font=("Arial", 16, "bold")).pack(anchor="w", pady=(10, 5))

        # ENCABEZADO EXPLICITO
        header = ctk.CTkFrame(main_area, height=45, fg_color="#34495E", corner_radius=8)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="Aparato", width=180, font=("Arial", 13, "bold")).pack(side="left", padx=5)
        # Cambio de nombre de columna solicitado
        ctk.CTkLabel(header, text="Días Mes | Horas Día", width=140, font=("Arial", 13, "bold")).pack(side="left",
                                                                                                      padx=5)
        ctk.CTkLabel(header, text="Costo/Hora", width=100, font=("Arial", 13, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Ingeniería (I / R / B)", width=200, font=("Arial", 13, "bold"),
                     text_color="#AED6F1").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Total Mes", width=80, font=("Arial", 13, "bold")).pack(side="right", padx=10)

        self.scroll_lista = ctk.CTkScrollableFrame(main_area, fg_color="#212F3C")
        self.scroll_lista.pack(fill="both", expand=True)

        # === PAGINACIÓN PARA LISTAS LARGAS ===
        # (Agregar después del scroll_lista, antes de self.burbuja_frame)

        self.frame_paginacion = ctk.CTkFrame(main_area, fg_color="transparent")
        self.frame_paginacion.pack(fill="x", pady=(5, 15))

        # Variables de paginación
        self.pagina_actual = 0
        self.items_por_pagina = 10  # Mostrar 10 items por página

        # Botones de navegación
        self.btn_pag_anterior = ctk.CTkButton(
            self.frame_paginacion,
            text="◀ Anterior",
            width=100,
            command=self.pagina_anterior,
            state="disabled"  # Inicialmente desactivado
        )
        self.btn_pag_anterior.pack(side="left", padx=5)

        self.lbl_pagina_info = ctk.CTkLabel(
            self.frame_paginacion,
            text="Página 1/1",
            font=("Arial", 12)
        )
        self.lbl_pagina_info.pack(side="left", padx=20)

        self.btn_pag_siguiente = ctk.CTkButton(
            self.frame_paginacion,
            text="Siguiente ▶",
            width=100,
            command=self.pagina_siguiente,
            state="disabled"  # Inicialmente desactivado
        )
        self.btn_pag_siguiente.pack(side="left", padx=5)

        self.burbuja_frame = ctk.CTkFrame(self, fg_color="#FEF9E7", corner_radius=20, border_color="#F1C40F",
                                          border_width=2)
        self.lbl_consejo = ctk.CTkLabel(self.burbuja_frame, text="", text_color="#7F8C8D", font=("Arial", 14, "italic"),
                                        wraplength=200)
        self.lbl_consejo.pack(padx=15, pady=10)

        self.al_cambiar_region("Lima y Callao")
        self.crear_boton_fope()

    # --- FUNCIONES ---
    def crear_tarjeta(self, padre, titulo, color):
        card = ctk.CTkFrame(padre, fg_color=color, height=100, corner_radius=10)
        card.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(card, text=titulo, text_color="white", font=("Arial", 12)).pack(pady=(15, 0))
        lbl = ctk.CTkLabel(card, text="0.00", text_color="white", font=("Arial", 28, "bold"))
        lbl.pack(pady=5)
        return lbl

    def toggle_voz(self):
        self.cerebro.set_voz(bool(self.switch_voz.get()))

    def toggle_ayuda(self):
        self.ayuda_activa = bool(self.switch_ayuda.get())

    def update_sliders(self, value):
        self.lbl_horas_valor.configure(text=f"{float(self.slider_horas.get()):.1f} h/día")

    def al_cambiar_region(self, region):
        self.tarifas_region_actual = MotorFinanzas.get_tarifas_region(region)
        self.recalcular_todo_logica()

    def al_seleccionar(self, opcion):
        val = CATALOGO_ELECTRO.get(opcion, 0)
        if val == -1:
            self.abrir_chat_manual("Hola Fope...")
            self.combo_aparatos.set("Selecciona un aparato...")
            return
        if val > 0:
            self.entry_watts.delete(0, "end")
            self.entry_watts.insert(0, str(val))
            if "Refrigeradora" in opcion:
                self.slider_horas.set(24)
            else:
                self.slider_horas.set(1)
            self.update_sliders(0)

    def agregar_item(self):
        """Agrega un electrodoméstico con validación mejorada"""
        try:
            # 1. Validar nombre
            nombre = self.combo_aparatos.get()
            if nombre == "Selecciona un aparato...":
                messagebox.showwarning("Selección requerida", "Por favor, selecciona un aparato del catálogo.")
                return

            # 2. Validar potencia (Watts)
            watts_text = self.entry_watts.get().strip()
            if not watts_text:
                messagebox.showwarning("Dato faltante", "Ingresa la potencia en watts.")
                return

            try:
                watts = float(watts_text)
                if watts <= 0:
                    messagebox.showwarning("Valor inválido", "La potencia debe ser mayor a 0 watts.")
                    return
                if watts > 10000:  # Límite razonable para hogares
                    respuesta = messagebox.askyesno("Confirmar alta potencia",
                                                    f"¿Estás seguro de que el aparato consume {watts}W?\n" +
                                                    "Esto es equivalente a aparatos industriales.\n" +
                                                    "¿Deseas continuar?")
                    if not respuesta:
                        return
            except ValueError:
                messagebox.showwarning("Formato inválido",
                                       "Ingresa un número válido para los watts.\n" +
                                       "Ejemplos: 1500, 350.5, 60")
                return

            # 3. Validar horas y días
            horas = float(self.slider_horas.get())
            dias = int(self.slider_dias.get())

            if horas == 0:
                messagebox.showinfo("Horas de uso",
                                    "El aparato tiene 0 horas de uso diario.\n" +
                                    "No se agregará al consumo mensual.")
                return

            if dias == 0:
                messagebox.showwarning("Días inválidos",
                                       "Selecciona al menos 1 día de uso al mes.")
                return

            # 4. Ajuste para refrigeradoras (operación continua)
            if "Refrigeradora" in nombre and horas == 24:
                watts_ajustado = watts / 3
            else:
                watts_ajustado = watts

            # 5. Límite de items (para rendimiento)
            if len(self.lista_items) >= 50:
                messagebox.showwarning("Límite alcanzado",
                                       "Has alcanzado el límite de 50 aparatos.\n" +
                                       "Por favor, agrupa aparatos similares o elimina algunos.")
                return

            # 6. Procesar el item
            datos_fisicos = MotorFisica.analizar_componente(watts_ajustado, horas, dias)
            kwh_mensual = (watts_ajustado * horas * dias) / 1000

            item = {
                "nombre": nombre,
                "watts": watts_ajustado,
                "horas": horas,
                "dias": dias,
                "kwh": kwh_mensual,
                "costo": 0,
                "fisica": datos_fisicos
            }

            # 7. AGREGAR A LA LISTA Y ACTUALIZAR PAGINACIÓN
            self.lista_items.append(item)
            self.pagina_actual = 0  # ← NUEVA: Reiniciar a página 1
            self.actualizar_paginacion()  # ← NUEVA: Actualizar visual con paginación

            self.recalcular_todo_logica()  # ← Esta ya la tienes

            # 8. Feedback visual y auditivo
            self.mostrar_notificacion(f"✅ {nombre} agregado", 3000)
            threading.Thread(target=self.pedir_consejo_burbuja, args=(nombre,), daemon=True).start()

        except Exception as e:
            print(f"Error al agregar item: {e}")
            messagebox.showerror("Error inesperado",
                                 f"Ocurrió un error al procesar el aparato:\n{str(e)}")
    def mostrar_notificacion(self, mensaje, duracion_ms=2000):
        """Muestra una notificación temporal"""
        # Crear ventana de notificación
        notif = ctk.CTkToplevel(self)
        notif.title("")
        notif.geometry("300x80")
        notif.configure(fg_color="#2ECC71")
        notif.overrideredirect(True)  # Sin bordes

        # Posicionar en la esquina superior derecha
        x = self.winfo_x() + self.winfo_width() - 320
        y = self.winfo_y() + 20
        notif.geometry(f"+{x}+{y}")

        # Contenido
        ctk.CTkLabel(notif, text=mensaje, text_color="white",
                     font=("Arial", 12)).pack(expand=True, fill="both", padx=20, pady=20)

        # Auto-cerrar después del tiempo especificado
        notif.after(duracion_ms, notif.destroy)

    def recalcular_todo_logica(self):
        """Recalcula todos los valores y actualiza la interfaz con paginación"""
        try:
            # 1. Calcular consumo total
            total_kwh = sum(i['kwh'] for i in self.lista_items)

            # 2. Calcular tarifa dinámica según FOSE
            precio_kwh, tiene_subsidio = MotorFinanzas.calcular_tarifa_dinamica(
                total_kwh,
                self.tarifas_region_actual
            )

            # 3. Actualizar variables internas
            self.tarifa_actual_valor = precio_kwh
            self.nombre_tarifa_actual = "Con FOSE" if tiene_subsidio else "Sin FOSE"

            # 4. Actualizar etiqueta de tarifa
            texto_tarifa = f"S/ {precio_kwh:.2f} ({self.nombre_tarifa_actual})"
            color_tarifa = "#2ECC71" if tiene_subsidio else "#E74C3C"
            self.lbl_tarifa_valor.configure(text=texto_tarifa, text_color=color_tarifa)

            # 5. Calcular costos individuales
            costo_variable_total = 0
            for item in self.lista_items:
                item['costo'] = item['kwh'] * precio_kwh
                costo_variable_total += item['costo']

            # 6. ACTUALIZAR PAGINACIÓN (EN LUGAR DE BORRAR TODO)
            self.actualizar_paginacion()

            # 7. Actualizar KPIs
            total_recibo = costo_variable_total + CARGO_FIJO_MENSUAL
            self.lbl_total_mes.configure(text=f"S/ {total_recibo:.2f}")
            self.lbl_kwh_mes.configure(text=f"{total_kwh:.1f} kWh")

        except Exception as e:
            print(f"Error en recalcular_todo_logica: {e}")
    # --- DIBUJAR FILA CLARISIMA ---
    def dibujar_fila(self, item):
        # 1. Crear el Frame de la fila
        fila = ctk.CTkFrame(self.scroll_lista, fg_color="#2C3E50", height=50)
        fila.pack(fill="x", pady=3)

        # Cursor manito
        fila.configure(cursor="hand2")
        command_click = lambda event=None: self.mostrar_analisis_tecnico(item)
        fila.bind("<Button-1>", command_click)

        f = item['fisica']
        costo_hora = (item['watts'] / 1000) * self.tarifa_actual_valor

        txt_uso = f"{item['dias']} d | {item['horas']} h"
        txt_costo_h = f"S/ {costo_hora:.4f}"
        txt_ciencia = f"{f['I']} A | {f['B']} µT"

        ToolTip(fila, f"CO2: {f['CO2']}kg | Joules: {f['J']}", self)

        # === AQUÍ ESTÁ LA CORRECCIÓN DE ALINEACIÓN ===
        # Antes tenías 170, 100, 80... Ahora deben coincidir con el Encabezado

        # 1. Nombre (Igual que header: 180)
        l1 = ctk.CTkLabel(fila, text=item['nombre'], width=180, anchor="w", font=("Arial", 12, "bold"))  # CORREGIDO

        # 2. Uso (Igual que header: 140)
        l2 = ctk.CTkLabel(fila, text=txt_uso, width=140, text_color="#F1C40F", font=("Arial", 12))  # CORREGIDO

        # 3. Costo (Igual que header: 100)
        l3 = ctk.CTkLabel(fila, text=txt_costo_h, width=100, text_color="#F7DC6F")  # CORREGIDO

        # 4. Ciencia (Header es 200, le damos 150 al texto + 40 al botón aprox)
        l4 = ctk.CTkLabel(fila, text=txt_ciencia, width=150, text_color="#5DADE2", font=("Consolas", 11))  # CORREGIDO

        # Colocamos los labels
        l1.pack(side="left", padx=5)
        l2.pack(side="left", padx=5)
        l3.pack(side="left", padx=5)
        l4.pack(side="left", padx=5)

        for label in [l1, l2, l3, l4]:
            label.bind("<Button-1>", command_click)
            label.configure(cursor="hand2")

        # Botón
        ctk.CTkButton(fila, text="📐", width=30, fg_color="#3498DB",
                      command=lambda: self.mostrar_analisis_tecnico(item)).pack(side="left", padx=5)

        ctk.CTkLabel(fila, text=f"S/ {item['costo']:.2f}", width=80, text_color="#2ECC71",
                     font=("Arial", 14, "bold")).pack(side="right", padx=10)

    def abrir_graficos(self):
        if not self.lista_items: return messagebox.showwarning("!", "Agrega aparatos primero.")
        VentanaGraficos(self, self.lista_items)

    def generar_pdf(self):
        if not self.lista_items: return
        total_pagar = float(self.lbl_total_mes.cget("text").split()[1])
        total_kwh = float(self.lbl_kwh_mes.cget("text").split()[0])
        totales = {"kwh": total_kwh, "dinero": total_pagar, "tarifa_nombre": f"{self.nombre_tarifa_actual}"}
        MotorReportes.generar_pdf(self.lista_items, totales, self.combo_region.get(), self.tarifa_actual_valor)

    def limpiar(self):
        """Limpia toda la lista y reinicia la paginación"""
        self.lista_items = []
        self.pagina_actual = 0  # Reiniciar a página 1
        self.actualizar_paginacion()  # Usar paginación en lugar de recálculo directo

        # También actualizar KPIs
        self.lbl_total_mes.configure(text="S/ 0.00")
        self.lbl_kwh_mes.configure(text="0.0 kWh")

        # Mostrar notificación
        self.mostrar_notificacion("✅ Lista limpiada correctamente", 2000)

    def pedir_consejo_burbuja(self, nombre):
        try:
            # 1. La IA piensa (esto toma unos segundos)
            cons = self.cerebro.pensar(nombre, "", self.combo_region.get(), 0, True)

            # 2. MOSTRAR BURBUJA (Visual)
            # Usamos after(0) para que la interfaz gráfica se actualice de inmediato
            self.after(0, lambda: self.mostrar_burbuja(cons))

            # 3. HABLAR CONSEJO (Audio)
            # Verificamos si el switch principal de "Voz Fope" está activado
            if self.switch_voz.get() == 1:
                self.cerebro.hablar(cons)

        except Exception as e:
            print(f"Error al generar consejo: {e}")

    def mostrar_burbuja(self, txt):
        self.lbl_consejo.configure(text=f"💡 {txt}")
        self.burbuja_frame.place(relx=0.85, rely=0.82, anchor="e")
        self.after(6000, lambda: self.burbuja_frame.place_forget())

    def crear_boton_fope(self):
        try:
            if os.path.exists("fope.png"):
                img = ctk.CTkImage(Image.open("fope.png"), size=(60, 60))
            else:
                raise Exception
            self.btn_fope = ctk.CTkButton(self, text="", image=img, width=70, height=70, fg_color="#F1C40F",
                                          corner_radius=35, command=self.abrir_chat_manual)
        except:
            self.btn_fope = ctk.CTkButton(self, text="💡", font=("Arial", 30), width=70, height=70, fg_color="#F1C40F",
                                          corner_radius=35, command=self.abrir_chat_manual)
        self.btn_fope.place(relx=0.92, rely=0.92, anchor="center")

    def abrir_chat_manual(self, mensaje=None):
        reg = self.combo_region.get()
        tar = self.tarifa_actual_valor
        contexto = "\n".join([f"- {i['nombre']}: {i['fisica']['I']}A, {i['fisica']['B']}µT" for i in self.lista_items])
        chat = VentanaChatFope(self, self.cerebro, lambda: contexto, reg, tar,
                               mensaje_inicial=mensaje if isinstance(mensaje, str) else None)
        chat.grab_set()

    # ==========================================
    # 📐 NUEVAS FUNCIONES DE ANÁLISIS TÉCNICO
    # ==========================================

    def mostrar_analisis_tecnico(self, item):
        """
        VENTANA EMERGENTE CON ANÁLISIS ELECTROMAGNÉTICO COMPLETO
        Muestra TODAS las ecuaciones y cálculos realizados
        """
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"📐 Análisis Técnico: {item['nombre']}")
        ventana.geometry("700x800")
        ventana.configure(fg_color="#1E1E1E")

        # Frame con scroll
        scroll = ctk.CTkScrollableFrame(ventana, fg_color="#2C2C2C")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        f = item['fisica']

        # === TÍTULO ===
        ctk.CTkLabel(scroll, text=f"ANÁLISIS ELECTROMAGNÉTICO",
                     font=("Arial", 20, "bold"),
                     text_color="#00FF00").pack(pady=10)

        ctk.CTkLabel(scroll, text=f"Aparato: {item['nombre']}",
                     font=("Arial", 14),
                     text_color="#FFFFFF").pack()

        # Aseguramos que existan las claves (por si MotorFisica es una versión antigua)
        # Esto evita que el programa se cierre si faltan datos
        f.setdefault('kWh', (item['watts'] * item['horas'] * item['dias']) / 1000)
        f.setdefault('Q', f['I'] * item['horas'] * 3600)
        f.setdefault('B_nivel', "Bajo")
        f.setdefault('P_perdida', 0.05)
        f.setdefault('eficiencia', 99)
        f.setdefault('arboles', 0.01)

        # === SECCIÓN 1: LEY DE OHM ===
        self.crear_seccion(scroll, "1️⃣ LEY DE OHM", [
            f"Fórmula: I = P/V",
            f"Cálculo: I = {item['watts']}W / 220V",
            f"Resultado: I = {f['I']} A (Amperios)",
            f"",
            f"Resistencia equivalente:",
            f"Fórmula: R = V²/P",
            f"R = (220)² / {item['watts']}",
            f"R = {f['R']} Ω (Ohmios)"
        ])

        # === SECCIÓN 2: LEY DE JOULE ===
        segundos_totales = item['horas'] * item['dias'] * 3600
        self.crear_seccion(scroll, "2️⃣ LEY DE JOULE (Energía)", [
            f"Fórmula: E = P·t",
            f"Tiempo total: {item['horas']}h/día × {item['dias']}días × 3600s/h",
            f"t = {segundos_totales:.0f} segundos",
            f"E = {item['watts']}W × {segundos_totales:.0f}s",
            f"E = {f['J']} Joules",
            f"E = {f.get('kWh', 0):.2f} kWh (Comercial)"
        ])

        # === SECCIÓN 3: LEY DE AMPÈRE ===
        self.crear_seccion(scroll, "3️⃣ LEY DE AMPÈRE (Campo Magnético)", [
            f"Fórmula: B = (μ₀·I)/(2πr)",
            f"μ₀ = 4π × 10⁻⁷ H/m (Permeabilidad del vacío)",
            f"I = {f['I']} A",
            f"r = 0.3 m (30 cm de distancia)",
            f"",
            f"B = (4π×10⁻⁷ × {f['I']}) / (2π × 0.3)",
            f"B = {f['B']} µT (Microteslas)",
            f"",
            f"Clasificación OMS: {f.get('B_nivel', 'N/A')}",
            f"Límite seguro: < 100 µT"
        ])

        # === SECCIÓN 4: CARGA ELÉCTRICA ===
        self.crear_seccion(scroll, "4️⃣ CARGA TRANSPORTADA", [
            f"Fórmula: Q = I·t",
            f"Q = {f['I']} A × {segundos_totales:.0f} s",
            f"Q = {f.get('Q', 0):.2f} Coulombs",
            f"",
            f"Equivalente a: {f.get('Q', 0) / 1.602e-19:.2e} electrones"
        ])

        # === SECCIÓN 5: PÉRDIDAS ===
        self.crear_seccion(scroll, "5️⃣ PÉRDIDAS POR EFECTO JOULE", [
            f"En 10m de cable de cobre (2.5mm²):",
            f"Fórmula: P = I²R",
            f"P_perdida = {f.get('P_perdida', 0):.4f} W",
            f"Eficiencia estimada: {f.get('eficiencia', 0)}%"
        ])

        # === SECCIÓN 6: IMPACTO AMBIENTAL ===
        self.crear_seccion(scroll, "6️⃣ HUELLA DE CARBONO", [
            f"Emisiones CO₂: {f['CO2']} kg",
            f"Árboles necesarios para compensar: {f.get('arboles', 0):.4f} árboles/año",
            f"Factor de emisión Perú: 0.203 kg CO₂/kWh"
        ])

        # Botón cerrar
        ctk.CTkButton(scroll, text="CERRAR",
                      command=ventana.destroy,
                      fg_color="#E74C3C",
                      height=40).pack(pady=20)


    # 📐 FUNCIONES DE ANÁLISIS TÉCNICO
    # ==========================================

    def mostrar_analisis_tecnico(self, item):
        """
        VENTANA EMERGENTE CON ANÁLISIS ELECTROMAGNÉTICO COMPLETO
        Muestra TODAS las ecuaciones y cálculos realizados
        """
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"📐 Análisis Técnico: {item['nombre']}")
        ventana.geometry("700x800")
        ventana.configure(fg_color="#1E1E1E")

        # Frame con scroll
        scroll = ctk.CTkScrollableFrame(ventana, fg_color="#2C2C2C")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        f = item['fisica']

        # === TÍTULO ===
        ctk.CTkLabel(scroll, text=f"ANÁLISIS ELECTROMAGNÉTICO",
                     font=("Arial", 20, "bold"),
                     text_color="#00FF00").pack(pady=10)

        ctk.CTkLabel(scroll, text=f"Aparato: {item['nombre']}",
                     font=("Arial", 14),
                     text_color="#FFFFFF").pack()

        # Aseguramos que existan las claves
        f.setdefault('kWh', (item['watts'] * item['horas'] * item['dias']) / 1000)
        f.setdefault('Q', f['I'] * item['horas'] * 3600)
        f.setdefault('B_nivel', "Bajo")
        f.setdefault('P_perdida', 0.05)
        f.setdefault('eficiencia', 99)
        f.setdefault('arboles', 0.01)

        # === SECCIÓN 1: LEY DE OHM ===
        self.crear_seccion(scroll, "1️⃣ LEY DE OHM", [
            f"Fórmula: I = P/V",
            f"Cálculo: I = {item['watts']}W / 220V",
            f"Resultado: I = {f['I']} A (Amperios)",
            f"",
            f"Resistencia equivalente:",
            f"Fórmula: R = V²/P",
            f"R = (220)² / {item['watts']}",
            f"R = {f['R']} Ω (Ohmios)"
        ])

        # === SECCIÓN 2: LEY DE JOULE ===
        segundos_totales = item['horas'] * item['dias'] * 3600
        self.crear_seccion(scroll, "2️⃣ LEY DE JOULE (Energía)", [
            f"Fórmula: E = P·t",
            f"Tiempo total: {item['horas']}h/día × {item['dias']}días × 3600s/h",
            f"t = {segundos_totales:.0f} segundos",
            f"E = {item['watts']}W × {segundos_totales:.0f}s",
            f"E = {f['J']} Joules",
            f"E = {f.get('kWh', 0):.2f} kWh (Comercial)"
        ])

        # === SECCIÓN 3: LEY DE AMPÈRE ===
        self.crear_seccion(scroll, "3️⃣ LEY DE AMPÈRE (Campo Magnético)", [
            f"Fórmula: B = (μ₀·I)/(2πr)",
            f"μ₀ = 4π × 10⁻⁷ H/m (Permeabilidad del vacío)",
            f"I = {f['I']} A",
            f"r = 0.3 m (30 cm de distancia)",
            f"",
            f"B = (4π×10⁻⁷ × {f['I']}) / (2π × 0.3)",
            f"B = {f['B']} µT (Microteslas)",
            f"",
            f"Clasificación OMS: {f.get('B_nivel', 'N/A')}",
            f"Límite seguro: < 100 µT"
        ])

        # === SECCIÓN 4: CARGA ELÉCTRICA ===
        self.crear_seccion(scroll, "4️⃣ CARGA TRANSPORTADA", [
            f"Fórmula: Q = I·t",
            f"Q = {f['I']} A × {segundos_totales:.0f} s",
            f"Q = {f.get('Q', 0):.2f} Coulombs",
            f"",
            f"Equivalente a: {f.get('Q', 0) / 1.602e-19:.2e} electrones"
        ])

        # === SECCIÓN 5: PÉRDIDAS ===
        self.crear_seccion(scroll, "5️⃣ PÉRDIDAS POR EFECTO JOULE", [
            f"En 10m de cable de cobre (2.5mm²):",
            f"Fórmula: P = I²R",
            f"P_perdida = {f.get('P_perdida', 0):.4f} W",
            f"Eficiencia estimada: {f.get('eficiencia', 0)}%"
        ])

        # === SECCIÓN 6: IMPACTO AMBIENTAL ===
        self.crear_seccion(scroll, "6️⃣ HUELLA DE CARBONO", [
            f"Emisiones CO₂: {f['CO2']} kg",
            f"Árboles necesarios para compensar: {f.get('arboles', 0):.4f} árboles/año",
            f"Factor de emisión Perú: 0.203 kg CO₂/kWh"
        ])

        # Botón cerrar
        ctk.CTkButton(scroll, text="CERRAR",
                      command=ventana.destroy,
                      fg_color="#E74C3C",
                      height=40).pack(pady=20)

    def crear_seccion(self, parent, titulo, lineas):
        """Helper para crear secciones en el análisis"""
        frame = ctk.CTkFrame(parent, fg_color="#3C3C3C", corner_radius=10)
        frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(frame, text=titulo,
                     font=("Arial", 14, "bold"),
                     text_color="#FFD700").pack(anchor="w", padx=15, pady=5)

        for linea in lineas:
            ctk.CTkLabel(frame, text=linea,
                         font=("Consolas", 12),
                         text_color="#CCCCCC",
                         anchor="w").pack(anchor="w", padx=20, pady=2)

    # ==========================================
    # ⚡ ANÁLISIS DE CIRCUITO TOTAL
    # ==========================================
    def analizar_circuito_total(self):
        if not self.lista_items:
            messagebox.showwarning("Aviso", "Agrega aparatos a la lista primero.")
            return

        # 1. CÁLCULOS MATEMÁTICOS (Kirchhoff)
        i_total = sum(item['fisica']['I'] for item in self.lista_items)
        p_total = sum(item['watts'] for item in self.lista_items)
        b_total = sum(item['fisica']['B'] for item in self.lista_items)

        # Resistencia Equivalente (Ley de Ohm total: R = V/I)
        r_eq = 220 / i_total if i_total > 0 else 0

        # Caída de tensión
        r_cable = 0.2
        caida_v = i_total * r_cable
        v_real = 220 - caida_v

        # Porcentaje de carga
        limite_termica = 20
        porcentaje = (i_total / limite_termica) * 100

        estado = "✅ NORMAL"
        if porcentaje > 80: estado = "⚠️ ALERTA (Sobrecarga próxima)"
        if porcentaje > 100: estado = "🚨 PELIGRO (Llave saltará)"

        # 2. CREAR VENTANA
        ventana = ctk.CTkToplevel(self)
        ventana.title("⚡ Análisis de Ingeniería: Circuito Total")
        ventana.geometry("650x550")
        ventana.configure(fg_color="#17202A")

        # 3. TEXTO DEL REPORTE
        texto = f"""
╔════════════════════════════════════════════════╗
║      ANÁLISIS DE CIRCUITO (PARALELO)           ║
╚════════════════════════════════════════════════╝

📊 APLICACIÓN DE LEYES DE KIRCHHOFF:

1️⃣ CORRIENTE TOTAL (Ley de Nodos):
   Σ I_entrada = Σ I_salida
   I_total = {i_total:.2f} A

2️⃣ POTENCIA TOTAL INSTALADA:
   P_total = {p_total:.2f} W

3️⃣ RESISTENCIA EQUIVALENTE DEL SISTEMA:
   R_eq = V / I_total
   R_eq = {r_eq:.2f} Ω

4️⃣ CAÍDA DE TENSIÓN (Cableado):
   ΔV = I_total × R_cable ({r_cable}Ω)
   ΔV = {caida_v:.2f} Voltios
   Voltaje Real en Enchufes: {v_real:.2f} V

5️⃣ CAMPO MAGNÉTICO ACUMULADO (Estimado):
   B_total ≈ {b_total:.2f} µT

--------------------------------------------------
🚦 ESTADO DE SEGURIDAD (Llave 20A):
--------------------------------------------------
Estado: {estado}
Carga del sistema: {porcentaje:.1f}%

⚠️ CONCLUSIÓN TÉCNICA:
{"El sistema opera dentro de parámetros seguros." if porcentaje < 80 else "REDUCE LA CARGA INMEDIATAMENTE. RIESGO DE INCENDIO."}
"""

        textbox = ctk.CTkTextbox(ventana, width=600, height=480,
                                 font=("Consolas", 12), fg_color="#212F3C", text_color="#AED6F1")
        textbox.pack(padx=20, pady=20)
        textbox.insert("1.0", texto)
        textbox.configure(state="disabled")

    # ==========================================
    # 📄 MÉTODOS DE PAGINACIÓN
    # ==========================================

    def pagina_anterior(self):
        """Ir a la página anterior"""
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_paginacion()

    def pagina_siguiente(self):
        """Ir a la página siguiente"""
        if self.pagina_actual < self.total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar_paginacion()

    def actualizar_paginacion(self):
        """Actualiza la visualización según la página actual"""
        try:
            # 1. Limpiar la lista actual
            for widget in self.scroll_lista.winfo_children():
                widget.destroy()

            # 2. Si no hay items, mostrar mensaje
            if not self.lista_items:
                lbl_vacio = ctk.CTkLabel(
                    self.scroll_lista,
                    text="📭 No hay aparatos agregados.\nAgrega algunos usando el formulario a la izquierda.",
                    text_color="#7F8C8D",
                    font=("Arial", 14),
                    justify="center"
                )
                lbl_vacio.pack(expand=True, pady=50)
                return

            # 3. Calcular qué items mostrar
            total_items = len(self.lista_items)
            self.items_por_pagina = 10

            # Calcular total de páginas
            self.total_paginas = max(1, (total_items + self.items_por_pagina - 1) // self.items_por_pagina)

            # Asegurarse de que página actual sea válida
            if self.pagina_actual >= self.total_paginas:
                self.pagina_actual = self.total_paginas - 1

            # Calcular índices de inicio y fin
            inicio = self.pagina_actual * self.items_por_pagina
            fin = min(inicio + self.items_por_pagina, total_items)

            # 4. Obtener items de la página actual
            items_pagina = self.lista_items[inicio:fin]

            # 5. Dibujar solo los items de esta página
            for item in items_pagina:
                self.dibujar_fila(item)

            # 6. Actualizar controles de paginación
            self.lbl_pagina_info.configure(
                text=f"Página {self.pagina_actual + 1}/{self.total_paginas} ({total_items} items)"
            )

            # Habilitar/deshabilitar botones según posición
            self.btn_pag_anterior.configure(
                state="normal" if self.pagina_actual > 0 else "disabled"
            )

            self.btn_pag_siguiente.configure(
                state="normal" if self.pagina_actual < self.total_paginas - 1 else "disabled"
            )

            # 7. Si solo hay una página, ocultar controles
            if self.total_paginas <= 1:
                self.frame_paginacion.pack_forget()
            else:
                self.frame_paginacion.pack(fill="x", pady=(5, 15))

        except Exception as e:
            print(f"Error en actualizar_paginacion: {e}")

# ==========================================
# 🏁 FIN DE LA CLASE - INICIO DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    app = LuzSmartFusion()
    app.mainloop()