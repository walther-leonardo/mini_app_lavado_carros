import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import datetime  # NUEVO: Para manejar la fecha actual
import sys       # NUEVO: Para forzar el cierre del programa

try:
    from app_logic import (
    actualizar_placas,
    actualizar_vin,
    actualizar_ordenes,
    procesar_logica_usuario,
    validar_placas_usuario
    )
    LOGICA_DISPONIBLE = True
except ImportError:
    LOGICA_DISPONIBLE = False

class AppSAP:
    def __init__(self, root):
        self.root = root
        
        # ==========================================
        # CONTROL DE FECHA DE EXPIRACIÓN (TIME BOMB)
        # ==========================================
        fecha_limite = datetime.date(2026, 12, 31)

        if datetime.date.today() > fecha_limite:
            self.root.withdraw()

            messagebox.showerror(
                "Licencia Expirada",
                "El período de validez de esta versión ha expirado.\n"
                "Por favor, solicite una versión actualizada al creador."
            )

            sys.exit()

        # ==========================================
        # CONFIGURACIÓN VENTANA PRINCIPAL
        # ==========================================
        self.root.title("Asistente SAP Portátil")
        self.root.geometry("650x550")
        self.password_admin = "EmperorProtects"
        self.admin_autenticado = False

        # ==========================================
        # NOTEBOOK PRINCIPAL
        # ==========================================
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(
            expand=True,
            fill='both',
            padx=10,
            pady=10
        )

        # ==========================================
        # CREACIÓN DE TABS
        # ==========================================
        self.tab_admin = ttk.Frame(self.notebook)
        self.tab_user = ttk.Frame(self.notebook)
        self.tab_validacion = ttk.Frame(self.notebook)

        # ==========================================
        # AGREGAR TABS AL NOTEBOOK
        # ==========================================
        self.notebook.add(
            self.tab_admin,
            text="Administrador"
        )

        self.notebook.add(
            self.tab_user,
            text="Usuario"
        )

        self.notebook.add(
            self.tab_validacion,
            text="Validación Placas"
        )
        
        self.notebook.bind("<<NotebookTabChanged>>", self.validar_tab_admin)

        # ==========================================
        # CONSTRUIR INTERFACES
        # ==========================================
        self.construir_tab_admin()
        self.construir_tab_user()
        self.construir_tab_validacion()
        self.notebook.select(self.tab_user)

    def seleccionar_archivo(self, variable_texto, tipos_archivo):
        ruta = filedialog.askopenfilename(filetypes=tipos_archivo)
        if ruta:
            variable_texto.set(ruta)

    def validar_tab_admin(self, event):
        """
        Solicita contraseña cuando el usuario intenta abrir
        la pestaña Administrador.
        """

        tab_actual = event.widget.select()
        texto_tab = event.widget.tab(tab_actual, "text")

        # Si no es la pestaña Administrador, no hacemos nada
        if texto_tab != "Administrador":
            return

        # Si ya inició sesión antes, dejar pasar
        if self.admin_autenticado:
            return

        password = simpledialog.askstring(
            "Acceso Administrador",
            "Ingrese la contraseña:",
            show="*"
        )

        if password == self.password_admin:
            self.admin_autenticado = True
        else:
            messagebox.showerror(
                "Acceso denegado",
                "Contraseña incorrecta."
            )

            # Regresar automáticamente a Usuario
            self.notebook.select(self.tab_user)

    # ==========================================
    # INTERFAZ: MÓDULO ADMINISTRADOR
    # ==========================================
    def construir_tab_admin(self):
        ttk.Label(self.tab_admin, text="Carga independiente de extracciones desde SAP", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.ruta_add = tk.StringVar()
        self.ruta_veh = tk.StringVar()
        self.ruta_crm = tk.StringVar()

        archivos_config = [
            ("VLCADDDATA (Placas):", self.ruta_add, "placas"), 
            ("VLCVEHICLE (VIN):", self.ruta_veh, "vin"), 
            ("CRMS4D_SERV_H (Órdenes):", self.ruta_crm, "ordenes")
        ]

        for label_text, var, tipo in archivos_config:
            frame = ttk.Frame(self.tab_admin)
            frame.pack(fill='x', padx=10, pady=10)
            
            ttk.Label(frame, text=label_text, width=22).pack(side='left')
            ttk.Entry(frame, textvariable=var, state='readonly').pack(side='left', expand=True, fill='x', padx=5)
            
            ttk.Button(frame, text="Buscar", 
                       command=lambda v=var: self.seleccionar_archivo(v, [("Archivos Excel", "*.xlsx")])
                      ).pack(side='left', padx=2)
            
            ttk.Button(frame, text="Subir a BD", 
                       command=lambda t=tipo, v=var: self.iniciar_carga_hilo(t, v)
                      ).pack(side='left', padx=2)

        self.frame_carga_admin = ttk.Frame(self.tab_admin)
        self.frame_carga_admin.pack(fill='x', padx=10, pady=20)
        
        self.lbl_estado = ttk.Label(self.frame_carga_admin, text="", foreground="blue", font=("Arial", 10, "italic"))
        self.lbl_estado.pack()
        
        self.progress_admin = ttk.Progressbar(self.frame_carga_admin, mode='indeterminate')
        self.progress_admin.pack_forget() 

    def iniciar_carga_hilo(self, tipo, var_ruta):
        ruta = var_ruta.get()
        if not ruta:
            messagebox.showwarning("Archivo faltante", "Por favor selecciona un archivo primero.")
            return
        if not LOGICA_DISPONIBLE: return

        self.lbl_estado.config(text=f"Procesando tabla de {tipo}. Por favor, espera...")
        self.progress_admin.pack(fill='x', padx=20, pady=5) 
        self.progress_admin.start(15) 
        
        hilo = threading.Thread(target=self._tarea_carga, args=(tipo, ruta))
        hilo.start()
        self.root.after(100, self._chequear_hilo_admin, hilo, tipo)

    def _tarea_carga(self, tipo, ruta):
        if tipo == "placas": self.resultado_carga = actualizar_placas(ruta)
        elif tipo == "vin": self.resultado_carga = actualizar_vin(ruta)
        elif tipo == "ordenes": self.resultado_carga = actualizar_ordenes(ruta)

    def _chequear_hilo_admin(self, hilo, tipo):
        if hilo.is_alive():
            self.root.after(100, self._chequear_hilo_admin, hilo, tipo)
        else:
            self.progress_admin.stop()
            self.progress_admin.pack_forget()
            self.lbl_estado.config(text="")
            if self.resultado_carga:
                messagebox.showinfo("Éxito", f"¡Tabla de {tipo} actualizada correctamente!")
            else:
                messagebox.showerror("Error", f"Hubo un problema al procesar el archivo de {tipo}.")

    # ==========================================
    # INTERFAZ: MÓDULO USUARIO (ACTUALIZADO)
    # ==========================================
    def construir_tab_user(self):
        ttk.Label(self.tab_user, text="Procesamiento de Negocio (Filtros y Cruces)", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.ruta_excel_usr = tk.StringVar()
        
        # Fila para buscar la Plantilla del Usuario
        frame_ex = ttk.Frame(self.tab_user)
        frame_ex.pack(fill='x', padx=20, pady=10)
        ttk.Label(frame_ex, text="Tu Plantilla (.xlsx):", width=18).pack(side='left')
        ttk.Entry(frame_ex, textvariable=self.ruta_excel_usr, state='readonly').pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(frame_ex, text="Buscar", 
                   command=lambda: self.seleccionar_archivo(self.ruta_excel_usr, [("Archivos Excel", "*.xlsx")])
                  ).pack(side='right')

        # Contenedor de Fechas
        frame_f = ttk.Frame(self.tab_user)
        frame_f.pack(fill='x', padx=20, pady=15)
        
        self.fecha_ini = tk.StringVar(value="01.01.2026")
        self.fecha_fin = tk.StringVar(value="31.12.2026")
        
        ttk.Label(frame_f, text="Fecha Inicio (DD.MM.YYYY):").pack(side='left')
        ttk.Entry(frame_f, textvariable=self.fecha_ini, width=12).pack(side='left', padx=5)
        
        ttk.Label(frame_f, text="Fecha Fin (DD.MM.YYYY):").pack(side='left', padx=(20,0))
        ttk.Entry(frame_f, textvariable=self.fecha_fin, width=12).pack(side='left', padx=5)

        # Botón de ejecución principal
        ttk.Button(self.tab_user, text="Ejecutar Cruce y Generar Excel", command=self.iniciar_proceso_usuario_hilo).pack(pady=20)

        # Contenedor de Indicadores de Carga del Usuario
        self.frame_carga_user = ttk.Frame(self.tab_user)
        self.frame_carga_user.pack(fill='x', padx=20, pady=10)
        
        self.lbl_estado_user = ttk.Label(self.frame_carga_user, text="", foreground="green", font=("Arial", 10, "italic"))
        self.lbl_estado_user.pack()
        
        self.progress_user = ttk.Progressbar(self.frame_carga_user, mode='indeterminate')
        self.progress_user.pack_forget()

    def iniciar_proceso_usuario_hilo(self):
        """Inicia el cruce de negocio en un hilo secundario para evitar congelar la GUI."""
        ruta = self.ruta_excel_usr.get()
        f_inicio = self.fecha_ini.get()
        f_fin = self.fecha_fin.get()
        
        if not ruta:
            messagebox.showwarning("Advertencia", "Debes seleccionar un archivo Excel de entrada primero.")
            return
        if not LOGICA_DISPONIBLE: return

        # Mostrar indicadores visuales
        self.lbl_estado_user.config(text="Cruzando información con Base de Datos y generando reporte...")
        self.progress_user.pack(fill='x', padx=20, pady=5)
        self.progress_user.start(15)

        # Desplegar tarea en fondo
        hilo_user = threading.Thread(target=self._tarea_usuario, args=(ruta, f_inicio, f_fin))
        hilo_user.start()
        
        # Monitorear estado del hilo
        self.root.after(100, self._chequear_hilo_user, hilo_user)

    def _tarea_usuario(self, ruta, f_inicio, f_fin):
        """Ejecuta la lógica de bases de datos de forma asíncrona."""
        self.resultado_user_ruta = procesar_logica_usuario(ruta, f_inicio, f_fin)

    def _chequear_hilo_user(self, hilo):
        """Monitorea el hilo de negocio y muestra los resultados al finalizar."""
        if hilo.is_alive():
            self.root.after(100, self._chequear_hilo_user, hilo)
        else:
            # Detener y ocultar indicadores
            self.progress_user.stop()
            self.progress_user.pack_forget()
            self.lbl_estado_user.config(text="")
            
            if self.resultado_user_ruta:
                messagebox.showinfo("Éxito", f"Reporte generado con éxito.\nGuardado en:\n{self.resultado_user_ruta}")
            else:
                messagebox.showerror("Error", "Ocurrió un error al procesar el reporte.\nAsegúrate de que las tablas maestras ya contengan información.")

    # ==========================================
    # INTERFAZ: VALIDACIÓN PLACAS
    # ==========================================
    def construir_tab_validacion(self):
        ttk.Label(
            self.tab_validacion,
            text="Validación de Placas SAP",
            font=("Arial", 12, "bold")
        ).pack(pady=15)

        ttk.Label(
            self.tab_validacion,
            text=(
                "Valida automáticamente si las placas:\n"
                "- Existen\n"
                "- Están duplicadas\n"
                "- Faltan crear"
            ),
            justify="center"
        ).pack(pady=5)

        # ==========================================
        # VARIABLE RUTA
        # ==========================================
        self.ruta_validacion = tk.StringVar()

        # ==========================================
        # FRAME ARCHIVO
        # ==========================================
        frame_archivo = ttk.Frame(self.tab_validacion)

        frame_archivo.pack(
            fill='x',
            padx=20,
            pady=20
        )

        ttk.Label(
            frame_archivo,
            text="Archivo Excel:",
            width=15
        ).pack(side='left')

        ttk.Entry(
            frame_archivo,
            textvariable=self.ruta_validacion,
            state='readonly'
        ).pack(
            side='left',
            expand=True,
            fill='x',
            padx=5
        )

        ttk.Button(
            frame_archivo,
            text="Buscar",
            command=lambda: self.seleccionar_archivo(
                self.ruta_validacion,
                [("Archivos Excel", "*.xlsx")]
            )
        ).pack(side='left')

        # ==========================================
        # BOTÓN PRINCIPAL
        # ==========================================
        ttk.Button(
            self.tab_validacion,
            text="Validar Placas",
            command=self.iniciar_validacion_hilo
        ).pack(pady=20)

        # ==========================================
        # ESTADO
        # ==========================================
        self.frame_validacion = ttk.Frame(
            self.tab_validacion
        )

        self.frame_validacion.pack(
            fill='x',
            padx=20,
            pady=10
        )

        self.lbl_estado_validacion = ttk.Label(
            self.frame_validacion,
            text="",
            foreground="green",
            font=("Arial", 10, "italic")
        )

        self.lbl_estado_validacion.pack()

        self.progress_validacion = ttk.Progressbar(
            self.frame_validacion,
            mode='indeterminate'
        )

        self.progress_validacion.pack_forget()

    def iniciar_validacion_hilo(self):

        ruta = self.ruta_validacion.get()

        if not ruta:
            messagebox.showwarning(
                "Advertencia",
                "Debes seleccionar un archivo Excel."
            )
            return

        self.lbl_estado_validacion.config(
            text="Validando placas..."
        )

        self.progress_validacion.pack(
            fill='x',
            padx=20,
            pady=5
        )

        self.progress_validacion.start(15)

        hilo = threading.Thread(
            target=self._tarea_validacion,
            args=(ruta,)
        )

        hilo.start()

        self.root.after(
            100,
            self._chequear_hilo_validacion,
            hilo
        )

    def _tarea_validacion(self, ruta):

        self.resultado_validacion = validar_placas_usuario(ruta)

    def _chequear_hilo_validacion(self, hilo):

        if hilo.is_alive():

            self.root.after(
                100,
                self._chequear_hilo_validacion,
                hilo
            )

        else:

            self.progress_validacion.stop()

            self.progress_validacion.pack_forget()

            self.lbl_estado_validacion.config(text="")

            if self.resultado_validacion:

                messagebox.showinfo(
                    "Proceso completado",
                    f"Archivo generado:\n\n{self.resultado_validacion}"
                )

            else:

                messagebox.showerror(
                    "Error",
                    "Ocurrió un error durante la validación."
                )


if __name__ == "__main__":
    root = tk.Tk()
    app = AppSAP(root)
    root.mainloop()