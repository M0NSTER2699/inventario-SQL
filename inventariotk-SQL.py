import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import tkinter.messagebox as messagebox
import datetime
import hashlib
import json
import shutil
import os
from PIL import Image, ImageTk
import tkinter.simpledialog as simpledialog

import csv
from tkinter import filedialog, messagebox
from tkcalendar import Calendar

from PIL import Image as pilimage


from fpdf import FPDF
import uuid

import mysql.connector

def conectar_mysql():
    try:
        mydb = mysql.connector.connect(
            host="127.0.0.1",       # Reemplaza con tu host de MySQL
            user="root",     # Reemplaza con tu usuario de MySQL
            password="", # Reemplaza con tu contraseña de MySQL
            database="sistema inventario corpoandes" # Reemplaza con el nombre de tu base de datos
        )
        return mydb
    except mysql.connector.Error as err:
        print(f"Error al conectar a MySQL: {err}")
        return None




inventario = {}
usuarios = {"admin": hashlib.sha256("admin".encode()).hexdigest()}  # Usuario administrador predeterminado
clave_admin = hashlib.sha256("NEVA".encode()).hexdigest()
salidas_departamentos = []
entradas_departamentos=[]
salidas_espera=[]
datos_consumo_para_guardar = []
datos_reportes_para_guardar = {
    "Bajo Stock": [],
    "Entradas": [],
    "Salidas": [],
    "Salidas en Espera": []}

#funciones de inicio de sesion




