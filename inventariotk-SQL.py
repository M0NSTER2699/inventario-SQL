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
import subprocess
import threading
import sys

import csv
from tkinter import filedialog, messagebox
from tkcalendar import Calendar

from PIL import Image as pilimage


from fpdf import FPDF
import uuid

import mysql.connector

#conector a la base de datos mysql

def conectar_mysql():
    try:
        mydb = mysql.connector.connect(
            host="192.168.0.5",       
            user="almacen",
            password="Almacen*",     
            database="corpoandes_base_datos_almacen" 
        )
        return mydb
    except mysql.connector.Error as err:
        messagebox.showerror(f"Error al conectar a MySQL: {err}")
        return None



lista_usuarios_widget = None
clave_admin = hashlib.sha256("NEVA".encode()).hexdigest()
current_user_role_is_admin = False
inventario = {}
entradas_departamentos = []
tabla_inventario_principal = None
ventana_reporte_salidas_espera = None
tabla_salidas_espera = None
menu_contextual = None
ventana = None
ventana_reporte_entradas = None 
tabla_entradas = None          
entry_busqueda_entradas = None 
categoria_seleccionada_reporte_entradas = None 
ventana_reporte_salidas = None
tree = None 
entry_busqueda_salidas = None
departamento_seleccionado_reporte = None
ventana_consumo = None
tabla_consumo_global_ref = None









                            #guarda todo los datos del programa

def guardar_datos():
    """Guarda los datos en un archivo sql."""
    global datos_consumo_para_guardar, datos_reportes_para_guardar, usuarios, entradas_departamentos 

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





                        #carga todos los datos al programa

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
            guardar_datos() 
    

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
        if cursor.fetchone() is None:  
            es_admin = 1 if nombre_usuario == "admin" else 0
            val = (nombre_usuario, contrasena_hash, es_admin)
            try:
                cursor.execute(sql_insert, val)
            except mysql.connector.Error as err:
                print(f"Error al insertar usuario {nombre_usuario}: {err}")

    mydb.commit()
    cursor.close()
    mydb.close()
    

def insertar_inventario_mysql(inventario):
    mydb = conectar_mysql()
    if mydb is None:
        return

    cursor = mydb.cursor()
    sql_insert = "INSERT INTO productos (Codigo, Nombre, Categoria, Stock, UnidadMedida, FechaEntrada, FechaSalida, Departamento) VALUES (%s, %s, %s, %s, %s, %s, %s,%s)"
    sql_check = "SELECT Codigo FROM productos WHERE Codigo = %s"

    for codigo, datos_producto in inventario.items():
        cursor.execute(sql_check, (codigo,))
        if cursor.fetchone() is None:    
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
    





                        #ES EL CODIGO DE ACCESO EN ESTE CASO NEVA
        

def verificar_clave(ventana_clave, entry_clave, ventana_login):
    """
    Verifica la clave maestra de administrador para el acceso adicional.
    Esta función solo se llama si el usuario ya es administrador en la DB y marcó la casilla.
    """
    global current_user_role_is_admin 

    clave_ingresada_hash = hashlib.sha256(entry_clave.get().encode()).hexdigest()
    
    if clave_ingresada_hash == clave_admin: 
        messagebox.showinfo("Acceso Permitido", "Acceso de administrador concedido.")
        ventana_clave.destroy()
        ventana_login.destroy()
        current_user_role_is_admin = True 
        mostrar_menu() 
    else:
        messagebox.showerror("Acceso Denegado", "Clave de administrador incorrecta.")
        current_user_role_is_admin = False 



        #INICIA SESION AL PROGRAMA CON EL USUARIO PRESETERMINADO Y CREADOS DENTRO DEL PROGRAMA

def resource_path(relative_path):
    """ ESTA FUNCION SE UTULIZA PARA COMPILAR TODOS LOS LOGOS AL EJECUTABLE """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def iniciar_sesion():
    """Permite al usuario iniciar sesión y establece los privilegios."""
    global ventana_login, current_user_role_is_admin

    
    current_user_role_is_admin = False 

    ventana_login = tk.Tk()
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
       
        imagen_logo = Image.open(resource_path("server/routes/imagenes/logo.png"))
        imagen_logo = imagen_logo.resize((300, 300))
        logo = ImageTk.PhotoImage(imagen_logo)
        label_logo = tk.Label(frame_logo, image=logo, bg="#263238")
        label_logo.image = logo
        label_logo.pack(fill="both", expand=True)
    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró el archivo del logo. Asegúrate de que 'logo.png' esté en la ruta correcta.")
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar la imagen del logo: {e}")


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
        global current_user_role_is_admin 

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
                es_admin_db_bool = bool(es_admin_db) 

                if contrasena_hash_ingresada == contrasena_hash_db:
                    if es_admin_seleccionado and es_admin_db_bool: 
                        ventana_clave = tk.Toplevel(ventana_login)
                        ventana_clave.title("Clave de Administrador")
                        ventana_clave.configure(bg="#263238")

                        style_clave = ttk.Style(ventana_clave)
                        style_clave.theme_use('clam')
                        style_clave.configure("TLabel", foreground="#eceff1", background="#263238", font=("Arial", 14))
                        style_clave.configure("TEntry", fieldbackground="#f0f0f0", foreground="black", font=("Arial", 14))
                        style_clave.configure("TButton", foreground="#eceff1", background="#008000", font=("Arial", 14, "bold"))
                        
                        ttk.Label(ventana_clave, text="Clave:", background="#263238", foreground="#eceff1", font=("Arial", 14)).pack(pady=5)
                        entry_clave_admin_local = ttk.Entry(ventana_clave, show="*", font=("Arial", 14), width=20)
                        entry_clave_admin_local.pack(pady=5)

                       
                        ttk.Button(ventana_clave, text="Verificar", command=lambda: verificar_clave(ventana_clave, entry_clave_admin_local, ventana_login), style="TButton").pack(pady=10)
                        
                       
                        ventana_login.wait_window(ventana_clave) 
                     

                    elif not es_admin_seleccionado and not es_admin_db_bool: 
                        current_user_role_is_admin = False # 
                        messagebox.showinfo("Acceso Permitido", "Acceso de operador concedido.")
                        ventana_login.destroy()
                        mostrar_menu() 
                    elif es_admin_seleccionado and not es_admin_db_bool: 
                        messagebox.showerror("Error", "Este usuario no tiene permisos de administrador.")
                        current_user_role_is_admin = False 

                    elif not es_admin_seleccionado and es_admin_db_bool: 
                        messagebox.showerror("Error", "Debe marcar la casilla de 'Administrador' para este usuario.")
                        current_user_role_is_admin = False 

                else:
                    messagebox.showerror("Error", "Contraseña incorrecta.")
                    current_user_role_is_admin = False
            else:
                messagebox.showerror("Error", "Usuario no encontrado.")
                current_user_role_is_admin = False

        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al consultar la base de datos: {err}")
            current_user_role_is_admin = False
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado durante el inicio de sesión: {e}")
            current_user_role_is_admin = False
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



                        #INGRESA PRODUCTOS NUEVOS AL INVENTARIO
       