def guardar_datos():
    """Guarda los datos en un archivo JSON."""
    global datos_consumo_para_guardar, datos_reportes_para_guardar, usuarios, entradas_departamentos # Asegúrate de incluir entradas_departamentos

    # Actualiza datos_reportes_para_guardar["Entradas"] antes de guardar
    datos_reportes_para_guardar["Entradas"] = [
        {
            "Código": entrada.get("Código", "N/A"),
            "Producto": entrada.get("Producto", "N/A"),
            "Cantidad": entrada.get("Cantidad", "N/A"),
            "Fecha": entrada.get("Fecha", "N/A").isoformat() if isinstance(entrada.get("Fecha"), datetime.date) else str(entrada.get("Fecha", "N/A")),
            "Destino": entrada.get("Destino", "N/A")
        }
        for entrada in entradas_departamentos
    ]
    # Actualiza datos_reportes_para_guardar["Salidas en Espera"]
    datos_reportes_para_guardar["Salidas en Espera"] = [
        {
            "código": salida.get("código", "N/A"),  
            "producto": salida.get("producto", "N/A"),
            "cantidad": salida.get("cantidad", "N/A"),
            "departamento": salida.get("departamento", "N/A")
        }
        for salida in salidas_espera
    ]

    datos = {
        "inventario": {
            producto: {
                **datos_prod,
                "fecha_entrada": datos_prod["fecha_entrada"].isoformat() if isinstance(datos_prod["fecha_entrada"], datetime.date) else None if datos_prod["fecha_entrada"] is None or str(datos_prod["fecha_entrada"]).lower() == "null" or str(datos_prod["fecha_entrada"]).lower() == "none" else str(datos_prod["fecha_entrada"]),
                "fecha_salida": datos_prod["fecha_salida"].isoformat() if isinstance(datos_prod["fecha_salida"], datetime.date) else None if datos_prod["fecha_salida"] is None or str(datos_prod["fecha_salida"]).lower() == "null" or str(datos_prod["fecha_salida"]).lower() == "none" else str(datos_prod["fecha_salida"])
            }
            for producto, datos_prod in inventario.items()
        },
        "usuarios": usuarios,
        "salidas_departamentos": salidas_departamentos,
        "Reportes": datos_reportes_para_guardar
    }
    try:
        with open("inventario.json", "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=4)
        messagebox.showinfo("Guardado", "Datos guardados correctamente.")
    except IOError as e:
        messagebox.showerror("Error", f"Error de entrada/salida: {e}")
    except TypeError as e:
        messagebox.showerror("Error", f"Error de tipo de datos: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado: {e}")

def cargar_datos():
    """Carga los datos desde un archivo JSON y los inserta en MySQL."""
    global inventario, usuarios, salidas_departamentos, datos_consumo_para_guardar, datos_reportes_para_guardar, entradas_departamentos, salidas_espera

    datos_consumo_para_guardar = []
    archivo_existe = True
    try:
        with open("inventario.json", "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            inventario = {}
            for codigo_producto, datos_producto in datos.get("inventario", {}).items():
                fecha_entrada = datos_producto.get("fecha_entrada")
                fecha_salida = datos_producto.get("fecha_salida")
                fecha_entrada = datetime.date.fromisoformat(fecha_entrada) if fecha_entrada and fecha_entrada != "null" and fecha_entrada != "None" else None
                fecha_salida = datetime.date.fromisoformat(fecha_salida) if fecha_salida and fecha_salida != "null" and fecha_salida != "None" else None
                inventario[codigo_producto] = {**datos_producto, "fecha_entrada": fecha_entrada, "fecha_salida": fecha_salida}
            usuarios = datos.get("usuarios", {})
            salidas_departamentos = datos.get("salidas_departamentos", [])
            datos_consumo_para_guardar = datos.get("Consumo", [])
            reportes = datos.get("Reportes", {"Bajo Stock": [], "Entradas": [], "Salidas": [], "Salidas en Espera": []})
            datos_reportes_para_guardar = {"Bajo Stock": reportes.get("Bajo Stock", []), "Entradas": reportes.get("Entradas", []), "Salidas": reportes.get("Salidas", []), "Salidas en Espera": reportes.get("Salidas en Espera", []), "Consumo": datos_consumo_para_guardar}
            entradas_departamentos = datos_reportes_para_guardar.get("Entradas", [])
            for entrada in entradas_departamentos:
                fecha_str = entrada.get("Fecha")
                if isinstance(fecha_str, str) and fecha_str != "N/A":
                    try:
                        entrada["Fecha"] = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    except ValueError:
                        print(f"Error al convertir fecha: {fecha_str}")
                        entrada["Fecha"] = "N/A"
            salidas_espera_cargadas = datos_reportes_para_guardar.get("Salidas en Espera", [])
            nuevas_salidas_espera = []
            for salida in salidas_espera_cargadas:
                if "código" in salida:
                    salida["Código"] = salida.pop("código")
                nuevas_salidas_espera.append(salida)
            salidas_espera = nuevas_salidas_espera

            # Insertar datos en MySQL al cargar (solo la primera vez o cuando sea necesario)
            insertar_inventario_mysql(inventario)

    except FileNotFoundError:
        archivo_existe = False
        messagebox.showinfo("Cargar Datos", "No se encontró el archivo inventario.json. Se creará uno nuevo.")
        inventario = {}
        usuarios = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        salidas_departamentos = []
        datos_consumo_para_guardar = []
        datos_reportes_para_guardar = {"Bajo Stock": [], "Entradas": [], "Salidas": [], "Salidas en Espera": []}
        entradas_departamentos = []
        salidas_espera = []
    except json.JSONDecodeError:
        messagebox.showerror("Error", "No se pudieron cargar los datos: El archivo JSON está corrupto.")
        inventario = {}
        usuarios = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        salidas_departamentos = []
        datos_consumo_para_guardar = []
        datos_reportes_para_guardar = {"Bajo Stock": [], "Entradas": [], "Salidas": [], "Salidas en Espera": []}
        entradas_departamentos = []
        salidas_espera = []
    except ValueError as e:
        messagebox.showerror("Error", f"No se pudieron cargar los datos: {e}")
        inventario = {}
        usuarios = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        salidas_departamentos = []
        datos_consumo_para_guardar = []
        datos_reportes_para_guardar = {"Bajo Stock": [], "Entradas": [], "Salidas": [], "Salidas en Espera": []}
        entradas_departamentos = []
        salidas_espera = []
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado al cargar los datos: {e}")
        inventario = {}
        usuarios = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        salidas_departamentos = []
        datos_consumo_para_guardar = []
        datos_reportes_para_guardar = {"Bajo Stock": [], "Entradas": [], "Salidas": [], "Salidas en Espera": []}
        entradas_departamentos = []
        salidas_espera = []
    finally:
        if not archivo_existe or not usuarios:
            usuarios["admin"] = hashlib.sha256("admin".encode()).hexdigest()
            guardar_datos() # Asegúrate de que esta función también se adapte a MySQL eventualmente
    
# Insertar usuarios iniciales en MySQL
    insertar_usuarios_mysql(usuarios)

def insertar_usuarios_mysql(usuarios_dict):
    mydb = conectar_mysql()
    if mydb is None:
        return

    cursor = mydb.cursor()
    sql_insert = "INSERT INTO usuarios (NombreUsuario, ContrasenaHash, EsAdmin) VALUES (%s, %s, %s)"
    sql_check = "SELECT NombreUsuario FROM usuarios WHERE NombreUsuario = %s"

    for nombre_usuario, contrasena_hash in usuarios_dict.items():
        cursor.execute(sql_check, (nombre_usuario,))
        if cursor.fetchone() is None:  # Si no existe un usuario con este nombre
            es_admin = 1 if nombre_usuario == "admin" else 0
            val = (nombre_usuario, contrasena_hash, es_admin)
            try:
                cursor.execute(sql_insert, val)
            except mysql.connector.Error as err:
                print(f"Error al insertar usuario {nombre_usuario}: {err}")

    mydb.commit()
    cursor.close()
    mydb.close()
    print("Proceso de inserción de usuarios en MySQL completado (se omitieron duplicados).")

def insertar_inventario_mysql(inventario):
    mydb = conectar_mysql()
    if mydb is None:
        return

    cursor = mydb.cursor()
    sql_insert = "INSERT INTO productos (Codigo, Nombre, Categoria, Stock, UnidadMedida, FechaEntrada, FechaSalida, Departamento) VALUES (%s, %s, %s, %s, %s, %s, %s,%s)"
    sql_check = "SELECT Codigo FROM productos WHERE Codigo = %s"

    for codigo, datos_producto in inventario.items():
        cursor.execute(sql_check, (codigo,))
        if cursor.fetchone() is None:  # Si no existe un producto con este código
            val = (
                codigo,
                datos_producto.get('nombre'),
                datos_producto.get('categoria'),
                datos_producto.get('stock'),
                datos_producto.get('unidad_medida'),
                datos_producto.get('fecha_entrada'),
                datos_producto.get('fecha_salida'),
                datos_producto.get('departamento')
            )
            try:
                cursor.execute(sql_insert, val)
            except mysql.connector.Error as err:
                print(f"Error al insertar producto {codigo}: {err}")

    mydb.commit()
    cursor.close()
    mydb.close()
    print("Proceso de inserción del inventario en MySQL completado (se omitieron duplicados).")
        

def verificar_clave(ventana_clave, entry_clave, ventana_login):
    clave_ingresada = hashlib.sha256(entry_clave.get().encode()).hexdigest()
    if clave_ingresada == clave_admin:
        messagebox.showinfo("Acceso Permitido", "Acceso de administrador concedido.")
        ventana_clave.destroy()
        ventana_login.destroy()
        mostrar_menu()
    else:
        messagebox.showerror("Acceso Denegado", "Clave incorrecta.")

def iniciar_sesion():
    """Permite al usuario iniciar sesión."""
    global ventana_login,usuarios

    ventana_login = tk.Tk() # Creación de la ventana principal de login
    ventana_login.title("Login")
    ventana_login.configure(bg="#263238")

    style = ttk.Style(ventana_login)
    style.theme_use('clam')
    style.configure("TLabel", foreground="#eceff1", background="#263238", font=("Arial", 14))
    style.configure("TEntry", fieldbackground="#f0f0f0", foreground="black", font=("Arial", 14))
    style.configure("TButton", foreground="#eceff1", background="#008000", font=("Arial", 14, "bold"))
    style.configure("TCheckbutton", foreground="#eceff1", background="#263238", font=("Arial", 14))

    frame_contenido = tk.Frame(ventana_login, bg="#263238")
    frame_contenido.pack(padx=20, pady=20, fill="both", expand=True)

    frame_logo = tk.Frame(frame_contenido, bg="#263238")
    frame_logo.pack(side="left", padx=20, pady=20, fill="both", expand=True)

    try:
        imagen_logo = Image.open("C:/Users/monster/Desktop/src/server/routes/imagenes/logo.png")
        imagen_logo = imagen_logo.resize((300, 300))
        logo = ImageTk.PhotoImage(imagen_logo)
        label_logo = tk.Label(frame_logo, image=logo, bg="#263238")
        label_logo.image = logo
        label_logo.pack(fill="both", expand=True)
    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró el archivo del logo.")

    frame_campos = tk.Frame(frame_contenido, bg="#263238")
    frame_campos.pack(side="right", padx=20, pady=20, fill="both", expand=True)
    frame_campos.grid_columnconfigure(1, weight=1)
    frame_campos.grid_rowconfigure(0, weight=1)
    frame_campos.grid_rowconfigure(1, weight=1)
    frame_campos.grid_rowconfigure(2, weight=1)
    frame_campos.grid_rowconfigure(3, weight=1)

    ttk.Label(frame_campos, text="Usuario:", background="#263238", foreground="#eceff1").grid(row=0, column=0, pady=5, sticky="e")
    entry_nombre = ttk.Entry(frame_campos, width=30)
    entry_nombre.grid(row=0, column=1, pady=5, sticky="ew")

    ttk.Label(frame_campos, text="Contraseña:", background="#263238", foreground="#eceff1").grid(row=1, column=0, pady=5, sticky="e")
    entry_contrasena = ttk.Entry(frame_campos, show="*", width=30)
    entry_contrasena.grid(row=1, column=1, pady=5, sticky="ew")

    var_admin = tk.IntVar()
    check_admin = ttk.Checkbutton(frame_campos, text="Administrador", variable=var_admin)
    check_admin.grid(row=2, column=0, columnspan=2, pady=5, sticky="w")

    def iniciar():
        nombre_usuario = entry_nombre.get()
        contrasena = entry_contrasena.get()
        contrasena_hash_ingresada = hashlib.sha256(contrasena.encode()).hexdigest()
        es_admin_seleccionado = var_admin.get()

        mydb = conectar_mysql()
        if mydb is None:
            return

        cursor = mydb.cursor()
        query = "SELECT ContrasenaHash, EsAdmin FROM usuarios WHERE NombreUsuario = %s"

        try:
            cursor.execute(query, (nombre_usuario,))
            resultado = cursor.fetchone()

            if resultado:
                contrasena_hash_db, es_admin_db = resultado

                if contrasena_hash_ingresada == contrasena_hash_db:
                    if es_admin_seleccionado and es_admin_db:
                        ventana_clave = tk.Toplevel(ventana_login)
                        ventana_clave.title("Clave de Administrador")
                        ventana_clave.configure(bg="#263238")

                        style_clave = ttk.Style(ventana_clave)
                        style_clave.theme_use('clam')
                        style_clave.configure("TLabel", foreground="#eceff1", background="#263238", font=("Arial", 14))
                        style_clave.configure("TEntry", fieldbackground="#f0f0f0", foreground="black", font=("Arial", 14))
                        style_clave.configure("TButton", foreground="#eceff1", background="#008000", font=("Arial", 14, "bold"))
                        style_clave.configure("TCheckbutton", foreground="#eceff1", background="#263238", font=("Arial", 14))

                        ttk.Label(ventana_clave, text="Clave:", background="#263238", foreground="#eceff1", font=("Arial", 14)).pack(pady=5)
                        entry_clave_admin_local = ttk.Entry(ventana_clave, show="*", font=("Arial", 14), width=20) # Definir aquí
                        entry_clave_admin_local.pack(pady=5)

                        ttk.Button(ventana_clave, text="Verificar", command=lambda: verificar_clave(ventana_clave, entry_clave_admin_local, ventana_login), style="TButton").pack(pady=10) # Pasar la referencia local
                    elif not es_admin_seleccionado and not es_admin_db:
                        ventana_login.destroy()
                        mostrar_menu()
                    elif es_admin_seleccionado and not es_admin_db:
                        messagebox.showerror("Error", "Este usuario no tiene permisos de administrador.")
                    elif not es_admin_seleccionado and es_admin_db:
                        messagebox.showerror("Error", "Debe marcar la casilla de 'Administrador' para este usuario.")
                else:
                    messagebox.showerror("Error", "Contraseña incorrecta.")
            else:
                messagebox.showerror("Error", "Usuario no encontrado.")

        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al consultar la base de datos: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

    ttk.Button(frame_campos, text="Iniciar Sesión", command=iniciar, style="TButton").grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
    ventana_login.mainloop() 



def abrir_calendario(ventana_padre, entry_fecha):
    """Abre una ventana con un calendario y actualiza el campo de fecha."""
    def seleccionar_fecha():
        fecha = cal.get_date()
        entry_fecha.delete(0, tk.END)
        entry_fecha.insert(0, fecha)
        ventana_calendario.destroy()

    ventana_calendario = tk.Toplevel(ventana_padre)
    ventana_calendario.title("Seleccionar Fecha")
    cal = Calendar(ventana_calendario, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.pack(padx=10, pady=10)
    ttk.Button(ventana_calendario, text="Seleccionar", command=seleccionar_fecha).pack(pady=5)
















    
    
                                            #funciones principales:
       
def agregar_producto():
    """Agrega un producto al inventario con fecha de entrada manual y código basado en la categoría."""

    def generar_codigo(categoria):
        """Genera un código único basado en la categoría consultando MySQL."""
        prefijos_categoria = {
            "COMIDA": "COM",
            "MATERIALES Y ARTICULOS DE OFICINA": "MAT",
            "TONNER": "TON",
            "MATERIAL DE LIMPIEZA": "LIM",
            "PLASTICO": "PLA",
            "MATERIAL DE FERRETERIA": "FER",
            "OTROS": "OTR"
            # Añade aquí más categorías y sus prefijos según necesites
        }
        prefijo = prefijos_categoria.get(categoria.upper(), "GEN")

        mydb = conectar_mysql()
        if not mydb:
            return f"{prefijo}-001"  # Si no hay conexión, genera un código básico

        cursor = mydb.cursor()
        query = """
            SELECT Codigo
            FROM productos
            WHERE Categoria = %s AND Codigo LIKE %s
            ORDER BY Codigo DESC
            LIMIT 1
        """
        try:
            cursor.execute(query, (categoria.upper(), f"{prefijo}-%"))
            ultimo_codigo = cursor.fetchone()
        except mysql.connector.Error as err:
            messagebox.showerror("Error al generar código", f"Error: {err}")
            ultimo_codigo = None
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

        if ultimo_codigo:
            try:
                ultimo_numero = int(ultimo_codigo[0].split("-")[1])
                return f"{prefijo}-{ultimo_numero + 1:03d}"
            except (IndexError, ValueError):
                return f"{prefijo}-001"
        else:
            return f"{prefijo}-001"

    def agregar():
        producto_nombre = entry_producto.get()
        categoria = categoria_var.get()
        destino_entrada = entry_destino_entrada.get()
        entrada_cantidad = int(entry_entrada.get())
        unidad_medida = unidad_medida_var.get()
        fecha_str = entry_fecha_entrada.get()
        try:
            fecha_entrada = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error de Fecha", "Formato de fecha incorrecto (YYYY-MM-DD).")
            return
        codigo_producto = generar_codigo(categoria)

        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        sql_producto = """
            INSERT INTO productos (Codigo, Nombre, Categoria, Stock, UnidadMedida, FechaEntrada, Departamento)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        val_producto = (codigo_producto, producto_nombre, categoria, entrada_cantidad, unidad_medida, fecha_entrada, destino_entrada) # Usamos destino como departamento inicial

        try:
            cursor.execute(sql_producto, val_producto)
            producto_id = cursor.lastrowid  # <--- CORRECCIÓN: Usar cursor.lastrowid

            sql_entrada = """
                INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, FechaEntrada, Destino)
                VALUES (%s, %s, %s, %s, %s)
            """
            val_entrada = (producto_id, codigo_producto, entrada_cantidad, fecha_entrada, destino_entrada)
            cursor.execute(sql_entrada, val_entrada)

            mydb.commit()
            messagebox.showinfo("Producto Agregado", f"Producto '{producto_nombre}' agregado al inventario con código: {codigo_producto}, Fecha de entrada: {fecha_entrada}")
            ventana_agregar.destroy()

        except mysql.connector.Error as err:
            mydb.rollback()
            messagebox.showerror("Error al agregar producto", f"Error: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

    def agregar_nueva_categoria():
        def guardar_nueva():
            nueva_cat = nueva_categoria_entry.get().strip().upper()
            if nueva_cat and nueva_cat not in categorias_list:
                categorias_list.insert(len(categorias_list) - 1, nueva_cat) # Insertar antes de "Añadir nueva"
                categorias_var.set(categorias_list)
                combo_categoria['values'] = categorias_list
                categoria_var.set(nueva_cat) # Establecer la nueva categoría como seleccionada
                ventana_nueva_categoria.destroy()
            else:
                messagebox.showerror("Error", "Por favor, ingrese una categoría válida que no exista.")

        ventana_nueva_categoria = tk.Toplevel(ventana_agregar)
        ventana_nueva_categoria.title("Nueva Categoría")
        ttk.Label(ventana_nueva_categoria, text="Ingrese la nueva categoría:", style="CustomLabel.TLabel").pack(padx=10, pady=10)
        nueva_categoria_entry = ttk.Entry(ventana_nueva_categoria, style="CustomEntry.TEntry")
        nueva_categoria_entry.pack(padx=10, pady=5)
        ttk.Button(ventana_nueva_categoria, text="Guardar", command=guardar_nueva, style="CustomButton.TButton").pack(pady=10)

    def agregar_nueva_unidad():
        def guardar_nueva_unidad():
            nueva_unidad = nueva_unidad_entry.get().strip()
            if nueva_unidad and nueva_unidad not in unidades_list:
                unidades_list.insert(len(unidades_list) - 1, nueva_unidad) # Insertar antes de "Añadir nueva"
                unidades_medida_var.set(unidades_list)
                combo_unidad_medida['values'] = unidades_list
                unidad_medida_var.set(nueva_unidad) # Establecer la nueva unidad como seleccionada
                ventana_nueva_unidad.destroy()
            else:
                messagebox.showerror("Error", "Por favor, ingrese una unidad de medida válida que no exista.")

        ventana_nueva_unidad = tk.Toplevel(ventana_agregar)
        ventana_nueva_unidad.title("Nueva Unidad de Medida")
        ttk.Label(ventana_nueva_unidad, text="Ingrese la nueva unidad de medida:", style="CustomLabel.TLabel").pack(padx=10, pady=10)
        nueva_unidad_entry = ttk.Entry(ventana_nueva_unidad, style="CustomEntry.TEntry")
        nueva_unidad_entry.pack(padx=10, pady=5)
        ttk.Button(ventana_nueva_unidad, text="Guardar", command=guardar_nueva_unidad, style="CustomButton.TButton").pack(pady=10)

    def mostrar_opciones_categoria(event):
        if categoria_var.get() == "Añadir nueva":
            agregar_nueva_categoria()
            categoria_var.set(categorias_list[0] if categorias_list and categorias_list[-1] == "Añadir nueva" else "") # Resetear la selección

    def mostrar_opciones_unidad(event):
        if unidad_medida_var.get() == "Añadir nueva":
            agregar_nueva_unidad()
            unidad_medida_var.set(unidades_list[0] if unidades_list and unidades_list[-1] == "Añadir nueva" else "") # Resetear la selección

    ventana_agregar = tk.Toplevel(ventana)
    ventana_agregar.title("Agregar Producto")
    ventana_agregar.configure(bg="#000080")

    # Listas predeterminadas
    categorias_predeterminadas = ["COMIDA", "MATERIALES Y ARTICULOS DE OFICINA", "TONNER", "MATERIAL DE LIMPIEZA", "PLASTICO", "MATERIAL DE FERRETERIA", "OTROS", "Añadir nueva"]
    unidades_medida_predeterminadas = ["Unidad", "Litro", "Kilogramo", "Metro", "Caja", "Paquete", "Añadir nueva"]

    # Variables para los Combobox
    categorias_var = tk.StringVar()
    unidades_medida_var = tk.StringVar()
    categoria_var = tk.StringVar()
    unidad_medida_var = tk.StringVar()
    categorias_list = sorted(categorias_predeterminadas)
    unidades_list = sorted(unidades_medida_predeterminadas)
    categorias_var.set(categorias_list[0] if categorias_list else "")
    unidades_medida_var.set(unidades_list[0] if unidades_list else "")

    def abrir_calendario_local():
        abrir_calendario(ventana_agregar, entry_fecha_entrada)

    style = ttk.Style(ventana_agregar)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#000080", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomButton.TButton", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"), padding=8, relief="raised", anchor="center")
    style.map("CustomButton.TButton", background=[('active', '#c1c1c1')], foreground=[('active', '#000000')])

    ttk.Label(ventana_agregar, text="Nombre del producto:", style="CustomLabel.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=10)
    entry_producto = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_producto.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(ventana_agregar, text="Categoría del producto:", style="CustomLabel.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=10)
    combo_categoria = ttk.Combobox(ventana_agregar, textvariable=categoria_var, values=categorias_list, style="TCombobox")
    combo_categoria.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
    combo_categoria.bind("<<ComboboxSelected>>", mostrar_opciones_categoria)

    ttk.Label(ventana_agregar, text="Destino de entrada:", style="CustomLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=10)
    entry_destino_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_destino_entrada.insert(0, "Almacén principal")
    entry_destino_entrada.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(ventana_agregar, text="Cantidad de entrada:", style="CustomLabel.TLabel").grid(row=3, column=0, sticky="w", padx=10, pady=10)
    entry_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_entrada.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(ventana_agregar, text="Unidad de medida:", style="CustomLabel.TLabel").grid(row=4, column=0, sticky="w", padx=10, pady=10)
    combo_unidad_medida = ttk.Combobox(ventana_agregar, textvariable=unidad_medida_var, values=unidades_list, style="TCombobox")
    combo_unidad_medida.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
    combo_unidad_medida.bind("<<ComboboxSelected>>", mostrar_opciones_unidad)

    ttk.Label(ventana_agregar, text="Fecha de entrada (YYYY-MM-DD):", style="CustomLabel.TLabel").grid(row=5, column=0, sticky="w", padx=10, pady=10)
    entry_fecha_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_fecha_entrada.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

    ttk.Button(ventana_agregar, text="Calendario", command=abrir_calendario_local, style="CustomButton.TButton").grid(row=5, column=2, padx=10, pady=10)
    ttk.Button(ventana_agregar, text="Agregar", command=agregar, style="CustomButton.TButton").grid(row=6, column=0, columnspan=3, pady=15, padx=10, sticky="ew")

    ventana_agregar.grid_columnconfigure(1, weight=1)
    
 


def realizar_salida():
    """Realiza una salida en espera de productos del inventario, permitiendo búsqueda por nombre o código."""

    def obtener_productos_con_codigo():
        """Obtiene la lista de productos (Nombre (Código)) desde la base de datos MySQL."""
        productos_con_codigo = []
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = "SELECT Nombre, Codigo, ProductoID FROM productos"  # Necesitamos el ProductoID para referenciar
            try:
                cursor.execute(query)
                productos_mysql = cursor.fetchall()
                for nombre, codigo, producto_id in productos_mysql:
                    productos_con_codigo.append(f"{nombre} ({codigo})")
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener productos: {err}")
            finally:
                cursor.close()
                mydb.close()
        return sorted(productos_con_codigo)

    def obtener_nombre_desde_seleccion(seleccion):
        """Extrae el nombre del producto de la string seleccionada en el Combobox."""
        if " (" in seleccion:
            return seleccion.split(" (")[0]
        return seleccion

    def obtener_codigo_desde_seleccion(seleccion):
        """Extrae el código del producto de la string seleccionada en el Combobox."""
        if " (" in seleccion and seleccion.endswith(")"):
            return seleccion.split(" (")[1][:-1]
        return None

    def salida_espera():
        """Agrega una solicitud de salida en espera a la base de datos MySQL."""
        departamento = departamento_var.get()
        seleccion_producto = combo_producto.get()
        cantidad = int(entry_cantidad.get())
        producto_nombre = obtener_nombre_desde_seleccion(seleccion_producto)
        codigo_producto = obtener_codigo_desde_seleccion(seleccion_producto)

        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        # Obtener el ProductoID basado en el código del producto seleccionado
        query_producto_id = "SELECT ProductoID FROM productos WHERE Codigo = %s"
        cursor.execute(query_producto_id, (codigo_producto,))
        resultado_id = cursor.fetchone()

        if resultado_id:
            producto_id = resultado_id[0]
            sql_insert_salida = """
                INSERT INTO salidas_espera (ProductoID, CodigoProducto, Cantidad, Departamento)
                VALUES (%s, %s, %s, %s)
            """
            val_salida = (producto_id, codigo_producto, cantidad, departamento)
            try:
                cursor.execute(sql_insert_salida, val_salida)
                mydb.commit()
                messagebox.showinfo("Salida en Espera", f"{cantidad} unidades de '{producto_nombre}' (código: {codigo_producto if codigo_producto else 'N/A'}) solicitadas para {departamento}. Agregado a la lista de espera.")
                ventana_salida_espera.destroy()
                # Ya no llamamos a guardar_datos() aquí, la información está en la base de datos
            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error al agregar salida en espera", f"Error: {err}")
            finally:
                cursor.close()
                mydb.close()
        else:
            messagebox.showerror("Error", f"No se encontró el producto con código: {codigo_producto}")

    ventana_salida_espera = tk.Toplevel(ventana)
    ventana_salida_espera.title("Salida en Espera")
    ventana_salida_espera.configure(bg="#000080")

    # --- Estilos ttk Personalizados ---
    style = ttk.Style(ventana_salida_espera)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#000080", font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomButton.TButton", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"), padding=8, relief="raised", anchor="center")
    style.map("CustomButton.TButton", background=[('active', '#c1c1c1')], foreground=[('active', '#000000')])

    # Obtener la lista de productos con su código para el Combobox
    productos_con_codigo = obtener_productos_con_codigo()

    ttk.Label(ventana_salida_espera, text="Nombre del producto (Código):", style="CustomLabel.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=10)
    combo_producto = ttk.Combobox(ventana_salida_espera, values=productos_con_codigo, style="TCombobox")
    combo_producto.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    # Función para filtrar la lista de productos por nombre o código
    def filtrar_productos(event):
        valor_escrito = combo_producto.get().lower()
        productos_filtrados = [
            pc
            for pc in productos_con_codigo
            if valor_escrito in pc.lower()
        ]
        combo_producto["values"] = productos_filtrados

    # Enlazar el evento de escritura al Combobox
    combo_producto.bind("<KeyRelease>", filtrar_productos)

    ttk.Label(ventana_salida_espera, text="Cantidad de salida:", style="CustomLabel.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=10)
    entry_cantidad = ttk.Entry(ventana_salida_espera, style="CustomEntry.TEntry")
    entry_cantidad.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    # Menú desplegable para seleccionar el departamento
    ttk.Label(ventana_salida_espera, text="Departamento:", style="CustomLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=10)
    departamentos = ["OTIC", "Oficina de Gestion Administrativa", "Oficina Contabilidad","Oficina Compras","Oficina de Bienes","Direccion de Servicios Generales y Transporte","Oficina de Seguimiento y Proyectos Estructurales","Direccion General de Planificacion Estrategica","Planoteca","Biblioteca","Direccion General de Seguimiento de Proyectos","Gestion Participativa Parque la isla","Oficina de Atencion ciudadana","Oficina de gestion Humana","Presidencia","Secretaria General","Consultoria Juridica","Oficina de Planificacion y Presupuesto","Auditoria","Direccion de informacion y Comunicacion","Direccion General de Formacion"]  # Reemplaza con tus departamentos
    departamentos.sort()
    departamento_var = tk.StringVar(ventana_salida_espera)
    departamento_var.set(departamentos[0])  # Valor predeterminado
    ttk.Combobox(ventana_salida_espera, textvariable=departamento_var, values=departamentos, style="TCombobox").grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    ttk.Button(ventana_salida_espera, text="Agregar a Salida en Espera", command=salida_espera, style="CustomButton.TButton").grid(row=3, column=0, columnspan=2, pady=15, padx=10, sticky="ew")

    ventana_salida_espera.grid_columnconfigure(1, weight=1)


   


def mostrar_inventario():
    """Muestra el inventario con menú desplegable de categorías y búsqueda por nombre o código dentro de la categoría."""

    ventana_inventario = tk.Toplevel(ventana)
    ventana_inventario.title("Inventario")
    ventana_inventario.geometry("1200x600")
    ventana_inventario.configure(bg="#A9A9A9")

    # --- Estilos ttk Personalizados ---
    style = ttk.Style(ventana_inventario)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomButton.TButton", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"), padding=8, relief="raised", anchor="center")
    style.map("CustomButton.TButton", background=[('active', '#c1c1c1')], foreground=[('active', '#000000')])
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    # Frame para los menús desplegables, totales y búsqueda
    frame_menu = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_menu.pack(pady=10, padx=10, fill=tk.X)

    # Frame para la búsqueda por texto
    frame_busqueda = tk.Frame(frame_menu, bg="#A9A9A9")
    frame_busqueda.pack(side=tk.LEFT, padx=10)

    ttk.Label(frame_busqueda, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda = ttk.Entry(frame_busqueda, style="CustomEntry.TEntry")
    entry_busqueda.pack(side=tk.LEFT)

    # Menú desplegable de categorías para mostrar
    categorias_mostrar = ["Todas"]
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        cursor.execute("SELECT DISTINCT Categoria FROM productos ORDER BY Categoria")
        categorias_db = [row[0] for row in cursor.fetchall()]
        categorias_mostrar.extend(categorias_db)
        cursor.close()
        mydb.close()
    categoria_seleccionada_mostrar = tk.StringVar(frame_menu)
    categoria_seleccionada_mostrar.set(categorias_mostrar[0])

    menu_categorias_mostrar = ttk.Combobox(frame_menu, textvariable=categoria_seleccionada_mostrar, values=categorias_mostrar, style="TCombobox")
    menu_categorias_mostrar.pack(side=tk.LEFT, padx=10)

    # Función para mostrar el inventario según la categoría seleccionada y el término de búsqueda
    def mostrar_inventario_filtrado(event=None):
        categoria = categoria_seleccionada_mostrar.get()
        termino_busqueda = entry_busqueda.get().lower()
        mostrar_tabla(categoria, termino_busqueda)

    # Enlazar el evento de selección de categoría y el evento de escritura en la búsqueda
    menu_categorias_mostrar.bind("<<ComboboxSelected>>", mostrar_inventario_filtrado)
    entry_busqueda.bind("<KeyRelease>", mostrar_inventario_filtrado)

    # Frame para la tabla de inventario
    frame_tabla = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Treeview (tabla)
    tabla_productos = ttk.Treeview(frame_tabla, columns=("Código", "Categoría", "Producto", "Destino Entrada", "Destino Salida", "Entrada", "Salida", "Stock", "Unidad Medida", "Fecha Entrada", "Fecha Salida"), show="headings", style="Grid.Treeview")
    tabla_productos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Definir encabezados de columna
    tabla_productos.heading("Código", text="Código", anchor=tk.W)
    tabla_productos.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla_productos.heading("Producto", text="Producto", anchor=tk.W)
    tabla_productos.heading("Destino Entrada", text="Destino Entrada", anchor=tk.W)
    tabla_productos.heading("Destino Salida", text="Destino Salida", anchor=tk.W)
    tabla_productos.heading("Entrada", text="Entrada", anchor=tk.E)
    tabla_productos.heading("Salida", text="Salida", anchor=tk.E)
    tabla_productos.heading("Stock", text="Stock", anchor=tk.E)
    tabla_productos.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla_productos.heading("Fecha Entrada", text="Fecha Entrada", anchor=tk.W)
    tabla_productos.heading("Fecha Salida", text="Fecha Salida", anchor=tk.W)

    # Configurar ancho de columnas
    tabla_productos.column("Código", width=150)
    tabla_productos.column("Categoría", width=120)
    tabla_productos.column("Producto", width=150)
    tabla_productos.column("Destino Entrada", width=150)
    tabla_productos.column("Destino Salida", width=150)
    tabla_productos.column("Entrada", width=80)
    tabla_productos.column("Salida", width=80)
    tabla_productos.column("Stock", width=80)
    tabla_productos.column("Unidad Medida", width=120)
    tabla_productos.column("Fecha Entrada", width=100)
    tabla_productos.column("Fecha Salida", width=100)

    # Agregar barra de desplazamiento vertical
    barra_desplazamiento = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla_productos.yview)
    tabla_productos.configure(yscrollcommand=barra_desplazamiento.set)
    barra_desplazamiento.pack(side=tk.RIGHT, fill=tk.Y)

    # Frame para los totales
    frame_totales = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_totales.pack(pady=10, padx=10, fill=tk.X)

    label_totales = ttk.Label(frame_totales, text="", style="CustomLabel.TLabel")
    label_totales.pack()

    def mostrar_tabla(categoria="Todas", termino_busqueda=""):
        tabla_productos.delete(*tabla_productos.get_children())
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = """
                SELECT Codigo, Categoria, Nombre, Departamento, '', Stock, UnidadMedida, FechaEntrada, ''
                FROM productos
            """
            conditions = []
            params = []

            if categoria != "Todas":
                conditions.append("Categoria = %s")
                params.append(categoria)

            if termino_busqueda:
                conditions.append("(Nombre LIKE %s OR Codigo LIKE %s)")
                params.extend([f"%{termino_busqueda}%", f"%{termino_busqueda}%"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            try:
                cursor.execute(query, params)
                productos_filtrados_db = cursor.fetchall()
                for codigo, categoria_prod, nombre, destino_entrada, _, stock, unidad_medida, fecha_entrada, _ in productos_filtrados_db:
                    tabla_productos.insert("", tk.END, values=(
                        codigo,
                        categoria_prod,
                        nombre,
                        destino_entrada,
                        "",  # Destino Salida (se llenará con otra lógica)
                        "",  # Entrada (se llenará con otra lógica)
                        "",  # Salida (se llenará con otra lógica)
                        stock,
                        unidad_medida,
                        fecha_entrada,
                        ""   # Fecha Salida (se llenará con otra lógica)
                    ))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al mostrar el inventario: {err}")
            finally:
                cursor.close()
                mydb.close()
        mostrar_totales(categoria) 

    

    def mostrar_totales(categoria):
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query_total = "SELECT COUNT(*) FROM productos"
            params_total = []

            if categoria != "Todas":
                query_total += " WHERE Categoria = %s"
                params_total.append(categoria)

            try:
                cursor.execute(query_total, params_total)
                total_productos = cursor.fetchone()[0]

                query_categorias = "SELECT COUNT(DISTINCT Categoria) FROM productos"
                cursor.execute(query_categorias)
                total_categorias = cursor.fetchone()[0]

                if categoria == "Todas":
                    label_totales.config(text=f"Total de productos: {total_productos}, Total de categorías: {total_categorias}", style="CustomLabel.TLabel")
                else:
                    label_totales.config(text=f"Total de productos en {categoria}: {total_productos}", style="CustomLabel.TLabel")

            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener los totales: {err}")
            finally:
                cursor.close()
                mydb.close()

    def realizar_entrada_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una entrada de productos desde el menú contextual usando el código del producto (actualizado para MySQL)."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.")
            return

        def confirmar_entrada():
            cantidad_str = entry_cantidad.get()
            fecha = entry_fecha.get()
            if not cantidad_str.isdigit():
                messagebox.showerror("Error", "La cantidad debe ser un número.")
                return
            cantidad = int(cantidad_str)

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                return

            cursor = mydb.cursor()

            try:
                # Actualizar el stock en la tabla productos
                sql_actualizar_stock = "UPDATE productos SET Stock = Stock + %s, FechaEntrada = %s WHERE Codigo = %s"
                val_actualizar_stock = (cantidad, fecha, codigo_producto_seleccionado)
                cursor.execute(sql_actualizar_stock, val_actualizar_stock)

                # Insertar un registro en la tabla entradas (opcional, si quieres historial)
                sql_insertar_entrada = "INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, FechaEntrada, Destino) SELECT ProductoID, Codigo, %s, %s, Departamento FROM productos WHERE Codigo = %s"
                val_insertar_entrada = (cantidad, fecha, codigo_producto_seleccionado)
                cursor.execute(sql_insertar_entrada, val_insertar_entrada)

                mydb.commit()
                mostrar_tabla(categoria_seleccionada_mostrar.get())
                messagebox.showinfo("Entrada Realizada", f"{cantidad} unidades de {nombre_producto} (Código: {codigo_producto_seleccionado}) entraron al inventario.")
                ventana_entrada.destroy()

            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error al realizar entrada", f"Error: {err}")
            finally:
                if mydb and mydb.is_connected():
                    cursor.close()
                    mydb.close()

        ventana_entrada = tk.Toplevel(ventana_inventario)
        ventana_entrada.title(f"Realizar Entrada - {nombre_producto} (Código: {codigo_producto_seleccionado})")
        ventana_entrada.configure(bg="#A9A9A9")

        ttk.Label(ventana_entrada, text="Cantidad:", style="CustomLabel.TLabel").grid(row=0, column=0, padx=10, pady=10)
        entry_cantidad = ttk.Entry(ventana_entrada, style="CustomEntry.TEntry")
        entry_cantidad.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(ventana_entrada, text="Fecha:", style="CustomLabel.TLabel").grid(row=1, column=0, padx=10, pady=10)
        entry_fecha = ttk.Entry(ventana_entrada, style="CustomEntry.TEntry")
        entry_fecha.grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(ventana_entrada, text="Calendario", command=lambda: abrir_calendario(ventana_entrada, entry_fecha), style="CustomButton.TButton").grid(row=1, column=2, padx=10, pady=10)

        ttk.Button(ventana_entrada, text="Confirmar Entrada", command=confirmar_entrada, style="CustomButton.TButton").grid(row=2, column=0, columnspan=3, pady=15, padx=10, sticky="ew")
        ventana_entrada.grid_columnconfigure(1, weight=1)

    def realizar_salida_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una salida de productos desde el menú contextual usando el código del producto (actualizado para MySQL)."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.")
            return

        def confirmar_salida():
            departamento = departamento_var.get()
            cantidad_str = entry_cantidad.get()
            fecha = entry_fecha.get()
            numero_requisicion = entry_numero_requisicion.get()

            if not cantidad_str.isdigit():
                messagebox.showerror("Error", "Cantidad inválida. Ingrese un número entero.")
                return
            cantidad = int(cantidad_str)

            if not departamento or not fecha or not numero_requisicion:
                messagebox.showerror("Error", "Por favor, complete todos los campos.")
                return

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                return

            cursor = mydb.cursor()

            try:
                # Verificar si hay suficiente stock
                cursor.execute("SELECT Stock FROM productos WHERE Codigo = %s", (codigo_producto_seleccionado,))
                resultado_stock = cursor.fetchone()
                if resultado_stock and resultado_stock[0] >= cantidad:
                    # Actualizar el stock en la tabla productos
                    sql_actualizar_stock = "UPDATE productos SET Stock = Stock - %s, FechaSalida = %s, Departamento = %s WHERE Codigo = %s"
                    val_actualizar_stock = (cantidad, fecha, departamento, codigo_producto_seleccionado)
                    cursor.execute(sql_actualizar_stock, val_actualizar_stock)

                    # Insertar un registro en la tabla salidas (o actualizar salidas_espera)
                    sql_insertar_salida = "INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, FechaSalida, Departamento, NumeroRequisicion) SELECT ProductoID, Codigo, %s, %s, %s, %s FROM productos WHERE Codigo = %s"
                    val_insertar_salida = (cantidad, fecha, departamento, numero_requisicion, codigo_producto_seleccionado)
                    cursor.execute(sql_insertar_salida, val_insertar_salida)

                    mydb.commit()
                    mostrar_tabla(categoria_seleccionada_mostrar.get())
                    messagebox.showinfo("Salida Realizada", f"{cantidad} unidades de {nombre_producto} (Código: {codigo_producto_seleccionado}) salieron para {departamento}.")
                    ventana_salida.destroy()
                else:
                    messagebox.showerror("Error", "No hay suficiente stock para realizar la salida.")

            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error al realizar salida", f"Error: {err}")
            finally:
                if mydb and mydb.is_connected():
                    cursor.close()
                    mydb.close()

        ventana_salida = tk.Toplevel(ventana_inventario)
        ventana_salida.title(f"Realizar Salida - {nombre_producto} (Código: {codigo_producto_seleccionado})")
        ventana_salida.configure(bg="#A9A9A9")

        ttk.Label(ventana_salida, text="Departamento:", style="CustomLabel.TLabel").grid(row=0, column=0, padx=10, pady=10)
        departamentos = ["OTIC", "Oficina de Gestion Administrativa", "Oficina Contabilidad","Oficina Compras","Oficina de Bienes","Direccion de Servicios Generales y Transporte","Oficina de Seguimiento y Proyectos Estructurales","Direccion General de Planificacion Estrategica","Planoteca","Biblioteca","Direccion General de Seguimiento de Proyectos","Gestion Participativa Parque la isla","Oficina de Atencion ciudadana","Oficina de gestion Humana","Presidencia","Secretaria General","Consultoria Juridica","Oficina de Planificacion y Presupuesto","Auditoria","Direccion de informacion y Comunicacion","Direccion General de Formacion"]
        departamentos.sort()
        departamento_var = tk.StringVar(ventana_salida)
        departamento_var.set(departamentos[0] if departamentos else "")
        combo_departamento = ttk.Combobox(ventana_salida, textvariable=departamento_var, values=departamentos, style="TCombobox")
        combo_departamento.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Cantidad:", style="CustomLabel.TLabel").grid(row=1, column=0, padx=10, pady=10)
        entry_cantidad = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_cantidad.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Fecha:", style="CustomLabel.TLabel").grid(row=2, column=0, padx=10, pady=10)
        entry_fecha = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_fecha.grid(row=2, column=1, padx=10, pady=10)
        ttk.Button(ventana_salida, text="Calendario", command=lambda: abrir_calendario(ventana_salida, entry_fecha), style="CustomButton.TButton").grid(row=2, column=2, padx=10, pady=10)

        ttk.Label(ventana_salida, text="Número de Requisición:", style="CustomLabel.TLabel").grid(row=3, column=0, padx=10, pady=10)
        entry_numero_requisicion = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_numero_requisicion.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ttk.Button(ventana_salida, text="Confirmar Salida", command=confirmar_salida, style="CustomButton.TButton").grid(row=4, column=0, columnspan=3, pady=15, padx=10, sticky="ew")
        ventana_salida.grid_columnconfigure(1, weight=1)

    def eliminar_producto_contextual(codigo_producto_seleccionado, nombre_producto):
        """Elimina un producto del inventario desde el menú contextual usando el código (actualizado para MySQL)."""
        if codigo_producto_seleccionado:
            if messagebox.askyesno("Eliminar Producto", f"¿Seguro que desea eliminar '{nombre_producto}' (Código: {codigo_producto_seleccionado}) del inventario?"):
                mydb = conectar_mysql()
                if not mydb:
                    messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                    return

                cursor = mydb.cursor()
                try:
                    sql_eliminar = "DELETE FROM productos WHERE Codigo = %s"
                    val_eliminar = (codigo_producto_seleccionado,)
                    cursor.execute(sql_eliminar, val_eliminar)
                    mydb.commit()
                    mostrar_tabla(categoria_seleccionada_mostrar.get())
                    messagebox.showinfo("Producto Eliminado", f"Producto '{nombre_producto}' (Código: {codigo_producto_seleccionado}) eliminado del inventario.")
                except mysql.connector.Error as err:
                    mydb.rollback()
                    messagebox.showerror("Error al eliminar producto", f"Error: {err}")
                finally:
                    if mydb and mydb.is_connected():
                        cursor.close()
                        mydb.close()
            else:
                messagebox.showerror("Error", "No se proporcionó el código del producto para eliminar.")

    # Función para manejar el clic derecho en un producto
    def menu_contextual(event):
        item = tabla_productos.identify_row(event.y)
        if item:
            codigo_producto = tabla_productos.item(item, "values")[0]  # Obtener el código del producto
            nombre_producto = inventario.get(codigo_producto, {}).get("nombre", "N/A")
            menu = tk.Menu(ventana_inventario, tearoff=0)
            menu.add_command(label="Realizar Entrada", command=lambda c=codigo_producto, n=nombre_producto: realizar_entrada_contextual(c, n))
            menu.add_command(label="Realizar Salida", command=lambda c=codigo_producto, n=nombre_producto: realizar_salida_contextual(c, n))
            menu.add_command(label="Eliminar Producto", command=lambda c=codigo_producto, n=nombre_producto: eliminar_producto_contextual(c, n))
            menu.post(event.x_root, event.y_root)

    # Enlazar el evento de clic derecho al Treeview
    tabla_productos.bind("<Button-3>", menu_contextual)

    ventana_inventario.grid_columnconfigure(0, weight=1)
    ventana_inventario.grid_rowconfigure(1, weight=1)



def calcular_consumo_departamento():
    """Calcula el consumo diario, semanal y mensual por departamento y en general desde la base de datos."""
    consumo_diario = calcular_consumo_periodo(datetime.timedelta(days=1))
    consumo_semanal = calcular_consumo_periodo(datetime.timedelta(weeks=1))
    consumo_mensual = calcular_consumo_periodo(datetime.timedelta(days=30))

    mostrar_consumo_periodos(consumo_diario, consumo_semanal, consumo_mensual)

def mostrar_consumo_periodos(consumo_diario, consumo_semanal, consumo_mensual):
    """Muestra el consumo para los tres períodos en una tabla."""
    ventana_consumo = tk.Toplevel(ventana)
    ventana_consumo.title("Consumo por Período")
    ventana_consumo.configure(bg="#A9A9A9")

    # --- Estilos ttk Personalizados ---
    style = ttk.Style(ventana_consumo)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    # Treeview (tabla) para mostrar el consumo
    tabla_consumo = ttk.Treeview(ventana_consumo, columns=("Departamento", "Código", "Producto", "Diario", "Semanal", "Mensual", "Unidad Medida", "Porcentaje"), show="headings", style="Grid.Treeview")
    tabla_consumo.pack(fill=tk.BOTH, expand=True)

    # Definir encabezados de columna
    tabla_consumo.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla_consumo.heading("Código", text="Código", anchor=tk.W)
    tabla_consumo.heading("Producto", text="Producto", anchor=tk.W)
    tabla_consumo.heading("Diario", text="Diario", anchor=tk.W)
    tabla_consumo.heading("Semanal", text="Semanal", anchor=tk.W)
    tabla_consumo.heading("Mensual", text="Mensual", anchor=tk.W)
    tabla_consumo.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla_consumo.heading("Porcentaje", text="Porcentaje", anchor=tk.W)

    # Configurar ancho de columnas
    tabla_consumo.column("Departamento", width=150)
    tabla_consumo.column("Código", width=100)
    tabla_consumo.column("Producto", width=150)
    tabla_consumo.column("Diario", width=80)
    tabla_consumo.column("Semanal", width=80)
    tabla_consumo.column("Mensual", width=80)
    tabla_consumo.column("Unidad Medida", width=100)
    tabla_consumo.column("Porcentaje", width=100)

    # Lista para almacenar los datos de consumo para guardar
    datos_consumo_guardar = []

    # Obtener todos los departamentos y códigos de productos únicos de los datos de consumo
    departamentos = set()
    codigos_consumidos = set()
    consumo_total_general = 0

    for periodo_consumo, total_periodo in [consumo_diario, consumo_semanal, consumo_mensual]:
        if periodo_consumo:
            departamentos.update(periodo_consumo.keys())
            for productos_departamento in periodo_consumo.values():
                codigos_consumidos.update(productos_departamento.keys())
                consumo_total_general += total_periodo

    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        for departamento in sorted(list(departamentos)):
            for codigo in sorted(list(codigos_consumidos)):
                diario = consumo_diario[0].get(departamento, {}).get(codigo, 0)
                semanal = consumo_semanal[0].get(departamento, {}).get(codigo, 0)
                mensual = consumo_mensual[0].get(departamento, {}).get(codigo, 0)

                # Obtener nombre y unidad de medida desde la base de datos
                cursor.execute("SELECT Nombre, UnidadMedida FROM productos WHERE Codigo = %s", (codigo,))
                producto_info = cursor.fetchone()
                nombre_producto = producto_info[0] if producto_info else "N/A"
                unidad_medida = producto_info[1] if producto_info else "N/A"

                # Calcular el consumo total para el producto
                total_consumo_producto = diario + semanal + mensual

                # Calcular el porcentaje de consumo del producto respecto al total general
                porcentaje = (total_consumo_producto / consumo_total_general) * 100 if consumo_total_general > 0 else 0

                values = (departamento, codigo, nombre_producto, diario, semanal, mensual, unidad_medida, f"{porcentaje:.2f}%")
                tabla_consumo.insert("", tk.END, values=values)
        cursor.close()
        mydb.close()


def calcular_consumo_periodo(periodo):
    """Calcula el consumo para un período específico desde la base de datos MySQL, utilizando el código del producto como clave."""
    consumo_departamentos = {}
    total_consumo = 0
    fecha_actual = datetime.date.today()
    fecha_inicio = fecha_actual - periodo

    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        query = """
            SELECT s.Departamento, s.CodigoProducto, s.Cantidad, s.FechaSalida, p.UnidadMedida, p.Nombre
            FROM salidas s
            JOIN productos p ON s.ProductoID = p.ProductoID
            WHERE s.FechaSalida BETWEEN %s AND %s
        """
        val = (fecha_inicio, fecha_actual)
        try:
            cursor.execute(query, val)
            salidas_periodo = cursor.fetchall()
            for departamento, codigo_producto, cantidad, fecha_salida, unidad_medida, nombre_producto in salidas_periodo:
                if departamento not in consumo_departamentos:
                    consumo_departamentos[departamento] = {}
                if codigo_producto not in consumo_departamentos[departamento]:
                    consumo_departamentos[departamento][codigo_producto] = 0
                try:
                    consumo_departamentos[departamento][codigo_producto] += int(cantidad)
                    total_consumo += int(cantidad)
                except ValueError:
                    print(f"Cantidad inválida en la salida para el producto con código {codigo_producto} en el departamento {departamento}")
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al calcular el consumo por período: {err}")
        finally:
            cursor.close()
            mydb.close()
    return consumo_departamentos, total_consumo


    




                            #Hasta aqui funciones principales.


















                                    #Funciones de reportes:

def generar_reporte_bajo_stock():
    """Genera un reporte de productos con bajo stock desde la base de datos MySQL y almacena los datos."""
    global datos_reportes_para_guardar
    ventana_reporte = tk.Toplevel(ventana)
    ventana_reporte.title("Reporte de Bajo Stock")
    ventana_reporte.configure(bg="#A9A9A9")

    style = ttk.Style(ventana_reporte)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    umbral_stock_minimo = 1
    productos_bajo_stock = []
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        query = """
            SELECT Codigo, Nombre, Stock, UnidadMedida
            FROM productos
            WHERE Stock < %s
        """
        try:
            cursor.execute(query, (umbral_stock_minimo,))
            productos_bajo_stock_db = cursor.fetchall()
            for codigo, nombre, stock, unidad_medida in productos_bajo_stock_db:
                productos_bajo_stock.append({"Código": codigo, "Producto": nombre, "Stock Actual": stock, "Unidad Medida": unidad_medida})
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al obtener productos con bajo stock: {err}")
        finally:
            cursor.close()
            mydb.close()

    datos_reporte = [] # Lista para almacenar los datos del reporte
    if productos_bajo_stock:
        tabla_bajo_stock = ttk.Treeview(ventana_reporte, columns=("Código", "Producto", "Stock Actual", "Unidad Medida"), show="headings", style="Grid.Treeview")
        tabla_bajo_stock.pack(fill=tk.BOTH, expand=True)
        tabla_bajo_stock.heading("Código", text="Código", anchor=tk.W)
        tabla_bajo_stock.heading("Producto", text="Producto", anchor=tk.W)
        tabla_bajo_stock.heading("Stock Actual", text="Stock Actual", anchor=tk.W)
        tabla_bajo_stock.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
        tabla_bajo_stock.column("Código", width=100)
        tabla_bajo_stock.column("Producto", width=150)
        tabla_bajo_stock.column("Stock Actual", width=100)
        tabla_bajo_stock.column("Unidad Medida", width=100)

        for producto in productos_bajo_stock:
            tabla_bajo_stock.insert("", tk.END, values=(producto["Código"], producto["Producto"], producto["Stock Actual"], producto["Unidad Medida"]))
            datos_reporte.append(producto)

        scrollbar_y = ttk.Scrollbar(ventana_reporte, orient="vertical", command=tabla_bajo_stock.yview)
        scrollbar_y.pack(side="right", fill="y")
        tabla_bajo_stock.configure(yscrollcommand=scrollbar_y.set)
    else:
        messagebox.showinfo("Reporte de Bajo Stock", "No hay productos con bajo stock.")

    datos_reportes_para_guardar["Bajo Stock"] = datos_reporte
    
           





def generar_reporte_entradas():
    """Genera un reporte del historial de entradas desde la base de datos MySQL."""
    ventana_reporte = tk.Toplevel(ventana)
    ventana_reporte.title("Reporte de Entradas")
    ventana_reporte.geometry("800x500")
    ventana_reporte.configure(bg="#A9A9A9")

    # --- Estilos ttk Personalizados --- (Mantenlos como están)
    style = ttk.Style(ventana_reporte)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    # Treeview (tabla) para mostrar las entradas
    tabla_entradas = ttk.Treeview(ventana_reporte, columns=("Código", "Producto", "Cantidad", "Fecha", "Destino", "EntradaID"), show="headings", style="Grid.Treeview")
    tabla_entradas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    tabla_entradas.column("EntradaID", width=0, stretch=tk.NO) # Columna oculta para el ID

    # Definir encabezados de columna
    tabla_entradas.heading("Código", text="Código", anchor=tk.W)
    tabla_entradas.heading("Producto", text="Producto", anchor=tk.W)
    tabla_entradas.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tabla_entradas.heading("Fecha", text="Fecha", anchor=tk.W)
    tabla_entradas.heading("Destino", text="Destino", anchor=tk.W)

    # Configurar ancho de columnas
    tabla_entradas.column("Código", width=100)
    tabla_entradas.column("Producto", width=150)
    tabla_entradas.column("Cantidad", width=80)
    tabla_entradas.column("Fecha", width=100)
    tabla_entradas.column("Destino", width=150)

    # Barras de desplazamiento
    scrollbar_vertical = ttk.Scrollbar(ventana_reporte, orient="vertical", command=tabla_entradas.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
    tabla_entradas.configure(yscrollcommand=scrollbar_vertical.set)

    def cargar_entradas():
        """Carga las entradas desde la base de datos y las muestra en la tabla."""
        tabla_entradas.delete(*tabla_entradas.get_children())
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = """
                SELECT e.EntradaID, p.Codigo, p.Nombre, e.Cantidad, e.FechaEntrada, e.Destino
                FROM entradas e
                JOIN productos p ON e.ProductoID = p.ProductoID
                ORDER BY e.FechaEntrada DESC
            """
            try:
                cursor.execute(query)
                entradas_db = cursor.fetchall()
                for entrada_id, codigo, producto, cantidad, fecha, destino in entradas_db:
                    tabla_entradas.insert("", tk.END, values=(codigo, producto, cantidad, fecha.strftime("%Y-%m-%d"), destino, entrada_id))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al cargar las entradas: {err}")
            finally:
                cursor.close()
                mydb.close()

    cargar_entradas()

    def eliminar_entrada():
        seleccion = tabla_entradas.selection()
        if seleccion:
            item_id = seleccion[0]
            entrada_id = tabla_entradas.item(item_id, "values")[-1] # Obtener el EntradaID (último valor)

            if messagebox.askyesno("Eliminar Entrada", "¿Seguro que desea eliminar esta entrada?"):
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_eliminar = "DELETE FROM entradas WHERE EntradaID = %s"
                    try:
                        cursor.execute(query_eliminar, (entrada_id,))
                        mydb.commit()
                        tabla_entradas.delete(item_id)
                        messagebox.showinfo("Entrada Eliminada", "La entrada ha sido eliminada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al eliminar la entrada: {err}")
                    finally:
                        cursor.close()
                        mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una entrada para eliminar.")

    def editar_entrada():
        seleccion = tabla_entradas.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_entradas.item(item_id, "values")
            codigo_actual = values[0]
            producto_actual = values[1]
            cantidad_actual = values[2]
            fecha_actual_str = values[3]
            destino_actual = values[4]
            entrada_id = values[5]

            ventana_edicion = tk.Toplevel(ventana_reporte)
            ventana_edicion.title("Editar Entrada")
            ventana_edicion.configure(bg="#A9A9A9")

            tk.Label(ventana_edicion, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5)
            entry_codigo = tk.Entry(ventana_edicion)
            entry_codigo.grid(row=0, column=1, padx=5, pady=5)
            entry_codigo.insert(0, codigo_actual)
            entry_codigo.config(state="readonly")

            tk.Label(ventana_edicion, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5)
            entry_producto = tk.Entry(ventana_edicion)
            entry_producto.grid(row=1, column=1, padx=5, pady=5)
            entry_producto.insert(0, producto_actual)

            tk.Label(ventana_edicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5)
            entry_cantidad = tk.Entry(ventana_edicion)
            entry_cantidad.grid(row=2, column=1, padx=5, pady=5)
            entry_cantidad.insert(0, cantidad_actual)

            tk.Label(ventana_edicion, text="Fecha:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5)
            entry_fecha = tk.Entry(ventana_edicion)
            entry_fecha.grid(row=3, column=1, padx=5, pady=5)
            entry_fecha.insert(0, fecha_actual_str)

            tk.Label(ventana_edicion, text="Destino:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5)
            entry_destino = tk.Entry(ventana_edicion)
            entry_destino.grid(row=4, column=1, padx=5, pady=5)
            entry_destino.insert(0, destino_actual)

            def guardar_cambios_edicion():
                producto_editado = entry_producto.get()
                try:
                    cantidad_editada = int(entry_cantidad.get())
                except ValueError:
                    messagebox.showerror("Error", "Cantidad debe ser un número entero.")
                    return
                fecha_editada_str = entry_fecha.get()
                try:
                    fecha_editada = datetime.datetime.strptime(fecha_editada_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).")
                    return
                destino_editado = entry_destino.get()

                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_actualizar = """
                        UPDATE entradas
                        SET ProductoID = (SELECT ProductoID FROM productos WHERE Codigo = %s),
                            Cantidad = %s,
                            FechaEntrada = %s,
                            Destino = %s
                        WHERE EntradaID = %s
                    """
                    try:
                        cursor.execute(query_actualizar, (codigo_actual, cantidad_editada, fecha_editada, destino_editado, entrada_id))
                        mydb.commit()
                        cargar_entradas() # Recargar la tabla después de editar
                        ventana_edicion.destroy()
                        messagebox.showinfo("Entrada Editada", "La entrada ha sido actualizada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al editar la entrada: {err}")
                    finally:
                        cursor.close()
                        mydb.close()

            ttk.Button(ventana_edicion, text="Guardar", command=guardar_cambios_edicion).grid(row=5, column=0, columnspan=2, pady=10)

    def buscar_producto_abreviatura():
        """Abre una ventana para buscar producto por abreviatura en las entradas."""
        ventana_busqueda_abreviatura = tk.Toplevel(ventana_reporte)
        ventana_busqueda_abreviatura.title("Buscar Producto por Abreviatura en Entradas")
        ventana_busqueda_abreviatura.configure(bg="#A9A9A9")

        tk.Label(ventana_busqueda_abreviatura, text="Ingrese abreviatura:", fg="#ffffff", bg="#A9A9A9").pack(padx=10, pady=10)
        entry_abreviatura = ttk.Entry(ventana_busqueda_abreviatura)
        entry_abreviatura.pack(padx=10, pady=5)

        def filtrar_por_abreviatura(event):
            abreviatura = entry_abreviatura.get().lower()
            tabla_entradas.delete(*tabla_entradas.get_children())
            mydb = conectar_mysql()
            if mydb:
                cursor = mydb.cursor()
                query_buscar = """
                    SELECT e.EntradaID, p.Codigo, p.Nombre, e.Cantidad, e.FechaEntrada, e.Destino
                    FROM entradas e
                    JOIN productos p ON e.ProductoID = p.ProductoID
                    WHERE LOWER(p.Nombre) LIKE %s
                    ORDER BY e.FechaEntrada DESC
                """
                try:
                    cursor.execute(query_buscar, (f"%{abreviatura}%",))
                    entradas_filtradas_db = cursor.fetchall()
                    for entrada_id, codigo, producto, cantidad, fecha, destino in entradas_filtradas_db:
                        tabla_entradas.insert("", tk.END, values=(codigo, producto, cantidad, fecha.strftime("%Y-%m-%d"), destino, entrada_id))
                except mysql.connector.Error as err:
                    messagebox.showerror("Error", f"Error al buscar por abreviatura: {err}")
                finally:
                    cursor.close()
                    mydb.close()

        entry_abreviatura.bind("<KeyRelease>", filtrar_por_abreviatura)

    # Crear menú contextual (clic derecho)
    menu_contextual = tk.Menu(ventana_reporte, tearoff=0)
    menu_contextual.add_command(label="Eliminar", command=eliminar_entrada)
    menu_contextual.add_command(label="Editar", command=editar_entrada)
    menu_contextual.add_command(label="Buscar por Abreviatura", command=buscar_producto_abreviatura)

    # Vincular el menú contextual al clic derecho
    def mostrar_menu_contextual(event):
        item = tabla_entradas.identify_row(event.y)
        if item:
            tabla_entradas.selection_set(item)
            menu_contextual.post(event.x_root, event.y_root)

    tabla_entradas.bind("<Button-3>", mostrar_menu_contextual)

def generar_reporte_salidas():
    """Genera un reporte del historial de salidas desde la base de datos MySQL."""
    ventana_reporte_salidas = tk.Toplevel(ventana)
    ventana_reporte_salidas.title("Reporte de Salidas")
    ventana_reporte_salidas.geometry("900x500")
    ventana_reporte_salidas.configure(bg="#A9A9A9")

    # --- Estilos ttk Personalizados --- (Mantenlos como están)
    style = ttk.Style(ventana_reporte_salidas)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    tree = ttk.Treeview(ventana_reporte_salidas, columns=("Código", "Producto", "Cantidad", "Fecha", "Destino", "Requisición", "SalidaID"), show="headings", style="Grid.Treeview")
    tree.heading("Código", text="Código", anchor=tk.W)
    tree.heading("Producto", text="Producto", anchor=tk.W)
    tree.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tree.heading("Fecha", text="Fecha", anchor=tk.W)
    tree.heading("Destino", text="Destino", anchor=tk.W)
    tree.heading("Requisición", text="Requisición", anchor=tk.W)
    tree.column("SalidaID", width=0, stretch=tk.NO) # Columna oculta para el ID
    tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    scrollbar = ttk.Scrollbar(ventana_reporte_salidas, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns", pady=10)

    def cargar_salidas():
        """Carga las salidas desde la base de datos y las muestra en la tabla."""
        tree.delete(*tree.get_children())
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = """
                SELECT s.SalidaID, p.Codigo, p.Nombre, s.Cantidad, s.FechaSalida, s.Departamento, s.NumeroRequisicion
                FROM salidas s
                JOIN productos p ON s.ProductoID = p.ProductoID
                ORDER BY s.FechaSalida DESC
            """
            try:
                cursor.execute(query)
                salidas_db = cursor.fetchall()
                for salida_id, codigo, producto, cantidad, fecha, destino, requisicion in salidas_db:
                    tree.insert("", "end", values=(codigo, producto, cantidad, fecha.strftime("%Y-%m-%d"), destino, requisicion, salida_id))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al cargar las salidas: {err}")
            finally:
                cursor.close()
                mydb.close()

    cargar_salidas()

    def eliminar_salida():
        seleccion = tree.selection()
        if seleccion:
            item_id = seleccion[0]
            salida_id = tree.item(item_id, "values")[-1] # Obtener el SalidaID

            if messagebox.askyesno("Eliminar Salida", "¿Seguro que desea eliminar esta salida?"):
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_eliminar = "DELETE FROM salidas WHERE SalidaID = %s"
                    try:
                        cursor.execute(query_eliminar, (salida_id,))
                        mydb.commit()
                        tree.delete(item_id)
                        messagebox.showinfo("Salida Eliminada", "La salida ha sido eliminada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al eliminar la salida: {err}")
                    finally:
                        cursor.close()
                        mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una salida para eliminar.")

    def editar_salida():
        seleccion = tree.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tree.item(item_id, "values")
            codigo_actual = values[0]
            producto_actual = values[1]
            cantidad_actual = values[2]
            fecha_actual_str = values[3]
            destino_actual = values[4]
            requisicion_actual = values[5]
            salida_id = values[6]

            ventana_edicion = tk.Toplevel(ventana_reporte_salidas)
            ventana_edicion.title("Editar Salida")
            ventana_edicion.configure(bg="#A9A9A9")

            tk.Label(ventana_edicion, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5)
            entry_codigo = tk.Entry(ventana_edicion)
            entry_codigo.grid(row=0, column=1, padx=5, pady=5)
            entry_codigo.insert(0, codigo_actual)
            entry_codigo.config(state="readonly")

            tk.Label(ventana_edicion, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5)
            entry_producto = tk.Entry(ventana_edicion)
            entry_producto.grid(row=1, column=1, padx=5, pady=5)
            entry_producto.insert(0, producto_actual)

            tk.Label(ventana_edicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5)
            entry_cantidad = tk.Entry(ventana_edicion)
            entry_cantidad.grid(row=2, column=1, padx=5, pady=5)
            entry_cantidad.insert(0, cantidad_actual)

            tk.Label(ventana_edicion, text="Fecha:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5)
            entry_fecha = tk.Entry(ventana_edicion)
            entry_fecha.grid(row=3, column=1, padx=5, pady=5)
            entry_fecha.insert(0, fecha_actual_str)

            tk.Label(ventana_edicion, text="Destino:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5)
            entry_destino = tk.Entry(ventana_edicion)
            entry_destino.grid(row=4, column=1, padx=5, pady=5)
            entry_destino.insert(0, destino_actual)

            tk.Label(ventana_edicion, text="Requisición:", fg="#ffffff", bg="#A9A9A9").grid(row=5, column=0, padx=5, pady=5)
            entry_requisicion = tk.Entry(ventana_edicion)
            entry_requisicion.grid(row=5, column=1, padx=5, pady=5)
            entry_requisicion.insert(0, requisicion_actual)

            def guardar_cambios():
                producto_editado = entry_producto.get()
                try:
                    cantidad_editada = int(entry_cantidad.get())
                except ValueError:
                    messagebox.showerror("Error", "Cantidad debe ser un número entero.")
                    return
                fecha_editada_str = entry_fecha.get()
                try:
                    fecha_editada = datetime.datetime.strptime(fecha_editada_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).")
                    return
                destino_editado = entry_destino.get()
                requisicion_editada = entry_requisicion.get()

                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_actualizar = """
                        UPDATE salidas
                        SET ProductoID = (SELECT ProductoID FROM productos WHERE Codigo = %s),
                            Cantidad = %s,
                            FechaSalida = %s,
                            Departamento = %s,
                            NumeroRequisicion = %s
                        WHERE SalidaID = %s
                    """
                    try:
                        cursor.execute(query_actualizar, (codigo_actual, cantidad_editada, fecha_editada, destino_editado, requisicion_editada, salida_id))
                        mydb.commit()
                        cargar_salidas() # Recargar la tabla
                        ventana_edicion.destroy()
                        messagebox.showinfo("Salida Editada", "La salida ha sido actualizada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al editar la salida: {err}")
                    finally:
                        cursor.close()
                        mydb.close()

            ttk.Button(ventana_edicion, text="Guardar", command=guardar_cambios).grid(row=6, column=0, columnspan=2, pady=10)

    def buscar_producto_abreviatura():
        """Abre una ventana para buscar producto por abreviatura en las salidas."""
        ventana_busqueda_abreviatura = tk.Toplevel(ventana_reporte_salidas)
        ventana_busqueda_abreviatura.title("Buscar Producto por Abreviatura en Salidas")
        ventana_busqueda_abreviatura.configure(bg="#A9A9A9")

        tk.Label(ventana_busqueda_abreviatura, text="Ingrese abreviatura:", fg="#ffffff", bg="#A9A9A9").pack(padx=10, pady=10)
        entry_abreviatura = ttk.Entry(ventana_busqueda_abreviatura)
        entry_abreviatura.pack(padx=10, pady=5)

        def filtrar_por_abreviatura(event):
            abreviatura = entry_abreviatura.get().lower()
            tree.delete(*tree.get_children())
            mydb = conectar_mysql()
            if mydb:
                cursor = mydb.cursor()
                query_buscar = """
                    SELECT s.SalidaID, p.Codigo, p.Nombre, s.Cantidad, s.FechaSalida, s.Departamento, s.NumeroRequisicion
                    FROM salidas s
                    JOIN productos p ON s.ProductoID = p.ProductoID
                    WHERE LOWER(p.Nombre) LIKE %s
                    ORDER BY s.FechaSalida DESC
                """
                try:
                    cursor.execute(query_buscar, (f"%{abreviatura}%",))
                    salidas_filtradas_db = cursor.fetchall()
                    for salida_id, codigo, producto, cantidad, fecha, destino, requisicion in salidas_filtradas_db:
                        tree.insert("", "end", values=(codigo, producto, cantidad, fecha.strftime("%Y-%m-%d"), destino, requisicion, salida_id))
                except mysql.connector.Error as err:
                    messagebox.showerror("Error", f"Error al buscar por abreviatura: {err}")
                finally:
                    cursor.close()
                    mydb.close()

        entry_abreviatura.bind("<KeyRelease>", filtrar_por_abreviatura)

    # Crear menú contextual (clic derecho)
    menu_contextual = tk.Menu(ventana_reporte_salidas, tearoff=0)
    menu_contextual.add_command(label="Eliminar", command=eliminar_salida)
    menu_contextual.add_command(label="Editar", command=editar_salida)
    menu_contextual.add_command(label="Buscar por Abreviatura", command=buscar_producto_abreviatura)

    # Vincular el menú contextual al clic derecho
    def mostrar_menu_contextual(event):
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            menu_contextual.post(event.x_root, event.y_root)

    tree.bind("<Button-3>", mostrar_menu_contextual)

    ventana_reporte_salidas.grid_columnconfigure(0, weight=1)
    ventana_reporte_salidas.grid_rowconfigure(0, weight=1)
    # Ya no guardamos los datos del reporte directamente aquí, las modificaciones se hacen en la base de datos

ventana_reporte_salidas_espera = None  # Variable global para la ventana del reporte de espera
tabla_salidas_espera = None          # Variable global para la tabla

def actualizar_tabla_salidas_espera():
    """Actualiza el contenido de la tabla de salidas en espera desde la base de datos."""
    global tabla_salidas_espera
    if tabla_salidas_espera:
        tabla_salidas_espera.delete(*tabla_salidas_espera.get_children())
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = """
                SELECT spe.SalidaEsperaID, p.Codigo, p.Nombre, spe.Cantidad, spe.Departamento
                FROM salidas_espera spe
                JOIN productos p ON spe.ProductoID = p.ProductoID
            """
            try:
                cursor.execute(query)
                salidas_espera_db = cursor.fetchall()
                for espera_id, codigo, producto, cantidad, departamento in salidas_espera_db:
                    tabla_salidas_espera.insert("", tk.END, values=(codigo, producto, cantidad, departamento, espera_id))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al actualizar la tabla de salidas en espera: {err}")
            finally:
                cursor.close()
                mydb.close()

def generar_reporte_salidas_espera():
    """Genera o trae al frente la ventana del reporte de salidas en espera desde la base de datos."""
    global ventana_reporte_salidas_espera, tabla_salidas_espera

    if ventana_reporte_salidas_espera and ventana_reporte_salidas_espera.winfo_exists():
        ventana_reporte_salidas_espera.lift()
        actualizar_tabla_salidas_espera()
        return

    ventana_reporte_salidas_espera = tk.Toplevel(ventana)
    ventana_reporte_salidas_espera.title("Reporte de Salidas en Espera")
    ventana_reporte_salidas_espera.geometry("700x500")
    ventana_reporte_salidas_espera.configure(bg="#A9A9A9")

    # --- Estilos ttk Personalizados --- (Mantenlos como están)
    style = ttk.Style(ventana_reporte_salidas_espera)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    # Treeview (tabla) para mostrar las salidas en espera
    tabla_salidas_espera = ttk.Treeview(ventana_reporte_salidas_espera, columns=("Código", "Producto", "Cantidad", "Departamento", "EsperaID"), show="headings", style="Grid.Treeview")
    tabla_salidas_espera.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    tabla_salidas_espera.column("EsperaID", width=0, stretch=tk.NO) # Columna oculta para el ID

    # Definir encabezados de columna
    tabla_salidas_espera.heading("Código", text="Código", anchor=tk.W)
    tabla_salidas_espera.heading("Producto", text="Producto", anchor=tk.W)
    tabla_salidas_espera.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tabla_salidas_espera.heading("Departamento", text="Departamento", anchor=tk.W)

    # Configurar ancho de columnas
    tabla_salidas_espera.column("Código", width=100)
    tabla_salidas_espera.column("Producto", width=200)
    tabla_salidas_espera.column("Cantidad", width=100)
    tabla_salidas_espera.column("Departamento", width=200)

    # Barras de desplazamiento
    scrollbar_vertical = ttk.Scrollbar(ventana_reporte_salidas_espera, orient="vertical", command=tabla_salidas_espera.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=10)
    tabla_salidas_espera.configure(yscrollcommand=scrollbar_vertical.set)

    actualizar_tabla_salidas_espera()

    def agregar_requisicion():
        item_seleccionado = tabla_salidas_espera.selection()
        if item_seleccionado:
            item = item_seleccionado[0]
            values = tabla_salidas_espera.item(item, "values")
            if len(values) >= 5:
                codigo_producto = values[0]
                producto = values[1]
                cantidad = values[2]
                destino = values[3]
                espera_id = values[4]

                def confirmar_requisicion():
                    numero_requisicion = entry_requisicion.get()
                    fecha_salida = entry_fecha.get()

                    mydb = conectar_mysql()
                    if mydb:
                        cursor = mydb.cursor()
                        try:
                            # Insertar en la tabla de salidas
                            query_insert_salida = """
                                INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, FechaSalida, Departamento, NumeroRequisicion)
                                SELECT ProductoID, Codigo, %s, %s, %s, %s
                                FROM productos
                                WHERE Codigo = %s
                            """
                            cursor.execute(query_insert_salida, (cantidad, fecha_salida, destino, numero_requisicion, codigo_producto))
                            mydb.commit()
                            messagebox.showinfo("Salida Registrada", "La salida ha sido registrada.")

                            # Eliminar de la tabla de salidas en espera
                            query_eliminar_espera = "DELETE FROM salidas_espera WHERE SalidaEsperaID = %s"
                            cursor.execute(query_eliminar_espera, (espera_id,))
                            mydb.commit()
                            actualizar_tabla_salidas_espera() # Actualizar la tabla
                        except mysql.connector.Error as err:
                            mydb.rollback()
                            messagebox.showerror("Error", f"Error al confirmar la requisición: {err}")
                        finally:
                            cursor.close()
                            mydb.close()

                        if ventana_requisicion.winfo_exists():
                            ventana_requisicion.destroy()

                ventana_requisicion = tk.Toplevel(ventana_reporte_salidas_espera)
                ventana_requisicion.title("Agregar Requisición y Fecha")
                ventana_requisicion.configure(bg="#A9A9A9")

                tk.Label(ventana_requisicion, text="Número de Requisición:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5)
                entry_requisicion = ttk.Entry(ventana_requisicion)
                entry_requisicion.grid(row=0, column=1, padx=5, pady=5)

                tk.Label(ventana_requisicion, text="Fecha de Salida:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5)
                entry_fecha = ttk.Entry(ventana_requisicion)
                entry_fecha.grid(row=1, column=1, padx=5, pady=5)
                ttk.Button(ventana_requisicion, text="Calendario", command=lambda: abrir_calendario(ventana_requisicion, entry_fecha)).grid(row=1, column=2, padx=5, pady=5)

                ttk.Button(ventana_requisicion, text="Confirmar", command=confirmar_requisicion).grid(row=2, column=0, columnspan=3, pady=10)
            else:
                messagebox.showerror("Error", "Datos de producto incompletos.")
        else:
            messagebox.showerror("Error", "Seleccione un producto.")

    def eliminar_salida_espera():
        seleccion = tabla_salidas_espera.selection()
        if seleccion:
            item_id = seleccion[0]
            espera_id = tabla_salidas_espera.item(item_id, "values")[-1] # Obtener SalidaEsperaID

            if messagebox.askyesno("Eliminar Salida en Espera", "¿Seguro que desea eliminar esta solicitud?"):
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_eliminar = "DELETE FROM salidas_espera WHERE SalidaEsperaID = %s"
                    try:
                        cursor.execute(query_eliminar, (espera_id,))
                        mydb.commit()
                        actualizar_tabla_salidas_espera()
                        messagebox.showinfo("Solicitud Eliminada", "La solicitud ha sido eliminada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al eliminar la solicitud: {err}")
                    finally:
                        cursor.close()
                        mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una solicitud para eliminar.")

    def editar_salida_espera():
        seleccion = tabla_salidas_espera.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_salidas_espera.item(item_id, "values")
            codigo_actual = values[0]
            producto_actual = values[1]
            cantidad_actual = values[2]
            departamento_actual = values[3]
            espera_id = values[4]

            ventana_edicion = tk.Toplevel(ventana_reporte_salidas_espera)
            ventana_edicion.title("Editar Salida en Espera")
            ventana_edicion.configure(bg="#A9A9A9")

            tk.Label(ventana_edicion, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5)
            entry_codigo = ttk.Entry(ventana_edicion)
            entry_codigo.grid(row=0, column=1, padx=5, pady=5)
            entry_codigo.insert(0, codigo_actual)
            entry_codigo.config(state="readonly")

            tk.Label(ventana_edicion, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5)
            entry_producto = ttk.Entry(ventana_edicion)
            entry_producto.grid(row=1, column=1, padx=5, pady=5)
            entry_producto.insert(0, producto_actual)

            tk.Label(ventana_edicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5)
            entry_cantidad = ttk.Entry(ventana_edicion)
            entry_cantidad.grid(row=2, column=1, padx=5, pady=5)
            entry_cantidad.insert(0, cantidad_actual)

            tk.Label(ventana_edicion, text="Departamento:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5)
            entry_departamento = ttk.Entry(ventana_edicion)
            entry_departamento.grid(row=3, column=1, padx=5, pady=5)
            entry_departamento.insert(0, departamento_actual)

            def guardar_cambios():
                producto_editado = entry_producto.get()
                try:
                    cantidad_editada = int(entry_cantidad.get())
                except ValueError:
                    messagebox.showerror("Error", "Cantidad debe ser un número entero.")
                    return
                departamento_editado = entry_departamento.get()

                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    query_actualizar = """
                        UPDATE salidas_espera
                        SET ProductoID = (SELECT ProductoID FROM productos WHERE Codigo = %s),
                            Cantidad = %s,
                            Departamento = %s
                        WHERE SalidaEsperaID = %s
                    """
                    try:
                        cursor.execute(query_actualizar, (codigo_actual, cantidad_editada, departamento_editado, espera_id))
                        mydb.commit()
                        actualizar_tabla_salidas_espera()
                        ventana_edicion.destroy()
                        messagebox.showinfo("Solicitud Editada", "La solicitud ha sido actualizada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al editar la solicitud: {err}")
                    finally:
                        cursor.close()
                        mydb.close()

            ttk.Button(ventana_edicion, text="Guardar", command=guardar_cambios).grid(row=4, column=0, columnspan=2, pady=10)
        else:
            messagebox.showerror("Error", "Por favor, seleccione una solicitud para editar.")

    def buscar_producto_abreviatura():
        """Abre una ventana para buscar producto por abreviatura en salidas en espera."""
        ventana_busqueda_abreviatura = tk.Toplevel(ventana_reporte_salidas_espera)
        ventana_busqueda_abreviatura.title("Buscar Producto por Abreviatura en Espera")
        ventana_busqueda_abreviatura.configure(bg="#A9A9A9")

        tk.Label(ventana_busqueda_abreviatura, text="Ingrese abreviatura:", fg="#ffffff", bg="#A9A9A9").pack(padx=10, pady=10)
        entry_abreviatura = ttk.Entry(ventana_busqueda_abreviatura)
        entry_abreviatura.pack(padx=10, pady=5)

        def filtrar_por_abreviatura(event):
            abreviatura = entry_abreviatura.get().lower()
            tabla_salidas_espera.delete(*tabla_salidas_espera.get_children())
            mydb = conectar_mysql()
            if mydb:
                cursor = mydb.cursor()
                query_buscar = """
                    SELECT spe.SalidaEsperaID, p.Codigo, p.Nombre, spe.Cantidad, spe.Departamento
                    FROM salidas_espera spe
                    JOIN productos p ON spe.ProductoID = p.ProductoID
                    WHERE LOWER(p.Nombre) LIKE %s
                """
                try:
                    cursor.execute(query_buscar, (f"%{abreviatura}%",))
                    salidas_filtradas_db = cursor.fetchall()
                    for espera_id, codigo, producto, cantidad, departamento in salidas_filtradas_db:
                        tabla_salidas_espera.insert("", tk.END, values=(codigo, producto, cantidad, departamento, espera_id))
                except mysql.connector.Error as err:
                    messagebox.showerror("Error", f"Error al buscar por abreviatura: {err}")
                finally:
                    cursor.close()
                    mydb.close()

        entry_abreviatura.bind("<KeyRelease>", filtrar_por_abreviatura)

    # Crear menú contextual (clic derecho)
    menu_contextual = tk.Menu(ventana_reporte_salidas_espera, tearoff=0)
    menu_contextual.add_command(label="Eliminar", command=eliminar_salida_espera)
    menu_contextual.add_command(label="Editar", command=editar_salida_espera)
    menu_contextual.add_command(label="Agregar Requisición", command=agregar_requisicion)
    menu_contextual.add_command(label="Buscar por Abreviatura", command=buscar_producto_abreviatura)

    # Vincular el menú contextual al clic derecho
    def mostrar_menu_contextual(event):
        item = tabla_salidas_espera.identify_row(event.y)
        if item:
            tabla_salidas_espera.selection_set(item)
            menu_contextual.post(event.x_root, event.y_root)

    tabla_salidas_espera.bind("<Button-3>", mostrar_menu_contextual)

    ventana_reporte_salidas_espera.grid_columnconfigure(0, weight=1)
    ventana_reporte_salidas_espera.grid_rowconfigure(0, weight=1)

def abrir_calendario(parent, entry):
    def seleccionar_fecha():
        fecha_seleccionada = cal.get_date()
        entry.delete(0, tk.END)
        entry.insert(0, fecha_seleccionada)
        ventana_calendario.destroy()

    ventana_calendario = tk.Toplevel(parent)
    ventana_calendario.title("Seleccionar Fecha")
    cal = Calendar(ventana_calendario, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.pack(padx=10, pady=10)
    tk.Button(ventana_calendario, text="Seleccionar", command=seleccionar_fecha).pack(pady=5)



def ventana_reportes():
    """Crea una ventana para generar reportes con opciones de filtrado y nuevos reportes."""
    ventana_reporte = tk.Toplevel()
    ventana_reporte.title("Generar Reportes")
    ventana_reporte.configure(bg="#A9A9A9")  # Fondo gris oscuro medio

    # --- Estilos ttk Personalizados --- (Mantener como estaban)
    style = ttk.Style(ventana_reporte)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("Small.TButton", font=("Segoe UI", 8)) # Define un estilo más pequeño
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TFrame", background="#A9A9A9") # Estilo para los frames

    # Marco principal para centrar el contenido
    main_frame = ttk.Frame(ventana_reporte, style="TFrame")
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    main_frame.grid_columnconfigure(0, weight=1) # Para centrar horizontalmente

    # Marcos para organizar los widgets
    frame_filtros = ttk.Frame(main_frame, style="TFrame")
    frame_filtros.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    frame_tabla = ttk.Frame(main_frame, style="TFrame")
    frame_tabla.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    frame_tabla.grid_rowconfigure(0, weight=1)
    frame_tabla.grid_columnconfigure(0, weight=1)

    # --- Filtro por Categoría con Selección de Lapso ---
    label_categoria = ttk.Label(frame_filtros, text="Filtrar por Categoría:", style="CustomLabel.TLabel")
    label_categoria.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    # Suponiendo que tienes una forma de obtener las categorías únicas de la base de datos
    def obtener_categorias_db():
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT DISTINCT Categoria FROM productos ORDER BY Categoria")
                categorias_db = [row[0] for row in cursor.fetchall()]
                return ["Todas"] + sorted(categorias_db)
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener categorías: {err}", parent=ventana_reporte)
                return ["Todas"]
            finally:
                cursor.close()
                mydb.close()
        return ["Todas"]

    categorias = obtener_categorias_db()
    categoria_seleccionada = ttk.Combobox(frame_filtros, values=categorias, style="TCombobox", width=20)
    categoria_seleccionada.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    categoria_seleccionada.set("Todas")

    fecha_inicio_cat = tk.StringVar()
    fecha_fin_cat = tk.StringVar()
    fecha_inicio_cat.set("")
    fecha_fin_cat.set("")

    def seleccionar_fecha_inicio_cat():
        top = tk.Toplevel(ventana_reporte)
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_inicio_cat.set(cal.get_date())
            label_fecha_inicio_seleccionada_cat.config(text="Inicio: " + fecha_inicio_cat.get())
            top.destroy()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)

    def seleccionar_fecha_fin_cat():
        top = tk.Toplevel(ventana_reporte)
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_fin_cat.set(cal.get_date())
            label_fecha_fin_seleccionada_cat.config(text="Fin: " + fecha_fin_cat.get())
            top.destroy()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)

    boton_fecha_inicio_cat = ttk.Button(frame_filtros, text="Inicio", command=seleccionar_fecha_inicio_cat)
    boton_fecha_inicio_cat.grid(row=0, column=2, padx=5, pady=5)
    label_fecha_inicio_seleccionada_cat = ttk.Label(frame_filtros, text="Inicio: --", style="CustomLabel.TLabel")
    label_fecha_inicio_seleccionada_cat.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    boton_fecha_fin_cat = ttk.Button(frame_filtros, text="Fin", command=seleccionar_fecha_fin_cat)
    boton_fecha_fin_cat.grid(row=0, column=4, padx=5, pady=5)
    label_fecha_fin_seleccionada_cat = ttk.Label(frame_filtros, text="Fin: --", style="CustomLabel.TLabel")
    label_fecha_fin_seleccionada_cat.grid(row=0, column=5, padx=5, pady=5, sticky="w")

    # Suponiendo que tienes una forma de obtener los departamentos únicos de la base de datos
    def obtener_departamentos_db():
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT DISTINCT Departamento FROM salidas ORDER BY Departamento")
                departamentos_db = [row[0] for row in cursor.fetchall()]
                return ["Todos"] + sorted(departamentos_db)
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener departamentos: {err}", parent=ventana_reporte)
                return ["Todos"]
            finally:
                cursor.close()
                mydb.close()
        return ["Todos"]

    lista_departamentos_reporte = obtener_departamentos_db()
    label_departamento = ttk.Label(frame_filtros, text="Filtrar por Departamento:", style="CustomLabel.TLabel")
    label_departamento.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    departamento_seleccionado = ttk.Combobox(frame_filtros, values=lista_departamentos_reporte, style="TCombobox", width=30)
    departamento_seleccionado.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    departamento_seleccionado.set("Todos")

    fecha_inicio_dep = tk.StringVar()
    fecha_fin_dep = tk.StringVar()
    fecha_inicio_dep.set("")
    fecha_fin_dep.set("")

    def seleccionar_fecha_inicio_dep():
        top = tk.Toplevel(ventana_reporte)
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_inicio_dep.set(cal.get_date())
            label_fecha_inicio_seleccionada_dep.config(text="Inicio: " + fecha_inicio_dep.get())
            top.destroy()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)

    def seleccionar_fecha_fin_dep():
        top = tk.Toplevel(ventana_reporte)
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_fin_dep.set(cal.get_date())
            label_fecha_fin_seleccionada_dep.config(text="Fin: " + fecha_fin_dep.get())
            top.destroy()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)

    boton_fecha_inicio_dep = ttk.Button(frame_filtros, text="Inicio", command=seleccionar_fecha_inicio_dep)
    boton_fecha_inicio_dep.grid(row=1, column=2, padx=5, pady=5)
    label_fecha_inicio_seleccionada_dep = ttk.Label(frame_filtros, text="Inicio: --", style="CustomLabel.TLabel")
    label_fecha_inicio_seleccionada_dep.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    boton_fecha_fin_dep = ttk.Button(frame_filtros, text="Fin", command=seleccionar_fecha_fin_dep)
    boton_fecha_fin_dep.grid(row=1, column=4, padx=5, pady=5)
    label_fecha_fin_seleccionada_dep = ttk.Label(frame_filtros, text="Fin: --", style="CustomLabel.TLabel")
    label_fecha_fin_seleccionada_dep.grid(row=1, column=5, padx=5, pady=5, sticky="w")


    label_stock = ttk.Label(frame_filtros, text="Filtrar por Stock:", style="CustomLabel.TLabel")
    label_stock.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    opciones_stock = ["Todos", "Bajo Stock (<= 2)", "Stock Medio (3-10)", "Stock Alto (>= 11)"]
    stock_seleccionado = ttk.Combobox(frame_filtros, values=opciones_stock, style="TCombobox", width=25)
    stock_seleccionado.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    stock_seleccionado.set("Todos")

    global tabla_reporte
    tabla_reporte = ttk.Treeview(frame_tabla, style="Grid.Treeview")
    tabla_reporte.pack(fill="both", expand=True)

    def limpiar_tabla_reporte():
        tabla_reporte.delete(*tabla_reporte.get_children())
        categoria_seleccionada.set("Todas")
        departamento_seleccionado.set("Todos")
        stock_seleccionado.set("Todos")
        fecha_inicio_cat.set("")
        fecha_fin_cat.set("")
        label_fecha_inicio_seleccionada_cat.config(text="Inicio: --")
        label_fecha_fin_seleccionada_cat.config(text="Fin: --")
        fecha_inicio_dep.set("")
        fecha_fin_dep.set("")
        label_fecha_inicio_seleccionada_dep.config(text="Inicio: --")
        label_fecha_fin_seleccionada_dep.config(text="Fin: --")

    boton_limpiar = ttk.Button(frame_tabla, text="Limpiar", command=limpiar_tabla_reporte, style="Small.TButton")
    boton_limpiar.pack(side="bottom", anchor="se", padx=10, pady=10)

    def generar_reporte():
        categoria = categoria_seleccionada.get()
        departamento = departamento_seleccionado.get()
        fecha_inicio_cat_str = fecha_inicio_cat.get()
        fecha_fin_cat_str = fecha_fin_cat.get()
        fecha_inicio_dep_str = fecha_inicio_dep.get()
        fecha_fin_dep_str = fecha_fin_dep.get()
        stock = stock_seleccionado.get()

        if departamento != "Todos":
            generar_reporte_departamento(departamento, categoria, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte, stock)
        else:
            generar_reporte_consumo_lapso_filtrado(categoria, fecha_inicio_cat_str, fecha_fin_cat_str, departamento, stock, tabla_reporte, ventana_reporte)

    boton_generar_filtrado = ttk.Button(frame_filtros, text="Generar Reporte Filtrado", command=generar_reporte)
    boton_generar_filtrado.grid(row=3, column=0, columnspan=6, pady=10)

    boton_pdf = ttk.Button(main_frame, text="Exportar a PDF", command=lambda: exportar_tabla_pdf(tabla_reporte))
    boton_pdf.grid(row=2, column=0, pady=10)
    boton_pdf.anchor(tk.CENTER)


    for i in range(6):
        frame_filtros.grid_columnconfigure(i, weight=1)


    frame_tabla.grid_columnconfigure(0, weight=1)

def generar_reporte_consumo_lapso_filtrado(categoria_filtro, fecha_inicio_str, fecha_fin_str, departamento_filtro, stock_filtro_texto, tabla, ventana):
    """Genera un reporte de consumo por lapso, filtrado desde la base de datos."""
    tabla.delete(*tabla.get_children())
    mydb = conectar_mysql()
    if not mydb:
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            p.Categoria,
            p.Nombre,
            s.Cantidad,
            s.FechaSalida,
            p.Stock
        FROM salidas s
        JOIN productos p ON s.ProductoID = p.ProductoID
        WHERE 1=1 -- Condición siempre verdadera para facilitar la adición de filtros
    """
    params = []
    lapso_texto = ""

    if categoria_filtro != "Todas":
        query += " AND p.Categoria = %s"
        params.append(categoria_filtro)

    if departamento_filtro != "Todos":
        query += " AND s.Departamento = %s"
        params.append(departamento_filtro)

    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"

    if stock_filtro_texto != "Todos":
        if stock_filtro_texto == "Bajo Stock (<= 2)":
            query += " AND p.Stock <= 2"
        elif stock_filtro_texto == "Stock Medio (3-10)":
            query += " AND p.Stock BETWEEN 3 AND 10"
        elif stock_filtro_texto == "Stock Alto (>= 11)":
            query += " AND p.Stock >= 11"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        tabla["columns"] = ("Categoría", "Producto", "Cantidad Consumida", "Fecha de Salida", "Lapso", "Stock Actual")
        tabla.heading("#1", text="Categoría")
        tabla.column("#1", minwidth=100, stretch=tk.YES)
        tabla.heading("#2", text="Producto")
        tabla.column("#2", minwidth=250, stretch=tk.YES)
        tabla.heading("#3", text="Cantidad Consumida")
        tabla.column("#3", minwidth=150, stretch=tk.YES)
        tabla.heading("#4", text="Fecha de Salida")
        tabla.column("#4", minwidth=150, stretch=tk.YES)
        tabla.heading("#5", text="Lapso")
        tabla.column("#5", minwidth=200, stretch=tk.YES)
        tabla.heading("#6", text="Stock Actual")
        tabla.column("#6", minwidth=100, stretch=tk.YES)

        for categoria, producto, cantidad, fecha_salida, stock in reporte_data:
            tabla.insert("", tk.END, values=(categoria, producto, cantidad, fecha_salida, lapso_texto, stock))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte: {err}", parent=ventana)
    finally:
        cursor.close()
        mydb.close()

def generar_reporte_departamento(departamento_filtro, categoria_filtro, fecha_inicio_str, fecha_fin_str, tabla, ventana, stock_filtro_texto):
    """Genera un reporte de consumo por departamento y lapso, filtrado desde la base de datos."""
    tabla.delete(*tabla.get_children())
    mydb = conectar_mysql()
    if not mydb:
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            s.Departamento,
            p.Nombre,
            p.Categoria,
            s.Cantidad,
            s.FechaSalida,
            p.Stock
        FROM salidas s
        JOIN productos p ON s.ProductoID = p.ProductoID
        WHERE s.Departamento = %s
    """
    params = [departamento_filtro]
    lapso_texto = ""

    if categoria_filtro != "Todas":
        query += " AND p.Categoria = %s"
        params.append(categoria_filtro)

    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"

    if stock_filtro_texto != "Todos":
        if stock_filtro_texto == "Bajo Stock (<= 2)":
            query += " AND p.Stock <= 2"
        elif stock_filtro_texto == "Stock Medio (3-10)":
            query += " AND p.Stock BETWEEN 3 AND 10"
        elif stock_filtro_texto == "Stock Alto (>= 11)":
            query += " AND p.Stock >= 11"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        tabla["columns"] = ("Departamento", "Producto", "Categoría", "Cantidad Consumida", "Fecha de Salida", "Lapso", "Stock Actual")
        tabla.heading("#1", text="Departamento")
        tabla.column("#1", minwidth=150, stretch=tk.YES)
        tabla.heading("#2", text="Producto")
        tabla.column("#2", minwidth=150, stretch=tk.YES)
        tabla.heading("#3", text="Categoría")
        tabla.column("#3", minwidth=100, stretch=tk.YES)
        tabla.heading("#4", text="Cantidad Consumida")
        tabla.column("#4", minwidth=150, stretch=tk.YES)
        tabla.heading("#5", text="Fecha de Salida")
        tabla.column("#5", minwidth=150, stretch=tk.YES)
        tabla.heading("#6", text="Lapso")
        tabla.column("#6", minwidth=200, stretch=tk.YES)
        tabla.heading("#7", text="Stock Actual")
        tabla.column("#7", minwidth=100, stretch=tk.YES)

        for departamento, producto, categoria, cantidad, fecha_salida, stock in reporte_data:
            tabla.insert("", tk.END, values=(departamento, producto, categoria, cantidad, fecha_salida, lapso_texto, stock))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte: {err}", parent=ventana)
    finally:
        cursor.close()
        mydb.close()
        
class PDFConMembrete(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.membrete_superior_altura = 20
        self.membrete_inferior_altura = 15
        self.margen_horizontal = 5  
        self.espacio_entre_tabla_y_membrete = 15
        self.altura_encabezados = 10
        self.altura_fila = 7  
        self.y_despues_membrete_superior = 5 + self.membrete_superior_altura + self.espacio_entre_tabla_y_membrete
        self.filas_por_pagina = self.calcular_filas_por_pagina()

    def calcular_filas_por_pagina(self):
        altura_disponible = self.h - self.t_margin - self.b_margin - self.membrete_inferior_altura - self.y_despues_membrete_superior - self.altura_encabezados - 5
        return int(altura_disponible / self.altura_fila)

    def header(self):
        self.set_y(5)
        ancho_disponible = self.w - (self.l_margin + self.r_margin)
        try:
            self.image(
                "C:/Users/monster/Desktop/src/server/routes/imagenes/OFICIOS-CORPOANDES-1.png",
                x=self.l_margin,
                y=self.get_y(),
                w=ancho_disponible,
                h=self.membrete_superior_altura,
            )
        except FileNotFoundError:
            self.set_font("Arial", 'B', 10)
            self.cell(0, 10, "¡Error: Membrete superior no encontrado!", ln=1, align='C')

    def footer(self):
        self.set_y(-1 * (self.membrete_inferior_altura + 10))
        self.set_x(self.margen_horizontal)
        self.set_font("Arial", 'I', 8)
        self.cell(
            0,
            5,
            "Av. Los Próceres Entrada al Parque La Isla Edificio CORPOANDES Mérida.",
            ln=1,
            align="C",
        )
        self.cell(
            0, 5, "Teléfonos: (0274) 2440511-2446293. Fax (0274) 2440451", ln=1, align="C"
        )
        self.cell(
            0, 5, "Correo corpoandespresidencia@gmail.com", ln=1, align="C"
        )

    def print_titulo(self):
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, "Reporte", ln=1, align='C')
        self.set_font("Arial", size=10)

    def print_encabezados_tabla(self, headers, col_widths, x_start):
        self.set_x(x_start)
        self.set_font("Arial", 'B', 8)  
        self.set_fill_color(200, 220, 255)
        self.set_text_color(0, 0, 0)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, txt=header, border=1, align='C', fill=True)  
        self.ln()


def exportar_tabla_pdf(tabla_treeview):
    """Exporta los datos del Treeview a un PDF con membrete según el diseño y lo abre en el navegador."""

    filename = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Archivos PDF", "*.pdf")],
        title="Guardar reporte como PDF",
    )
    if not filename:
        return

    pdf = PDFConMembrete(orientation="L", unit="mm", format="A4")
    pdf.set_margins(left=5, top=20, right=5)
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.set_font("Arial", size=7)
    pdf.add_page()

    #  Configuración de Anchos de Columna 
    cols = tabla_treeview["columns"]
    headers = [tabla_treeview.heading(col)["text"] for col in cols]
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    lapso_width_fixed = 50  
    col_widths = []

    new_headers = list(headers)
    if "Stock Actual" in new_headers:
        index_stock = new_headers.index("Stock Actual")
        new_headers[index_stock] = "Stock"
    if "Cantidad Consumida" in new_headers:
        index_cantidad = new_headers.index("Cantidad Consumida")
        new_headers[index_cantidad] = "Cantidad"

    if tuple(new_headers) == ("Departamento", "Producto", "Categoría", "Cantidad", "Lapso", "Stock"):
        col_widths = [
            available_width * 0.15,  
            available_width * 0.30,  
            available_width * 0.15, 
            available_width * 0.10,  
            lapso_width_fixed,      
            available_width * 0.10,  
        ]
    elif tuple(new_headers) == ("Categoría", "Producto", "Cantidad", "Lapso", "Stock"):
        remaining_width = available_width - lapso_width_fixed
        col_widths = [
            remaining_width * 0.15,  
            remaining_width * 0.30,  
            remaining_width * 0.10, 
            lapso_width_fixed,      
            remaining_width * 0.10,  
        ]
    else:
        # Configuración de anchos por defecto si no coinciden los encabezados esperados
        col_widths = [available_width / len(headers)] * len(headers)

    total_width = sum(col_widths)
    x_start = (pdf.w - total_width) / 2
    row_height = 7

    # --- Iterar sobre los Datos e Imprimir Filas por página ---
    pdf.set_text_color(0, 0, 0)
    items = tabla_treeview.get_children()
    num_items = len(items)
    filas_impresas = 0

    while filas_impresas < num_items:
        pdf.set_y(pdf.y_despues_membrete_superior)
        pdf.print_titulo()
        pdf.print_encabezados_tabla(new_headers, col_widths, x_start)

        for i in range(filas_impresas, min(filas_impresas + pdf.filas_por_pagina, num_items)):
            child = items[i]
            pdf.set_x(x_start)
            if i % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)
            for j, col in enumerate(cols):
                value = tabla_treeview.set(child, col)
                pdf.cell(col_widths[j], row_height, txt=str(value), border=1, align='L', fill=True)
            pdf.ln()
        filas_impresas += pdf.filas_por_pagina
        if filas_impresas < num_items:
            pdf.add_page()

    pdf.output(filename, "F")
    messagebox.showinfo("Exportar a PDF", "Reporte exportado exitosamente a PDF.", parent=tabla_treeview)

   
    try:
        os.startfile(filename)  
    except AttributeError:
        try:
            os.system(f"open '{filename}'") 
        except:
            os.system(f"xdg-open '{filename}'")  














    


                            # Función para configurar la aplicación
def configuracion():
    """Abre una ventana de configuración para ajustar notificaciones y tema de color."""
    ventana_config = tk.Toplevel(ventana)
    ventana_config.title("Configuración")
    ventana_config.configure(bg="#A9A9A9")  # Fondo gris oscuro medio

    style = ttk.Style(ventana_config)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TCheckbutton", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("TFrame", background="#A9A9A9") # Estilo para los frames


    main_frame = ttk.Frame(ventana_config, style="TFrame")
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    main_frame.grid_columnconfigure(0, weight=1)

    config_frame = ttk.Frame(main_frame, style="TFrame")
    config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    config_frame.columnconfigure(0, weight=1)
    config_frame.columnconfigure(1, weight=1)

    

    backup_restore_frame = ttk.Frame(main_frame, style="TFrame")
    backup_restore_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
    backup_restore_frame.columnconfigure(0, weight=1)
    backup_restore_frame.columnconfigure(1, weight=1)

    def realizar_copia_seguridad():
        try:
            fecha_hora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_copia_seguridad = f"inventario_backup_{fecha_hora}.json"
            shutil.copy2("inventario.json", nombre_copia_seguridad)
            messagebox.showinfo("Copia de Seguridad", f"Copia de seguridad creada: {nombre_copia_seguridad}", parent=ventana_config)
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear la copia de seguridad: {e}", parent=ventana_config)

    btn_copia_seguridad = ttk.Button(backup_restore_frame, text="Copia de Seguridad", command=realizar_copia_seguridad)
    btn_copia_seguridad.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

    def restaurar_copia_seguridad():
        try:
            archivos_copia_seguridad = [f for f in os.listdir() if f.startswith("inventario_backup_")]
            if not archivos_copia_seguridad:
                messagebox.showerror("Error", "No se encontraron copias de seguridad.", parent=ventana_config)
                return

            ventana_restaurar = tk.Toplevel(ventana_config)
            ventana_restaurar.title("Restaurar Copia de Seguridad")
            ventana_restaurar.configure(bg="#A9A9A9")

            label_seleccionar = ttk.Label(ventana_restaurar, text="Seleccione la copia de seguridad a restaurar:", style="CustomLabel.TLabel")
            label_seleccionar.pack(pady=5, padx=10)

            lista_copias_seguridad = tk.Listbox(ventana_restaurar, bg="#ffffff", fg="#000000")
            for archivo in archivos_copia_seguridad:
                lista_copias_seguridad.insert(tk.END, archivo)
            lista_copias_seguridad.pack(padx=10, pady=5, fill="both", expand=True)

            botones_restaurar_eliminar_frame = ttk.Frame(ventana_restaurar, style="TFrame")
            botones_restaurar_eliminar_frame.pack(pady=5, padx=10)
            botones_restaurar_eliminar_frame.columnconfigure(0, weight=1)
            botones_restaurar_eliminar_frame.columnconfigure(1, weight=1)

            def restaurar_seleccionada():
                seleccion = lista_copias_seguridad.curselection()
                if seleccion:
                    archivo_seleccionado = lista_copias_seguridad.get(seleccion[0])
                    shutil.copy2(archivo_seleccionado, "inventario.json")
                    messagebox.showinfo("Restaurar", f"Datos restaurados desde: {archivo_seleccionado}", parent=ventana_restaurar)
                    ventana_restaurar.destroy()
                else:
                    messagebox.showerror("Error", "Seleccione una copia de seguridad.", parent=ventana_restaurar)

            btn_restaurar_seleccionada = ttk.Button(botones_restaurar_eliminar_frame, text="Restaurar", command=restaurar_seleccionada)
            btn_restaurar_seleccionada.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

            def eliminar_seleccionada():
                seleccion = lista_copias_seguridad.curselection()
                if seleccion:
                    archivo_seleccionado = lista_copias_seguridad.get(seleccion[0])
                    os.remove(archivo_seleccionado)
                    lista_copias_seguridad.delete(seleccion[0])
                    messagebox.showinfo("Eliminar", f"Copia de seguridad '{archivo_seleccionado}' eliminada.", parent=ventana_restaurar)
                else:
                    messagebox.showerror("Error", "Seleccione una copia de seguridad.", parent=ventana_restaurar)

            btn_eliminar_seleccionada = ttk.Button(botones_restaurar_eliminar_frame, text="Eliminar", command=eliminar_seleccionada)
            btn_eliminar_seleccionada.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        except Exception as e:
            messagebox.showerror("Error", f"Error al restaurar la copia de seguridad: {e}", parent=ventana_config)

    btn_restaurar = ttk.Button(backup_restore_frame, text="Restaurar", command=restaurar_copia_seguridad)
    btn_restaurar.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

    def gestionar_usuarios():
        ventana_usuarios = tk.Toplevel(ventana_config)
        ventana_usuarios.title("Gestión de Usuarios")
        ventana_usuarios.configure(bg="#A9A9A9")

        label_usuarios = ttk.Label(ventana_usuarios, text="Usuarios:", style="CustomLabel.TLabel")
        label_usuarios.pack(pady=5, padx=10)

        global lista_usuarios_widget
        lista_usuarios_widget = tk.Listbox(ventana_usuarios, bg="#ffffff", fg="#000000")
        actualizar_lista_usuarios()
        lista_usuarios_widget.pack(padx=10, pady=5, fill="both", expand=True)

        frame_crear_usuario = ttk.Frame(ventana_usuarios, style="TFrame")
        frame_crear_usuario.pack(pady=5, padx=10, fill="x")
        frame_crear_usuario.columnconfigure(1, weight=1)

        label_nombre = ttk.Label(frame_crear_usuario, text="Nombre:", style="CustomLabel.TLabel")
        label_nombre.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        entry_nombre = ttk.Entry(frame_crear_usuario, style="CustomEntry.TEntry")
        entry_nombre.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        label_contrasena = ttk.Label(frame_crear_usuario, text="Contraseña:", style="CustomLabel.TLabel")
        label_contrasena.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        entry_contrasena = ttk.Entry(frame_crear_usuario, show="*", style="CustomEntry.TEntry")
        entry_contrasena.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        def verificar_codigo_administrador(codigo):
            return hashlib.sha256(codigo.encode()).hexdigest() == clave_admin

        def crear_usuario():
            nombre = entry_nombre.get()
            contrasena = entry_contrasena.get()
            codigo_admin = simpledialog.askstring("Código de Administrador", "Ingrese el código de administrador:", parent=ventana_usuarios)
            if codigo_admin and verificar_codigo_administrador(codigo_admin):
                if nombre and contrasena:
                    usuarios[nombre] = hashlib.sha256(contrasena.encode()).hexdigest()
                    
                    actualizar_lista_usuarios()
                    messagebox.showinfo("Usuario Creado", f"Usuario '{nombre}' creado.", parent=ventana_usuarios)
                    entry_nombre.delete(0, tk.END)
                    entry_contrasena.delete(0, tk.END)
                    guardar_datos() 
                else:
                    messagebox.showerror("Error", "Ingrese nombre y contraseña.", parent=ventana_usuarios)
            else:
                messagebox.showerror("Error", "Código de administrador incorrecto.", parent=ventana_usuarios)

        btn_crear_usuario = ttk.Button(ventana_usuarios, text="Crear Usuario", command=crear_usuario)
        btn_crear_usuario.pack(pady=5, padx=10, fill="x")

        def eliminar_usuario():
            seleccion = lista_usuarios_widget.curselection()
            if seleccion:
                usuario_seleccionado = lista_usuarios_widget.get(seleccion[0])
                if usuario_seleccionado == "admin":
                    messagebox.showerror("Error", "No se puede eliminar el usuario administrador.", parent=ventana_usuarios)
                    return
                del usuarios[usuario_seleccionado]
                actualizar_lista_usuarios()
                messagebox.showinfo("Usuario Eliminado", f"Usuario '{usuario_seleccionado}' eliminado.", parent=ventana_usuarios)
                guardar_datos() # Guardar después de eliminar un usuario
            else:
                messagebox.showerror("Error", "Seleccione un usuario.", parent=ventana_usuarios)

        btn_eliminar_usuario = ttk.Button(ventana_usuarios, text="Eliminar Usuario", command=eliminar_usuario)
        btn_eliminar_usuario.pack(pady=5, padx=10, fill="x")

    btn_gestion_usuarios = ttk.Button(main_frame, text="Gestión de Usuarios", command=gestionar_usuarios)
    btn_gestion_usuarios.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

    def guardar_configuracion():
      
        
        ventana_config.destroy()
       

    btn_aceptar = ttk.Button(main_frame, text="Aceptar", command=guardar_configuracion)
    btn_aceptar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

def actualizar_lista_usuarios():
    """Actualiza la lista de usuarios en la ventana de gestión de usuarios."""
    if 'lista_usuarios_widget' in globals():
        lista_usuarios_widget.delete(0, tk.END)
        for usuario in usuarios:
            lista_usuarios_widget.insert(tk.END, usuario)



def mostrar_notificacion_bajo_stock():
    """Muestra una notificación de advertencia general sobre bajo stock."""
    global ventana  # Hacer la variable 'ventana' global
    umbral_stock_minimo = 1  # Ajusta este valor según tus necesidades
    productos_bajo_stock = []
    for producto, datos in inventario.items():
        if datos["stock"] < umbral_stock_minimo:
            productos_bajo_stock.append(producto)

    if productos_bajo_stock:
        mensaje = "¡Advertencia! Hay productos con bajo stock"

        # Crear ventana de notificación flotante
        ventana_notificacion = tk.Toplevel(ventana)
        ventana_notificacion.title("Advertencia: Bajo Stock")
        ventana_notificacion.geometry("+{}+0".format(ventana.winfo_screenwidth() - 300))  # Posición superior derecha
        ventana_notificacion.overrideredirect(True)  # Eliminar bordes y barra de título
        ventana_notificacion.configure(bg="yellow")

        # Etiqueta con el mensaje
        label_mensaje = ttk.Label(ventana_notificacion, text=mensaje, background="yellow", foreground="black", padding=10, font=("Segoe UI", 10, "bold"))
        label_mensaje.pack()

        # Botón para cerrar la notificación
        boton_cerrar = ttk.Button(ventana_notificacion, text="Cerrar", command=ventana_notificacion.destroy)
        boton_cerrar.pack(pady=5)

        # Destruir la notificación después de un tiempo (opcional)
        ventana_notificacion.after(5000, ventana_notificacion.destroy)

def importar_datos():
    """Importa datos desde el archivo JSON y actualiza el inventario."""
    global inventario, entradas_departamentos  # Asegurarse de que estamos usando las variables globales

    try:
        with open("inventario.json", "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        inventario = {}
        for producto, datos_producto in datos.get("inventario", {}).items():
            try:
                fecha_entrada = datetime.date.fromisoformat(datos_producto["fecha_entrada"]) if datos_producto["fecha_entrada"] and datos_producto["fecha_entrada"] != 'None' else None
                fecha_salida = datetime.date.fromisoformat(datos_producto["fecha_salida"]) if datos_producto["fecha_salida"] and datos_producto["fecha_salida"] != 'None' else None
            except ValueError:
                messagebox.showerror("Error", f"Fecha inválida para el producto {producto}. Se omitirá.")
                continue  # Saltar al siguiente producto
            inventario[producto] = {
                **datos_producto,
                "fecha_entrada": fecha_entrada,
                "fecha_salida": fecha_salida
            }
        # Asegurarse de que entradas_departamentos sea una lista
        entradas_departamentos = datos.get("entradas_departamentos", [])
        if not isinstance(entradas_departamentos, list): #Verificamos si es lista, sino se asigna una lista vacía.
            entradas_departamentos = []

        messagebox.showinfo("Importar Datos", f"Se importaron {len(inventario)} productos.")

    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró el archivo inventario.json.")
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Error al cargar los datos: Formato JSON incorrecto.\nDetalles: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al importar los datos: {e}")

def exportar_datos():
    """Exporta los datos del inventario a un archivo CSV."""
    global inventario  # Asegurarse de que estamos usando la variable global

    try:
        archivo = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Archivos CSV", "*.csv")])

        if archivo:
            with open(archivo, 'w', newline='', encoding='utf-8') as file:
                campos = ["producto", "categoria", "destino_entrada", "entrada", "salida", "stock", "unidad_medida", "fecha_entrada", "fecha_salida", "destino_salida"]
                escritor_csv = csv.DictWriter(file, fieldnames=campos)
                escritor_csv.writeheader()

                for producto, datos in inventario.items():
                    # Verificar si las fechas son válidas antes de formatearlas
                    fecha_entrada = datos["fecha_entrada"]
                    fecha_salida = datos["fecha_salida"]

                    if isinstance(fecha_entrada, datetime.date):
                        fecha_entrada_str = fecha_entrada.strftime("%Y-%m-%d")
                    else:
                        fecha_entrada_str = "Fecha no disponible"  # O algún otro valor predeterminado

                    if isinstance(fecha_salida, datetime.date):
                        fecha_salida_str = fecha_salida.strftime("%Y-%m-%d")
                    else:
                        fecha_salida_str = "Fecha no disponible"  # O algún otro valor predeterminado

                    fila = {
                        "producto": producto,
                        "categoria": datos["categoria"],
                        "destino_entrada": datos["destino_entrada"],
                        "entrada": datos["entrada"],
                        "salida": datos["salida"],
                        "stock": datos["stock"],
                        "unidad_medida": datos["unidad_medida"],
                        "fecha_entrada": fecha_entrada_str,
                        "fecha_salida": fecha_salida_str,
                        "destino_salida": datos["destino_salida"]
                    }
                    escritor_csv.writerow(fila)

            messagebox.showinfo("Exportar Datos", f"Se exportaron {len(inventario)} productos.")

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al exportar los datos: {e}")

def guardar_como():
    """Permite al usuario elegir la ubicación y el nombre del archivo para guardar."""
    archivo = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Archivos JSON", "*.json")])
    if archivo:
        guardar_datos(archivo)
            














                                    #Funcion de Mostrar el Menu


def mostrar_menu():
    """Muestra el menú principal con la estructura original y colores oscuros."""
    global ventana

    ventana = tk.Tk()
    ventana.title("Menú Principal")
    ventana.configure(bg="#263238")

    #
    # --- Barra de Menú Superior   ---
    menu_principal = tk.Menu(ventana)
    ventana.config(menu=menu_principal)

    menu_archivo = tk.Menu(menu_principal, tearoff=0)
    menu_principal.add_cascade(label="Archivo", menu=menu_archivo)
    menu_archivo.add_command(label="Guardar", command=guardar_datos)
    menu_archivo.add_command(label="Guardar como...", command=guardar_como)
    menu_archivo.add_command(label="Importar", command=importar_datos)
    menu_archivo.add_command(label="Exportar", command=exportar_datos)
    menu_archivo.add_separator()
    menu_archivo.add_command(label="Salir", command=ventana.destroy)

    menu_reportes = tk.Menu(menu_principal, tearoff=0)
    menu_principal.add_cascade(label="Reportes", menu=menu_reportes)
    menu_reportes.add_command(label="Productos con bajo stock", command=generar_reporte_bajo_stock)
    menu_reportes.add_command(label="Historial de entradas", command=generar_reporte_entradas)
    menu_reportes.add_command(label="Historial de salidas", command=generar_reporte_salidas)
    menu_reportes.add_command(label="Historial de salidas en espera", command=generar_reporte_salidas_espera)
    menu_reportes.add_command(label="Reporte completo", command=ventana_reportes)

    menu_configuracion = tk.Menu(menu_principal, tearoff=0)
    menu_principal.add_cascade(label="Configuración", menu=menu_configuracion)
    menu_configuracion.add_command(label="Ajustes generales", command=configuracion)


    # --- Estilos ttk Personalizados ---
    style = ttk.Style(ventana)
    style.theme_use('clam')

    style.configure("MenuButtonDarkGrid.TButton",
                    foreground="#eceff1",
                    background="#37474F",
                    font=("Segoe UI", 12, "bold"),
                    padding=15,
                    relief="raised",
                    anchor="center")
    style.map("MenuButtonDarkGrid.TButton",
              background=[('active', '#455a64')],
              foreground=[('active', '#fff')])

    # --- Cargar Logos de los botones ---
    try:
        ventana.logo_agregar_img = tk.PhotoImage(file="C:/Users/monster/Desktop/src/server/routes/imagenes/agregar-producto.png").subsample(3, 3)
        print(f"Cargado logo_agregar: {ventana.logo_agregar_img}") # Debugging
        logo_agregar = ventana.logo_agregar_img

        ventana.logo_salida_img = tk.PhotoImage(file="C:/Users/monster/Desktop/src/server/routes/imagenes/espera.png").subsample(3, 3)
        print(f"Cargado logo_salida: {ventana.logo_salida_img}") # Debugging
        logo_salida = ventana.logo_salida_img

        ventana.logo_mostrar_img = tk.PhotoImage(file="C:/Users/monster/Desktop/src/server/routes/imagenes/inventario.png").subsample(3, 3)
        print(f"Cargado logo_mostrar: {ventana.logo_mostrar_img}") # Debugging
        logo_mostrar = ventana.logo_mostrar_img

        ventana.logo_consumo_img = tk.PhotoImage(file="C:/Users/monster/Desktop/src/server/routes/imagenes/consumo.png").subsample(3, 3)
        print(f"Cargado logo_consumo: {ventana.logo_consumo_img}") # Debugging
        logo_consumo = ventana.logo_consumo_img

    except tk.TclError as e:
        print(f"Error AL CARGAR imágenes: {e}")
        logo_agregar = None
        logo_salida = None
        logo_mostrar = None
        logo_consumo = None

    # --- Crear botones para cada opción con logos encima ---
    print(f"Valor de logo_agregar ANTES del botón: {logo_agregar}") # Debugging
    boton_agregar = ttk.Button(ventana, text="Agregar producto", image=ventana.logo_agregar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=agregar_producto)
    boton_agregar.image = ventana.logo_agregar_img  # Guardar referencia

    boton_salida = ttk.Button(ventana, text="Realizar salida en espera", image=ventana.logo_salida_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=realizar_salida)
    boton_salida.image = ventana.logo_salida_img  # Guardar referencia

    boton_mostrar = ttk.Button(ventana, text="Mostrar inventario", image=ventana.logo_mostrar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=mostrar_inventario)
    boton_mostrar.image = ventana.logo_mostrar_img  # Guardar referencia

    boton_consumo = ttk.Button(ventana, text="Calcular consumo por departamento", image=ventana.logo_consumo_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=calcular_consumo_departamento)
    boton_consumo.image = ventana.logo_consumo_img  # Guardar referencia

    # --- Organizar los botones en una cuadrícula ---
    boton_agregar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    boton_salida.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
    boton_mostrar.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
    boton_consumo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    # --- Cargar y mostrar el logo en la esquina inferior derecha ---
    try:
        ventana.logo_app_img = tk.PhotoImage(file="C:/Users/monster/Desktop/src/server/routes/imagenes/NEVA.png").subsample(4, 4) 
        logo_app_label = tk.Label(ventana, image=ventana.logo_app_img, bd=0, highlightthickness=0, bg="#263238") 
        logo_app_label.image = ventana.logo_app_img 
        logo_app_label.place(relx=1.0, rely=1.0, anchor=tk.SE, x=-10, y=-10) 
    except tk.TclError as e:
        print(f"Error al cargar el logo de la aplicación: {e}")

    # --- Configurar la expansión de las columnas ---
    ventana.grid_columnconfigure(0, weight=1)
    ventana.grid_columnconfigure(1, weight=1)


    
    
    mostrar_notificacion_bajo_stock()

    ventana.mainloop()

# --- Ejecución de la aplicación ---
cargar_datos()


iniciar_sesion()