def agregar_producto():
    """Agrega un producto al inventario con fecha de entrada manual y código basado en la categoría."""

    def generar_codigo(categoria_nombre):
        """Genera un código único basado en la categoría consultando MySQL."""
        prefijos_categoria = {
            "COMIDA": "COM",
            "MATERIALES Y ARTICULOS DE OFICINA": "MAT",
            "TONNER": "TON",
            "MATERIAL DE LIMPIEZA": "LIM",
            "PLASTICO": "PLA",
            "MATERIAL DE FERRETERIA": "FER",
            "OTROS": "OTR"
        }
        prefijo = prefijos_categoria.get(categoria_nombre.upper(), "GEN")

        mydb = conectar_mysql()
        if not mydb:
            return f"{prefijo}-001"

        cursor = mydb.cursor()
        categoria_id = None
        query_categoria_id = "SELECT CategoriaID FROM categorias WHERE NombreCategoria = %s"
        try:
            cursor.execute(query_categoria_id, (categoria_nombre.upper(),))
            resultado_categoria = cursor.fetchone()
            if resultado_categoria:
                categoria_id = resultado_categoria[0]
            else:
                return f"{prefijo}-001"
        except mysql.connector.Error as err:
            messagebox.showerror("Error al obtener CategoriaID", f"Error: {err}")
            return f"{prefijo}-001"

        query = """
            SELECT Codigo
            FROM productos
            WHERE CategoriaID = %s AND Codigo LIKE %s
        """
        codigos_existentes = []
        try:
            cursor.execute(query, (categoria_id, f"{prefijo}-%"))
            resultados = cursor.fetchall()
            for resultado in resultados:
                codigos_existentes.append(resultado[0])
        except mysql.connector.Error as err:
            messagebox.showerror("Error al obtener códigos", f"Error: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

        numeros_existentes = []
        for codigo in codigos_existentes:
            try:
                numero = int(codigo.split("-")[1])
                numeros_existentes.append(numero)
            except (IndexError, ValueError):
                continue

        if not numeros_existentes:
            return f"{prefijo}-001"
        else:
            ultimo_numero = max(numeros_existentes)
            return f"{prefijo}-{ultimo_numero + 1:03d}"

    def agregar():
        producto_nombre = entry_producto.get().strip()
        categoria_nombre = categoria_var.get().strip()
        entrada_cantidad_str = entry_entrada.get().strip()
        unidad_medida = unidad_medida_var.get().strip()
        fecha_entrada_str = entry_fecha_entrada.get().strip()

        
        if not producto_nombre:
            messagebox.showwarning("Campos Incompletos", "Por favor, ingrese el nombre del producto.")
            return
        if not categoria_nombre or categoria_nombre == "Añadir nueva":
            messagebox.showwarning("Campos Incompletos", "Por favor, seleccione o añada una categoría válida.")
            return
        if not entrada_cantidad_str:
            messagebox.showwarning("Campos Incompletos", "Por favor, ingrese la cantidad de entrada.")
            return
        if not unidad_medida or unidad_medida == "Añadir nueva":
            messagebox.showwarning("Campos Incompletos", "Por favor, seleccione o añada una unidad de medida válida.")
            return
        if not fecha_entrada_str:
            messagebox.showwarning("Campos Incompletos", "Por favor, ingrese la fecha de entrada.")
            return

        
        try:
            entrada_cantidad = float(entrada_cantidad_str)
            if entrada_cantidad <= 0:
                messagebox.showwarning("Cantidad Inválida", "La cantidad de entrada debe ser un número positivo.")
                return
        except ValueError:
            messagebox.showwarning("Cantidad Inválida", "La cantidad de entrada debe ser un número entero válido.")
            return

        
        try:
            fecha_entrada = datetime.datetime.strptime(fecha_entrada_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Fecha Inválida", "El formato de la fecha debe ser AAAA-MM-DD (ej. 2025-05-26).")
            return

        
        codigo_producto = generar_codigo(categoria_nombre)

        mydb = conectar_mysql()
        if not mydb:
            return

        cursor = mydb.cursor()

        
        query_categoria_id = "SELECT CategoriaID FROM categorias WHERE NombreCategoria = %s"
        categoria_id = None
        try:
            cursor.execute(query_categoria_id, (categoria_nombre.upper(),))
            resultado_categoria = cursor.fetchone()
            if resultado_categoria:
                categoria_id = resultado_categoria[0]
            else:
                messagebox.showerror("Error", f"La categoría '{categoria_nombre}' no existe en la base de datos.")
                mydb.close()
                return
        except mysql.connector.Error as err:
            messagebox.showerror("Error al obtener CategoriaID", f"Error: {err}")
            mydb.close()
            return

        
        query_verificar_producto = """
            SELECT COUNT(*)
            FROM productos
            WHERE Nombre = %s AND CategoriaID = %s AND UnidadMedida = %s
        """
        try:
            cursor.execute(query_verificar_producto, (producto_nombre, categoria_id, unidad_medida))
            count = cursor.fetchone()[0]
            if count > 0:
                messagebox.showerror(
                    "Error de Duplicado",
                    f"Ya existe un producto con el nombre '{producto_nombre}', categoría '{categoria_nombre}' "
                    f"y unidad de medida '{unidad_medida}'.\n"
                    "Por favor, elija un nombre, categoría o unidad de medida diferente o actualice el producto existente."
                )
                mydb.close()
                return 
        except mysql.connector.Error as err:
            messagebox.showerror("Error de base de datos", f"Error al verificar producto existente: {err}")
            mydb.close()
            return

        destino_entrada_nombre = "Almacén principal"

        sql_producto = """
            INSERT INTO productos (Codigo, Nombre, CategoriaID, Stock, UnidadMedida, FechaEntrada)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        val_producto = (codigo_producto, producto_nombre, categoria_id, entrada_cantidad, unidad_medida, fecha_entrada)
        try:
            cursor.execute(sql_producto, val_producto)
            producto_id = cursor.lastrowid

            sql_entrada = """
                INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, UnidadMedida, FechaEntrada, Destino)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            val_entrada = (producto_id, codigo_producto, entrada_cantidad, unidad_medida, fecha_entrada, destino_entrada_nombre) # Agrega unidad_medida aquí
            cursor.execute(sql_entrada, val_entrada)

            mydb.commit()
            messagebox.showinfo("Producto Agregado", f"Producto '{producto_nombre}' agregado al inventario con código: {codigo_producto}, Fecha de entrada: {fecha_entrada}, Destino: {destino_entrada_nombre}")

           
            entry_producto.delete(0, tk.END)
            entry_entrada.delete(0, tk.END)
            entry_fecha_entrada.delete(0, tk.END)
            
            categoria_var.set("")
            unidad_medida_var.set("")


        except mysql.connector.Error as err:
            mydb.rollback()
            messagebox.showerror("Error al agregar producto", f"Error: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

    def agregar_categoria_predeterminada_a_db(nombre_categoria):
        """Agrega una categoría a la DB si no existe."""
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                sql_verificar = "SELECT CategoriaID FROM categorias WHERE NombreCategoria = %s"
                cursor.execute(sql_verificar, (nombre_categoria.upper(),))
                if not cursor.fetchone():
                    sql_insertar = "INSERT INTO categorias (NombreCategoria) VALUES (%s)"
                    cursor.execute(sql_insertar, (nombre_categoria.upper(),))
                    mydb.commit()
                    print(f"Categoría '{nombre_categoria}' agregada a la base de datos.")
                
            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error", f"Error al agregar categoría '{nombre_categoria}': {err}")
            finally:
                if cursor:
                    cursor.close()
                if mydb and mydb.is_connected():
                    mydb.close()

 
    def agregar_unidad_predeterminada_a_db(nombre_unidad):
        """Agrega una unidad de medida a la DB si no existe."""
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                sql_verificar = "SELECT UnidadID FROM unidades_medida WHERE NombreUnidad = %s"
                cursor.execute(sql_verificar, (nombre_unidad,))
                if not cursor.fetchone():
                    sql_insertar = "INSERT INTO unidades_medida (NombreUnidad) VALUES (%s)"
                    cursor.execute(sql_insertar, (nombre_unidad,))
                    mydb.commit()
                    print(f"Unidad de medida '{nombre_unidad}' agregada a la base de datos.")
                
            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error", f"Error al agregar unidad de medida '{nombre_unidad}': {err}")
            finally:
                if cursor:
                    cursor.close()
                if mydb and mydb.is_connected():
                    mydb.close()


    def agregar_nueva_categoria():
        def guardar_nueva():
            nueva_cat = nueva_categoria_entry.get().strip().upper()
            if nueva_cat:
                if nueva_cat not in categorias_list: 
                    mydb = conectar_mysql()
                    if mydb:
                        cursor = mydb.cursor()
                        try:
                            
                            sql_insertar_categoria = "INSERT INTO categorias (NombreCategoria) VALUES (%s)"
                            cursor.execute(sql_insertar_categoria, (nueva_cat,))
                            mydb.commit()

                            
                            categorias_list.insert(len(categorias_list) - 1, nueva_cat)
                            combo_categoria['values'] = categorias_list
                            categoria_var.set(nueva_cat) 
                            ventana_nueva_categoria.destroy()
                            messagebox.showinfo("Categoría Agregada", f"Categoría '{nueva_cat}' agregada exitosamente.")
                        except mysql.connector.Error as err:
                            mydb.rollback()
                            if "Duplicate entry" in str(err): 
                                messagebox.showerror("Error al guardar categoría", f"La categoría '{nueva_cat}' ya existe en la base de datos.")
                                
                                recargar_listas_categorias_y_unidades()
                                categoria_var.set(nueva_cat) 
                                ventana_nueva_categoria.destroy()
                            else:
                                messagebox.showerror("Error al guardar categoría", f"Error: {err}")
                        finally:
                            if cursor:
                                cursor.close()
                            if mydb and mydb.is_connected():
                                mydb.close()
                    else:
                        messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                else:
                    messagebox.showwarning("Advertencia", "La categoría ingresada ya existe en la lista.")
                    categoria_var.set(nueva_cat) 
                    ventana_nueva_categoria.destroy()
            else:
                messagebox.showwarning("Advertencia", "Por favor, ingrese un nombre para la nueva categoría.")

        ventana_nueva_categoria = tk.Toplevel(ventana_agregar)
        ventana_nueva_categoria.title("Nueva Categoría")
        ventana_nueva_categoria.transient(ventana_agregar)
        ventana_nueva_categoria.grab_set()
        ttk.Label(ventana_nueva_categoria, text="Ingrese la nueva categoría:", style="CustomLabel.TLabel").pack(padx=10, pady=10)
        nueva_categoria_entry = ttk.Entry(ventana_nueva_categoria, style="CustomEntry.TEntry")
        nueva_categoria_entry.pack(padx=10, pady=5)
        ttk.Button(ventana_nueva_categoria, text="Guardar", command=guardar_nueva, style="CustomButton.TButton").pack(pady=10)
        ventana_nueva_categoria.wait_window() 

    def agregar_nueva_unidad():
        def guardar_nueva_unidad():
            nueva_unidad = nueva_unidad_entry.get().strip()
            if nueva_unidad:
                if nueva_unidad not in unidades_list:
                    mydb = conectar_mysql()
                    if mydb:
                        cursor = mydb.cursor()
                        try:
                            
                            sql_insertar_unidad = "INSERT INTO unidades_medida (NombreUnidad) VALUES (%s)"
                            cursor.execute(sql_insertar_unidad, (nueva_unidad,))
                            mydb.commit()

                           
                            unidades_list.insert(len(unidades_list) - 1, nueva_unidad)
                            combo_unidad_medida['values'] = unidades_list
                            unidad_medida_var.set(nueva_unidad) 
                            ventana_nueva_unidad.destroy()
                            messagebox.showinfo("Unidad de Medida Agregada", f"Unidad de medida '{nueva_unidad}' agregada exitosamente.")
                        except mysql.connector.Error as err:
                            mydb.rollback()
                            if "Duplicate entry" in str(err): 
                                messagebox.showerror("Error al guardar unidad", f"La unidad de medida '{nueva_unidad}' ya existe en la base de datos.")
                               
                                recargar_listas_categorias_y_unidades()
                                unidad_medida_var.set(nueva_unidad)
                                ventana_nueva_unidad.destroy()
                            else:
                                messagebox.showerror("Error al guardar unidad", f"Error: {err}")
                        finally:
                            if cursor:
                                cursor.close()
                            if mydb and mydb.is_connected():
                                mydb.close()
                    else:
                        messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                else:
                    messagebox.showwarning("Advertencia", "La unidad de medida ingresada ya existe en la lista.")
                    unidad_medida_var.set(nueva_unidad) 
                    ventana_nueva_unidad.destroy()
            else:
                messagebox.showwarning("Advertencia", "Por favor, ingrese un nombre para la nueva unidad de medida.")


        ventana_nueva_unidad = tk.Toplevel(ventana_agregar)
        ventana_nueva_unidad.title("Nueva Unidad de Medida")
        ventana_nueva_unidad.transient(ventana_agregar)
        ventana_nueva_unidad.grab_set()
        ttk.Label(ventana_nueva_unidad, text="Ingrese la nueva unidad de medida:", style="CustomLabel.TLabel").pack(padx=10, pady=10)
        nueva_unidad_entry = ttk.Entry(ventana_nueva_unidad, style="CustomEntry.TEntry")
        nueva_unidad_entry.pack(padx=10, pady=5)
        ttk.Button(ventana_nueva_unidad, text="Guardar", command=guardar_nueva_unidad, style="CustomButton.TButton").pack(pady=10)
        ventana_nueva_unidad.wait_window() 


    def cargar_categorias_desde_db():
        """Carga las categorías desde la base de datos."""
        mydb = conectar_mysql()
        categorias = []
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT NombreCategoria FROM categorias ORDER BY NombreCategoria")
                for (nombre,) in cursor:
                    categorias.append(nombre)
            except mysql.connector.Error as err:
                messagebox.showerror("Error DB", f"Error al cargar categorías: {err}")
            finally:
                if cursor:
                    cursor.close()
                if mydb and mydb.is_connected():
                    mydb.close()
        return categorias

    def cargar_unidades_desde_db():
        """Carga las unidades de medida desde la base de datos."""
        mydb = conectar_mysql()
        unidades = []
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT NombreUnidad FROM unidades_medida ORDER BY NombreUnidad")
                for (nombre,) in cursor:
                    unidades.append(nombre)
            except mysql.connector.Error as err:
                messagebox.showerror("Error DB", f"Error al cargar unidades de medida: {err}")
            finally:
                if cursor:
                    cursor.close()
                if mydb and mydb.is_connected():
                    mydb.close()
        return unidades

    def recargar_listas_categorias_y_unidades():
        """Recarga ambas listas y actualiza los Comboboxes."""
        global categorias_list, unidades_list 
        categorias_list = cargar_categorias_desde_db()
        unidades_list = cargar_unidades_desde_db()

        
        if "Añadir nueva" not in categorias_list:
            categorias_list.append("Añadir nueva")
        if "Añadir nueva" not in unidades_list:
            unidades_list.append("Añadir nueva")

        combo_categoria['values'] = categorias_list
        combo_unidad_medida['values'] = unidades_list

       
        if categoria_var.get() not in categorias_list:
            categoria_var.set(categorias_list[0] if categorias_list else "")
        if unidad_medida_var.get() not in unidades_list:
            unidad_medida_var.set(unidades_list[0] if unidades_list else "")


    def mostrar_opciones_categoria(event):
        if categoria_var.get() == "Añadir nueva":
            agregar_nueva_categoria()
            

    def mostrar_opciones_unidad(event):
        if unidad_medida_var.get() == "Añadir nueva":
            agregar_nueva_unidad()
            


    ventana_agregar = tk.Toplevel(ventana)
    ventana_agregar.title("Agregar Producto")
    ventana_agregar.configure(bg="#000080")
    ventana_agregar.grab_set() 
    ventana_agregar.transient(ventana) 

  
    categorias_predeterminadas_inicial = ["COMIDA", "MATERIALES Y ARTICULOS DE OFICINA", "TONNER", "MATERIAL DE LIMPIEZA", "PLASTICO", "MATERIAL DE FERRETERIA", "OTROS"]
    for cat in categorias_predeterminadas_inicial:
        agregar_categoria_predeterminada_a_db(cat)

    unidades_medida_predeterminadas_inicial = ["Unidad", "Litro", "Kilogramo", "Metro", "Caja", "Paquete"]
    for uni in unidades_medida_predeterminadas_inicial:
        agregar_unidad_predeterminada_a_db(uni)

    
    categorias_list = cargar_categorias_desde_db()
    unidades_list = cargar_unidades_desde_db()

   
    if "Añadir nueva" not in categorias_list:
        categorias_list.append("Añadir nueva")
    if "Añadir nueva" not in unidades_list:
        unidades_list.append("Añadir nueva")


    
    categoria_var = tk.StringVar()
    unidad_medida_var = tk.StringVar()

    #categoria_var.set(categorias_list[0] if categorias_list else "")
    #unidad_medida_var.set(unidades_list[0] if unidades_list else "")


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
    combo_categoria = ttk.Combobox(ventana_agregar, textvariable=categoria_var, values=categorias_list, style="TCombobox", state="readonly") # Hazlo readonly
    combo_categoria.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
    combo_categoria.bind("<<ComboboxSelected>>", mostrar_opciones_categoria)

    ttk.Label(ventana_agregar, text="Destino de entrada:", style="CustomLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=10)
    entry_destino_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_destino_entrada.insert(0, "Almacén principal")
    entry_destino_entrada.config(state="readonly")
    entry_destino_entrada.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(ventana_agregar, text="Cantidad de entrada:", style="CustomLabel.TLabel").grid(row=3, column=0, sticky="w", padx=10, pady=10)
    entry_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_entrada.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(ventana_agregar, text="Unidad de medida:", style="CustomLabel.TLabel").grid(row=4, column=0, sticky="w", padx=10, pady=10)
    combo_unidad_medida = ttk.Combobox(ventana_agregar, textvariable=unidad_medida_var, values=unidades_list, style="TCombobox", state="readonly") # Hazlo readonly
    combo_unidad_medida.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
    combo_unidad_medida.bind("<<ComboboxSelected>>", mostrar_opciones_unidad)

    ttk.Label(ventana_agregar, text="Fecha de entrada (YYYY-MM-DD):", style="CustomLabel.TLabel").grid(row=5, column=0, sticky="w", padx=10, pady=10)
    entry_fecha_entrada = ttk.Entry(ventana_agregar, style="CustomEntry.TEntry")
    entry_fecha_entrada.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

    ttk.Button(ventana_agregar, text="Calendario", command=abrir_calendario_local, style="CustomButton.TButton").grid(row=5, column=2, padx=10, pady=10)
    ttk.Button(ventana_agregar, text="Agregar", command=agregar, style="CustomButton.TButton").grid(row=6, column=0, columnspan=3, pady=15, padx=10, sticky="ew")

    ventana_agregar.grid_columnconfigure(1, weight=1)
    ventana_agregar.wait_window() 



    
    
 

                                     #REALIZA UNA SALIDA PENDIENTE(ESPERA)
def realizar_salida():
    """Realiza una salida en espera de productos del inventario, permitiendo búsqueda por nombre o código."""

    def obtener_productos_con_codigo_y_unidad(): 
        """Obtiene la lista de productos (Nombre (Código)) y su UnidadMedida desde la base de datos MySQL."""
        productos_info = []
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            
            query = "SELECT Nombre, Codigo, ProductoID, UnidadMedida FROM productos"
            try:
                cursor.execute(query)
                productos_mysql = cursor.fetchall()
                for nombre, codigo, producto_id, unidad_medida in productos_mysql:
                   
                    productos_info.append((f"{nombre} ({codigo})", unidad_medida)) 
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener productos: {err}")
            finally:
                if mydb.is_connected():
                    cursor.close()
                    mydb.close()
        
        return sorted(productos_info, key=lambda x: x[0]) 

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
    
    def obtener_departamentos_para_combobox():
        departamentos_map = {}
        nombres_departamentos = []
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT DepartamentoID, NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
                for dep_id, dep_nombre in cursor.fetchall():
                    departamentos_map[dep_nombre] = dep_id
                    nombres_departamentos.append(dep_nombre)
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al cargar departamentos: {err}")
            finally:
                if mydb.is_connected():
                    cursor.close()
                    mydb.close()
        return nombres_departamentos, departamentos_map

    def salida_espera():
        
        departamento_nombre_seleccionado = departamento_var.get() 
        
        seleccion_producto_display = combo_producto.get() 
        
        try:
            cantidad = float(entry_cantidad.get())
            if cantidad <= 0:
                messagebox.showerror("Error", "La cantidad debe ser un número positivo.")
                return
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido (entero o decimal).")
            return

        producto_nombre = obtener_nombre_desde_seleccion(seleccion_producto_display)
        codigo_producto = obtener_codigo_desde_seleccion(seleccion_producto_display)

        if not codigo_producto:
            messagebox.showerror("Error", "Por favor, seleccione un producto válido de la lista.")
            return
            
        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        
        try:
            
            query_producto_info = "SELECT ProductoID, UnidadMedida FROM productos WHERE Codigo = %s"
            cursor.execute(query_producto_info, (codigo_producto,))
            resultado_info = cursor.fetchone()

            if not resultado_info:
                messagebox.showerror("Error", f"No se encontró el producto con código: {codigo_producto}")
                return
            
            producto_id = resultado_info[0]
            unidad_medida_producto = resultado_info[1] 

            
            if not unidad_medida_producto:
                 messagebox.showwarning("Advertencia", f"El producto '{producto_nombre}' no tiene una unidad de medida definida. Se agregará sin unidad de medida.")
            
            departamento_id = departamentos_map_global.get(departamento_nombre_seleccionado)
            
            if departamento_id is None:
                messagebox.showerror("Error", f"Departamento '{departamento_nombre_seleccionado}' no válido.")
                return

           
            sql_insert_salida = """
                INSERT INTO salidas_espera (ProductoID, CodigoProducto, Cantidad, UnidadMedida, DepartamentoID, FechaSolicitud, Estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            fecha_actual = datetime.date.today() 
           
            val_salida = (producto_id, codigo_producto, cantidad, unidad_medida_producto, departamento_id, fecha_actual, "Pendiente")
            
            cursor.execute(sql_insert_salida, val_salida)
            mydb.commit()
            
            messagebox.showinfo("Salida en Espera", f"{cantidad} {unidad_medida_producto} de '{producto_nombre}' (código: {codigo_producto}) solicitadas para {departamento_nombre_seleccionado}. Agregado a la lista de espera.")
            entry_cantidad.delete(0, tk.END)
            
        except mysql.connector.Error as err:
            mydb.rollback()
            messagebox.showerror("Error al agregar salida en espera", f"Error: {err}")
        except Exception as e:
            mydb.rollback()
            messagebox.showerror("Error inesperado", f"Ocurrió un error: {e}")
        finally:
            if mydb.is_connected():
                cursor.close()
                mydb.close()


    ventana_salida_espera = tk.Toplevel(ventana)
    ventana_salida_espera.title("Salida en Espera")
    ventana_salida_espera.configure(bg="#000080")

    
    style = ttk.Style(ventana_salida_espera)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#000080", font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("CustomButton.TButton", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"), padding=8, relief="raised", anchor="center")
    style.map("CustomButton.TButton", background=[('active', '#c1c1c1')], foreground=[('active', '#000000')])

    
    productos_con_codigo_y_unidad = obtener_productos_con_codigo_y_unidad()
    
    productos_display_strings = [item[0] for item in productos_con_codigo_y_unidad]


    ttk.Label(ventana_salida_espera, text="Nombre del producto (Código):", style="CustomLabel.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=10)
    
    combo_producto = ttk.Combobox(ventana_salida_espera, values=productos_display_strings, style="TCombobox")
    combo_producto.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    
    def filtrar_productos(event):
        valor_escrito = combo_producto.get().lower()
        
        productos_filtrados_display = [
            pc_display
            for pc_display, _ in productos_con_codigo_y_unidad 
            if valor_escrito in pc_display.lower()
        ]
        combo_producto["values"] = productos_filtrados_display

    
    combo_producto.bind("<KeyRelease>", filtrar_productos)

    ttk.Label(ventana_salida_espera, text="Cantidad de salida:", style="CustomLabel.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=10)
    entry_cantidad = ttk.Entry(ventana_salida_espera, style="CustomEntry.TEntry")
    entry_cantidad.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    
    ttk.Label(ventana_salida_espera, text="Departamento:", style="CustomLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=10)
    
    
    nombres_departamentos_para_combobox, departamentos_map_global = obtener_departamentos_para_combobox() # Asigna a una variable global o pásala
    
    departamento_var = tk.StringVar(ventana_salida_espera)
    #if nombres_departamentos_para_combobox:
        #departamento_var.set(nombres_departamentos_para_combobox[0])  
    #else:
        #departamento_var.set("") 
        #messagebox.showwarning("Advertencia", "No se encontraron departamentos en la base de datos.")

    ttk.Combobox(ventana_salida_espera, textvariable=departamento_var, values=nombres_departamentos_para_combobox, style="TCombobox", state="readonly").grid(row=2, column=1, padx=10, pady=10, sticky="ew")

   

    ttk.Button(ventana_salida_espera, text="Agregar a Salida en Espera", command=salida_espera, style="CustomButton.TButton").grid(row=3, column=0, columnspan=2, pady=15, padx=10, sticky="ew")

    ventana_salida_espera.grid_columnconfigure(1, weight=1)


   
         #MUESTRA TODO EL INVENTARIO DONDE PODEMOS REALIZAR ENTRADAS,SALIDAS,ELIMINAR ETC

def mostrar_inventario(ventana):
    """Muestra el inventario con menú desplegable de categorías y búsqueda por nombre o código dentro de la categoría."""

   
    def agregar_departamento_a_db(nombre_departamento):
        """Agrega un departamento a la base de datos si no existe.
           Utiliza la función 'conectar_mysql' que debe estar disponible
           en el ámbito superior o global.
        """
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                sql_verificar = "SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s"
                cursor.execute(sql_verificar, (nombre_departamento,))
                if not cursor.fetchone():
                    sql_insertar = "INSERT INTO departamentos (NombreDepartamento) VALUES (%s)"
                    cursor.execute(sql_insertar, (nombre_departamento,))
                    mydb.commit()
            except mysql.connector.Error as err:
                print(f"Error al agregar departamento '{nombre_departamento}': {err}")
            finally:
                if cursor: cursor.close()
                if mydb and mydb.is_connected(): mydb.close()

    #current_user_role_is_admin = True

    


    ventana_inventario = tk.Toplevel(ventana)
    ventana_inventario.title("Inventario")
    ventana_inventario.geometry("1200x600")
    ventana_inventario.configure(bg="#A9A9A9")
    ventana_inventario.protocol("WM_DELETE_WINDOW", lambda: ventana_inventario.destroy())

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

    frame_menu = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_menu.pack(pady=10, padx=10, fill=tk.X)

    frame_busqueda = tk.Frame(frame_menu, bg="#A9A9A9")
    frame_busqueda.pack(side=tk.LEFT, padx=10)

    ttk.Label(frame_busqueda, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda = ttk.Entry(frame_busqueda, style="CustomEntry.TEntry")
    entry_busqueda.pack(side=tk.LEFT)

    categorias_mostrar = ["Todas"]
    mydb_cat = conectar_mysql()
    if mydb_cat:
        cursor_cat = mydb_cat.cursor()
        try:
            cursor_cat.execute("SELECT NombreCategoria FROM categorias ORDER BY NombreCategoria")
            categorias_db = [row[0] for row in cursor_cat.fetchall()]
            categorias_mostrar.extend(categorias_db)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de BD", f"Error al cargar categorías: {err}", parent=ventana_inventario)
        finally:
            if cursor_cat: cursor_cat.close()
            if mydb_cat and mydb_cat.is_connected(): mydb_cat.close()

    categoria_seleccionada_mostrar = tk.StringVar(frame_menu)
    categoria_seleccionada_mostrar.set(categorias_mostrar[0])

    menu_categorias_mostrar = ttk.Combobox(frame_menu, textvariable=categoria_seleccionada_mostrar, values=categorias_mostrar, style="TCombobox", state="readonly")
    menu_categorias_mostrar.pack(side=tk.LEFT, padx=10)

    frame_tabla = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tabla_productos = ttk.Treeview(frame_tabla, columns=("Código", "Categoría", "Producto", "Destino Entrada", "Destino Salida", "Entrada", "Salida", "Stock", "Unidad Medida", "Fecha Entrada", "Fecha Salida"), show="headings", style="Grid.Treeview")
    tabla_productos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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

    tabla_productos.column("Código", width=100)
    tabla_productos.column("Categoría", width=100)
    tabla_productos.column("Producto", width=150)
    tabla_productos.column("Destino Entrada", width=120)
    tabla_productos.column("Destino Salida", width=120)
    tabla_productos.column("Entrada", width=70)
    tabla_productos.column("Salida", width=70)
    tabla_productos.column("Stock", width=70)
    tabla_productos.column("Unidad Medida", width=100)
    tabla_productos.column("Fecha Entrada", width=100)
    tabla_productos.column("Fecha Salida", width=100)

    barra_desplazamiento = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla_productos.yview)
    tabla_productos.configure(yscrollcommand=barra_desplazamiento.set)
    barra_desplazamiento.pack(side=tk.RIGHT, fill=tk.Y)

    frame_totales = tk.Frame(ventana_inventario, bg="#A9A9A9")
    frame_totales.pack(pady=10, padx=10, fill=tk.X)

    label_totales = ttk.Label(frame_totales, text="", style="CustomLabel.TLabel")
    label_totales.pack()

    def mostrar_tabla(categoria_nombre="Todas", termino_busqueda=""):
        tabla_productos.delete(*tabla_productos.get_children())
        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos para cargar el inventario.", parent=ventana_inventario)
            return

        cursor = mydb.cursor()
        query = """
            SELECT
                p.Codigo,
                c.NombreCategoria,
                p.Nombre,
                'Almacén principal' AS DestinoEntrada,
                COALESCE(d.NombreDepartamento, 'N/A') AS DestinoSalida,
                -- Aquí obtendremos la ÚLTIMA cantidad de entrada
                (SELECT e.Cantidad FROM entradas e WHERE e.CodigoProducto = p.Codigo ORDER BY e.FechaEntrada DESC, e.EntradaID DESC LIMIT 1) AS CantidadEntrada,
                -- Aquí obtendremos la ÚLTIMA cantidad de salida (con la mejora de ordenación)
                (SELECT s.Cantidad FROM salidas s WHERE s.CodigoProducto = p.Codigo ORDER BY s.FechaSalida DESC, s.SalidaID DESC LIMIT 1) AS CantidadSalida,
                p.Stock,
                p.UnidadMedida,
                -- Última fecha de entrada
                (SELECT e.FechaEntrada FROM entradas e WHERE e.CodigoProducto = p.Codigo ORDER BY e.FechaEntrada DESC, e.EntradaID DESC LIMIT 1) AS FechaUltimaEntrada,
                -- Última fecha de salida (con la mejora de ordenación)
                (SELECT s.FechaSalida FROM salidas s WHERE s.CodigoProducto = p.Codigo ORDER BY s.FechaSalida DESC, s.SalidaID DESC LIMIT 1) AS FechaUltimaSalida
            FROM productos p
            LEFT JOIN categorias c ON p.CategoriaID = c.CategoriaID
            LEFT JOIN departamentos d ON p.DepartamentoID = d.DepartamentoID
        """
        conditions = []
        params = []

        if categoria_nombre != "Todas":
            conditions.append("c.NombreCategoria = %s")
            params.append(categoria_nombre)

        if termino_busqueda:
            conditions.append("(p.Nombre LIKE %s OR p.Codigo LIKE %s)")
            params.extend([f"%{termino_busqueda}%", f"%{termino_busqueda}%"])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY p.Nombre ASC"

        try:
            cursor.execute(query, params)
            productos_filtrados_db = cursor.fetchall()
            for codigo, nombre_categoria, nombre_producto, destino_entrada, destino_salida, cantidad_entrada, cantidad_salida, stock, unidad_medida, fecha_entrada, fecha_salida in productos_filtrados_db:
                fecha_entrada_str = fecha_entrada.strftime("%Y-%m-%d") if isinstance(fecha_entrada, (datetime.date, datetime.datetime)) else ""
                fecha_salida_str = fecha_salida.strftime("%Y-%m-%d") if isinstance(fecha_salida, (datetime.date, datetime.datetime)) else ""

                tabla_productos.insert("", tk.END, values=(
                    codigo,
                    nombre_categoria if nombre_categoria else "",
                    nombre_producto,
                    destino_entrada if destino_entrada else "",
                    destino_salida if destino_salida else "",
                    cantidad_entrada if cantidad_entrada is not None else "",
                    cantidad_salida if cantidad_salida is not None else "",
                    stock,
                    unidad_medida if unidad_medida else "",
                    fecha_entrada_str,
                    fecha_salida_str
                ))
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al mostrar el inventario: {err}", parent=ventana_inventario)
        finally:
            if cursor: cursor.close()
            if mydb and mydb.is_connected(): mydb.close()
        mostrar_totales(categoria_seleccionada_mostrar.get())

    def mostrar_totales(categoria_nombre):
        mydb = conectar_mysql()
        if not mydb: return

        cursor = mydb.cursor()
        query_total = """
            SELECT COUNT(*)
            FROM productos p
            LEFT JOIN categorias c ON p.CategoriaID = c.CategoriaID
        """
        params_total = []

        if categoria_nombre != "Todas":
            query_total += " WHERE c.NombreCategoria = %s"
            params_total.append(categoria_nombre)

        try:
            cursor.execute(query_total, params_total)
            total_productos = cursor.fetchone()[0]

            query_categorias = "SELECT COUNT(*) FROM categorias"
            cursor.execute(query_categorias)
            total_categorias = cursor.fetchone()[0]

            if categoria_nombre == "Todas":
                label_totales.config(text=f"Total de productos: {total_productos}, Total de categorías: {total_categorias}", style="CustomLabel.TLabel")
            else:
                label_totales.config(text=f"Total de productos en {categoria_nombre}: {total_productos}", style="CustomLabel.TLabel")

        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al obtener los totales: {err}", parent=ventana_inventario)
        finally:
            if cursor: cursor.close()
            if mydb and mydb.is_connected(): mydb.close()

    def mostrar_inventario_filtrado(event=None):
        categoria_nombre = categoria_seleccionada_mostrar.get()
        termino_busqueda = entry_busqueda.get().strip()
        mostrar_tabla(categoria_nombre, termino_busqueda)

    menu_categorias_mostrar.bind("<<ComboboxSelected>>", mostrar_inventario_filtrado)
    entry_busqueda.bind("<KeyRelease>", mostrar_inventario_filtrado)

    def realizar_entrada_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una entrada de productos desde el menú contextual."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.", parent=ventana_inventario)
            return

        def confirmar_entrada():
            cantidad_str = entry_cantidad.get().strip()
            fecha_str = entry_fecha.get().strip()

            if not cantidad_str.replace('.', '', 1).isdigit() or float(cantidad_str) <= 0:
                messagebox.showerror("Error", "La cantidad debe ser un número positivo.", parent=ventana_entrada)
                return
            cantidad = float(cantidad_str)

            try:
                fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).", parent=ventana_entrada)
                return

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=ventana_entrada)
                return

            cursor = mydb.cursor()

            try:
                mydb.start_transaction()

                cursor.execute("SELECT ProductoID, UnidadMedida FROM productos WHERE Codigo = %s", (codigo_producto_seleccionado,))
                producto_result = cursor.fetchone() 

                if not producto_result:
                    messagebox.showerror("Error", "Producto no encontrado.", parent=ventana_entrada)
                    mydb.rollback()
                    return
                producto_id = producto_result[0]
                unidad_medida = producto_result[1] 

                sql_actualizar_stock = "UPDATE productos SET Stock = Stock + %s, FechaEntrada = %s WHERE ProductoID = %s "
                val_actualizar_stock = (cantidad, fecha, producto_id)
                cursor.execute(sql_actualizar_stock, val_actualizar_stock)

                sql_insertar_entrada = "INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, FechaEntrada, Destino) VALUES (%s, %s, %s, %s, 'Almacén principal')"
                val_insertar_entrada = (producto_id, codigo_producto_seleccionado, cantidad, fecha)
                cursor.execute(sql_insertar_entrada, val_insertar_entrada)

                mydb.commit()
                
                messagebox.showinfo("Entrada Realizada", f"{cantidad} {unidad_medida} de {nombre_producto} (Código: {codigo_producto_seleccionado}) entraron al inventario.", parent=ventana_entrada)
                mostrar_tabla(categoria_seleccionada_mostrar.get(), entry_busqueda.get())
                ventana_entrada.destroy()

            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error al realizar entrada", f"Error: {err}", parent=ventana_entrada)
            except Exception as e:
                mydb.rollback()
                messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_entrada)
            finally:
                if mydb and mydb.is_connected():
                    if cursor: cursor.close()
                    mydb.close()

        ventana_entrada = tk.Toplevel(ventana_inventario)
        ventana_entrada.title(f"Realizar Entrada - {nombre_producto} (Código: {codigo_producto_seleccionado})")
        ventana_entrada.configure(bg="#A9A9A9")
        ventana_entrada.transient(ventana_inventario)
        ventana_entrada.grab_set()

        ttk.Label(ventana_entrada, text="Cantidad:", style="CustomLabel.TLabel").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_cantidad = ttk.Entry(ventana_entrada, style="CustomEntry.TEntry")
        entry_cantidad.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_entrada, text="Fecha (YYYY-MM-DD):", style="CustomLabel.TLabel").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_fecha = ttk.Entry(ventana_entrada, style="CustomEntry.TEntry")
        entry_fecha.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        entry_fecha.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(ventana_entrada, text="Calendario", command=lambda: abrir_calendario(ventana_entrada, entry_fecha), style="CustomButton.TButton").grid(row=1, column=2, padx=10, pady=10)

        ttk.Button(ventana_entrada, text="Confirmar Entrada", command=confirmar_entrada, style="CustomButton.TButton").grid(row=2, column=0, columnspan=3, pady=15, padx=10, sticky="ew")
        ventana_entrada.grid_columnconfigure(1, weight=1)
        ventana_entrada.wait_window()

    def realizar_salida_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una salida de productos desde el menú contextual."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.", parent=ventana_inventario)
            return

        def confirmar_salida():
            departamento_nombre = departamento_var.get().strip()
            cantidad_str = entry_cantidad_salida.get().strip()
            fecha_str = entry_fecha_salida.get().strip()
            numero_requisicion = entry_numero_requisicion.get().strip()

            if not cantidad_str.replace('.', '', 1).isdigit() or float(cantidad_str) <= 0:
                messagebox.showerror("Error", "Cantidad inválida. Ingrese un número positivo.", parent=ventana_salida)
                return
            cantidad = float(cantidad_str)

            try:
                fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).", parent=ventana_salida)
                return

            if not departamento_nombre or not numero_requisicion:
                messagebox.showerror("Error", "Por favor, complete todos los campos.", parent=ventana_salida)
                return

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=ventana_salida)
                return

            cursor = mydb.cursor()

            try:
                mydb.start_transaction()

                cursor.execute("SELECT ProductoID, Stock, UnidadMedida FROM productos WHERE Codigo = %s", (codigo_producto_seleccionado,))
                resultado_producto = cursor.fetchone()

                if not resultado_producto:
                    messagebox.showerror("Error", "Producto no encontrado.", parent=ventana_salida)
                    mydb.rollback()
                    return

                producto_id = resultado_producto[0]
                stock_actual = resultado_producto[1]
                unidad_medida_salida = resultado_producto[2]

                if stock_actual >= cantidad:
                    query_departamento_salida_id = "SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s"
                    cursor.execute(query_departamento_salida_id, (departamento_nombre,))
                    resultado_departamento_salida = cursor.fetchone()
                    if not resultado_departamento_salida:
                        messagebox.showerror("Error", f"El departamento '{departamento_nombre}' no existe. Por favor, asegúrese de que el departamento esté en la base de datos.", parent=ventana_salida)
                        mydb.rollback()
                        return
                    departamento_salida_id = resultado_departamento_salida[0]

                    sql_actualizar_stock_departamento = "UPDATE productos SET Stock = Stock - %s, FechaSalida = %s, DepartamentoID = %s WHERE ProductoID = %s"
                    val_actualizar_stock_departamento = (cantidad, fecha, departamento_salida_id, producto_id)
                    cursor.execute(sql_actualizar_stock_departamento, val_actualizar_stock_departamento)

                    sql_insertar_salida = "INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, FechaSalida, DepartamentoID, NumeroRequisicion, UnidadMedida) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    val_insertar_salida = (producto_id, codigo_producto_seleccionado, cantidad, fecha, departamento_salida_id, numero_requisicion, unidad_medida_salida)
                    cursor.execute(sql_insertar_salida, val_insertar_salida)

                    mydb.commit()
                    messagebox.showinfo("Salida Realizada", f"{cantidad} {unidad_medida_salida} de {nombre_producto} (Código: {codigo_producto_seleccionado}) salieron para {departamento_nombre}.", parent=ventana_salida)
                    mostrar_tabla(categoria_seleccionada_mostrar.get(), entry_busqueda.get())
                    ventana_salida.destroy()
                else:
                    messagebox.showerror("Error", "No hay suficiente stock para realizar la salida.", parent=ventana_salida)

            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error al realizar salida", f"Error de base de datos: {err}\n\n"
                                                                f"Asegúrese de que las relaciones ON DELETE CASCADE estén configuradas o que la eliminación de registros relacionados se realice correctamente.",
                                        parent=ventana_salida)
            except Exception as e:
                mydb.rollback()
                messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_salida)
            finally:
                if mydb and mydb.is_connected():
                    if cursor: cursor.close()
                    mydb.close()

        ventana_salida = tk.Toplevel(ventana_inventario)
        ventana_salida.title(f"Realizar Salida - {nombre_producto} (Código: {codigo_producto_seleccionado})")
        ventana_salida.configure(bg="#A9A9A9")
        ventana_salida.transient(ventana_inventario)
        ventana_salida.grab_set()

        ttk.Label(ventana_salida, text="Departamento:", style="CustomLabel.TLabel").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        departamentos = []
        mydb_dep = conectar_mysql()
        if mydb_dep:
            cursor_dep = mydb_dep.cursor()
            try:
                cursor_dep.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
                departamentos = [row[0] for row in cursor_dep.fetchall()]
                if not departamentos:
                    departamentos_predefinidos = [
                        "OTIC", "Oficina de Gestion Administrativa", "Oficina Contabilidad","Oficina Compras","Oficina de Bienes",
                        "Direccion de Servicios Generales y Transporte","Oficina de Seguimiento y Proyectos Estructurales",
                        "Direccion General de Planificacion Estrategica","Planoteca","Biblioteca",
                        "Direccion General de Seguimiento de Proyectos","Gestion Participativa Parque la isla",
                        "Oficina de Atencion ciudadana","Oficina de gestion Humana","Presidencia","Secretaria General",
                        "Consultoria Juridica","Oficina de Planificacion y Presupuesto","Auditoria",
                        "Direccion de informacion y Comunicacion","Direccion General de Formacion"
                    ]
                    for dep_name in departamentos_predefinidos:
                        agregar_departamento_a_db(dep_name)
                    cursor_dep.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
                    departamentos = [row[0] for row in cursor_dep.fetchall()]

            except mysql.connector.Error as err:
                messagebox.showerror("Error de BD", f"Error al cargar departamentos: {err}", parent=ventana_salida)
            finally:
                if cursor_dep: cursor_dep.close()
                if mydb_dep and mydb_dep.is_connected(): mydb_dep.close()

        departamento_var = tk.StringVar(ventana_salida)
        #departamento_var.set(departamentos[0] if departamentos else "")
        combo_departamento = ttk.Combobox(ventana_salida, textvariable=departamento_var, values=departamentos, style="TCombobox", state="readonly")
        combo_departamento.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Cantidad:", style="CustomLabel.TLabel").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_cantidad_salida = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_cantidad_salida.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Fecha (YYYY-MM-DD):", style="CustomLabel.TLabel").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        entry_fecha_salida = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_fecha_salida.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        entry_fecha_salida.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(ventana_salida, text="Calendario", command=lambda: abrir_calendario(ventana_salida, entry_fecha_salida), style="CustomButton.TButton").grid(row=2, column=2, padx=10, pady=10)

        ttk.Label(ventana_salida, text="Número de Requisición:", style="CustomLabel.TLabel").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        entry_numero_requisicion = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_numero_requisicion.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ttk.Button(ventana_salida, text="Confirmar Salida", command=confirmar_salida, style="CustomButton.TButton").grid(row=4, column=0, columnspan=3, pady=15, padx=10, sticky="ew")
        ventana_salida.grid_columnconfigure(1, weight=1)
        ventana_salida.wait_window()

    def editar_producto(codigo_producto_seleccionado):
        """Permite editar los detalles de un producto seleccionado, con más campos editables y Combobox para Unidad de Medida."""
        global current_user_role_is_admin 

        if not current_user_role_is_admin:
            messagebox.showwarning("Permiso Denegado", "No tiene los permisos para editar productos.", parent=ventana_inventario)
            return

        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se seleccionó ningún producto para editar.", parent=ventana_inventario)
            return

        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=ventana_inventario)
            return

        cursor = mydb.cursor(dictionary=True)
        try:
            query_producto_data = """
                SELECT
                    p.ProductoID,
                    p.Codigo,
                    p.Nombre,
                    p.Stock,
                    p.UnidadMedida,
                    p.FechaEntrada,
                    COALESCE(p.FechaSalida, NULL) AS FechaSalida,
                    c.NombreCategoria,
                    c.CategoriaID,
                    p.DepartamentoID,
                    'Almacén principal' AS DestinoEntrada, 
                    COALESCE(d.NombreDepartamento, 'N/A') AS NombreDepartamentoSalida,
                    (SELECT e.Cantidad FROM entradas e WHERE e.CodigoProducto = p.Codigo ORDER BY e.FechaEntrada DESC, e.EntradaID DESC LIMIT 1) AS CantidadEntrada,
                    (SELECT s.Cantidad FROM salidas s WHERE s.CodigoProducto = p.Codigo ORDER BY s.FechaSalida DESC, s.SalidaID DESC LIMIT 1) AS CantidadSalida
                FROM productos p
                LEFT JOIN categorias c ON p.CategoriaID = c.CategoriaID
                LEFT JOIN departamentos d ON p.DepartamentoID = d.DepartamentoID
                WHERE p.Codigo = %s
                LIMIT 1;
                """
            cursor.execute(query_producto_data, (codigo_producto_seleccionado,))
            producto_data = cursor.fetchone()

            if not producto_data:
                messagebox.showerror("Error", "Producto no encontrado en la base de datos.", parent=ventana_inventario)
                return

            def confirmar_edicion():
                
                if not current_user_role_is_admin:
                    messagebox.showwarning("Permiso Denegado", "No tiene los permisos para guardar cambios de edición.", parent=ventana_edicion)
                    return

                nuevo_nombre = entry_nombre.get().strip()
                nueva_categoria_nombre = categoria_var.get().strip()
                nueva_unidad_medida = unidad_medida_var.get().strip()
                
                nueva_fecha_entrada_str = entry_fecha_entrada.get().strip()
                nueva_fecha_salida_str = entry_fecha_salida.get().strip()
                nuevo_departamento_nombre = departamento_salida_var.get().strip()

                if not nuevo_nombre:
                    messagebox.showerror("Error", "El nombre del producto no puede estar vacío.", parent=ventana_edicion)
                    return
                if not nueva_unidad_medida:
                    messagebox.showerror("Error", "La unidad de medida no puede estar vacía.", parent=ventana_edicion)
                    return

                try:
                    nueva_fecha_entrada = datetime.datetime.strptime(nueva_fecha_entrada_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha de entrada incorrecto (YYYY-MM-DD).", parent=ventana_edicion)
                    return

                nueva_fecha_salida = None
                if nueva_fecha_salida_str and nueva_fecha_salida_str.upper() != "N/A":
                    try:
                        nueva_fecha_salida = datetime.datetime.strptime(nueva_fecha_salida_str, "%Y-%m-%d").date()
                    except ValueError:
                        messagebox.showerror("Error", "Formato de fecha de salida incorrecto (YYYY-MM-DD) o 'N/A'.", parent=ventana_edicion)
                        return

                mydb_edit = conectar_mysql()
                if not mydb_edit:
                    messagebox.showerror("Error", "No se pudo conectar a la base de datos para actualizar.", parent=ventana_edicion)
                    return
                cursor_edit = mydb_edit.cursor()
                try:
                    mydb_edit.start_transaction()

                    cursor_edit.execute("SELECT CategoriaID FROM categorias WHERE NombreCategoria = %s", (nueva_categoria_nombre,))
                    nueva_categoria_id_result = cursor_edit.fetchone()
                    if not nueva_categoria_id_result:
                        messagebox.showerror("Error", f"La categoría '{nueva_categoria_nombre}' no existe. Asegúrese de que la categoría esté en la base de datos.", parent=ventana_edicion)
                        mydb_edit.rollback()
                        return
                    nueva_categoria_id = nueva_categoria_id_result[0]

                    nuevo_departamento_id = None
                    if nuevo_departamento_nombre and nuevo_departamento_nombre.upper() != "N/A":
                        cursor_edit.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (nuevo_departamento_nombre,))
                        nuevo_departamento_id_result = cursor_edit.fetchone()
                        if not nuevo_departamento_id_result:
                            messagebox.showerror("Error", f"El departamento '{nuevo_departamento_nombre}' no existe en la base de datos.", parent=ventana_edicion)
                            mydb_edit.rollback()
                            return
                        nuevo_departamento_id = nuevo_departamento_id_result[0]

                    sql_update = """
                        UPDATE productos SET
                            Nombre = %s,
                            CategoriaID = %s,
                            UnidadMedida = %s,
                            -- Stock ya NO se actualiza directamente desde esta ventana de edición.
                            -- Se gestiona a través de entradas y salidas.
                            FechaEntrada = %s,
                            FechaSalida = %s,
                            DepartamentoID = %s
                        WHERE Codigo = %s
                        """
                    val_update = (
                        nuevo_nombre,
                        nueva_categoria_id,
                        nueva_unidad_medida,
                        
                        nueva_fecha_entrada,
                        nueva_fecha_salida,
                        nuevo_departamento_id,
                        codigo_producto_seleccionado
                    )
                    cursor_edit.execute(sql_update, val_update)

                    mydb_edit.commit()
                    messagebox.showinfo("Éxito", f"Producto '{nuevo_nombre}' ({codigo_producto_seleccionado}) actualizado correctamente.", parent=ventana_edicion)
                    
                   
                    mostrar_tabla(categoria_seleccionada_mostrar.get(), entry_busqueda.get())
                    ventana_edicion.destroy()

                except mysql.connector.Error as err:
                    mydb_edit.rollback()
                    messagebox.showerror("Error de BD", f"Error al actualizar el producto: {err}", parent=ventana_edicion)
                except Exception as e:
                    mydb_edit.rollback()
                    messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_edicion)
                finally:
                    if cursor_edit: cursor_edit.close()
                    if mydb_edit and mydb_edit.is_connected(): mydb_edit.close()

            ventana_edicion = tk.Toplevel(ventana_inventario)
            ventana_edicion.title(f"Editar Producto - {codigo_producto_seleccionado}")
            ventana_edicion.configure(bg="#A9A9A9")
            ventana_edicion.transient(ventana_inventario)
            ventana_edicion.grab_set()

            categorias_disponibles = []
            unidades_medida_disponibles = []
            departamentos_disponibles = ["N/A"]

            try:
                mydb_list = conectar_mysql()
                if mydb_list:
                    cursor_list = mydb_list.cursor()
                    cursor_list.execute("SELECT NombreCategoria FROM categorias ORDER BY NombreCategoria")
                    categorias_disponibles = [row[0] for row in cursor_list.fetchall()]

                    cursor_list.execute("SELECT NombreUnidad FROM unidades_medida ORDER BY NombreUnidad")
                    unidades_medida_disponibles = [row[0] for row in cursor_list.fetchall()]
                    current_unidad = producto_data['UnidadMedida']
                    if current_unidad and current_unidad not in unidades_medida_disponibles:
                        unidades_medida_disponibles.append(current_unidad)
                        unidades_medida_disponibles.sort()

                    cursor_list.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
                    deps_from_db = [row[0] for row in cursor_list.fetchall()]
                    departamentos_disponibles.extend(deps_from_db)
                    current_departamento_salida = producto_data['NombreDepartamentoSalida']
                    if current_departamento_salida and current_departamento_salida.upper() != "N/A" and current_departamento_salida not in departamentos_disponibles:
                        departamentos_disponibles.append(current_departamento_salida)
                        departamentos_disponibles.sort()

            except mysql.connector.Error as err:
                messagebox.showerror("Error de BD", f"Error al cargar listas para edición: {err}", parent=ventana_edicion)
                ventana_edicion.destroy()
                return
            finally:
                if 'cursor_list' in locals() and cursor_list: cursor_list.close()
                if 'mydb_list' in locals() and mydb_list and mydb_list.is_connected(): mydb_list.close()

            row_idx = 0

            ttk.Label(ventana_edicion, text="Código:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(ventana_edicion, text=producto_data['Codigo'], style="CustomLabel.TLabel").grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")
            row_idx += 1

            ttk.Label(ventana_edicion, text="Nombre:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_nombre = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry")
            entry_nombre.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            entry_nombre.insert(0, producto_data['Nombre'])
            row_idx += 1

            ttk.Label(ventana_edicion, text="Categoría:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            categoria_var = tk.StringVar(ventana_edicion)
            categoria_var.set(producto_data['NombreCategoria'] if producto_data['NombreCategoria'] else (categorias_disponibles[0] if categorias_disponibles else ""))
            combo_categoria = ttk.Combobox(ventana_edicion, textvariable=categoria_var, values=categorias_disponibles, style="TCombobox", state="readonly")
            combo_categoria.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            row_idx += 1

            ttk.Label(ventana_edicion, text="Destino Entrada:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(ventana_edicion, text=producto_data.get('DestinoEntrada', 'N/A'), style="CustomLabel.TLabel").grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")
            row_idx += 1

            ttk.Label(ventana_edicion, text="Destino Salida:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            departamento_salida_var = tk.StringVar(ventana_edicion)
            departamento_salida_var.set(producto_data['NombreDepartamentoSalida'] if producto_data['NombreDepartamentoSalida'] else "N/A")
            combo_departamento_salida = ttk.Combobox(ventana_edicion, textvariable=departamento_salida_var, values=departamentos_disponibles, style="TCombobox", state="readonly")
            combo_departamento_salida.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            row_idx += 1

            ttk.Label(ventana_edicion, text="Última Cantidad Cant.:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_ultima_entrada_cant = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry", state='readonly') 
            entry_ultima_entrada_cant.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            
            entry_ultima_entrada_cant.configure(state='normal')
            entry_ultima_entrada_cant.insert(0, str(int(producto_data['CantidadEntrada'])) if producto_data['CantidadEntrada'] is not None else "0")
            entry_ultima_entrada_cant.configure(state='readonly')
            row_idx += 1

            ttk.Label(ventana_edicion, text="Última Salida Cant.:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_ultima_salida_cant = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry", state='readonly') 
            entry_ultima_salida_cant.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            
            entry_ultima_salida_cant.configure(state='normal')
            entry_ultima_salida_cant.insert(0, str(int(producto_data['CantidadSalida'])) if producto_data['CantidadSalida'] is not None else "0")
            entry_ultima_salida_cant.configure(state='readonly')
            row_idx += 1

            ttk.Label(ventana_edicion, text="Stock Actual:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_stock = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry", state='readonly')
            entry_stock.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            
            entry_stock.configure(state='normal')
            entry_stock.insert(0, str(int(producto_data['Stock'])) if producto_data['Stock'] is not None else "0")
            entry_stock.configure(state='readonly')
            row_idx += 1

            ttk.Label(ventana_edicion, text="Unidad Medida:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            unidad_medida_var = tk.StringVar(ventana_edicion)
            unidad_medida_var.set(producto_data['UnidadMedida'] if producto_data['UnidadMedida'] else "")
            combo_unidad_medida = ttk.Combobox(ventana_edicion, textvariable=unidad_medida_var, values=unidades_medida_disponibles, style="TCombobox", state="readonly") 
            combo_unidad_medida.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            row_idx += 1

            ttk.Label(ventana_edicion, text="Fecha Última Entrada:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_fecha_entrada = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry")
            entry_fecha_entrada.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            fecha_entrada_str = producto_data['FechaEntrada'].strftime("%Y-%m-%d") if isinstance(producto_data['FechaEntrada'], (datetime.date, datetime.datetime)) else ""
            entry_fecha_entrada.insert(0, fecha_entrada_str)
            ttk.Button(ventana_edicion, text="Calendario", command=lambda: abrir_calendario(ventana_edicion, entry_fecha_entrada), style="CustomButton.TButton").grid(row=row_idx, column=2, padx=5, pady=5)
            row_idx += 1

            ttk.Label(ventana_edicion, text="Fecha Última Salida:", style="CustomLabel.TLabel").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            entry_fecha_salida = ttk.Entry(ventana_edicion, style="CustomEntry.TEntry")
            entry_fecha_salida.grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
            fecha_salida_str = producto_data['FechaSalida'].strftime("%Y-%m-%d") if isinstance(producto_data['FechaSalida'], (datetime.date, datetime.datetime)) else "N/A"
            entry_fecha_salida.insert(0, fecha_salida_str)
            ttk.Button(ventana_edicion, text="Calendario", command=lambda: abrir_calendario(ventana_edicion, entry_fecha_salida), style="CustomButton.TButton").grid(row=row_idx, column=2, padx=5, pady=5)
            row_idx += 1

            ttk.Button(ventana_edicion, text="Guardar Cambios", command=confirmar_edicion, style="CustomButton.TButton").grid(row=row_idx, column=0, columnspan=3, pady=15, padx=5, sticky="ew")
            ventana_edicion.grid_columnconfigure(1, weight=1)
            ventana_edicion.wait_window()

        except mysql.connector.Error as err:
            messagebox.showerror("Error de BD", f"Error al cargar datos del producto para edición: {err}", parent=ventana_inventario)
        finally:
            if cursor: cursor.close()
            if mydb and mydb.is_connected(): mydb.close()

    def eliminar_producto(codigo_producto_seleccionado, nombre_producto):
        """Elimina un producto de la base de datos."""
        global current_user_role_is_admin 

        if not current_user_role_is_admin:
            messagebox.showwarning("Permiso Denegado", "No tiene los permisos para eliminar productos.", parent=ventana_inventario)
            return

        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se seleccionó ningún producto para eliminar.", parent=ventana_inventario)
            return

        respuesta = messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar el producto '{nombre_producto}' (Código: {codigo_producto_seleccionado})?\n\n"
            "¡ADVERTENCIA: Esto también eliminará todas las entradas y salidas asociadas a este producto!"
            "Asegúrese de tener configurado ON DELETE CASCADE en sus tablas de base de datos para evitar errores de integridad.",
            parent=ventana_inventario
        )

        if not respuesta:
            return

        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.", parent=ventana_inventario)
            return

        cursor = mydb.cursor()
        try:
            mydb.start_transaction()

            cursor.execute("SELECT ProductoID FROM productos WHERE Codigo = %s", (codigo_producto_seleccionado,))
            producto_id_result = cursor.fetchone()
            if not producto_id_result:
                messagebox.showerror("Error", "Producto no encontrado.", parent=ventana_inventario)
                mydb.rollback()
                return
            producto_id = producto_id_result[0]

            cursor.execute("DELETE FROM entradas WHERE ProductoID = %s", (producto_id,))
            cursor.execute("DELETE FROM salidas WHERE ProductoID = %s", (producto_id,))

            sql_delete_producto = "DELETE FROM productos WHERE ProductoID = %s"
            cursor.execute(sql_delete_producto, (producto_id,))

            mydb.commit()
            messagebox.showinfo("Éxito", f"Producto '{nombre_producto}' y sus registros asociados eliminados correctamente.", parent=ventana_inventario)
            mostrar_tabla(categoria_seleccionada_mostrar.get(), entry_busqueda.get())

        except mysql.connector.Error as err:
            mydb.rollback()
            messagebox.showerror("Error al eliminar", f"Error de base de datos: {err}\n\n"
                                                     f"Asegúrese de que las relaciones ON DELETE CASCADE estén configuradas o que la eliminación de registros relacionados se realice correctamente.",
                                 parent=ventana_inventario)
        except Exception as e:
            mydb.rollback()
            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado al eliminar: {e}", parent=ventana_inventario)
        finally:
            if mydb and mydb.is_connected():
                if cursor: cursor.close()
                mydb.close()

    def menu_contextual(event):
        item = tabla_productos.identify_row(event.y)
        if item:
            values = tabla_productos.item(item, "values")
            codigo_producto = values[0]
            nombre_producto = values[2]

            menu = tk.Menu(ventana_inventario, tearoff=0)
            menu.add_command(label="Realizar Entrada", command=lambda c=codigo_producto, n=nombre_producto: realizar_entrada_contextual(c, n))
            menu.add_command(label="Realizar Salida", command=lambda c=codigo_producto, n=nombre_producto: realizar_salida_contextual(c, n))
            menu.add_separator()

            
            global current_user_role_is_admin 
            if current_user_role_is_admin:
                menu.add_command(label="Editar Producto", command=lambda c=codigo_producto: editar_producto(c))
                menu.add_command(label="Eliminar Producto", command=lambda c=codigo_producto, n=nombre_producto: eliminar_producto(c, n))
            else:
                menu.add_command(label="Editar Producto (Solo Admin)", state=tk.DISABLED)
                menu.add_command(label="Eliminar Producto (Solo Admin)", state=tk.DISABLED)

            menu.post(event.x_root, event.y_root)

    tabla_productos.bind("<Button-3>", menu_contextual)

    mostrar_tabla()

    ventana_inventario.grid_columnconfigure(0, weight=1)
    ventana_inventario.grid_rowconfigure(1, weight=1)

    

                         #MUESTRA EL CONSUMO QUE A TENIDO CADA DEPARTAMENTO




def obtener_meses_anios_disponibles_db():
    """
    Obtiene una lista de meses y años únicos de las fechas de salida desde la base de datos.
    Esta es una función de apoyo para el Combobox de filtro.
    """
    years_months = set()
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        try:
            cursor.execute("SELECT DISTINCT YEAR(FechaSalida), MONTH(FechaSalida) FROM salidas ORDER BY YEAR(FechaSalida) DESC, MONTH(FechaSalida) DESC")
            results = cursor.fetchall()
            for year, month in results:
                years_months.add(f"{month:02d}-{year}") 
        except mysql.connector.Error as err:
            messagebox.showerror("Error de BD", f"Error al obtener meses/años disponibles: {err}")
        finally:
            cursor.close()
            mydb.close()
    return sorted(list(years_months), reverse=True)

def calcular_consumo_periodo(periodo):
    """
    Calcula el consumo para un período específico desde la base de datos MySQL,
    utilizando el código del producto como clave, solo desde la tabla de salidas.
    'periodo' puede ser un datetime.timedelta O una tupla (start_date, end_date).
    Retorna un diccionario anidado con consumo por departamento/código de producto
    y el total general para ese período.
    """
    consumo_departamentos = {}
    total_consumo = 0
    
    fecha_actual = datetime.date.today()
    start_date = None
    end_date = None

    if isinstance(periodo, datetime.timedelta):
        end_date = fecha_actual
        start_date = fecha_actual - periodo
    elif isinstance(periodo, tuple) and len(periodo) == 2:
        start_date, end_date = periodo
    else:
        raise ValueError("El parámetro 'periodo' debe ser un timedelta o una tupla de fechas (start_date, end_date).")

    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        query = """
            SELECT d.NombreDepartamento, s.CodigoProducto, s.Cantidad, s.FechaSalida, p.UnidadMedida, p.Nombre
            FROM salidas s
            JOIN productos p ON s.ProductoID = p.ProductoID
            JOIN departamentos d ON s.DepartamentoID = d.DepartamentoID
            WHERE s.FechaSalida BETWEEN %s AND %s
        """
        val = (start_date, end_date)
        try:
            cursor.execute(query, val)
            salidas_periodo = cursor.fetchall()
            for nombre_departamento, codigo_producto, cantidad, fecha_salida, unidad_medida, nombre_producto in salidas_periodo:
                if nombre_departamento not in consumo_departamentos:
                    consumo_departamentos[nombre_departamento] = {}
                if codigo_producto not in consumo_departamentos[nombre_departamento]:
                    consumo_departamentos[nombre_departamento][codigo_producto] = {
                        'cantidad': 0,
                        'nombre_producto': nombre_producto,
                        'unidad_medida': unidad_medida
                    }
                try:
                    consumo_departamentos[nombre_departamento][codigo_producto]['cantidad'] += int(cantidad)
                    total_consumo += int(cantidad)
                except ValueError:
                    print(f"Cantidad inválida en la salida para el producto con código {codigo_producto} en el departamento {nombre_departamento}. Cantidad: '{cantidad}'")
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al calcular el consumo por período: {err}")
        finally:
            cursor.close()
            mydb.close()
    return consumo_departamentos, total_consumo

def calcular_consumo_departamento():
    """Calcula el consumo semanal y mensual por departamento y en general desde la base de datos."""
    consumo_semanal_dummy = {}
    consumo_mensual_dummy = {}
    mostrar_consumo_periodos(consumo_semanal_dummy, consumo_mensual_dummy)

def mostrar_consumo_periodos(consumo_semanal, consumo_mensual):
    """
    Muestra el consumo desglosado por semanas y mensual para el mes seleccionado,
    con filtro por mes y optimizaciones para el orden.
    """
    global ventana_consumo, tabla_consumo_global_ref 

    if ventana_consumo is not None and ventana_consumo.winfo_exists():
        ventana_consumo.lift() 
        return

    ventana_consumo = tk.Toplevel(ventana)
    ventana_consumo.title("Consumo por Período")
    ventana_consumo.configure(bg="#A9A9A9")
    ventana_consumo.geometry("1400x650") 

    style = ttk.Style(ventana_consumo)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("Total.Treeview", font=("Segoe UI", 10, "bold"), background='#e0e0e0', foreground='#000000')

   
    frame_controles = tk.Frame(ventana_consumo, bg="#A9A9A9")
    frame_controles.pack(pady=10, padx=10, fill=tk.X)

    ttk.Label(frame_controles, text="Filtrar por Mes:", style="CustomLabel.TLabel").pack(side=tk.LEFT, padx=5)

    meses_anios = obtener_meses_anios_disponibles_db()
    mes_seleccionado_cb = ttk.Combobox(frame_controles, values=meses_anios, state="readonly", width=12)
    mes_seleccionado_cb.pack(side=tk.LEFT, padx=5)
    if meses_anios:
        mes_seleccionado_cb.set(meses_anios[0])
    else:
        mes_seleccionado_cb.set("No hay datos")
        mes_seleccionado_cb.config(state="disabled")

   
    boton_exportar_pdf = ttk.Button(frame_controles, text="Exportar a PDF", 
                                    command=lambda: exportar_tabla_pdf(tabla_consumo_global_ref, f"Reporte de Consumo Mensual - {mes_seleccionado_cb.get()}"))
    boton_exportar_pdf.pack(side=tk.RIGHT, padx=5)


    
    tabla_consumo = ttk.Treeview(ventana_consumo, columns=(
        "Departamento", "Código", "Producto",
        "Semana 1", "Semana 2", "Semana 3", "Semana 4",
        "Mensual", "Unidad Medida", "Porcentaje"
    ), show="headings", style="Grid.Treeview")
    tabla_consumo.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    tabla_consumo_global_ref = tabla_consumo 

    tabla_consumo.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla_consumo.heading("Código", text="Código", anchor=tk.W)
    tabla_consumo.heading("Producto", text="Producto", anchor=tk.W)
    tabla_consumo.heading("Semana 1", text="Semana 1", anchor=tk.W)
    tabla_consumo.heading("Semana 2", text="Semana 2", anchor=tk.W)
    tabla_consumo.heading("Semana 3", text="Semana 3", anchor=tk.W)
    tabla_consumo.heading("Semana 4", text="Semana 4", anchor=tk.W)
    tabla_consumo.heading("Mensual", text="Mensual", anchor=tk.W)
    tabla_consumo.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla_consumo.heading("Porcentaje", text="Porcentaje", anchor=tk.W)

    tabla_consumo.column("Departamento", width=180)
    tabla_consumo.column("Código", width=90)
    tabla_consumo.column("Producto", width=180)
    tabla_consumo.column("Semana 1", width=80)
    tabla_consumo.column("Semana 2", width=80)
    tabla_consumo.column("Semana 3", width=80)
    tabla_consumo.column("Semana 4", width=80)
    tabla_consumo.column("Mensual", width=80)
    tabla_consumo.column("Unidad Medida", width=100)
    tabla_consumo.column("Porcentaje", width=100)

    
    def poblar_tabla_segun_filtro(event=None):
        selected_month_year = mes_seleccionado_cb.get()
        if not selected_month_year or selected_month_year == "No hay datos":
            for item in tabla_consumo.get_children():
                tabla_consumo.delete(item)
            return

        month, year = map(int, selected_month_year.split('-'))

       
        first_day_of_month = datetime.date(year, month, 1)
        if month == 12:
            last_day_of_month = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last_day_of_month = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        
        for item in tabla_consumo.get_children():
            tabla_consumo.delete(item)

        
        week_ranges = []
       
        week_ranges.append((first_day_of_month, min(first_day_of_month + datetime.timedelta(days=6), last_day_of_month)))
        
        
        week_ranges.append((first_day_of_month + datetime.timedelta(days=7), min(first_day_of_month + datetime.timedelta(days=13), last_day_of_month)))
        
       
        week_ranges.append((first_day_of_month + datetime.timedelta(days=14), min(first_day_of_month + datetime.timedelta(days=20), last_day_of_month)))
        
       
        week_ranges.append((first_day_of_month + datetime.timedelta(days=21), last_day_of_month))

       
        consumo_semanal_data = [{}, {}, {}, {}]
        total_semanal_data = [0, 0, 0, 0]

        all_unique_products = {} 

        
        for i, (w_start, w_end) in enumerate(week_ranges):
           
            if w_start <= w_end:
                current_week_consumo, current_week_total = calcular_consumo_periodo((w_start, w_end))
                consumo_semanal_data[i] = current_week_consumo
                total_semanal_data[i] = current_week_total
                
               
                for dept, prods in current_week_consumo.items():
                    for prod_code, details in prods.items():
                        if (dept, prod_code) not in all_unique_products:
                            all_unique_products[(dept, prod_code)] = {'nombre_producto': details['nombre_producto'], 'unidad_medida': details['unidad_medida']}


       
        consumo_mensual_total, total_mensual_general = calcular_consumo_periodo((first_day_of_month, last_day_of_month))

       
        for dept, prods in consumo_mensual_total.items():
            for prod_code, details in prods.items():
                if (dept, prod_code) not in all_unique_products:
                    all_unique_products[(dept, prod_code)] = {'nombre_producto': details['nombre_producto'], 'unidad_medida': details['unidad_medida']}


       
        sorted_unique_keys = sorted(all_unique_products.keys())

       
        for dept, prod_code in sorted_unique_keys:
            cantidad_semanas = [0, 0, 0, 0]
            
           
            for i in range(4):
                cantidad_semanas[i] = consumo_semanal_data[i].get(dept, {}).get(prod_code, {}).get('cantidad', 0)

           
            cantidad_mensual = consumo_mensual_total.get(dept, {}).get(prod_code, {}).get('cantidad', 0)

           
            product_details = all_unique_products[(dept, prod_code)]
            nombre_producto = product_details['nombre_producto']
            unidad_medida = product_details['unidad_medida']

            
            if any(q > 0 for q in cantidad_semanas) or cantidad_mensual > 0:
                porcentaje = (cantidad_mensual / total_mensual_general) * 100 if total_mensual_general > 0 else 0
                
                values = (
                    dept,
                    prod_code,
                    nombre_producto,
                    cantidad_semanas[0],
                    cantidad_semanas[1], 
                    cantidad_semanas[2], 
                    cantidad_semanas[3], 
                    cantidad_mensual,
                    unidad_medida,
                    f"{porcentaje:.2f}%"
                )
                tabla_consumo.insert("", tk.END, values=values)
        
       
        display_total_semanal = []
        for i in range(4):
            display_total_semanal.append(total_semanal_data[i] if total_semanal_data[i] > 0 else "")

        display_total_mensual = total_mensual_general if total_mensual_general > 0 else ""

       
        if total_mensual_general > 0 or any(t > 0 for t in total_semanal_data):
            total_row_values = ["", "", "TOTAL GENERAL"]
            total_row_values.extend(display_total_semanal) 
            total_row_values.append(display_total_mensual) 
            total_row_values.extend(["", "100.00%"]) 

            tabla_consumo.insert("", tk.END, values=total_row_values, tags=('total_row',))
            tabla_consumo.tag_configure('total_row', font=('Segoe UI', 10, 'bold'), background='#d9f0f0', foreground='#000000')


    
    mes_seleccionado_cb.bind("<<ComboboxSelected>>", poblar_tabla_segun_filtro)

    
    if meses_anios:
        poblar_tabla_segun_filtro() 
    else:
        messagebox.showinfo("Información", "No se encontraron datos de salidas en la base de datos para mostrar.")



                            #Hasta aqui funciones principales.


















                                    #Funciones de reportes:


                     #GENERA UNA VENTANA CON LOS PRODUCTOS CON BAJO STOCK

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

    umbral_stock_minimo = 10
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

    datos_reporte = [] 
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
    
           



            
                        #GENERA UNA VENTANA CON TODAS LAS ENTRADAS DE PRODUCTOS
def generar_reporte_entradas():
    """Genera un reporte del historial de entradas con búsqueda, filtro por categoría, edición y eliminación."""
    global ventana, ventana_reporte_entradas, tabla_entradas, entry_busqueda_entradas, categoria_seleccionada_reporte_entradas, current_user_role_is_admin

    
    if ventana_reporte_entradas and ventana_reporte_entradas.winfo_exists():
        ventana_reporte_entradas.lift()
        aplicar_filtro_entradas()
        return

    
    try:
        if ventana is None or not ventana.winfo_exists():
            ventana = tk.Tk()
            ventana.withdraw() 
    except NameError:
        ventana = tk.Tk()
        ventana.withdraw()

    ventana_reporte_entradas = tk.Toplevel(ventana)
    ventana_reporte_entradas.title("Reporte de Entradas")
    ventana_reporte_entradas.geometry("1000x600")
    ventana_reporte_entradas.configure(bg="#A9A9A9")
    
    ventana_reporte_entradas.protocol("WM_DELETE_WINDOW", lambda: ventana_reporte_entradas.destroy())


    
    style = ttk.Style(ventana_reporte_entradas)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))


    
    frame_controles = tk.Frame(ventana_reporte_entradas, bg="#A9A9A9")
    frame_controles.pack(pady=10, padx=10, fill=tk.X)


    ttk.Label(frame_controles, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda_entradas = ttk.Entry(frame_controles, style="CustomEntry.TEntry")
    entry_busqueda_entradas.pack(side=tk.LEFT, padx=(0, 10))


   
    categorias_mostrar = ["Todas las categorías"]
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        try:
            cursor.execute("SELECT NombreCategoria FROM categorias ORDER BY NombreCategoria")
            categorias_db = [row[0] for row in cursor.fetchall()]
            categorias_mostrar.extend(categorias_db)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de BD", f"Error al cargar categorías: {err}")
        finally:
            cursor.close()
            mydb.close()

    categoria_seleccionada_reporte_entradas = tk.StringVar(frame_controles)
    categoria_seleccionada_reporte_entradas.set(categorias_mostrar[0])
    menu_categorias_reporte = ttk.Combobox(frame_controles,
                                           textvariable=categoria_seleccionada_reporte_entradas,
                                           values=categorias_mostrar,
                                           style="TCombobox",
                                           state="readonly")
    menu_categorias_reporte.pack(side=tk.LEFT, padx=(0, 10))

    
    boton_exportar_pdf = ttk.Button(frame_controles, text="Exportar a PDF",
                                    command=lambda: exportar_tabla_pdf(tabla_entradas, "Historial de Entradas"))
    boton_exportar_pdf.pack(side=tk.RIGHT, padx=(10, 0))


    
    frame_tabla_contenedor = tk.Frame(ventana_reporte_entradas, bg="#A9A9A9")
    frame_tabla_contenedor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


    
    tabla_entradas = ttk.Treeview(frame_tabla_contenedor,
                                  columns=("Código", "Producto", "Cantidad", "Unidad Medida", "Fecha", "Destino", "EntradaID"),
                                  show="headings",
                                  style="Grid.Treeview")
    tabla_entradas.column("EntradaID", width=0, stretch=tk.NO) 

    tabla_entradas.heading("Código", text="Código", anchor=tk.W)
    tabla_entradas.heading("Producto", text="Producto", anchor=tk.W)
    tabla_entradas.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tabla_entradas.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla_entradas.heading("Fecha", text="Fecha", anchor=tk.W)
    tabla_entradas.heading("Destino", text="Destino", anchor=tk.W)

    
    tabla_entradas.column("Código", width=100)
    tabla_entradas.column("Producto", width=180)
    tabla_entradas.column("Cantidad", width=80)
    tabla_entradas.column("Unidad Medida", width=100)
    tabla_entradas.column("Fecha", width=100)
    tabla_entradas.column("Destino", width=150)


    
    scrollbar_vertical = ttk.Scrollbar(frame_tabla_contenedor, orient="vertical", command=tabla_entradas.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_entradas.configure(yscrollcommand=scrollbar_vertical.set)
    tabla_entradas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


    def cargar_entradas(filtro_busqueda="", categoria_filtro="Todas las categorías"):
        """Carga y muestra los registros de entradas en el Treeview, aplicando filtros."""
        for item in tabla_entradas.get_children():
            tabla_entradas.delete(item) 

        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        try:
            sql_query = """
                SELECT
                    e.CodigoProducto,
                    p.Nombre AS NombreProducto,
                    e.Cantidad,
                    p.UnidadMedida AS UnidadMedida, -- <--- CAMBIO AQUÍ: Ahora selecciona desde 'p' (productos)
                    e.FechaEntrada,
                    e.Destino,
                    e.EntradaID
                FROM
                    entradas e
                JOIN
                    productos p ON e.ProductoID = p.ProductoID
                JOIN
                    categorias c ON p.CategoriaID = c.CategoriaID
                WHERE 1=1
            """
            params = []

            if filtro_busqueda:
                sql_query += " AND (e.CodigoProducto LIKE %s OR p.Nombre LIKE %s)"
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")

            if categoria_filtro and categoria_filtro != "Todas las categorías":
                sql_query += " AND c.NombreCategoria = %s"
                params.append(categoria_filtro)

            sql_query += " ORDER BY e.FechaEntrada DESC, e.EntradaID DESC"

            cursor.execute(sql_query, tuple(params))
            registros = cursor.fetchall()

            for registro in registros:
               
                tabla_entradas.insert("", "end", values=registro)

        except mysql.connector.Error as err:
            messagebox.showerror("Error de Base de Datos", f"Error al cargar el reporte de entradas: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()


    def aplicar_filtro_entradas(*args):
        """Función que se llama cuando se aplica un filtro (búsqueda o categoría)."""
        filtro_busqueda = entry_busqueda_entradas.get().strip()
        categoria_filtro = categoria_seleccionada_reporte_entradas.get()
        cargar_entradas(filtro_busqueda, categoria_filtro)


    
    entry_busqueda_entradas.bind("<KeyRelease>", aplicar_filtro_entradas)
    menu_categorias_reporte.bind("<<ComboboxSelected>>", aplicar_filtro_entradas)


    cargar_entradas() 


    def editar_entrada():
        """Abre una ventana para editar un registro de entrada seleccionado y ajusta el stock."""
        seleccion = tabla_entradas.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_entradas.item(item_id, "values")
           
            codigo_actual = values[0]
            producto_nombre_actual = values[1]
            cantidad_actual = float(values[2]) 
            unidad_medida_actual = values[3]
            fecha_actual = values[4]
            destino_actual = values[5]
            entrada_id = values[6] 

            print(f"DEBUG: Editando entrada con EntradaID: {entrada_id}")

            ventana_edicion_entrada = tk.Toplevel(ventana_reporte_entradas)
            ventana_edicion_entrada.title(f"Editar Entrada ID: {entrada_id}")
            ventana_edicion_entrada.configure(bg="#A9A9A9")
            ventana_edicion_entrada.transient(ventana_reporte_entradas) 
            ventana_edicion_entrada.grab_set() 

            
            cantidad_var = tk.StringVar(value=str(cantidad_actual))
            fecha_var = tk.StringVar(value=fecha_actual)
            destino_var = tk.StringVar(value=destino_actual)
            unidad_medida_var = tk.StringVar(value=unidad_medida_actual) 

            
            def cargar_unidades_desde_db():
                mydb = conectar_mysql()
                unidades = []
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        cursor.execute("SELECT NombreUnidad FROM unidades_medida ORDER BY NombreUnidad")
                        for (nombre,) in cursor:
                            unidades.append(nombre)
                    except mysql.connector.Error as err:
                        messagebox.showerror("Error DB", f"Error al cargar unidades de medida: {err}", parent=ventana_edicion_entrada)
                    finally:
                        if cursor: cursor.close()
                        if mydb and mydb.is_connected(): mydb.close()
                return unidades

            unidades_disponibles = cargar_unidades_desde_db()

            
            tk.Label(ventana_edicion_entrada, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            entry_codigo_edicion = ttk.Entry(ventana_edicion_entrada, width=30)
            entry_codigo_edicion.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            entry_codigo_edicion.insert(0, codigo_actual)
            entry_codigo_edicion.config(state="readonly")

            tk.Label(ventana_edicion_entrada, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            entry_producto_edicion = ttk.Entry(ventana_edicion_entrada, width=30)
            entry_producto_edicion.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
            entry_producto_edicion.insert(0, producto_nombre_actual)
            entry_producto_edicion.config(state="readonly") 

            tk.Label(ventana_edicion_entrada, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            entry_cantidad_edicion = ttk.Entry(ventana_edicion_entrada, textvariable=cantidad_var, width=30)
            entry_cantidad_edicion.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
            

            tk.Label(ventana_edicion_entrada, text="Unidad Medida:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5, sticky="w")
           
            combo_unidad_medida_edicion = ttk.Combobox(ventana_edicion_entrada,
                                                       textvariable=unidad_medida_var,
                                                       values=unidades_disponibles,
                                                       width=30,
                                                       style="TCombobox")
            combo_unidad_medida_edicion.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
            
            if unidad_medida_actual in unidades_disponibles:
                combo_unidad_medida_edicion.set(unidad_medida_actual)
            else:
                
               
                if unidades_disponibles:
                    combo_unidad_medida_edicion.set(unidades_disponibles[0])
                else:
                    combo_unidad_medida_edicion.set("") 

            tk.Label(ventana_edicion_entrada, text="Fecha:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5, sticky="w")
            entry_fecha_edicion = ttk.Entry(ventana_edicion_entrada, textvariable=fecha_var, width=30)
            entry_fecha_edicion.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
            
            ttk.Button(ventana_edicion_entrada, text="Calendario", command=lambda: abrir_calendario(ventana_edicion_entrada, entry_fecha_edicion)).grid(row=4, column=2, padx=5, pady=5)

            tk.Label(ventana_edicion_entrada, text="Destino:", fg="#ffffff", bg="#A9A9A9").grid(row=5, column=0, padx=5, pady=5, sticky="w")
            entry_destino_edicion = ttk.Entry(ventana_edicion_entrada, textvariable=destino_var, width=30)
            entry_destino_edicion.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
            


            def guardar_cambios_entrada():
                """Guarda los cambios de una entrada y ajusta el stock del producto."""
                nueva_cantidad_str = cantidad_var.get().strip() 
                nueva_unidad_medida = unidad_medida_var.get().strip() 
                nuevo_destino = destino_var.get().strip() 
                nueva_fecha_str = fecha_var.get().strip()

                
                try:
                    nueva_cantidad = float(nueva_cantidad_str)
                    if nueva_cantidad <= 0:
                        messagebox.showerror("Error", "La cantidad debe ser un número positivo.", parent=ventana_edicion_entrada)
                        return
                except ValueError:
                    messagebox.showerror("Error", "La cantidad debe ser un número válido.", parent=ventana_edicion_entrada)
                    return
                
                if not nueva_unidad_medida:
                    messagebox.showerror("Error", "La unidad de medida no puede estar vacía.", parent=ventana_edicion_entrada)
                    return

                try:
                    nueva_fecha = datetime.datetime.strptime(nueva_fecha_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).", parent=ventana_edicion_entrada)
                    return

                if not nuevo_destino:
                    messagebox.showerror("Error", "El destino no puede estar vacío.", parent=ventana_edicion_entrada)
                    return

                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction() 

                       
                        cursor.execute("SELECT ProductoID FROM entradas WHERE EntradaID = %s", (entrada_id,))
                        producto_id_result = cursor.fetchone()
                        if not producto_id_result:
                            messagebox.showerror("Error", "No se pudo encontrar el ProductoID para esta entrada.", parent=ventana_edicion_entrada)
                            mydb.rollback() 
                            return
                        producto_id = producto_id_result[0]

                       
                        cursor.execute("SELECT Cantidad, UnidadMedida FROM entradas WHERE EntradaID = %s", (entrada_id,))
                        cantidad_unidad_original_result = cursor.fetchone()
                        if not cantidad_unidad_original_result:
                            messagebox.showerror("Error", "No se pudo encontrar la cantidad o unidad de medida original de la entrada.", parent=ventana_edicion_entrada)
                            mydb.rollback() # Revertir
                            return
                        cantidad_original_db = float(cantidad_unidad_original_result[0])
                        unidad_medida_original_db = cantidad_unidad_original_result[1]

                        
                        diferencia_cantidad = nueva_cantidad - cantidad_original_db

                        
                        query_update_stock = """
                            UPDATE productos
                            SET Stock = Stock + %s
                            WHERE ProductoID = %s
                        """
                        cursor.execute(query_update_stock, (diferencia_cantidad, producto_id))

                        
                        
                        query_update_entrada = """
                            UPDATE entradas
                            SET Cantidad = %s, UnidadMedida = %s, FechaEntrada = %s, Destino = %s
                            WHERE EntradaID = %s
                        """
                        cursor.execute(query_update_entrada, (nueva_cantidad, nueva_unidad_medida, nueva_fecha, nuevo_destino, entrada_id))

                        mydb.commit() 
                        messagebox.showinfo("Éxito", "Entrada actualizada y stock ajustado correctamente.", parent=ventana_edicion_entrada)
                        aplicar_filtro_entradas() 
                        ventana_edicion_entrada.destroy()

                    except mysql.connector.Error as err:
                        mydb.rollback() 
                        messagebox.showerror("Error de Base de Datos", f"Error al actualizar la entrada o el stock: {err}", parent=ventana_edicion_entrada)
                    except Exception as e:
                        mydb.rollback() 
                        messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_edicion_entrada)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
                
            ttk.Button(ventana_edicion_entrada, text="Guardar Cambios", command=guardar_cambios_entrada).grid(row=6, column=0, columnspan=3, pady=10)
            ventana_edicion_entrada.grid_columnconfigure(1, weight=1) 
            ventana_edicion_entrada.mainloop() 
        else:
            messagebox.showerror("Error", "Seleccione una entrada para editar.", parent=ventana_reporte_entradas)

    def eliminar_entrada():
        """Elimina un registro de entrada seleccionado y ajusta el stock del producto."""
        seleccion = tabla_entradas.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_entradas.item(item_id, "values")
            
            entrada_id = values[6] 
            cantidad_entrada = float(values[2])
            codigo_producto = values[0] 
            confirmacion = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Está seguro de que desea eliminar la entrada con ID {entrada_id} ({codigo_producto} - Cantidad: {cantidad_entrada})?\n"
                "¡Esta acción restará la cantidad de esta entrada del stock actual del producto!",
                parent=ventana_reporte_entradas
            )

            if confirmacion:
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction() 

                       
                        cursor.execute("SELECT ProductoID FROM entradas WHERE EntradaID = %s", (entrada_id,))
                        producto_id_result = cursor.fetchone()
                        if not producto_id_result:
                            messagebox.showerror("Error", "No se pudo encontrar el ProductoID para esta entrada.", parent=ventana_reporte_entradas)
                            mydb.rollback()
                            return
                        producto_id = producto_id_result[0]

                        
                        query_eliminar_entrada = "DELETE FROM entradas WHERE EntradaID = %s"
                        cursor.execute(query_eliminar_entrada, (entrada_id,))

                        
                        query_ajustar_stock = "UPDATE productos SET Stock = Stock - %s WHERE ProductoID = %s"
                        cursor.execute(query_ajustar_stock, (cantidad_entrada, producto_id))

                        mydb.commit() 
                        messagebox.showinfo("Eliminación Exitosa", "La entrada ha sido eliminada y el stock ajustado correctamente.", parent=ventana_reporte_entradas)
                        aplicar_filtro_entradas()
                    except mysql.connector.Error as err:
                        mydb.rollback() 
                        messagebox.showerror("Error", f"Error al eliminar la entrada o ajustar el stock: {err}", parent=ventana_reporte_entradas)
                    except Exception as e:
                        mydb.rollback() 
                        messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_reporte_entradas)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una entrada para eliminar.", parent=ventana_reporte_entradas)


    
    menu_contextual_entradas = tk.Menu(ventana_reporte_entradas, tearoff=0)
    menu_contextual_entradas.add_command(label="Editar Entrada", command=editar_entrada)
    menu_contextual_entradas.add_command(label="Eliminar Entrada", command=eliminar_entrada)

    def mostrar_menu_contextual_entradas(event):
        global current_user_role_is_admin
        if current_user_role_is_admin:
            item = tabla_entradas.identify_row(event.y)
            if item:
                tabla_entradas.selection_set(item)
                menu_contextual_entradas.post(event.x_root, event.y_root) 
        else:
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones en el historial.", parent=ventana_reporte_entradas)

    tabla_entradas.bind("<Button-3>", mostrar_menu_contextual_entradas) 

   
    ventana_reporte_entradas.mainloop()



                        #GENERA UNA VENTANA CON TODOS LOS PRODUCTOS QUE HAN SALIDO
def generar_reporte_salidas():
    """Genera un reporte del historial de salidas desde la base de datos MySQL."""
    global ventana, ventana_reporte_salidas, tree, entry_busqueda_salidas, departamento_seleccionado_reporte, current_user_role_is_admin

    
    if ventana_reporte_salidas and ventana_reporte_salidas.winfo_exists():
        ventana_reporte_salidas.lift()
        aplicar_filtro_salidas() 
        return

    
    try:
        if ventana is None or not ventana.winfo_exists():
            ventana = tk.Tk()
            ventana.withdraw() 
    except NameError:
        ventana = tk.Tk()
        ventana.withdraw()

    ventana_reporte_salidas = tk.Toplevel(ventana)
    ventana_reporte_salidas.title("Reporte de Salidas")
    ventana_reporte_salidas.geometry("1000x600")
    ventana_reporte_salidas.configure(bg="#A9A9A9")
    ventana_reporte_salidas.protocol("WM_DELETE_WINDOW", lambda: ventana_reporte_salidas.destroy())


    style = ttk.Style(ventana_reporte_salidas)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))


    frame_controles_salidas = tk.Frame(ventana_reporte_salidas, bg="#A9A9A9")
    frame_controles_salidas.pack(pady=10, padx=10, fill=tk.X)

    ttk.Label(frame_controles_salidas, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda_salidas = ttk.Entry(frame_controles_salidas, style="CustomEntry.TEntry")
    entry_busqueda_salidas.pack(side=tk.LEFT, padx=(0, 10))

    departamentos_mostrar = ["Todos los departamentos"]
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        try:
            cursor.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
            departamentos_db = [row[0] for row in cursor.fetchall()]
            departamentos_mostrar.extend(departamentos_db)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de BD", f"Error al cargar departamentos: {err}")
        finally:
            if cursor: cursor.close()
            if mydb and mydb.is_connected(): mydb.close()

    departamento_seleccionado_reporte = tk.StringVar(frame_controles_salidas)
    departamento_seleccionado_reporte.set(departamentos_mostrar[0])

    menu_departamentos_reporte = ttk.Combobox(frame_controles_salidas,
                                               textvariable=departamento_seleccionado_reporte,
                                               values=departamentos_mostrar,
                                               style="TCombobox",
                                               state="readonly")
    menu_departamentos_reporte.pack(side=tk.LEFT, padx=(0, 10))

    
    boton_exportar_pdf = ttk.Button(frame_controles_salidas, text="Exportar a PDF",
                                    command=lambda: exportar_tabla_pdf(tree, "Historial de Salidas"))
    boton_exportar_pdf.pack(side=tk.RIGHT, padx=(10, 0))

    frame_tabla_contenedor_salidas = tk.Frame(ventana_reporte_salidas, bg="#A9A9A9")
    frame_tabla_contenedor_salidas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

   
    tree = ttk.Treeview(frame_tabla_contenedor_salidas, columns=("Código", "Producto", "Cantidad", "Unidad Medida", "Fecha", "Destino", "Requisición", "SalidaID"), show="headings", style="Grid.Treeview")
    tree.heading("Código", text="Código", anchor=tk.W)
    tree.heading("Producto", text="Producto", anchor=tk.W)
    tree.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tree.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tree.heading("Fecha", text="Fecha", anchor=tk.W)
    tree.heading("Destino", text="Departamento", anchor=tk.W) 
    tree.heading("Requisición", text="Requisición", anchor=tk.W)
    tree.column("SalidaID", width=0, stretch=tk.NO) 

    tree.column("Código", width=100)
    tree.column("Producto", width=180)
    tree.column("Cantidad", width=80)
    tree.column("Unidad Medida", width=100) 
    tree.column("Fecha", width=100)
    tree.column("Destino", width=150)
    tree.column("Requisición", width=120)

    scrollbar = ttk.Scrollbar(frame_tabla_contenedor_salidas, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


    def cargar_salidas(filtro_busqueda="", departamento_filtro="Todos los departamentos"):
        """Carga las salidas desde la base de datos y las muestra en la tabla con filtros."""
        tree.delete(*tree.get_children())
        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        try:
            
            sql_query = """
                SELECT
                    s.SalidaID,
                    p.Codigo,
                    p.Nombre,
                    s.Cantidad,
                    s.UnidadMedida,  -- <--- Agregada aquí
                    s.FechaSalida,
                    d.NombreDepartamento,
                    s.NumeroRequisicion
                FROM
                    salidas s
                JOIN
                    productos p ON s.ProductoID = p.ProductoID
                JOIN
                    departamentos d ON s.DepartamentoID = d.DepartamentoID
                WHERE 1=1
            """
            params = []

            if filtro_busqueda:
                sql_query += " AND (p.Codigo LIKE %s OR p.Nombre LIKE %s OR s.NumeroRequisicion LIKE %s)"
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")


            if departamento_filtro and departamento_filtro != "Todos los departamentos":
                sql_query += " AND d.NombreDepartamento = %s"
                params.append(departamento_filtro)

            sql_query += " ORDER BY s.FechaSalida DESC, s.SalidaID DESC"

            cursor.execute(sql_query, tuple(params))
            salidas_db = cursor.fetchall()

           
            for salida_id, codigo, producto_nombre, cantidad, unidad_medida, fecha, departamento_nombre, requisicion in salidas_db:
                tree.insert("", "end", values=(codigo, producto_nombre, cantidad, unidad_medida, fecha.strftime("%Y-%m-%d"), departamento_nombre, requisicion, salida_id))

        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al cargar las salidas: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

    def editar_salida():
        """Abre una ventana para editar un registro de salida seleccionado y ajusta el stock."""
        seleccion = tree.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tree.item(item_id, "values")
           
            codigo_actual = values[0]
            producto_nombre_actual = values[1]
            cantidad_actual = float(values[2]) 
            unidad_medida_actual = values[3] 
            fecha_actual = values[4]
            departamento_nombre_actual = values[5] 
            requisicion_actual = values[6]
            salida_id = values[7] 

            print(f"DEBUG: Editando salida con SalidaID: {salida_id}")

            ventana_edicion_salida = tk.Toplevel(ventana_reporte_salidas)
            ventana_edicion_salida.title(f"Editar Salida ID: {salida_id}")
            ventana_edicion_salida.configure(bg="#A9A9A9")
            ventana_edicion_salida.transient(ventana_reporte_salidas) 
            ventana_edicion_salida.grab_set() 

            
            cantidad_var = tk.StringVar(value=str(cantidad_actual))
            unidad_medida_var = tk.StringVar(value=unidad_medida_actual) 
            fecha_var = tk.StringVar(value=fecha_actual)
            departamento_var = tk.StringVar(value=departamento_nombre_actual)
            requisicion_var = tk.StringVar(value=requisicion_actual)

            
            def cargar_departamentos_desde_db():
                mydb = conectar_mysql()
                departamentos = []
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        cursor.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
                        for (nombre,) in cursor:
                            departamentos.append(nombre)
                    except mysql.connector.Error as err:
                        messagebox.showerror("Error DB", f"Error al cargar departamentos: {err}", parent=ventana_edicion_salida)
                    finally:
                        if cursor: cursor.close()
                        if mydb and mydb.is_connected(): mydb.close()
                return departamentos

            departamentos_disponibles = cargar_departamentos_desde_db()

            def cargar_unidades_medida():
                
                mydb = conectar_mysql()
                unidades = []
                if mydb:
                    cursor = mydb.cursor()
                    try:
                       
                        cursor.execute("SELECT DISTINCT UnidadMedida FROM productos ORDER BY UnidadMedida")
                        unidades = [row[0] for row in cursor.fetchall()]
                    except mysql.connector.Error as err:
                        print(f"Error al cargar unidades de medida: {err}")
                    finally:
                        if cursor: cursor.close()
                        if mydb and mydb.is_connected(): mydb.close()
                return unidades

            unidades_disponibles = cargar_unidades_medida()


            
            tk.Label(ventana_edicion_salida, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            entry_codigo_edicion = ttk.Entry(ventana_edicion_salida, width=30)
            entry_codigo_edicion.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            entry_codigo_edicion.insert(0, codigo_actual)
            entry_codigo_edicion.config(state="readonly") 

            tk.Label(ventana_edicion_salida, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            entry_producto_edicion = ttk.Entry(ventana_edicion_salida, width=30)
            entry_producto_edicion.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
            entry_producto_edicion.insert(0, producto_nombre_actual)
            entry_producto_edicion.config(state="readonly") 

            tk.Label(ventana_edicion_salida, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            entry_cantidad_edicion = ttk.Entry(ventana_edicion_salida, textvariable=cantidad_var, width=30)
            entry_cantidad_edicion.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

            
            tk.Label(ventana_edicion_salida, text="Unidad Medida:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5, sticky="w")
            combo_unidad_medida_edicion = ttk.Combobox(ventana_edicion_salida,
                                                     textvariable=unidad_medida_var,
                                                     values=unidades_disponibles, 
                                                     width=30,
                                                     style="TCombobox",
                                                     state="readonly")
            combo_unidad_medida_edicion.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
            if unidad_medida_actual in unidades_disponibles:
                combo_unidad_medida_edicion.set(unidad_medida_actual)
            elif unidades_disponibles: 
                combo_unidad_medida_edicion.set(unidades_disponibles[0])
            else: 
                combo_unidad_medida_edicion.set("")
            
            
            tk.Label(ventana_edicion_salida, text="Fecha:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5, sticky="w")
            entry_fecha_edicion = ttk.Entry(ventana_edicion_salida, textvariable=fecha_var, width=30)
            entry_fecha_edicion.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
            ttk.Button(ventana_edicion_salida, text="Calendario", command=lambda: abrir_calendario(ventana_edicion_salida, entry_fecha_edicion)).grid(row=4, column=2, padx=5, pady=5)

            tk.Label(ventana_edicion_salida, text="Departamento:", fg="#ffffff", bg="#A9A9A9").grid(row=5, column=0, padx=5, pady=5, sticky="w")
            combo_departamento_edicion = ttk.Combobox(ventana_edicion_salida,
                                                     textvariable=departamento_var,
                                                     values=departamentos_disponibles,
                                                     width=30,
                                                     style="TCombobox",
                                                     state="readonly")
            combo_departamento_edicion.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
            if departamento_nombre_actual in departamentos_disponibles:
                combo_departamento_edicion.set(departamento_nombre_actual)
            else:
                if departamentos_disponibles:
                    combo_departamento_edicion.set(departamentos_disponibles[0])
                else:
                    combo_departamento_edicion.set("")

            tk.Label(ventana_edicion_salida, text="Requisición:", fg="#ffffff", bg="#A9A9A9").grid(row=6, column=0, padx=5, pady=5, sticky="w")
            entry_requisicion_edicion = ttk.Entry(ventana_edicion_salida, textvariable=requisicion_var, width=30)
            entry_requisicion_edicion.grid(row=6, column=1, padx=5, pady=5, sticky="ew")


            def guardar_cambios_salida():
                """Guarda los cambios de una salida y ajusta el stock del producto."""
                nueva_cantidad_str = cantidad_var.get().strip()
                nueva_unidad_medida = unidad_medida_var.get().strip()
                nueva_fecha_str = fecha_var.get().strip()
                nuevo_departamento_nombre = departamento_var.get().strip()
                nueva_requisicion = requisicion_var.get().strip()

                
                try:
                    nueva_cantidad = float(nueva_cantidad_str)
                    if nueva_cantidad <= 0:
                        messagebox.showerror("Error", "La cantidad debe ser un número positivo.", parent=ventana_edicion_salida)
                        return
                except ValueError:
                    messagebox.showerror("Error", "La cantidad debe ser un número válido.", parent=ventana_edicion_salida)
                    return

                try:
                    nueva_fecha = datetime.datetime.strptime(nueva_fecha_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).", parent=ventana_edicion_salida)
                    return

                if not nuevo_departamento_nombre:
                    messagebox.showerror("Error", "El departamento no puede estar vacío.", parent=ventana_edicion_salida)
                    return
                
                if not nueva_unidad_medida: 
                    messagebox.showerror("Error", "La unidad de medida no puede estar vacía.", parent=ventana_edicion_salida)
                    return


                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction() 

                        
                        cursor.execute("SELECT ProductoID, Cantidad, UnidadMedida FROM salidas WHERE SalidaID = %s", (salida_id,))
                        salida_original_data = cursor.fetchone()
                        if not salida_original_data:
                            messagebox.showerror("Error", "No se pudo encontrar la salida original.", parent=ventana_edicion_salida)
                            mydb.rollback()
                            return
                        
                        producto_id_original = salida_original_data[0]
                        cantidad_original = float(salida_original_data[1])
                        
                        cursor.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (nuevo_departamento_nombre,))
                        nuevo_departamento_id_result = cursor.fetchone()
                        if not nuevo_departamento_id_result:
                            messagebox.showerror("Error", "Departamento seleccionado no válido.", parent=ventana_edicion_salida)
                            mydb.rollback()
                            return
                        nuevo_departamento_id = nuevo_departamento_id_result[0]

                       
                        ajuste_stock = cantidad_original - nueva_cantidad

                        
                        query_update_stock = """
                            UPDATE productos
                            SET Stock = Stock + %s
                            WHERE ProductoID = %s
                        """
                        cursor.execute(query_update_stock, (ajuste_stock, producto_id_original))

                       
                        query_update_salida = """
                            UPDATE salidas
                            SET Cantidad = %s, UnidadMedida = %s, FechaSalida = %s, DepartamentoID = %s, NumeroRequisicion = %s
                            WHERE SalidaID = %s
                        """
                        cursor.execute(query_update_salida, (nueva_cantidad, nueva_unidad_medida, nueva_fecha, nuevo_departamento_id, nueva_requisicion, salida_id))

                        mydb.commit()
                        messagebox.showinfo("Éxito", "Salida actualizada y stock ajustado correctamente.", parent=ventana_edicion_salida)
                        
                        aplicar_filtro_salidas() 


                        ventana_edicion_salida.destroy()

                    except mysql.connector.Error as err:
                        mydb.rollback() 
                        messagebox.showerror("Error de Base de Datos", f"Error al actualizar la salida o el stock: {err}", parent=ventana_edicion_salida)
                    except Exception as e:
                        mydb.rollback() 
                        messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_edicion_salida)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
            
           
            ttk.Button(ventana_edicion_salida, text="Guardar Cambios", command=guardar_cambios_salida).grid(row=7, column=0, columnspan=3, pady=10)
            ventana_edicion_salida.grid_columnconfigure(1, weight=1)
            ventana_edicion_salida.mainloop()
        else:
            messagebox.showerror("Error", "Seleccione una salida para editar.", parent=ventana_reporte_salidas)

    def eliminar_salida():
        """Elimina un registro de salida seleccionado y ajusta el stock del producto (reingresando la cantidad)."""
        seleccion = tree.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tree.item(item_id, "values")
            
            salida_id = values[7] 
            cantidad_salida = float(values[2]) 
            codigo_producto = values[0] 
            
            confirmacion = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Está seguro de que desea eliminar la salida con ID {salida_id} ({codigo_producto} - Cantidad: {cantidad_salida})?\n"
                "¡Esta acción REINGRESARÁ la cantidad de esta salida al stock actual del producto!",
                parent=ventana_reporte_salidas
            )

            if confirmacion:
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction() 
                        
                        cursor.execute("SELECT ProductoID FROM salidas WHERE SalidaID = %s", (salida_id,))
                        producto_id_result = cursor.fetchone()
                        if not producto_id_result:
                            messagebox.showerror("Error", "No se pudo encontrar el ProductoID para esta salida.", parent=ventana_reporte_salidas)
                            mydb.rollback()
                            return
                        producto_id = producto_id_result[0]

                        
                        query_eliminar_salida = "DELETE FROM salidas WHERE SalidaID = %s"
                        cursor.execute(query_eliminar_salida, (salida_id,))

                        
                        query_ajustar_stock = "UPDATE productos SET Stock = Stock + %s WHERE ProductoID = %s"
                        cursor.execute(query_ajustar_stock, (cantidad_salida, producto_id))

                        mydb.commit() 
                        messagebox.showinfo("Eliminación Exitosa", "La salida ha sido eliminada y el stock ajustado correctamente.", parent=ventana_reporte_salidas)
                        aplicar_filtro_salidas() 
                    except mysql.connector.Error as err:
                        mydb.rollback() 
                        messagebox.showerror("Error", f"Error al eliminar la salida o ajustar el stock: {err}", parent=ventana_reporte_salidas)
                    except Exception as e:
                        mydb.rollback() 
                        messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_reporte_salidas)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una salida para eliminar.", parent=ventana_reporte_salidas)


    
    menu_contextual_salidas = tk.Menu(ventana_reporte_salidas, tearoff=0)
    menu_contextual_salidas.add_command(label="Editar Salida", command=editar_salida)
    menu_contextual_salidas.add_command(label="Eliminar Salida", command=eliminar_salida)
    
    def mostrar_menu_contextual_salidas(event):
        global current_user_role_is_admin 

        if current_user_role_is_admin: 
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
                menu_contextual_salidas.post(event.x_root, event.y_root)
        else:
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones en el historial de salidas.", parent=ventana_reporte_salidas)
    
    tree.bind("<Button-3>", mostrar_menu_contextual_salidas)

    
    def aplicar_filtro_salidas(*args):
        filtro_busqueda = entry_busqueda_salidas.get().strip()
        departamento_filtro = departamento_seleccionado_reporte.get()
        cargar_salidas(filtro_busqueda, departamento_filtro)

    
    entry_busqueda_salidas.bind("<KeyRelease>", aplicar_filtro_salidas)
    menu_departamentos_reporte.bind("<<ComboboxSelected>>", aplicar_filtro_salidas)

    
    cargar_salidas()

    
    ventana_reporte_salidas.grid_columnconfigure(0, weight=1)
    ventana_reporte_salidas.grid_rowconfigure(0, weight=1) 

    ventana_reporte_salidas.mainloop()

tabla_salidas_espera = None




def actualizar_tabla_salidas_espera(filtro_busqueda=""):
    """Actualiza el contenido de la tabla de salidas en espera desde la base de datos con filtro."""
    global tabla_salidas_espera 
    
    if tabla_salidas_espera: 
        tabla_salidas_espera.delete(*tabla_salidas_espera.get_children())
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
           
            query = """
                SELECT spe.SalidaEsperaID, p.Codigo, p.Nombre, spe.Cantidad, spe.UnidadMedida, d.NombreDepartamento, spe.FechaSolicitud
                FROM salidas_espera spe
                JOIN productos p ON spe.ProductoID = p.ProductoID
                JOIN departamentos d ON spe.DepartamentoID = d.DepartamentoID
                WHERE 1=1 -- Cláusula siempre verdadera para facilitar la adición de AND
            """
            params = []

            if filtro_busqueda:
                query += " AND (p.Codigo LIKE %s OR p.Nombre LIKE %s OR d.NombreDepartamento LIKE %s)"
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")
            query += " ORDER BY spe.FechaSolicitud DESC"

            try:
                cursor.execute(query, tuple(params))
                salidas_espera_db = cursor.fetchall()
                
                for espera_id, codigo, producto, cantidad, unidad_medida, departamento_nombre, fecha_solicitud in salidas_espera_db: 
                   
                   
                    fecha_str = fecha_solicitud.strftime("%Y-%m-%d") if fecha_solicitud else ""
                    tabla_salidas_espera.insert("", tk.END, values=(codigo, producto, cantidad, unidad_medida, departamento_nombre, fecha_str, espera_id))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al actualizar la tabla de salidas en espera: {err}")
            finally:
                if mydb and mydb.is_connected():
                    cursor.close()
                    mydb.close()

def generar_reporte_salidas_espera():
    """Genera o trae al frente la ventana del reporte de salidas en espera desde la base de datos."""
    global ventana_reporte_salidas_espera, tabla_salidas_espera, entry_busqueda_espera, ventana 

    if ventana_reporte_salidas_espera and ventana_reporte_salidas_espera.winfo_exists():
        ventana_reporte_salidas_espera.lift()
        if entry_busqueda_espera:
            filtro_actual = entry_busqueda_espera.get().strip()
            actualizar_tabla_salidas_espera(filtro_actual)
        return
    
   
    ventana_reporte_salidas_espera = tk.Toplevel(ventana) 
    ventana_reporte_salidas_espera.title("Reporte de Salidas en Espera")
    ventana_reporte_salidas_espera.geometry("1000x600")
    ventana_reporte_salidas_espera.configure(bg="#A9A9A9")
    ventana_reporte_salidas_espera.protocol("WM_DELETE_WINDOW", ventana_reporte_salidas_espera.destroy)

    style = ttk.Style(ventana_reporte_salidas_espera)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))

    frame_controles = tk.Frame(ventana_reporte_salidas_espera, bg="#A9A9A9")
    frame_controles.pack(pady=10, padx=10, fill=tk.X)

    ttk.Label(frame_controles, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda_espera = ttk.Entry(frame_controles, style="CustomEntry.TEntry")
    entry_busqueda_espera.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)

    boton_exportar_pdf_espera = ttk.Button(frame_controles, text="Exportar a PDF",
                                            command=lambda: exportar_tabla_pdf(tabla_salidas_espera, "Reporte de Salidas en Espera"))
    boton_exportar_pdf_espera.pack(side=tk.RIGHT, padx=(10, 0))

    frame_tabla_contenedor = tk.Frame(ventana_reporte_salidas_espera, bg="#A9A9A9")
    frame_tabla_contenedor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

   
    tabla_salidas_espera = ttk.Treeview(frame_tabla_contenedor,
                                        columns=("Código", "Producto", "Cantidad", "Unidad Medida", "Departamento", "Fecha Solicitud", "EsperaID"),
                                        show="headings",
                                        style="Grid.Treeview")
    tabla_salidas_espera.column("EsperaID", width=0, stretch=tk.NO) 

    tabla_salidas_espera.heading("Código", text="Código", anchor=tk.W)
    tabla_salidas_espera.heading("Producto", text="Producto", anchor=tk.W)
    tabla_salidas_espera.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tabla_salidas_espera.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W) 
    tabla_salidas_espera.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla_salidas_espera.heading("Fecha Solicitud", text="Fecha Solicitud", anchor=tk.W)

    tabla_salidas_espera.column("Código", width=100)
    tabla_salidas_espera.column("Producto", width=180)
    tabla_salidas_espera.column("Cantidad", width=80)
    tabla_salidas_espera.column("Unidad Medida", width=100)
    tabla_salidas_espera.column("Departamento", width=150) 
    tabla_salidas_espera.column("Fecha Solicitud", width=120) 

    scrollbar_vertical = ttk.Scrollbar(frame_tabla_contenedor, orient="vertical", command=tabla_salidas_espera.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_salidas_espera.configure(yscrollcommand=scrollbar_vertical.set)

    tabla_salidas_espera.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def obtener_unidades_medida():
        mydb = conectar_mysql()
        unidades = []
        if mydb:
            cursor = mydb.cursor()
            try:
               
                cursor.execute("SELECT DISTINCT UnidadMedida FROM productos WHERE UnidadMedida IS NOT NULL AND UnidadMedida != '' ORDER BY UnidadMedida")
                unidades = [row[0] for row in cursor.fetchall()]
            except mysql.connector.Error as err:
                print(f"Error al cargar unidades de medida: {err}")
            finally:
                if cursor: cursor.close()
                if mydb and mydb.is_connected(): mydb.close()
        return unidades

    def agregar_requisicion():
        item_seleccionado = tabla_salidas_espera.selection()
        if item_seleccionado:
            item = item_seleccionado[0]
            values = tabla_salidas_espera.item(item, "values")

            
            if len(values) >= 7: 
                codigo_producto = values[0]
                producto_nombre = values[1]
                cantidad_salida = float(values[2])
                unidad_medida_salida = values[3] 
                departamento_nombre = values[4]
               
                espera_id = values[6] 

                def confirmar_requisicion():
                    numero_requisicion = entry_requisicion.get().strip()
                    if not numero_requisicion:
                        messagebox.showerror("Error", "El número de requisición no puede estar vacío.", parent=ventana_requisicion)
                        return

                    fecha_salida_str = entry_fecha.get()
                    try:
                        fecha_salida = datetime.datetime.strptime(fecha_salida_str, "%Y-%m-%d").date()
                    except ValueError:
                        messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).", parent=ventana_requisicion)
                        return

                    mydb = conectar_mysql()
                    if mydb:
                        cursor = mydb.cursor()
                        try:
                            mydb.start_transaction() 

                            cursor.execute("SELECT ProductoID, Stock FROM productos WHERE Codigo = %s", (codigo_producto,))
                            resultado_prod = cursor.fetchone()
                            if not resultado_prod:
                                messagebox.showerror("Error", f"Producto con código '{codigo_producto}' no encontrado.", parent=ventana_requisicion)
                                mydb.rollback()
                                return
                            producto_id_para_salida = resultado_prod[0]
                            stock_actual = resultado_prod[1]

                            if stock_actual < cantidad_salida:
                                messagebox.showerror("Error de Stock", f"No hay suficiente stock para el producto '{producto_nombre}'. Stock actual: {stock_actual}. Cantidad solicitada: {cantidad_salida}.", parent=ventana_requisicion)
                                mydb.rollback()
                                return

                            cursor.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (departamento_nombre,))
                            resultado_dep = cursor.fetchone()
                            if not resultado_dep:
                                messagebox.showerror("Error", f"Departamento '{departamento_nombre}' no encontrado en la base de datos.", parent=ventana_requisicion)
                                mydb.rollback()
                                return
                            departamento_id_para_salida = resultado_dep[0]

                            
                            query_insert_salida = """
                                INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, UnidadMedida, FechaSalida, DepartamentoID, NumeroRequisicion)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(query_insert_salida, (producto_id_para_salida, codigo_producto, cantidad_salida, unidad_medida_salida, fecha_salida, departamento_id_para_salida, numero_requisicion))

                          
                            query_update_producto = """
                                UPDATE productos
                                SET Stock = Stock - %s,
                                    DepartamentoID = %s -- ¡Aquí está el cambio!
                                WHERE ProductoID = %s
                            """
                           
                            cursor.execute(query_update_producto, (cantidad_salida, departamento_id_para_salida, producto_id_para_salida))

                            
                            query_eliminar_espera = "DELETE FROM salidas_espera WHERE SalidaEsperaID = %s"
                            cursor.execute(query_eliminar_espera, (espera_id,))

                            mydb.commit() 
                            messagebox.showinfo("Salida Registrada", f"La salida del producto '{producto_nombre}' al departamento '{departamento_nombre}' (Cantidad: {cantidad_salida} {unidad_medida_salida}) ha sido registrada y el inventario actualizado.", parent=ventana_requisicion)

                           
                            actualizar_tabla_salidas_espera(entry_busqueda_espera.get().strip())
                            
                            
                            if ventana_requisicion.winfo_exists():
                                ventana_requisicion.destroy()
                            
                            
                            mostrar_tabla() 
                            

                        except mysql.connector.Error as err:
                            mydb.rollback()
                            messagebox.showerror("Error", f"Error al confirmar la requisición: {err}", parent=ventana_requisicion)
                        except Exception as e: 
                            mydb.rollback()
                            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}", parent=ventana_requisicion)
                        finally:
                            if mydb and mydb.is_connected():
                                cursor.close()
                                mydb.close()

                ventana_requisicion = tk.Toplevel(ventana_reporte_salidas_espera)
                ventana_requisicion.title("Confirmar Requisición y Salida")
                ventana_requisicion.configure(bg="#A9A9A9")
                ventana_requisicion.transient(ventana_reporte_salidas_espera)
                ventana_requisicion.grab_set()

                
                tk.Label(ventana_requisicion, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5, sticky="w")
                tk.Label(ventana_requisicion, text=codigo_producto, fg="#ffffff", bg="#A9A9A9", anchor="w").grid(row=0, column=1, padx=5, pady=5, sticky="ew")

                tk.Label(ventana_requisicion, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5, sticky="w")
                tk.Label(ventana_requisicion, text=producto_nombre, fg="#ffffff", bg="#A9A9A9", anchor="w").grid(row=1, column=1, padx=5, pady=5, sticky="ew")

                tk.Label(ventana_requisicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5, sticky="w")
                
                tk.Label(ventana_requisicion, text=f"{cantidad_salida} {unidad_medida_salida}", fg="#ffffff", bg="#A9A9A9", anchor="w").grid(row=2, column=1, padx=5, pady=5, sticky="ew")

                tk.Label(ventana_requisicion, text="Departamento:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5, sticky="w")
                tk.Label(ventana_requisicion, text=departamento_nombre, fg="#ffffff", bg="#A9A9A9", anchor="w").grid(row=3, column=1, padx=5, pady=5, sticky="ew")

                
                tk.Label(ventana_requisicion, text="Número de Requisición:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5, sticky="w")
                entry_requisicion = ttk.Entry(ventana_requisicion, width=30)
                entry_requisicion.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

                tk.Label(ventana_requisicion, text="Fecha de Salida:", fg="#ffffff", bg="#A9A9A9").grid(row=5, column=0, padx=5, pady=5, sticky="w")
                entry_fecha = ttk.Entry(ventana_requisicion, width=30)
                entry_fecha.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
                entry_fecha.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
                ttk.Button(ventana_requisicion, text="Calendario", command=lambda: abrir_calendario(ventana_requisicion, entry_fecha)).grid(row=5, column=2, padx=5, pady=5)

                ttk.Button(ventana_requisicion, text="Confirmar Salida", command=confirmar_requisicion).grid(row=6, column=0, columnspan=3, pady=10)

                ventana_requisicion.grid_columnconfigure(1, weight=1)
                ventana_requisicion.mainloop()
            else:
                messagebox.showerror("Error", "Datos de producto incompletos. Asegúrese de seleccionar un producto válido y que la información esté completa.", parent=ventana_reporte_salidas_espera)
        else:
            messagebox.showerror("Error", "Seleccione una solicitud para agregar requisición.", parent=ventana_reporte_salidas_espera)

    def eliminar_salida_espera():
        """Elimina un registro de salida en espera. No afecta el stock."""
        seleccion = tabla_salidas_espera.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_salidas_espera.item(item_id, "values")
            
            espera_id = values[6] 
            producto_nombre = values[1]

            confirmacion = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Está seguro de que desea eliminar la solicitud de salida en espera del producto '{producto_nombre}' (ID: {espera_id})?\n"
                "Esta acción NO afectará el inventario actual, ya que el producto NO ha salido del stock.",
                parent=ventana_reporte_salidas_espera
            )

            if confirmacion:
                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction()
                        query_eliminar = "DELETE FROM salidas_espera WHERE SalidaEsperaID = %s"
                        cursor.execute(query_eliminar, (espera_id,))
                        mydb.commit()
                        messagebox.showinfo("Eliminación Exitosa", "La solicitud de salida en espera ha sido eliminada correctamente.", parent=ventana_reporte_salidas_espera)
                        actualizar_tabla_salidas_espera(entry_busqueda_espera.get().strip())
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al eliminar la solicitud: {err}", parent=ventana_reporte_salidas_espera)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
        else:
            messagebox.showerror("Error", "Por favor, seleccione una solicitud para eliminar.", parent=ventana_reporte_salidas_espera)


    def editar_salida_espera():
        """Abre una ventana para editar un registro de salida en espera seleccionado."""
        seleccion = tabla_salidas_espera.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_salidas_espera.item(item_id, "values")
            
            codigo_actual = values[0]
            producto_actual = values[1]
            cantidad_actual = values[2]
            unidad_medida_actual = values[3]
            departamento_actual_nombre = values[4]
            fecha_solicitud_actual = values[5] 
            espera_id = values[6] 

            print(f"DEBUG: Editando solicitud con SalidaEsperaID: {espera_id}")

            ventana_edicion = tk.Toplevel(ventana_reporte_salidas_espera)
            ventana_edicion.title(f"Editar Solicitud ID: {espera_id}")
            ventana_edicion.configure(bg="#A9A9A9")
            ventana_edicion.transient(ventana_reporte_salidas_espera)
            ventana_edicion.grab_set()

            
            cantidad_var = tk.StringVar(value=cantidad_actual)
            unidad_medida_var = tk.StringVar(value=unidad_medida_actual)
            departamento_var = tk.StringVar(value=departamento_actual_nombre)
            fecha_solicitud_var = tk.StringVar(value=fecha_solicitud_actual)


            tk.Label(ventana_edicion, text="Código:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            entry_codigo = ttk.Entry(ventana_edicion, width=30)
            entry_codigo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            entry_codigo.insert(0, codigo_actual)
            entry_codigo.config(state="readonly")

            tk.Label(ventana_edicion, text="Producto:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            entry_producto = ttk.Entry(ventana_edicion, width=30)
            entry_producto.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
            entry_producto.insert(0, producto_actual)
            entry_producto.config(state="readonly")

            
            tk.Label(ventana_edicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            entry_cantidad = ttk.Entry(ventana_edicion, textvariable=cantidad_var, width=30)
            entry_cantidad.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

            
            tk.Label(ventana_edicion, text="Unidad Medida:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5, sticky="w")
            combo_unidad_medida_edicion = ttk.Combobox(ventana_edicion,
                                                     textvariable=unidad_medida_var,
                                                     values=obtener_unidades_medida(), 
                                                     width=30,
                                                     style="TCombobox",
                                                     state="readonly")
            combo_unidad_medida_edicion.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
            
            if unidad_medida_actual in obtener_unidades_medida():
                combo_unidad_medida_edicion.set(unidad_medida_actual)
            elif obtener_unidades_medida():
                combo_unidad_medida_edicion.set(obtener_unidades_medida()[0])
            else:
                combo_unidad_medida_edicion.set("") 

            tk.Label(ventana_edicion, text="Departamento:", fg="#ffffff", bg="#A9A9A9").grid(row=4, column=0, padx=5, pady=5, sticky="w") # Ajuste de fila
            combo_departamento = ttk.Combobox(ventana_edicion, textvariable=departamento_var, values=obtener_departamentos(), state="readonly", width=30)
            combo_departamento.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
            if departamento_actual_nombre in obtener_departamentos():
                combo_departamento.set(departamento_actual_nombre)
            else:
                if obtener_departamentos():
                    combo_departamento.set(obtener_departamentos()[0])
                else:
                    combo_departamento.set("")
            

            tk.Label(ventana_edicion, text="Fecha Solicitud:", fg="#ffffff", bg="#A9A9A9").grid(row=5, column=0, padx=5, pady=5, sticky="w") # Ajuste de fila
            entry_fecha_solicitud = ttk.Entry(ventana_edicion, textvariable=fecha_solicitud_var, width=30)
            entry_fecha_solicitud.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
            ttk.Button(ventana_edicion, text="Calendario", command=lambda: abrir_calendario(ventana_edicion, entry_fecha_solicitud)).grid(row=5, column=2, padx=5, pady=5)


            def guardar_cambios():
                try:
                    nueva_cantidad = float(cantidad_var.get())
                    if nueva_cantidad <= 0:
                        messagebox.showerror("Error", "La cantidad debe ser un número positivo.", parent=ventana_edicion)
                        return
                except ValueError:
                    messagebox.showerror("Error", "La cantidad debe ser un número (entero o decimal).", parent=ventana_edicion)
                    return

                nueva_unidad_medida = unidad_medida_var.get().strip() 
                if not nueva_unidad_medida:
                    messagebox.showerror("Error", "La unidad de medida no puede estar vacía.", parent=ventana_edicion)
                    return

                nuevo_departamento_nombre = departamento_var.get()
                if not nuevo_departamento_nombre:
                    messagebox.showerror("Error", "Debe seleccionar un departamento.", parent=ventana_edicion)
                    return
                
                nueva_fecha_solicitud_str = fecha_solicitud_var.get().strip()
                try:
                    nueva_fecha_solicitud = datetime.datetime.strptime(nueva_fecha_solicitud_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha de solicitud incorrecto (YYYY-MM-DD).", parent=ventana_edicion)
                    return


                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        mydb.start_transaction()

                        
                        cursor.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (nuevo_departamento_nombre,))
                        resultado_dep_id = cursor.fetchone()
                        if not resultado_dep_id:
                            messagebox.showerror("Error", f"Departamento '{nuevo_departamento_nombre}' no encontrado.", parent=ventana_edicion)
                            mydb.rollback()
                            return
                        departamento_id_asociado = resultado_dep_id[0]

                        
                        query_update_espera = """
                            UPDATE salidas_espera
                            SET Cantidad = %s, UnidadMedida = %s, DepartamentoID = %s, FechaSolicitud = %s
                            WHERE SalidaEsperaID = %s
                        """
                       
                        cursor.execute(query_update_espera, (nueva_cantidad, nueva_unidad_medida, departamento_id_asociado, nueva_fecha_solicitud, espera_id))

                        mydb.commit()
                        messagebox.showinfo("Éxito", "Solicitud de salida en espera actualizada correctamente.", parent=ventana_edicion)
                        actualizar_tabla_salidas_espera(entry_busqueda_espera.get().strip())
                        ventana_edicion.destroy()

                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error de BD", f"Error al actualizar la solicitud de salida en espera: {err}", parent=ventana_edicion)
                    except Exception as e:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}", parent=ventana_edicion)
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()
            
            ttk.Button(ventana_edicion, text="Guardar Cambios", command=guardar_cambios).grid(row=6, column=0, columnspan=3, pady=10) # Ajuste de fila
            ventana_edicion.grid_columnconfigure(1, weight=1)
            ventana_edicion.mainloop()
        else:
            messagebox.showerror("Error", "Seleccione una solicitud para editar.", parent=ventana_reporte_salidas_espera)


    
    menu_contextual = tk.Menu(ventana_reporte_salidas_espera, tearoff=0)
    menu_contextual.add_command(label="Agregar Requisición", command=agregar_requisicion)
    menu_contextual.add_separator()
    menu_contextual.add_command(label="Editar Solicitud", command=editar_salida_espera)
    menu_contextual.add_command(label="Eliminar Solicitud", command=eliminar_salida_espera)


    def mostrar_menu_contextual(event):
        global current_user_role_is_admin 

        
        item = tabla_salidas_espera.identify_row(event.y)
        
        
        if item:
            tabla_salidas_espera.selection_set(item)
            values = tabla_salidas_espera.item(item, "values")
        
           
            menu = tk.Menu(tabla_salidas_espera, tearoff=0) 

           
            menu.add_command(label="Agregar Requisición", command=agregar_requisicion)
            
           
            if current_user_role_is_admin:
                menu.add_separator() 
                menu.add_command(label="Editar Solicitud", command=editar_salida_espera)
                menu.add_command(label="Eliminar Solicitud", command=eliminar_salida_espera)
            else:
                
                menu.add_separator() 
                menu.add_command(label="Editar Solicitud (Solo Admin)", state=tk.DISABLED)
                menu.add_command(label="Eliminar Solicitud (Solo Admin)", state=tk.DISABLED)

           
            menu.post(event.x_root, event.y_root)
            
        else:
            
            tabla_salidas_espera.selection_remove(tabla_salidas_espera.selection())
            
           
            pass


    
    tabla_salidas_espera.bind("<Button-3>", mostrar_menu_contextual)
    def aplicar_filtro_espera(*args):
        filtro_busqueda = entry_busqueda_espera.get().strip()
        actualizar_tabla_salidas_espera(filtro_busqueda)

    entry_busqueda_espera.bind("<KeyRelease>", aplicar_filtro_espera)

    actualizar_tabla_salidas_espera() 
    ventana_reporte_salidas_espera.grid_columnconfigure(0, weight=1)
    ventana_reporte_salidas_espera.grid_rowconfigure(0, weight=1)

    ventana_reporte_salidas_espera.mainloop()




def obtener_departamentos():
    departamentos = []
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        try:
            cursor.execute("SELECT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
            for (nombre,) in cursor.fetchall():
                departamentos.append(nombre)
        except mysql.connector.Error as err:
            print(f"Error al obtener departamentos: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()
    return departamentos



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


         


             #GENERA UNA VENTANA DONDE PODEMOS REALIZAR VARIOS REPORTES PARA EXPORTAR A PDF

def ventana_reportes():
    """Crea una ventana para generar reportes con opciones de filtrado y nuevos reportes."""
    ventana_reporte = tk.Toplevel()
    ventana_reporte.title("Generar Reportes")
    ventana_reporte.configure(bg="#A9A9A9")
    ventana_reporte.geometry("900x650") 

    style = ttk.Style(ventana_reporte)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("Small.TButton", font=("Segoe UI", 8))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TFrame", background="#A9A9A9")

    main_frame = ttk.Frame(ventana_reporte, style="TFrame")
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    main_frame.grid_columnconfigure(0, weight=1) 
    main_frame.grid_rowconfigure(1, weight=1) 

    frame_filtros = ttk.Frame(main_frame, style="TFrame")
    frame_filtros.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    for i in range(6):
        frame_filtros.grid_columnconfigure(i, weight=1)

    
    label_categoria = ttk.Label(frame_filtros, text="Filtrar por Categoría:", style="CustomLabel.TLabel")
    label_categoria.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
    def obtener_categorias_db():
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT DISTINCT c.NombreCategoria FROM categorias c JOIN productos p ON c.CategoriaID = p.CategoriaID ORDER BY c.NombreCategoria")
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
    categoria_seleccionada.set("")

    fecha_inicio_cat = tk.StringVar()
    fecha_fin_cat = tk.StringVar()
    fecha_inicio_cat.set("")
    fecha_fin_cat.set("")

    def seleccionar_fecha_inicio_cat():
        top = tk.Toplevel(ventana_reporte)
        top.title("Seleccionar Fecha")
        top.transient(ventana_reporte) 
        top.grab_set() 
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_inicio_cat.set(cal.get_date())
            label_fecha_inicio_seleccionada_cat.config(text="Inicio: " + fecha_inicio_cat.get())
            top.destroy()
            ventana_reporte.grab_release() 
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)
        ventana_reporte.wait_window(top) 

    def seleccionar_fecha_fin_cat():
        top = tk.Toplevel(ventana_reporte)
        top.title("Seleccionar Fecha")
        top.transient(ventana_reporte)
        top.grab_set()
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_fin_cat.set(cal.get_date())
            label_fecha_fin_seleccionada_cat.config(text="Fin: " + fecha_fin_cat.get())
            top.destroy()
            ventana_reporte.grab_release()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)
        ventana_reporte.wait_window(top)

    boton_fecha_inicio_cat = ttk.Button(frame_filtros, text="Inicio", command=seleccionar_fecha_inicio_cat, style="Small.TButton")
    boton_fecha_inicio_cat.grid(row=0, column=2, padx=5, pady=5)
    label_fecha_inicio_seleccionada_cat = ttk.Label(frame_filtros, text="Inicio: --", style="CustomLabel.TLabel")
    label_fecha_inicio_seleccionada_cat.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    boton_fecha_fin_cat = ttk.Button(frame_filtros, text="Fin", command=seleccionar_fecha_fin_cat, style="Small.TButton")
    boton_fecha_fin_cat.grid(row=0, column=4, padx=5, pady=5)
    label_fecha_fin_seleccionada_cat = ttk.Label(frame_filtros, text="Fin: --", style="CustomLabel.TLabel")
    label_fecha_fin_seleccionada_cat.grid(row=0, column=5, padx=5, pady=5, sticky="w")

    
    def obtener_departamentos_db():
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            try:
                cursor.execute("SELECT DISTINCT NombreDepartamento FROM departamentos ORDER BY NombreDepartamento")
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
    departamento_seleccionado.set("")

    fecha_inicio_dep = tk.StringVar()
    fecha_fin_dep = tk.StringVar()
    fecha_inicio_dep.set("")
    fecha_fin_dep.set("")

    def seleccionar_fecha_inicio_dep():
        top = tk.Toplevel(ventana_reporte)
        top.title("Seleccionar Fecha")
        top.transient(ventana_reporte)
        top.grab_set()
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_inicio_dep.set(cal.get_date())
            label_fecha_inicio_seleccionada_dep.config(text="Inicio: " + fecha_inicio_dep.get())
            top.destroy()
            ventana_reporte.grab_release()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)
        ventana_reporte.wait_window(top)

    def seleccionar_fecha_fin_dep():
        top = tk.Toplevel(ventana_reporte)
        top.title("Seleccionar Fecha")
        top.transient(ventana_reporte)
        top.grab_set()
        top.configure(bg="#A9A9A9")
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', background="#ffffff", foreground="#000000", bordercolor="#d9d9d9", selectbackground="#bddfff", selectforeground="#000000")
        cal.pack(padx=10, pady=10)
        def grabar_fecha():
            fecha_fin_dep.set(cal.get_date())
            label_fecha_fin_seleccionada_dep.config(text="Fin: " + fecha_fin_dep.get())
            top.destroy()
            ventana_reporte.grab_release()
        boton_seleccionar = ttk.Button(top, text="Seleccionar", command=grabar_fecha)
        boton_seleccionar.pack(pady=5)
        ventana_reporte.wait_window(top)

    boton_fecha_inicio_dep = ttk.Button(frame_filtros, text="Inicio", command=seleccionar_fecha_inicio_dep, style="Small.TButton")
    boton_fecha_inicio_dep.grid(row=1, column=2, padx=5, pady=5)
    label_fecha_inicio_seleccionada_dep = ttk.Label(frame_filtros, text="Inicio: --", style="CustomLabel.TLabel")
    label_fecha_inicio_seleccionada_dep.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    boton_fecha_fin_dep = ttk.Button(frame_filtros, text="Fin", command=seleccionar_fecha_fin_dep, style="Small.TButton")
    boton_fecha_fin_dep.grid(row=1, column=4, padx=5, pady=5)
    label_fecha_fin_seleccionada_dep = ttk.Label(frame_filtros, text="Fin: --", style="CustomLabel.TLabel")
    label_fecha_fin_seleccionada_dep.grid(row=1, column=5, padx=5, pady=5, sticky="w")

   
    label_stock = ttk.Label(frame_filtros, text="Filtrar por Stock:", style="CustomLabel.TLabel")
    label_stock.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    opciones_stock = ["Todos", "Bajo Stock (<= 2)", "Stock Medio (3-10)", "Stock Alto (>= 11)"]
    stock_seleccionado = ttk.Combobox(frame_filtros, values=opciones_stock, style="TCombobox", width=25)
    stock_seleccionado.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    stock_seleccionado.set("")

    
    label_requisicion = ttk.Label(frame_filtros, text="Número de Requisición:", style="CustomLabel.TLabel")
    label_requisicion.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    entry_numero_requisicion = ttk.Entry(frame_filtros, style="CustomEntry.TEntry", width=20)
    entry_numero_requisicion.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

    
    frame_tabla = ttk.Frame(main_frame, style="TFrame")
    frame_tabla.grid(row=1, column=0, padx=10, pady=10, sticky="nsew") 
    frame_tabla.grid_rowconfigure(0, weight=1) 
    frame_tabla.grid_columnconfigure(0, weight=1) 
    
    global tabla_reporte
    tabla_reporte = ttk.Treeview(frame_tabla, style="Grid.Treeview")
    tabla_reporte.grid(row=0, column=0, sticky="nsew") 

    
    scrollbar_y = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_reporte.yview)
    tabla_reporte.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.grid(row=0, column=1, sticky="ns") 
    
    scrollbar_x = ttk.Scrollbar(frame_tabla, orient="horizontal", command=tabla_reporte.xview)
    tabla_reporte.configure(xscrollcommand=scrollbar_x.set)
    scrollbar_x.grid(row=1, column=0, sticky="ew") 


    def limpiar_tabla_reporte():
        tabla_reporte.delete(*tabla_reporte.get_children())
        tabla_reporte["columns"] = () 
        tabla_reporte.heading("#0", text="") 
        categoria_seleccionada.set("")
        departamento_seleccionado.set("")
        stock_seleccionado.set("")
        fecha_inicio_cat.set("")
        fecha_fin_cat.set("")
        label_fecha_inicio_seleccionada_cat.config(text="Inicio: --")
        label_fecha_fin_seleccionada_cat.config(text="Fin: --")
        fecha_inicio_dep.set("")
        fecha_fin_dep.set("")
        label_fecha_inicio_seleccionada_dep.config(text="Inicio: --")
        label_fecha_fin_seleccionada_dep.config(text="Fin: --")
        entry_numero_requisicion.delete(0, tk.END) 
        ventana_reporte.current_report_title = "Reporte General"

    boton_limpiar = ttk.Button(frame_tabla, text="Limpiar", command=limpiar_tabla_reporte, style="Small.TButton")
    boton_limpiar.grid(row=2, column=0, columnspan=2, pady=5, sticky="se") 

    ventana_reporte.current_report_title = "Reporte General"

    def generar_reporte_filtrado():
        tabla_reporte.delete(*tabla_reporte.get_children())
        tabla_reporte["columns"] = ()
        tabla_reporte.heading("#0", text="")

        categoria = categoria_seleccionada.get().strip()
        departamento = departamento_seleccionado.get().strip()
        stock = stock_seleccionado.get().strip()
        numero_requisicion = entry_numero_requisicion.get().strip() 

        fecha_inicio_cat_str = fecha_inicio_cat.get()
        fecha_fin_cat_str = fecha_fin_cat.get()
        fecha_inicio_dep_str = fecha_inicio_dep.get()
        fecha_fin_dep_str = fecha_fin_dep.get()

        print("\n--- INICIO DE GENERAR_REPORTE_FILTRADO ---")
        print(f"Valores RAW: Cat='{categoria}', Dep='{departamento}', Stock='{stock}', Req='{numero_requisicion}', FechaICat='{fecha_inicio_cat_str}', FechaFCat='{fecha_fin_cat_str}', FechaIDep='{fecha_inicio_dep_str}', FechaFDep='{fecha_fin_dep_str}'")

       
        hay_seleccion_categoria = (categoria != "")
        hay_fechas_categoria = (fecha_inicio_cat_str != "" or fecha_fin_cat_str != "")

        hay_seleccion_departamento = (departamento != "")
        hay_fechas_departamento = (fecha_inicio_dep_str != "" or fecha_fin_dep_str != "")
        
        hay_seleccion_stock = (stock != "")
        hay_numero_requisicion = (numero_requisicion != "")

        print(f"Banderas de Selección: HayCat={hay_seleccion_categoria}, FechasCat={hay_fechas_categoria}, HayDep={hay_seleccion_departamento}, FechasDep={hay_fechas_departamento}, HayStock={hay_seleccion_stock}, HayReq={hay_numero_requisicion}")

        
        if hay_numero_requisicion:
            print("DEBUG: Detectado: Filtro por Número de Requisición activo.")
            
            generar_reporte_por_requisicion(numero_requisicion, departamento, tabla_reporte, ventana_reporte)
            
        elif hay_seleccion_categoria or hay_fechas_categoria:
            print("DEBUG: Detectado: Filtro de Categoría activo (incluyendo 'Todas') o fechas de categoría.")
            
            generar_reporte_consumo_lapso_filtrado(categoria, fecha_inicio_cat_str, fecha_fin_cat_str, departamento, stock, tabla_reporte, ventana_reporte)
            
        elif hay_seleccion_departamento or hay_fechas_departamento:
            print("DEBUG: Detectado: Filtro de Departamento activo (incluyendo 'Todos') o fechas de departamento.")
            
            generar_reporte_departamento(departamento, categoria, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte, stock)
            
        elif hay_seleccion_stock:
            print("DEBUG: Detectado: Filtro de Stock activo (incluyendo 'Todos').")
            
            generar_reporte_de_stock(stock, categoria, departamento, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte)
            
        else:
            print("DEBUG: Ningún filtro principal activo. Mostrando mensaje de información.")
            messagebox.showinfo("Selección de Filtros",
                                 "Por favor, selecciona al menos un criterio en Categoría, Departamento, Stock o ingresa un Número de Requisición para generar un reporte filtrado, o utiliza el botón 'Generar Inventario Completo'.",
                                 parent=ventana_reporte)
            ventana_reporte.current_report_title = "Reporte General" 

        print("--- FIN DE GENERAR_REPORTE_FILTRADO ---")
    
    
    boton_generar_filtrado = ttk.Button(frame_filtros, text="Generar Reporte Filtrado", command=generar_reporte_filtrado)
    boton_generar_filtrado.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew", padx=5) 

    boton_generar_completo = ttk.Button(frame_filtros, text="Generar Inventario Completo", command=lambda: generar_reporte_inventario_completo(tabla_reporte, ventana_reporte))
    boton_generar_completo.grid(row=4, column=2, columnspan=2, pady=10, sticky="ew", padx=5)

    

    boton_pdf = ttk.Button(main_frame, text="Exportar a PDF", command=lambda: exportar_tabla_pdf(tabla_reporte, titulo_reporte=getattr(ventana_reporte, 'current_report_title', 'Reporte General')))
    boton_pdf.grid(row=2, column=0, pady=10, sticky="ew")

    for i in range(6):
        frame_filtros.grid_columnconfigure(i, weight=1)

    frame_tabla.grid_columnconfigure(0, weight=1)


def generar_reporte_inventario_completo(tabla, ventana):
    """
    Genera un reporte completo de todo el inventario existente,
    con las mismas columnas que la interfaz 'Mostrar Inventario'.
    """
    tabla.delete(*tabla.get_children()) 

    
    ventana.current_report_title = "REPORTE DE TODO EL INVENTARIO"

    columnas = ("Código", "Categoría", "Producto", "Destino Entrada", "Destino Salida",
                "Entrada", "Salida", "Stock", "Unidad Medida", "Fecha Entrada", "Fecha Salida")
    tabla["columns"] = columnas
    tabla.heading("#0", text="") 

    for col in columnas:
        tabla.heading(col, text=col, anchor=tk.W)
        if col == "Stock": tabla.column(col, width=80, anchor=tk.CENTER)
        elif col in ("Entrada", "Salida", "Código", "Unidad Medida"): tabla.column(col, width=100, anchor=tk.CENTER)
        elif col in ("Fecha Entrada", "Fecha Salida", "Destino Entrada", "Destino Salida"): tabla.column(col, width=120, anchor=tk.W)
        else: tabla.column(col, width=150, anchor=tk.W)
    tabla.column("#0", width=0, stretch=tk.NO)

    mydb = conectar_mysql()
    if not mydb: 
        ventana.current_report_title = "Inventario Completo (Error de Conexión)" 
        return

    cursor = mydb.cursor()
    
    query = """
        SELECT
            p.Codigo,
            c.NombreCategoria,
            p.Nombre AS NombreProducto,
            COALESCE(e.Destino, '') AS DestinoEntrada,
            COALESCE(d_sal.NombreDepartamento, '') AS DestinoSalida,
            COALESCE(SUM(e.Cantidad), 0) AS TotalEntradas,
            COALESCE(SUM(s.Cantidad), 0) AS TotalSalidas,
            p.Stock,
            p.UnidadMedida,
            p.FechaEntrada,
            p.FechaSalida
        FROM
            productos p
        LEFT JOIN
            categorias c ON p.CategoriaID = c.CategoriaID
        LEFT JOIN
            entradas e ON p.ProductoID = e.ProductoID
        LEFT JOIN
            salidas s ON p.ProductoID = s.ProductoID
        LEFT JOIN
            departamentos d_sal ON s.DepartamentoID = d_sal.DepartamentoID
        GROUP BY
            p.ProductoID, p.Codigo, c.NombreCategoria, p.Nombre, p.Stock, p.UnidadMedida, p.FechaEntrada, p.FechaSalida, DestinoEntrada, DestinoSalida
        ORDER BY
            p.Codigo;
    """

    try:
        cursor.execute(query)
        inventario_data = cursor.fetchall()

        if not inventario_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron productos en el inventario.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Inventario Completo (Sin Resultados)"
            return

        for row in inventario_data:
            formatted_row = tuple("" if item is None else str(item) for item in row)
            tabla.insert("", tk.END, values=formatted_row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de inventario completo: {err}", parent=ventana)
        ventana.current_report_title = "Inventario Completo (Error)" 
    finally:
        if cursor: cursor.close()
        if mydb and mydb.is_connected(): mydb.close()


def generar_reporte_consumo_lapso_filtrado(categoria_filtro, fecha_inicio_str, fecha_fin_str, departamento_filtro_ignorado, stock_filtro_ignorado, tabla, ventana):
    """
    Genera un reporte de consumo por categoría/lapso.
    Muestra: Categoría, Producto, Cantidad Consumida, Unidad Medida, Lapso (rango de fechas).
    """
    tabla.delete(*tabla.get_children()) 

    
    report_title_parts = ["REPORTE DE CONSUMO"]
    if categoria_filtro and categoria_filtro != "Todas":
        report_title_parts.append(f"Categoría: '{categoria_filtro}'")
    
    lapso_texto = "Todo el Historial"
    if fecha_inicio_str and fecha_fin_str:
        report_title_parts.append(f"Fechas: {fecha_inicio_str} al {fecha_fin_str}")
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        report_title_parts.append("Todo el Historial")
    
    ventana.current_report_title = " | ".join(report_title_parts)
    
    tabla["columns"] = ("Categoría", "Producto", "Cantidad Consumida", "Unidad Medida", "Lapso")
    tabla.heading("#0", text="") 
    tabla.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla.heading("Producto", text="Producto", anchor=tk.W)
    tabla.heading("Cantidad Consumida", text="Cantidad Consumida", anchor=tk.W)
    tabla.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla.heading("Lapso", text="Lapso", anchor=tk.W)

    tabla.column("#0", width=0, stretch=tk.NO) 
    tabla.column("Categoría", width=120, anchor=tk.W)
    tabla.column("Producto", width=200, anchor=tk.W)
    tabla.column("Cantidad Consumida", width=100, anchor=tk.CENTER)
    tabla.column("Unidad Medida", width=100, anchor=tk.W) 
    tabla.column("Lapso", width=180, anchor=tk.W) 

    mydb = conectar_mysql()
    if not mydb:
        ventana.current_report_title = "Reporte de Consumo (Error de Conexión)"
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            cat.NombreCategoria,
            p.Nombre,
            SUM(s.Cantidad) AS CantidadTotalConsumida,
            p.UnidadMedida, -- Seleccionar UnidadMedida de la tabla productos
            MIN(s.FechaSalida) AS FechaInicioLapso,
            MAX(s.FechaSalida) AS FechaFinLapso
        FROM salidas s
        JOIN productos p ON s.ProductoID = p.ProductoID
        JOIN categorias cat ON p.CategoriaID = cat.CategoriaID
        WHERE 1=1
    """
    params = []
    

    if categoria_filtro != "Todas" and categoria_filtro != "":
        query += " AND cat.NombreCategoria = %s"
        params.append(categoria_filtro)

    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
    
    


    query += " GROUP BY cat.NombreCategoria, p.Nombre, p.UnidadMedida"
    query += " ORDER BY cat.NombreCategoria, p.Nombre"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron datos de consumo para los filtros de categoría y/o fecha seleccionados.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Reporte de Consumo (Sin Resultados)" 
            return

        total_consumo = 0
        for categoria_nombre, producto, cantidad_consumida, unidad_medida, _, _ in reporte_data:
            tabla.insert("", tk.END, values=(categoria_nombre, producto, cantidad_consumida, unidad_medida, lapso_texto))
            total_consumo += cantidad_consumida
        
        tabla.insert("", tk.END, values=("", "", "TOTAL CONSUMIDO:", total_consumo, "", ""), tags=('total_row',))
        tabla.tag_configure('total_row', background='#E0FFFF', font=('Segoe UI', 10, 'bold'))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de categoría/consumo: {err}", parent=ventana)
        ventana.current_report_title = "Reporte de Consumo (Error)" 
    finally:
        if cursor:
            cursor.close()
        if mydb and mydb.is_connected():
            mydb.close()

def generar_reporte_departamento(departamento_filtro, categoria_filtro, fecha_inicio_str, fecha_fin_str, tabla, ventana, stock_filtro_texto):
    """
    Genera un reporte de consumo por departamento y lapso.
    Muestra: Departamento, Categoría, Producto, Cantidad Consumida, Unidad Medida, Lapso, Número de Requisición.
    """
    tabla.delete(*tabla.get_children()) 

    report_title_parts = ["REPORTE DE DEPARTAMENTO"]
    if departamento_filtro and departamento_filtro != "Todos":
        report_title_parts.append(f"Departamento: '{departamento_filtro}'")
    if categoria_filtro and categoria_filtro != "Todas":
        report_title_parts.append(f"Categoría: '{categoria_filtro}'")
    
    lapso_texto = "Todo el Historial"
    if fecha_inicio_str and fecha_fin_str:
        report_title_parts.append(f"Fechas: {fecha_inicio_str} a {fecha_fin_str}")
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        report_title_parts.append("Todo el Historial")
    
    if stock_filtro_texto and stock_filtro_texto != "Todos":
        report_title_parts.append(f"Stock: '{stock_filtro_texto}'")

    ventana.current_report_title = " | ".join(report_title_parts)
    
    tabla["columns"] = ("Departamento", "Categoría", "Producto", "Cantidad Consumida", "Unidad Medida", "Lapso", "Número Requisición")
    tabla.heading("#0", text="") 
    tabla.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla.heading("Producto", text="Producto", anchor=tk.W)
    tabla.heading("Cantidad Consumida", text="Cantidad Consumida", anchor=tk.W)
    tabla.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla.heading("Lapso", text="Lapso", anchor=tk.W)
    tabla.heading("Número Requisición", text="Número Requisición", anchor=tk.W)

    tabla.column("#0", width=0, stretch=tk.NO)
    tabla.column("Departamento", width=120, anchor=tk.W)
    tabla.column("Categoría", width=100, anchor=tk.W)
    tabla.column("Producto", width=150, anchor=tk.W)
    tabla.column("Cantidad Consumida", width=100, anchor=tk.CENTER)
    tabla.column("Unidad Medida", width=100, anchor=tk.W)
    tabla.column("Lapso", width=120, anchor=tk.W) 
    tabla.column("Número Requisición", width=120, anchor=tk.W) 

    mydb = conectar_mysql()
    if not mydb:
        ventana.current_report_title = "Reporte por Departamento (Error de Conexión)"
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            d.NombreDepartamento,
            cat.NombreCategoria,
            p.Nombre,
            s.Cantidad,
            p.UnidadMedida,
            s.FechaSalida, -- Se usa para construir el lapso_texto si es necesario
            s.NumeroRequisicion 
        FROM salidas s
        JOIN productos p ON s.ProductoID = p.ProductoID
        JOIN departamentos d ON s.DepartamentoID = d.DepartamentoID
        JOIN categorias cat ON p.CategoriaID = cat.CategoriaID
        WHERE 1=1 
    """
    params = []
    
    if departamento_filtro != "Todos" and departamento_filtro != "":
        query += " AND d.NombreDepartamento = %s"
        params.append(departamento_filtro)

    if categoria_filtro != "Todas" and categoria_filtro != "":
        query += " AND cat.NombreCategoria = %s"
        params.append(categoria_filtro)

    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
    
    if stock_filtro_texto != "Todos" and stock_filtro_texto != "":
        if stock_filtro_texto == "Bajo Stock (<= 2)":
            query += " AND p.Stock <= 2"
        elif stock_filtro_texto == "Stock Medio (3-10)":
            query += " AND p.Stock BETWEEN 3 AND 10"
        elif stock_filtro_texto == "Stock Alto (>= 11)":
            query += " AND p.Stock >= 11"
    
   
    query += " ORDER BY s.NumeroRequisicion ASC, d.NombreDepartamento ASC, s.FechaSalida DESC" 

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron datos de consumo para los filtros de departamento seleccionados.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Reporte por Departamento (Sin Resultados)"
            return

        total_consumo = 0
        for departamento_nombre, categoria_nombre, producto, cantidad, unidad_medida, fecha_salida, numero_requisicion in reporte_data:
           
            display_lapso = f"{fecha_salida.strftime('%Y-%m-%d')}" if not (fecha_inicio_str and fecha_fin_str) else lapso_texto

            tabla.insert("", tk.END, values=(departamento_nombre, categoria_nombre, producto, cantidad, unidad_medida, display_lapso, numero_requisicion))
            total_consumo += cantidad
        
        tabla.insert("", tk.END, values=("", "", "TOTAL CONSUMIDO:", total_consumo, "", "", ""), tags=('total_row',))
        tabla.tag_configure('total_row', background='#E0FFFF', font=('Segoe UI', 10, 'bold'))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de departamento: {err}", parent=ventana)
        ventana.current_report_title = "Reporte por Departamento (Error)" 
    finally:
        if cursor:
            cursor.close()
        if mydb and mydb.is_connected():
            mydb.close()

def generar_reporte_de_stock(stock_filtro_texto, categoria_filtro, departamento_filtro, fecha_inicio_str, fecha_fin_str, tabla, ventana):
    """
    Genera un reporte de productos basado en el nivel de stock,
    con filtros opcionales por categoría y departamento.
    Muestra: Producto, Categoría, Unidad de Medida, Stock Actual.
    """
    tabla.delete(*tabla.get_children())

   
    report_title_parts = ["REPORTE DE STOCK"]
    if stock_filtro_texto and stock_filtro_texto != "Todos":
        report_title_parts.append(f"Nivel: '{stock_filtro_texto}'")
    if categoria_filtro and categoria_filtro != "Todas":
        report_title_parts.append(f"Categoría: '{categoria_filtro}'")
   
    ventana.current_report_title = " | ".join(report_title_parts)

    tabla["columns"] = ("Producto", "Categoría", "Unidad Medida", "Stock Actual")
    tabla.heading("#0", text="")
    tabla.heading("Producto", text="Producto", anchor=tk.W)
    tabla.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla.heading("Stock Actual", text="Stock Actual", anchor=tk.W)

    tabla.column("#0", width=0, stretch=tk.NO)
    tabla.column("Producto", width=250, anchor=tk.W)
    tabla.column("Categoría", width=150, anchor=tk.W)
    tabla.column("Unidad Medida", width=120, anchor=tk.W)
    tabla.column("Stock Actual", width=100, anchor=tk.CENTER)


    mydb = conectar_mysql()
    if not mydb:
        ventana.current_report_title = "Reporte de Stock (Error de Conexión)"
        return

    cursor = mydb.cursor()

    query = """
        SELECT
            p.Nombre AS NombreProducto,
            cat.NombreCategoria,
            p.UnidadMedida,
            p.Stock AS StockActualProducto
        FROM productos p
        JOIN categorias cat ON p.CategoriaID = cat.CategoriaID
        WHERE 1=1 -- Base para añadir condiciones dinámicas
    """
    params = []

    if stock_filtro_texto != "Todos" and stock_filtro_texto != "":
        if stock_filtro_texto == "Bajo Stock (<= 2)":
            query += " AND p.Stock <= 2"
        elif stock_filtro_texto == "Stock Medio (3-10)":
            query += " AND p.Stock BETWEEN 3 AND 10"
        elif stock_filtro_texto == "Stock Alto (>= 11)":
            query += " AND p.Stock >= 11"

    if categoria_filtro != "Todas" and categoria_filtro != "":
        query += " AND cat.NombreCategoria = %s"
        params.append(categoria_filtro)
   


    query += " ORDER BY p.Nombre"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron productos para los filtros de stock seleccionados.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Reporte de Stock (Sin Resultados)" 
            return

        for row in reporte_data:
            tabla.insert("", tk.END, values=row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de stock: {err}", parent=ventana)
        ventana.current_report_title = "Reporte de Stock (Error)"
    finally:
        if cursor:
            cursor.close()
        if mydb and mydb.is_connected():
            mydb.close()
def generar_reporte_por_requisicion(numero_requisicion_filtro, departamento_filtro, tabla, ventana):
    """
    Genera un reporte de salidas de productos filtrado por número de requisición y opcionalmente por departamento.
    Muestra: Número de Requisición, Departamento, Producto, Cantidad, Unidad Medida, Fecha de Salida.
    """
    tabla.delete(*tabla.get_children()) 

    report_title_parts = ["REPORTE POR REQUISICIÓN"]
    if numero_requisicion_filtro:
        report_title_parts.append(f"No. Requisición: '{numero_requisicion_filtro}'")
    if departamento_filtro and departamento_filtro != "Todos":
        report_title_parts.append(f"Departamento: '{departamento_filtro}'")
    else:
        report_title_parts.append("Todos los Departamentos")

    ventana.current_report_title = " | ".join(report_title_parts)
    
    columnas = ("Número Requisición", "Departamento", "Producto", "Cantidad", "Unidad Medida", "Fecha Salida")
    tabla["columns"] = columnas
    tabla.heading("#0", text="") 

    for col in columnas:
        tabla.heading(col, text=col, anchor=tk.W)
        if col == "Cantidad": tabla.column(col, width=90, anchor=tk.CENTER)
        elif col == "Unidad Medida": tabla.column(col, width=100, anchor=tk.W)
        elif col == "Fecha Salida": tabla.column(col, width=120, anchor=tk.W)
        elif col == "Número Requisición": tabla.column(col, width=130, anchor=tk.W)
        else: tabla.column(col, width=150, anchor=tk.W)
    tabla.column("#0", width=0, stretch=tk.NO)

    mydb = conectar_mysql() 
    if not mydb: 
        ventana.current_report_title = "Reporte por Requisición (Error de Conexión)" 
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            s.NumeroRequisicion,
            d.NombreDepartamento,
            p.Nombre AS NombreProducto,
            s.Cantidad,
            p.UnidadMedida,
            s.FechaSalida
        FROM
            salidas s
        JOIN
            productos p ON s.ProductoID = p.ProductoID
        JOIN
            departamentos d ON s.DepartamentoID = d.DepartamentoID
        WHERE 1=1
    """
    params = []

    if numero_requisicion_filtro:
        query += " AND s.NumeroRequisicion = %s"
        params.append(numero_requisicion_filtro)

    if departamento_filtro and departamento_filtro != "Todos":
        query += " AND d.NombreDepartamento = %s"
        params.append(departamento_filtro)
    
    query += " ORDER BY s.FechaSalida DESC, s.NumeroRequisicion, p.Nombre;"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", f"No se encontraron salidas para la requisición '{numero_requisicion_filtro}' y/o departamento '{departamento_filtro}'.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Reporte por Requisición (Sin Resultados)"
            return

        for row in reporte_data:
            formatted_row = tuple("" if item is None else str(item) for item in row)
            tabla.insert("", tk.END, values=formatted_row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte por requisición: {err}", parent=ventana)
        ventana.current_report_title = "Reporte por Requisición (Error)"
    finally:
        if cursor: cursor.close()
        if mydb and mydb.is_connected(): mydb.close()
def generar_reporte_categoria_departamento(categoria_filtro, departamento_filtro, fecha_inicio_str, fecha_fin_str, tabla, ventana):
    """
    Genera un reporte de consumo de productos de una categoría específica por un departamento específico.
    Muestra: Categoría, Departamento, Producto, Cantidad Consumida, Unidad Medida, Lapso.
    Incluye un total de la cantidad consumida.
    """
    tabla.delete(*tabla.get_children()) 

   
    report_title_parts = ["REPORTE DE CONSUMO POR CATEGORÍA Y DEPARTAMENTO"]
    if categoria_filtro and categoria_filtro != "Todas":
        report_title_parts.append(f"Categoría: '{categoria_filtro}'")
    if departamento_filtro and departamento_filtro != "Todos":
        report_title_parts.append(f"Departamento: '{departamento_filtro}'")
    
    lapso_texto_display = "Todo el Historial"
    if fecha_inicio_str and fecha_fin_str:
        report_title_parts.append(f"Fechas: {fecha_inicio_str} a {fecha_fin_str}")
        lapso_texto_display = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        report_title_parts.append("Todo el Historial")
    
    ventana.current_report_title = " | ".join(report_title_parts)

    columnas_reporte = ("Categoría", "Departamento", "Producto", "Cantidad Consumida", "Unidad Medida", "Lapso")
    tabla["columns"] = columnas_reporte
    tabla.heading("#0", text="") 

    tabla.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla.heading("Producto", text="Producto", anchor=tk.W)
    tabla.heading("Cantidad Consumida", text="Cantidad Consumida", anchor=tk.CENTER)
    tabla.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla.heading("Lapso", text="Lapso", anchor=tk.W)

    tabla.column("#0", width=0, stretch=tk.NO)
    tabla.column("Categoría", width=120, anchor=tk.W)
    tabla.column("Departamento", width=120, anchor=tk.W)
    tabla.column("Producto", width=180, anchor=tk.W)
    tabla.column("Cantidad Consumida", width=120, anchor=tk.CENTER)
    tabla.column("Unidad Medida", width=100, anchor=tk.W)
    tabla.column("Lapso", width=150, anchor=tk.W)


    mydb = conectar_mysql()
    if not mydb:
        ventana.current_report_title = "Reporte Combinado (Error de Conexión)"
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            cat.NombreCategoria,
            d.NombreDepartamento,
            p.Nombre AS NombreProducto,
            SUM(s.Cantidad) AS CantidadConsumida,
            p.UnidadMedida,
            MIN(s.FechaSalida) AS FechaInicioLapso,
            MAX(s.FechaSalida) AS FechaFinLapso
        FROM
            salidas s
        JOIN
            productos p ON s.ProductoID = p.ProductoID
        JOIN
            categorias cat ON p.CategoriaID = cat.CategoriaID
        JOIN
            departamentos d ON s.DepartamentoID = d.DepartamentoID
        WHERE
            cat.NombreCategoria = %s AND d.NombreDepartamento = %s
    """
    params = [categoria_filtro, departamento_filtro]

    
    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
    
    query += " GROUP BY cat.NombreCategoria, d.NombreDepartamento, p.Nombre, p.UnidadMedida"
    query += " ORDER BY cat.NombreCategoria, d.NombreDepartamento, p.Nombre"

    total_cantidad_consumida = 0

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", f"No se encontraron productos de la categoría '{categoria_filtro}' consumidos por el departamento '{departamento_filtro}' para los filtros seleccionados.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            ventana.current_report_title = "Reporte Combinado (Sin Resultados)" 
            return

        for row in reporte_data:
            categoria_nombre, departamento_nombre, producto_nombre, cantidad_consumida, unidad_medida, _, _ = row
            
           

            tabla.insert("", tk.END, values=(categoria_nombre, departamento_nombre, producto_nombre, cantidad_consumida, unidad_medida, lapso_texto_display))
            total_cantidad_consumida += cantidad_consumida

        tabla.insert("", tk.END, values=("", "", "TOTAL CONSUMIDO:", total_cantidad_consumida, "", ""), tags=('total_row',))
        tabla.tag_configure('total_row', background='#E0FFFF', font=('Segoe UI', 10, 'bold'))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte combinado de categoría y departamento: {err}", parent=ventana)
        ventana.current_report_title = "Reporte Combinado (Error)"
    finally:
        if cursor:
            cursor.close()
        if mydb and mydb.is_connected():
            mydb.close()


        
class PDFConMembrete(FPDF):
    def __init__(self, titulo_reporte="Reporte General", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.membrete_superior_altura = 20
        self.membrete_inferior_altura = 15
        self.margen_horizontal = 5
        self.espacio_entre_tabla_y_membrete = 15
        self.altura_encabezados = 10
        self.altura_fila = 7
        
        
        self.y_despues_membrete_superior = 5 + self.membrete_superior_altura + self.espacio_entre_tabla_y_membrete
        self.filas_por_pagina = self.calcular_filas_por_pagina()
        self.titulo_reporte = titulo_reporte 

    def calcular_filas_por_pagina(self):
       
        altura_util_contenido = self.h - (self.t_margin + self.membrete_superior_altura + self.espacio_entre_tabla_y_membrete + self.altura_encabezados + 5) - \
                                 (self.b_margin + self.membrete_inferior_altura + 10)
        return int(altura_util_contenido / self.altura_fila)

    def header(self):
        self.set_y(5)
        ancho_disponible = self.w - (self.l_margin + self.r_margin)
        try:
            self.image(
                resource_path("server/routes/imagenes/OFICIOS-CORPOANDES-1.png"),
                x=self.l_margin,
                y=self.get_y(),
                w=ancho_disponible,
                h=self.membrete_superior_altura,
            )
        except FileNotFoundError:
            self.set_font("Arial", 'B', 10)
            self.cell(0, 10, "¡Error: Membrete superior no encontrado!", ln=1, align='C')
        self.set_y(self.membrete_superior_altura + 10)
        self.print_titulo()

    def footer(self):
        self.set_y(-1 * (self.membrete_inferior_altura + 10))
        self.set_x(self.l_margin)
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
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", 0, 0, 'R')


    def print_titulo(self):
        self.set_font("Arial", 'B', 7)
        self.cell(0, 10, self.titulo_reporte, ln=1, align='C')
        self.set_font("Arial", size=10)

    def print_encabezados_tabla(self, headers, col_widths, x_start):
        self.set_x(x_start)
        self.set_font("Arial", 'B', 8)
        self.set_fill_color(200, 220, 255)
        self.set_text_color(0, 0, 0)
        for i, header in enumerate(headers):
           
            start_x_cell = self.get_x()
            start_y_cell = self.get_y()
            
            
            self.set_font("Arial", 'B', 8) 
            temp_height = self.font_size * 1.2 * (self.get_string_width(header) // col_widths[i] + 1)
            
           
            cell_height = max(self.altura_encabezados, temp_height)
            
            self.multi_cell(col_widths[i], cell_height / (temp_height / self.font_size * 1.2), 
                            txt=header, border=1, align='C', fill=True)
            
           
            self.set_xy(start_x_cell + col_widths[i], start_y_cell)
            
        self.ln()


def exportar_tabla_pdf(tabla_treeview, titulo_reporte="Reporte"):
    """
    Exporta los datos del Treeview a un PDF con membrete según el diseño y lo abre en el navegador.
    Ahora acepta un `titulo_reporte` para el PDF y maneja múltiples estructuras de tabla.
    """

    filename = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Archivos PDF", "*.pdf")],
        title=f"Guardar {titulo_reporte} como PDF",
    )
    if not filename:
        return

   
    pdf = PDFConMembrete(titulo_reporte=titulo_reporte, orientation="L", unit="mm", format="A4")
    pdf.set_margins(left=5, top=5, right=5)
    
    
    pdf.set_auto_page_break(auto=True, margin=pdf.membrete_inferior_altura + 10 + 5)
    pdf.set_font("Arial", size=7)
    pdf.add_page() 

    
    all_cols_from_treeview = tabla_treeview["columns"]
    display_cols = [] 
    display_headers = []

    
    columns_to_omit = ["EntradaID", "SalidaID", "EsperaID", "SolicitudID"] 
    for col_name in all_cols_from_treeview:
        if col_name not in columns_to_omit:
            display_cols.append(col_name)
            header_text = tabla_treeview.heading(col_name)["text"]
            
            
            if header_text == "Stock Actual":
                display_headers.append("Stock")
            elif header_text == "Cantidad Consumida":
                display_headers.append("Cantidad")
            elif header_text == "Depto. Solicitante": 
                display_headers.append("Departamento")
            else:
                display_headers.append(header_text)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_widths = []

   

    
    if tuple(display_headers) == ("Código", "Producto", "Cantidad", "Unidad Medida", "Fecha", "Destino"):
        col_widths = [
            available_width * 0.10,  
            available_width * 0.28, 
            available_width * 0.10,  
            available_width * 0.12,  
            available_width * 0.15,  
            available_width * 0.25,  
        ]
    
   
    elif tuple(display_headers) == ("ID Salida", "Producto", "Cantidad", "Departamento", "Fecha Salida"):
        col_widths = [
            available_width * 0.08, 
            available_width * 0.32, 
            available_width * 0.10,
            available_width * 0.25,
            available_width * 0.25, 
        ]
    
   
    elif tuple(display_headers) == ("Código", "Producto", "Cantidad", "Departamento"):
        col_widths = [
            available_width * 0.15,
            available_width * 0.40, 
            available_width * 0.15, 
            available_width * 0.30, 
        ]
    
   
    elif tuple(display_headers) == ("Departamento", "Producto", "Categoría", "Cantidad", "Lapso", "Stock"):
       
        lapso_width_fixed = 40
        
        remaining_width = available_width - lapso_width_fixed
        col_widths = [
            remaining_width * 0.20, 
            remaining_width * 0.30, 
            remaining_width * 0.15, 
            remaining_width * 0.10, 
            lapso_width_fixed,      
            remaining_width * 0.10,
        ]
    
    else: 
        if len(display_headers) > 0:
            
            data_rows = [tabla_treeview.item(child, "values") for child in tabla_treeview.get_children()]
            
           
            col_indices_to_display = [all_cols_from_treeview.index(col_name) for col_name in display_cols]

            
            min_widths = [pdf.get_string_width(h) + 6 for h in display_headers] 

            
            for row in data_rows:
                for i, col_idx in enumerate(col_indices_to_display):
                    if col_idx < len(row):
                        cell_value = str(row[col_idx])
                        min_widths[i] = max(min_widths[i], pdf.get_string_width(cell_value) + 6)
            
            total_min_width = sum(min_widths)
            
            if total_min_width > available_width:
                
                col_widths = [w * (available_width / total_min_width) for w in min_widths]
            else:
               
                remaining_space = available_width - total_min_width
                if remaining_space > 0:
                    col_widths = [w + (remaining_space / len(display_headers)) for w in min_widths]
                else:
                    col_widths = min_widths

        else:
            print("ADVERTENCIA: No hay columnas para mostrar en el PDF.")
            messagebox.showwarning("Advertencia", "No hay datos o columnas válidas para exportar.", parent=tabla_treeview)
            return

    total_width = sum(col_widths)
    x_start = (pdf.w - total_width) / 2
    row_height = pdf.altura_fila

    
    pdf.print_encabezados_tabla(display_headers, col_widths, x_start)

    current_y = pdf.get_y() 

    for i, child in enumerate(tabla_treeview.get_children()):
       
        row_values_full = tabla_treeview.item(child, "values")
        row_values_display = []
        for col_name in display_cols:
           
            value = tabla_treeview.set(child, col_name)
            row_values_display.append(str(value))

       
        max_cell_height = row_height
        pdf.set_font("Arial", size=7) 
        for j, value in enumerate(row_values_display):
            text_width = pdf.get_string_width(value)
            
            
            
            
            
            
            temp_pdf_for_height = FPDF(unit="mm")
            temp_pdf_for_height.set_font("Arial", size=7)
            
            if col_widths[j] > 0: 
                num_lines = int(pdf.get_string_width(value) / col_widths[j]) + 1
                max_cell_height = max(max_cell_height, num_lines * row_height)


       
        if current_y + max_cell_height > pdf.h - pdf.b_margin - pdf.membrete_inferior_altura - 5:
            pdf.add_page()
            current_y = pdf.get_y() + 5 
            pdf.print_encabezados_tabla(display_headers, col_widths, x_start)
            current_y = pdf.get_y()

        pdf.set_x(x_start)
        if i % 2 == 0:
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        pdf.set_font("Arial", size=7)

        
        for j, value in enumerate(row_values_display):
          
            start_x_cell = pdf.get_x()
            start_y_cell = pdf.get_y()

            
            pdf.multi_cell(col_widths[j], row_height, txt=value, border=1, align='L', fill=True)
            
            
            pdf.set_xy(start_x_cell + col_widths[j], start_y_cell)
        
        
        pdf.set_y(start_y_cell + max_cell_height)
        current_y = pdf.get_y() 

    pdf.output(filename, "F")
    messagebox.showinfo("Exportar a PDF", "Reporte exportado exitosamente a PDF.", parent=tabla_treeview)

    try:
        os.startfile(filename)
    except AttributeError: 
        try:
            os.system(f"open '{filename}'")
        except:
            os.system(f"xdg-open '{filename}'")  














    


                            # Función para configurar
def realizar_copia_seguridad(ventana_config):
    """
    Realiza una copia de seguridad de la base de datos MySQL usando mysqldump.
    """
    test_connection = conectar_mysql()
    if not test_connection:
        messagebox.showerror("Copia de Seguridad Fallida", "No se pudo conectar a la base de datos para realizar la copia de seguridad.", parent=ventana_config)
        return
    test_connection.close()

    _host = "192.168.0.5"
    _user = "almacen"
    _password = "Almacen*"
    _database = "corpoandes_base_datos_almacen" 

    try:
        ruta_guardar = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("Archivos SQL", "*.sql")],
            title="Guardar Copia de Seguridad de la Base de Datos"
        )
        
        if not ruta_guardar: 
            return

        fecha_hora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base_sugerido = f"{_database.replace(' ', '_')}_backup_{fecha_hora}.sql"

        ruta_directorio = os.path.dirname(ruta_guardar)
        nombre_archivo_elegido = os.path.basename(ruta_guardar)
        
        if not nombre_archivo_elegido.strip() or not nombre_archivo_elegido.lower().endswith(".sql"):
            ruta_completa = os.path.join(ruta_directorio, nombre_base_sugerido)
        else:
            ruta_completa = ruta_guardar 
            
        
        mysqldump_path = r"C:\xampp\mysql\bin\mysqldump.exe" 

        comando = [
            mysqldump_path,
            f"-h{_host}",
            f"-u{_user}",
            _database, 
            f"--result-file={ruta_completa}"
        ]

        if _password: 
            comando.insert(3, f"-p{_password}") 

        proceso = subprocess.run(comando, capture_output=True, text=True, shell=True)

        if proceso.returncode == 0:
            messagebox.showinfo("Copia de Seguridad", f"Copia de seguridad de la base de datos creada:\n{ruta_completa}", parent=ventana_config)
        else:
            messagebox.showerror("Error", f"Error al crear la copia de seguridad:\n{proceso.stderr}\nComando ejecutado: {' '.join(comando)}", parent=ventana_config)

    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró 'mysqldump'. Asegúrate de que MySQL está instalado y 'mysqldump' está en tu PATH o la ruta especificada es correcta.", parent=ventana_config)
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado al crear la copia de seguridad: {e}", parent=ventana_config)

def _ejecutar_restauracion_en_hilo(ruta_archivo, _host, _user, _password, _database, mysql_path, ventana_config):
    """
    Función que contiene la lógica de restauración de la DB y se ejecuta en un hilo separado.
    """
    try:
        comando = [
            mysql_path,
            f"-h{_host}",
            f"-u{_user}",
            
            _database
        ]

        if _password:
            comando.insert(3, f"-p{_password}")
        
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            proceso = subprocess.run(comando, stdin=f, capture_output=True, text=True, shell=True)

        if proceso.returncode == 0:
            ventana_config.after(0, lambda: messagebox.showinfo("Restauración Completada", f"Base de datos restaurada exitosamente desde:\n{ruta_archivo}", parent=ventana_config))
        else:
            ventana_config.after(0, lambda: messagebox.showerror("Error de Restauración", f"Error al restaurar la base de datos:\n{proceso.stderr}\nComando ejecutado: {' '.join(comando)}", parent=ventana_config))

    except FileNotFoundError:
        ventana_config.after(0, lambda: messagebox.showerror("Error", "No se encontró el cliente 'mysql'. Asegúrate de que MySQL está instalado (con XAMPP) y 'mysql.exe' está en la ruta especificada.", parent=ventana_config))
    except Exception as e:
        ventana_config.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error inesperado al restaurar la base de datos: {e}", parent=ventana_config))

def restaurar_copia_seguridad(ventana_config):
    """
    Inicia el proceso de restauración de la base de datos en un hilo separado
    para evitar que la interfaz de usuario se congele.
    """
    _host = "192.168.0.5"
    _user = "almacen"
    _password = "Almacen*"
    _database = "corpoandes_base_datos_almacen"
    
    
    mysql_path = r"C:\xampp\mysql\bin\mysql.exe" 

    try:
        ruta_archivo = filedialog.askopenfilename(
            defaultextension=".sql",
            filetypes=[("Archivos SQL", "*.sql")],
            title="Seleccionar Archivo de Copia de Seguridad SQL"
        )

        if not ruta_archivo:
            return

        if not messagebox.askyesno("Confirmar Restauración",
                                    "¡ADVERTENCIA! Esto BORRARÁ Y REEMPLAZARÁ TODOS LOS DATOS ACTUALES DE SU BASE DE DATOS.\n\n¿Está absolutamente seguro de que desea continuar?",
                                    parent=ventana_config):
            return

        restauracion_thread = threading.Thread(
            target=_ejecutar_restauracion_en_hilo,
            args=(ruta_archivo, _host, _user, _password, _database, mysql_path, ventana_config)
        )
        restauracion_thread.start()

        messagebox.showinfo("Iniciando Restauración", "La restauración de la base de datos ha comenzado en segundo plano. La interfaz de usuario no se congelará. Se le notificará cuando termine.", parent=ventana_config)

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al iniciar la restauración: {e}", parent=ventana_config)


def obtener_usuarios_db():
    """Obtiene todos los usuarios y su estado de administrador de la base de datos."""
    db = conectar_mysql()
    if db:
        cursor = db.cursor()
        try:
            
            cursor.execute("SELECT NombreUsuario, EsAdmin FROM usuarios")
            usuarios_data = cursor.fetchall()
            return usuarios_data 
        except mysql.connector.Error as err:
            messagebox.showerror("Error de DB", f"Error al obtener usuarios: {err}")
            return []
        finally:
            cursor.close()
            db.close()
    return []

def insertar_usuario_db(nombre, contrasena_hash, es_admin_int):
    """Inserta un nuevo usuario en la base de datos, asignando EsAdmin (0 o 1)."""
    db = conectar_mysql()
    if db:
        cursor = db.cursor()
        try:
            
            sql = "INSERT INTO usuarios (NombreUsuario, ContrasenaHash, EsAdmin) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nombre, contrasena_hash, es_admin_int))
            db.commit()
            return True
        except mysql.connector.Error as err:
            if err.errno == 1062: 
                messagebox.showerror("Error de DB", f"El usuario '{nombre}' ya existe.")
            else:
                messagebox.showerror("Error de DB", f"Error al crear usuario: {err}")
            return False
        finally:
            cursor.close()
            db.close()
    return False

def eliminar_usuario_db(nombre_usuario):
    """Elimina un usuario de la base de datos por su NombreUsuario."""
    db = conectar_mysql()
    if db:
        cursor = db.cursor()
        try:
            
            sql = "DELETE FROM usuarios WHERE NombreUsuario = %s"
            cursor.execute(sql, (nombre_usuario,))
            db.commit()
            return True
        except mysql.connector.Error as err:
            messagebox.showerror("Error de DB", f"Error al eliminar usuario: {err}")
            return False
        finally:
            cursor.close()
            db.close()
    return False

def actualizar_lista_usuarios():
    """Actualiza la lista de usuarios en el Listbox de la ventana de gestión."""
    global lista_usuarios_widget
    if lista_usuarios_widget: 
        lista_usuarios_widget.delete(0, tk.END)
        usuarios_data = obtener_usuarios_db()
        for nombre, es_admin_val in usuarios_data:
            rol_display = "Administrador" if es_admin_val == 1 else "Operador"
            lista_usuarios_widget.insert(tk.END, f"{nombre} ({rol_display})")

def gestionar_usuarios(ventana_config):
    """
    Gestiona la creación, eliminación y visualización de usuarios desde la base de datos.
    Requiere la clave maestra de administrador para acciones críticas.
    """
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
    
    es_admin_var = tk.BooleanVar(value=False) 
    check_es_admin = ttk.Checkbutton(frame_crear_usuario, text="Otorgar Privilegios de Administrador", variable=es_admin_var, style="TCheckbutton")
    check_es_admin.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    def verificar_codigo_administrador(codigo):
        
        return hashlib.sha256(codigo.encode()).hexdigest() == clave_admin

    def crear_usuario():
        nombre = entry_nombre.get().strip()
        contrasena = entry_contrasena.get().strip()
        es_admin_val = 1 if es_admin_var.get() else 0 
        
        if not nombre or not contrasena:
            messagebox.showerror("Error", "Ingrese nombre y contraseña para el nuevo usuario.", parent=ventana_usuarios)
            return

        if es_admin_val == 1:
            codigo_admin = simpledialog.askstring("Código de Administrador", "Ingrese el código de administrador para otorgar privilegios:", show='*', parent=ventana_usuarios)
            if not (codigo_admin and verificar_codigo_administrador(codigo_admin)):
                messagebox.showerror("Error", "Código de administrador incorrecto. No se puede crear un usuario administrador sin la clave maestra.", parent=ventana_usuarios)
                return
        
        contrasena_hash = hashlib.sha256(contrasena.encode()).hexdigest()
        if insertar_usuario_db(nombre, contrasena_hash, es_admin_val):
            actualizar_lista_usuarios() 
            rol_msg = "Administrador" if es_admin_val == 1 else "Operador"
            messagebox.showinfo("Usuario Creado", f"Usuario '{nombre}' con rol '{rol_msg}' creado.", parent=ventana_usuarios)
            entry_nombre.delete(0, tk.END)
            entry_contrasena.delete(0, tk.END)
            es_admin_var.set(False) 

    btn_crear_usuario = ttk.Button(ventana_usuarios, text="Crear Usuario", command=crear_usuario)
    btn_crear_usuario.pack(pady=5, padx=10, fill="x")

    def eliminar_usuario():
        seleccion = lista_usuarios_widget.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Seleccione un usuario para eliminar.", parent=ventana_usuarios)
            return

        usuario_display_text = lista_usuarios_widget.get(seleccion[0])
        usuario_a_eliminar = usuario_display_text.split(' ')[0] 
        
        if usuario_a_eliminar == "admin": 
            messagebox.showerror("Error", "No se puede eliminar el usuario administrador principal.", parent=ventana_usuarios)
            return

        codigo_admin = simpledialog.askstring("Código de Administrador", "Ingrese el código de administrador para eliminar:", show='*', parent=ventana_usuarios)
        if codigo_admin and verificar_codigo_administrador(codigo_admin):
            if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar el usuario '{usuario_a_eliminar}'?", parent=ventana_usuarios):
                if eliminar_usuario_db(usuario_a_eliminar):
                    actualizar_lista_usuarios()
                    messagebox.showinfo("Usuario Eliminado", f"Usuario '{usuario_a_eliminar}' eliminado.", parent=ventana_usuarios)
        else:
            messagebox.showerror("Error", "Código de administrador incorrecto o cancelación.", parent=ventana_usuarios)

    btn_eliminar_usuario = ttk.Button(ventana_usuarios, text="Eliminar Usuario", command=eliminar_usuario)
    btn_eliminar_usuario.pack(pady=5, padx=10, fill="x")

    
    ventana_usuarios.transient(ventana_config) 
    ventana_usuarios.grab_set()
    ventana_usuarios.wait_window(ventana_usuarios)

def configuracion():
    """Abre una ventana de configuración para ajustar notificaciones y tema de color."""
    ventana_config = tk.Toplevel(ventana)
    ventana_config.title("Configuración")
    ventana_config.configure(bg="#A9A9A9") 

    style = ttk.Style(ventana_config)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("TCombobox", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TCheckbutton", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("TFrame", background="#A9A9A9") 


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

   
    btn_copia_seguridad = ttk.Button(backup_restore_frame, text="Copia de Seguridad", command=lambda: realizar_copia_seguridad(ventana_config))
    btn_copia_seguridad.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

    btn_restaurar = ttk.Button(backup_restore_frame, text="Restaurar", command=lambda: restaurar_copia_seguridad(ventana_config))
    btn_restaurar.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

    
    btn_gestion_usuarios = ttk.Button(main_frame, text="Gestión de Usuarios", command=lambda: gestionar_usuarios(ventana_config))
    btn_gestion_usuarios.grid(row=2, column=0, sticky="ew", padx=10, pady=10) 

    def guardar_configuracion():
        
        ventana_config.destroy()

   
    btn_aceptar = ttk.Button(main_frame, text="Aceptar", command=guardar_configuracion)
    btn_aceptar.grid(row=3, column=0, sticky="ew", padx=10, pady=10) # row=3

    
    ventana_config.transient(ventana)
    ventana_config.grab_set()
    ventana_config.wait_window(ventana_config)

def mostrar_notificacion_bajo_stock():
    """Muestra una notificación de advertencia general sobre bajo stock."""
    global ventana  
    umbral_stock_minimo = 1  
    productos_bajo_stock = []
    for producto, datos in inventario.items():
        if datos["stock"] < umbral_stock_minimo:
            productos_bajo_stock.append(producto)

    if productos_bajo_stock:
        mensaje = "¡Advertencia! Hay productos con bajo stock"

      
        ventana_notificacion = tk.Toplevel(ventana)
        ventana_notificacion.title("Advertencia: Bajo Stock")
        ventana_notificacion.geometry("+{}+0".format(ventana.winfo_screenwidth() - 300))  
        ventana_notificacion.overrideredirect(True) 
        ventana_notificacion.configure(bg="yellow")

        
        label_mensaje = ttk.Label(ventana_notificacion, text=mensaje, background="yellow", foreground="black", padding=10, font=("Segoe UI", 10, "bold"))
        label_mensaje.pack()

       
        boton_cerrar = ttk.Button(ventana_notificacion, text="Cerrar", command=ventana_notificacion.destroy)
        boton_cerrar.pack(pady=5)

       
        ventana_notificacion.after(5000, ventana_notificacion.destroy)
def mostrar_tabla():
    global tabla_inventario_principal, inventario

    if tabla_inventario_principal is None or not tabla_inventario_principal.winfo_exists():
        
        return

   
    for item in tabla_inventario_principal.get_children():
        tabla_inventario_principal.delete(item)

    
    for codigo, datos in inventario.items():
        tabla_inventario_principal.insert("", tk.END, values=(
            datos["codigo"],
            datos["nombre"],
            datos["cantidad"],
            datos["departamento"],
            datos["fecha_entrada"].strftime("%Y-%m-%d") if datos["fecha_entrada"] else "",
            datos["fecha_salida"].strftime("%Y-%m-%d") if datos["fecha_salida"] else "",
            datos["unidad_medida"]
        ))
    print("DEBUG: Tabla de inventario principal actualizada desde mostrar_tabla().")

def importar_datos():
    """Importa datos del inventario y movimientos desde la base de datos MySQL."""
    global inventario, entradas_departamentos
    inventario = {}
    entradas_departamentos = []
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor(dictionary=True)
        try:
           
            query_productos = """
                SELECT
                    p.ProductoID,
                    p.Codigo,
                    p.Nombre AS ProductoNombre,
                    p.Stock AS Cantidad,
                    p.FechaEntrada,
                    p.FechaSalida,
                    p.UnidadMedida,
                    p.CategoriaID,
                    d.NombreDepartamento AS Departamento
                FROM
                    productos p
                LEFT JOIN
                    departamentos d ON p.DepartamentoID = d.DepartamentoID
                ORDER BY p.Codigo;
            """
            cursor.execute(query_productos)
            productos_db = cursor.fetchall()
            for prod in productos_db:
                codigo = prod["Codigo"]
                inventario[codigo] = {
                    "codigo": prod["Codigo"],
                    "nombre": prod["ProductoNombre"],
                    "cantidad": prod["Cantidad"],
                    "descripcion": "",
                    "fecha_entrada": prod["FechaEntrada"],
                    "fecha_salida": prod["FechaSalida"],
                    "departamento": prod["Departamento"],
                    "ubicacion": "",
                    "responsable": "N/A",
                    "unidad_medida": prod["UnidadMedida"],
                    "categoria_id": prod["CategoriaID"]
                }

            
            query_entradas = """
                SELECT
                    e.FechaEntrada AS Fecha,
                    p.Nombre AS Producto,
                    e.Cantidad,
                    e.Destino AS Departamento,
                    'Entrada' AS TipoMovimiento
                FROM
                    entradas e
                JOIN
                    productos p ON e.ProductoID = p.ProductoID
                ORDER BY e.FechaEntrada DESC
                LIMIT 50;
            """
            cursor.execute(query_entradas)
            movimientos_entradas = cursor.fetchall()

           
            query_salidas = """
                SELECT
                    s.FechaSalida AS Fecha,
                    p.Nombre AS Producto,
                    s.Cantidad,
                    d.NombreDepartamento AS Departamento,
                    s.NumeroRequisicion,
                    'Salida' AS TipoMovimiento
                FROM
                    salidas s
                JOIN
                    productos p ON s.ProductoID = p.ProductoID
                LEFT JOIN
                    departamentos d ON s.DepartamentoID = d.DepartamentoID
                ORDER BY s.FechaSalida DESC
                LIMIT 50;
            """
            cursor.execute(query_salidas)
            movimientos_salidas = cursor.fetchall()

            todos_movimientos = movimientos_entradas + movimientos_salidas
            todos_movimientos.sort(key=lambda x: x['Fecha'] if x['Fecha'] else datetime.datetime.min, reverse=True)

            for movimiento in todos_movimientos:
                fecha_str = movimiento["Fecha"].strftime("%Y-%m-%d %H:%M:%S") if movimiento["Fecha"] else "N/A"
                producto = movimiento["Producto"]
                cantidad = movimiento["Cantidad"]
                departamento = movimiento.get("Departamento", "N/A")
                tipo = movimiento["TipoMovimiento"]
                if tipo == 'Entrada':
                    responsable = "Sistema"
                    entradas_departamentos.append(f"[{fecha_str}] {tipo} de {cantidad}x '{producto}' en {departamento} por {responsable}")
                elif tipo == 'Salida':
                    requisicion = movimiento.get("NumeroRequisicion", "N/A")
                    entradas_departamentos.append(f"[{fecha_str}] {tipo} de {cantidad}x '{producto}' a {departamento} (Req: {requisicion})")

            messagebox.showinfo("Importar Datos", f"Se importaron {len(inventario)} productos y {len(entradas_departamentos)} registros de movimientos desde MySQL.")

            
            mostrar_tabla()

        except mysql.connector.Error as err:
            messagebox.showerror("Error de Base de Datos", f"Error al importar datos desde MySQL: {err}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado al importar los datos: {e}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()
    else:
        messagebox.showerror("Error de Conexión", "No se pudo establecer conexión con la base de datos.")



def get_create_table_statement(cursor, table_name):
    try:
        cursor.execute(f"SHOW CREATE TABLE `{table_name}`;")
        result = cursor.fetchone()
        if result:
            return result['Create Table']
        return None
    except Exception as e:
        print(f"Error al obtener CREATE TABLE para {table_name}: {e}")
        return None

def get_insert_statements(cursor, table_name):
    inserts = []
    try:
        
        cursor.execute(f"SELECT * FROM `{table_name}`;")
        
        
        columns = [col[0] for col in cursor.description]
        
        rows = cursor.fetchall()

        for row_dict in rows: 
            values = []
            for col_name in columns:
                value = row_dict[col_name] 
                if value is None:
                    values.append("NULL")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, datetime.date):
                    values.append(f"'{value.strftime('%Y-%m-%d')}'")
                elif isinstance(value, datetime.datetime):
                    values.append(f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'")
                else:
                   
                    escaped_value = str(value).replace("'", "''")
                    values.append(f"'{escaped_value}'")
            
            
            columns_str = '`, `'.join(columns)
            values_str = ', '.join(values)
            inserts.append(f"INSERT INTO `{table_name}` (`{columns_str}`) VALUES ({values_str});")
            
        return inserts
    except Exception as e:
        print(f"Error al obtener INSERT statements para {table_name}: {e}")
        return []
    
def exportar_datos():
    """Exporta la estructura y los datos de TODAS las tablas de la base de datos a un archivo .sql."""
    
    all_tables = [
        "productos",
        "entradas",
        "salidas",
        "salidas_espera",
        "usuarios",
        "departamentos"
    ]

   
    output_file = filedialog.asksaveasfilename(
        defaultextension=".sql",
        filetypes=[("Archivos SQL", "*.sql")],
        title="Guardar Base de Datos como SQL"
    )

    if not output_file:
        messagebox.showinfo("Exportar Datos", "Exportación cancelada.")
        return

    mydb = conectar_mysql()
    if not mydb:
        return

    cursor = mydb.cursor(dictionary=True)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- SQL Export generated by Inventory App on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n") 

            for table_name in all_tables:
                f.write(f"-- Dumping table `{table_name}`\n")
                f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")

                # Incluir estructura (CREATE TABLE)
                create_statement = get_create_table_statement(cursor, table_name)
                if create_statement:
                    f.write(create_statement + ";\n")
                else:
                    messagebox.showwarning("Advertencia de Exportación", f"No se pudo obtener la estructura para la tabla: {table_name}. Se omitirá.")
                    continue 

                
                inserts = get_insert_statements(cursor, table_name)
                if inserts:
                    for insert_sql in inserts:
                        f.write(insert_sql + "\n")
                else:
                    f.write(f"-- No data to export for table `{table_name}`\n")
                f.write("\n") 

            f.write("SET FOREIGN_KEY_CHECKS = 1;\n") 

        messagebox.showinfo("Exportar Datos", f"Toda la base de datos exportada exitosamente a:\n{output_file}")

    except mysql.connector.Error as err:
        messagebox.showerror("Error de Base de Datos", f"Error al exportar datos a SQL: {err}")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error inesperado al exportar los datos: {e}")
    finally:
        if mydb and mydb.is_connected():
            cursor.close()
            mydb.close()

def guardar_como():
    exportar_datos()














                                    #Funcion de Mostrar el Menu


def mostrar_menu():
    """Muestra el menú principal con la estructura original, colores oscuros y privilegios."""
    global ventana, current_user_role_is_admin 

    ventana = tk.Tk()
    ventana.title("Menú Principal - " + ("Administrador" if current_user_role_is_admin else "Operador"))
    ventana.configure(bg="#263238")
    ventana.geometry("1000x700")
    ventana.resizable(True, True)

    menu_principal = tk.Menu(ventana)
    ventana.config(menu=menu_principal)

    menu_archivo = tk.Menu(menu_principal, tearoff=0)
    menu_principal.add_cascade(label="Archivo", menu=menu_archivo)
    
    menu_archivo.add_command(label="Guardar como...", command=guardar_como)
    
    if current_user_role_is_admin:
        menu_archivo.add_command(label="Importar", command=importar_datos)
        menu_archivo.add_command(label="Exportar", command=exportar_datos)
    else:
        menu_archivo.add_command(label="Importar", state=tk.DISABLED)
        menu_archivo.add_command(label="Exportar", state=tk.DISABLED)
        
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
    
    
    if current_user_role_is_admin:
        menu_configuracion.add_command(label="Ajustes generales", command=configuracion)
        menu_configuracion.add_command(label="Gestionar Usuarios", command=lambda: gestionar_usuarios(ventana))
    else:
        menu_configuracion.add_command(label="Ajustes generales", state=tk.DISABLED)
        menu_configuracion.add_command(label="Gestionar Usuarios", state=tk.DISABLED)

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

    try:
        ventana.logo_agregar_img = tk.PhotoImage(file=resource_path("server/routes/imagenes/agregar-producto.png")).subsample(3, 3)
        ventana.logo_salida_img = tk.PhotoImage(file=resource_path("server/routes/imagenes/espera.png")).subsample(3, 3)
        ventana.logo_mostrar_img = tk.PhotoImage(file=resource_path("server/routes/imagenes/inventario.png")).subsample(3, 3)
        ventana.logo_consumo_img = tk.PhotoImage(file=resource_path("server/routes/imagenes/consumo.png")).subsample(3, 3) 
    except tk.TclError as e:
        print(f"Error AL CARGAR imágenes de botones: {e}")
        
        ventana.logo_agregar_img = None
        ventana.logo_salida_img = None
        ventana.logo_mostrar_img = None
        ventana.logo_consumo_img = None

    frame_botones_menu = tk.Frame(ventana, bg="#263238")
    frame_botones_menu.pack(expand=True, fill="both", padx=20, pady=20)
    frame_botones_menu.grid_columnconfigure(0, weight=1)
    frame_botones_menu.grid_columnconfigure(1, weight=1)

    
    boton_mostrar = ttk.Button(frame_botones_menu, text="Mostrar inventario", image=ventana.logo_mostrar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=lambda: mostrar_inventario(ventana))
    boton_mostrar.image = ventana.logo_mostrar_img
    
    boton_consumo = ttk.Button(frame_botones_menu, text="Calcular consumo por departamento", image=ventana.logo_consumo_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=calcular_consumo_departamento)
    boton_consumo.image = ventana.logo_consumo_img

    if current_user_role_is_admin:
        
        boton_agregar = ttk.Button(frame_botones_menu, text="Agregar producto", image=ventana.logo_agregar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=agregar_producto)
        boton_agregar.image = ventana.logo_agregar_img
        boton_agregar.grid(row=0, column=0, padx=10, pady=10, sticky="ew") 

        boton_salida = ttk.Button(frame_botones_menu, text="Realizar salida en espera", image=ventana.logo_salida_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=realizar_salida)
        boton_salida.image = ventana.logo_salida_img
        boton_salida.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

       
        boton_mostrar.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        boton_consumo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
    else:
        
        boton_agregar = ttk.Button(frame_botones_menu, text="Agregar producto", image=ventana.logo_agregar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=agregar_producto)
        boton_agregar.image = ventana.logo_agregar_img
        boton_agregar.grid(row=0, column=0, padx=10, pady=10, sticky="ew") 

        boton_salida = ttk.Button(frame_botones_menu, text="Realizar salida en espera", image=ventana.logo_salida_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=realizar_salida)
        boton_salida.image = ventana.logo_salida_img
        boton_salida.grid(row=0, column=1, padx=10, pady=10, sticky="ew") 

       
        boton_mostrar.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        boton_consumo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")


    try:
        ventana.logo_app_img = tk.PhotoImage(file=resource_path("server/routes/imagenes/NEVA.png")).subsample(4, 4) 
        logo_app_label = tk.Label(ventana, image=ventana.logo_app_img, bd=0, highlightthickness=0, bg="#263238") 
        logo_app_label.image = ventana.logo_app_img 
        logo_app_label.place(relx=1.0, rely=1.0, anchor=tk.SE, x=-10, y=-10) 
    except tk.TclError as e:
        print(f"Error al cargar el logo de la aplicación (NEVA.png): {e}")

    mostrar_notificacion_bajo_stock()

    ventana.mainloop()

# Ejecución de la aplicación 
cargar_datos()


iniciar_sesion()
