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
                INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, FechaEntrada, Destino)
                VALUES (%s, %s, %s, %s, %s)
            """
            val_entrada = (producto_id, codigo_producto, entrada_cantidad, fecha_entrada, destino_entrada_nombre)
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

    categoria_var.set(categorias_list[0] if categorias_list else "")
    unidad_medida_var.set(unidades_list[0] if unidades_list else "")


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

    def obtener_productos_con_codigo():
        """Obtiene la lista de productos (Nombre (Código)) desde la base de datos MySQL."""
        productos_con_codigo = []
        mydb = conectar_mysql()
        if mydb:
            cursor = mydb.cursor()
            query = "SELECT Nombre, Codigo, ProductoID FROM productos"
            try:
                cursor.execute(query)
                productos_mysql = cursor.fetchall()
                for nombre, codigo, producto_id in productos_mysql:
                    productos_con_codigo.append(f"{nombre} ({codigo})")
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al obtener productos: {err}")
            finally:
                if mydb.is_connected():
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
        
        seleccion_producto = combo_producto.get()
        
        try:
            cantidad = float(entry_cantidad.get())
            if cantidad <= 0:
                messagebox.showerror("Error", "La cantidad debe ser un número positivo.")
                return
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero válido.")
            return

        producto_nombre = obtener_nombre_desde_seleccion(seleccion_producto)
        codigo_producto = obtener_codigo_desde_seleccion(seleccion_producto)

        if not codigo_producto:
            messagebox.showerror("Error", "Por favor, seleccione un producto válido de la lista.")
            return
            
        mydb = conectar_mysql()
        if not mydb:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
            return

        cursor = mydb.cursor()
        
        try:
           
            query_producto_id = "SELECT ProductoID FROM productos WHERE Codigo = %s"
            cursor.execute(query_producto_id, (codigo_producto,))
            resultado_id = cursor.fetchone()

            if not resultado_id:
                messagebox.showerror("Error", f"No se encontró el producto con código: {codigo_producto}")
                return
            
            producto_id = resultado_id[0]

           
            departamento_id = departamentos_map_global.get(departamento_nombre_seleccionado)
            
            if departamento_id is None:
                messagebox.showerror("Error", f"Departamento '{departamento_nombre_seleccionado}' no válido.")
                return

          
            sql_insert_salida = """
                INSERT INTO salidas_espera (ProductoID, CodigoProducto, Cantidad, DepartamentoID, FechaSolicitud, Estado)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            fecha_actual = datetime.datetime.now()
            val_salida = (producto_id, codigo_producto, cantidad, departamento_id, fecha_actual, "Pendiente")
            
            cursor.execute(sql_insert_salida, val_salida)
            mydb.commit()
            messagebox.showinfo("Salida en Espera", f"{cantidad} unidades de '{producto_nombre}' (código: {codigo_producto}) solicitadas para {departamento_nombre_seleccionado}. Agregado a la lista de espera.")
            entry_cantidad.delete(0, tk.END)
            
         

        except mysql.connector.Error as err:
            mydb.rollback()
            messagebox.showerror("Error al agregar salida en espera", f"Error: {err}")
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

    
    productos_con_codigo = obtener_productos_con_codigo()

    ttk.Label(ventana_salida_espera, text="Nombre del producto (Código):", style="CustomLabel.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=10)
    combo_producto = ttk.Combobox(ventana_salida_espera, values=productos_con_codigo, style="TCombobox")
    combo_producto.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    
    def filtrar_productos(event):
        valor_escrito = combo_producto.get().lower()
        productos_filtrados = [
            pc
            for pc in productos_con_codigo
            if valor_escrito in pc.lower()
        ]
        combo_producto["values"] = productos_filtrados

    
    combo_producto.bind("<KeyRelease>", filtrar_productos)

    ttk.Label(ventana_salida_espera, text="Cantidad de salida:", style="CustomLabel.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=10)
    entry_cantidad = ttk.Entry(ventana_salida_espera, style="CustomEntry.TEntry")
    entry_cantidad.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    
    ttk.Label(ventana_salida_espera, text="Departamento:", style="CustomLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=10)
    
    
    nombres_departamentos_para_combobox, departamentos_map_global = obtener_departamentos_para_combobox() # Asigna a una variable global o pásala
    
    departamento_var = tk.StringVar(ventana_salida_espera)
    if nombres_departamentos_para_combobox:
        departamento_var.set(nombres_departamentos_para_combobox[0])  
    else:
        departamento_var.set("No hay departamentos") 
        messagebox.showwarning("Advertencia", "No se encontraron departamentos en la base de datos.")

    ttk.Combobox(ventana_salida_espera, textvariable=departamento_var, values=nombres_departamentos_para_combobox, style="TCombobox", state="readonly").grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    ttk.Button(ventana_salida_espera, text="Agregar a Salida en Espera", command=salida_espera, style="CustomButton.TButton").grid(row=3, column=0, columnspan=2, pady=15, padx=10, sticky="ew")

    ventana_salida_espera.grid_columnconfigure(1, weight=1)


   
         #MUESTRA TODO EL INVENTARIO DONDE PODEMOS REALIZAR ENTRADAS,SALIDAS,ELIMINAR ETC

def mostrar_inventario(ventana):
    """Muestra el inventario con menú desplegable de categorías y búsqueda por nombre o código dentro de la categoría."""

    ventana_inventario = tk.Toplevel(ventana)
    ventana_inventario.title("Inventario")
    ventana_inventario.geometry("1200x600")
    ventana_inventario.configure(bg="#A9A9A9")

   
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
    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        cursor.execute("SELECT NombreCategoria FROM categorias ORDER BY NombreCategoria")
        categorias_db = [row[0] for row in cursor.fetchall()]
        categorias_mostrar.extend(categorias_db)
        cursor.close()
        mydb.close()
    categoria_seleccionada_mostrar = tk.StringVar(frame_menu)
    categoria_seleccionada_mostrar.set(categorias_mostrar[0])

    menu_categorias_mostrar = ttk.Combobox(frame_menu, textvariable=categoria_seleccionada_mostrar, values=categorias_mostrar, style="TCombobox")
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
        if mydb:
            cursor = mydb.cursor()
            query = """
                SELECT
                    p.Codigo,
                    c.NombreCategoria,
                    p.Nombre,
                    'Almacén principal' AS DestinoEntrada,
                    d.NombreDepartamento AS DestinoSalida,  -- Obtener el nombre del departamento de salida de la tabla departamentos usando p.DepartamentoID
                    (SELECT e.Cantidad FROM entradas e WHERE e.CodigoProducto = p.Codigo ORDER BY e.FechaEntrada DESC LIMIT 1) AS CantidadEntrada,
                    (SELECT s.Cantidad FROM salidas s WHERE s.CodigoProducto = p.Codigo ORDER BY s.FechaSalida DESC LIMIT 1) AS CantidadSalida,
                    p.Stock,
                    p.UnidadMedida,
                    p.FechaEntrada,
                    (SELECT s.FechaSalida FROM salidas s WHERE s.CodigoProducto = p.Codigo ORDER BY s.FechaSalida DESC LIMIT 1) AS FechaSalida
                FROM productos p
                LEFT JOIN categorias c ON p.CategoriaID = c.CategoriaID
                LEFT JOIN departamentos d ON p.DepartamentoID = d.DepartamentoID  -- Join para obtener el nombre del departamento de salida
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

            try:
                cursor.execute(query, params)
                productos_filtrados_db = cursor.fetchall()
                for codigo, nombre_categoria, nombre_producto, destino_entrada, destino_salida, cantidad_entrada, cantidad_salida, stock, unidad_medida, fecha_entrada, fecha_salida in productos_filtrados_db:
                    tabla_productos.insert("", tk.END, values=(
                        codigo,
                        nombre_categoria if nombre_categoria else "",
                        nombre_producto,
                        destino_entrada if destino_entrada else "",
                        destino_salida if destino_salida else "",
                        cantidad_entrada if cantidad_entrada is not None else "",
                        cantidad_salida if cantidad_salida is not None else "",
                        stock,
                        unidad_medida,
                        fecha_entrada,
                        fecha_salida if fecha_salida else ""
                    ))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al mostrar el inventario: {err}")
            finally:
                cursor.close()
                mydb.close()
        mostrar_totales(categoria_nombre)

    def mostrar_totales(categoria_nombre):
        mydb = conectar_mysql()
        if mydb:
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
                messagebox.showerror("Error", f"Error al obtener los totales: {err}")
            finally:
                cursor.close()
                mydb.close()

    
    def mostrar_inventario_filtrado(event=None):
        categoria_nombre = categoria_seleccionada_mostrar.get()
        termino_busqueda = entry_busqueda.get().lower()
        mostrar_tabla(categoria_nombre, termino_busqueda)

    
    menu_categorias_mostrar.bind("<<ComboboxSelected>>", mostrar_inventario_filtrado)
    entry_busqueda.bind("<KeyRelease>", mostrar_inventario_filtrado)

    def realizar_entrada_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una entrada de productos desde el menú contextual usando el código del producto (actualizado para MySQL)."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.")
            return

        def confirmar_entrada():
            cantidad_str = entry_cantidad.get()
            fecha = datetime.datetime.now()
            if not cantidad_str.isdigit():
                messagebox.showerror("Error", "La cantidad debe ser un número.")
                return
            cantidad = float(cantidad_str)

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                return

            cursor = mydb.cursor()

            try:
                
                
                sql_actualizar_stock = "UPDATE productos SET Stock = Stock + %s, FechaEntrada = %s WHERE Codigo = %s "
                val_actualizar_stock = (cantidad, fecha, codigo_producto_seleccionado)
                cursor.execute(sql_actualizar_stock, val_actualizar_stock)

                
                sql_insertar_entrada = "INSERT INTO entradas (ProductoID, CodigoProducto, Cantidad, FechaEntrada, Destino) SELECT ProductoID, Codigo, %s, %s, 'Almacén principal' FROM productos WHERE Codigo = %s"
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


    def agregar_departamento_a_db(nombre_departamento):
        """Agrega un departamento a la base de datos si no existe."""
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
                    print(f"Departamento '{nombre_departamento}' agregado a la base de datos.")
                else:
                    print(f"Departamento '{nombre_departamento}' ya existe en la base de datos.")
            except mysql.connector.Error as err:
                mydb.rollback()
                messagebox.showerror("Error", f"Error al agregar departamento '{nombre_departamento}': {err}")
            finally:
                if mydb and mydb.is_connected():
                    cursor.close()
                    mydb.close()

    def realizar_salida_contextual(codigo_producto_seleccionado, nombre_producto):
        """Realiza una salida de productos desde el menú contextual usando el código del producto (actualizado para MySQL)."""
        if not codigo_producto_seleccionado:
            messagebox.showerror("Error", "No se proporcionó el código del producto.")
            return

        def confirmar_salida():
            departamento_nombre = departamento_var.get()
            cantidad_str = entry_cantidad_salida.get()
            fecha = datetime.datetime.now()
            numero_requisicion = entry_numero_requisicion.get()

            if not cantidad_str.isdigit():
                messagebox.showerror("Error", "Cantidad inválida. Ingrese un número entero.")
                return
            cantidad = float(cantidad_str)

            if not departamento_nombre or not fecha or not numero_requisicion:
                messagebox.showerror("Error", "Por favor, complete todos los campos.")
                return

            mydb = conectar_mysql()
            if not mydb:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
                return

            cursor = mydb.cursor()

            try:
                
                query_departamento_salida_id = "SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s"
                cursor.execute(query_departamento_salida_id, (departamento_nombre,))
                resultado_departamento_salida = cursor.fetchone()
                if not resultado_departamento_salida:
                    messagebox.showerror("Error", f"El departamento '{departamento_nombre}' no existe.")
                    mydb.close()
                    return
                departamento_salida_id = resultado_departamento_salida[0]

                
                cursor.execute("SELECT Stock FROM productos WHERE Codigo = %s", (codigo_producto_seleccionado,))
                resultado_stock = cursor.fetchone()
                if resultado_stock and resultado_stock[0] >= cantidad:
                   
                    sql_actualizar_stock_departamento = "UPDATE productos SET Stock = Stock - %s, FechaSalida = %s, DepartamentoID = %s WHERE Codigo = %s"
                    val_actualizar_stock_departamento = (cantidad, fecha, departamento_salida_id, codigo_producto_seleccionado)
                    cursor.execute(sql_actualizar_stock_departamento, val_actualizar_stock_departamento)

                    
                    sql_insertar_salida = "INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, FechaSalida, DepartamentoID, NumeroRequisicion) SELECT ProductoID, Codigo, %s, %s, %s, %s FROM productos WHERE Codigo = %s"
                    val_insertar_salida = (cantidad, fecha, departamento_salida_id, numero_requisicion, codigo_producto_seleccionado)
                    cursor.execute(sql_insertar_salida, val_insertar_salida)

                    mydb.commit()
                    mostrar_tabla(categoria_seleccionada_mostrar.get())
                    messagebox.showinfo("Salida Realizada", f"{cantidad} unidades de {nombre_producto} (Código: {codigo_producto_seleccionado}) salieron para {departamento_nombre}.")
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

        
        for departamento in departamentos:
            agregar_departamento_a_db(departamento)

        departamento_var = tk.StringVar(ventana_salida)
        departamento_var.set(departamentos[0] if departamentos else "")
        combo_departamento = ttk.Combobox(ventana_salida, textvariable=departamento_var, values=departamentos, style="TCombobox")
        combo_departamento.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Cantidad:", style="CustomLabel.TLabel").grid(row=1, column=0, padx=10, pady=10)
        entry_cantidad_salida = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_cantidad_salida.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(ventana_salida, text="Fecha:", style="CustomLabel.TLabel").grid(row=2, column=0, padx=10, pady=10)
        entry_fecha_salida = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_fecha_salida.grid(row=2, column=1, padx=10, pady=10)
        ttk.Button(ventana_salida, text="Calendario", command=lambda: abrir_calendario(ventana_salida, entry_fecha_salida), style="CustomButton.TButton").grid(row=2, column=2, padx=10, pady=10)

        ttk.Label(ventana_salida, text="Número de Requisición:", style="CustomLabel.TLabel").grid(row=3, column=0, padx=10, pady=10)
        entry_numero_requisicion = ttk.Entry(ventana_salida, style="CustomEntry.TEntry")
        entry_numero_requisicion.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ttk.Button(ventana_salida, text="Confirmar Salida", command=confirmar_salida, style="CustomButton.TButton").grid(row=4, column=0, columnspan=3, pady=15, padx=10, sticky="ew")
        ventana_salida.grid_columnconfigure(1, weight=1)

    
     
    def menu_contextual(event):
        
        if current_user_role_is_admin:
            item = tabla_productos.identify_row(event.y)
            if item:
               
                values = tabla_productos.item(item, "values")
                codigo_producto = values[0]
                nombre_producto = values[2] 
                
                menu = tk.Menu(ventana_inventario, tearoff=0)
                menu.add_command(label="Realizar Entrada", command=lambda c=codigo_producto, n=nombre_producto: realizar_entrada_contextual(c, n))
                menu.add_command(label="Realizar Salida", command=lambda c=codigo_producto, n=nombre_producto: realizar_salida_contextual(c, n))
               
                menu.post(event.x_root, event.y_root)
        else:
           
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones.")

   
    tabla_productos.bind("<Button-3>", menu_contextual)
    
    mostrar_tabla() 

    ventana_inventario.grid_columnconfigure(0, weight=1)
    ventana_inventario.grid_rowconfigure(1, weight=1)

    

                         #MUESTRA EL CONSUMO QUE A TENIDO CADA DEPARTAMENTO
def calcular_consumo_departamento():
    """Calcula el consumo semanal y mensual por departamento y en general desde la base de datos."""
   
    
    consumo_semanal = calcular_consumo_periodo(datetime.timedelta(weeks=1))
    consumo_mensual = calcular_consumo_periodo(datetime.timedelta(days=30))

    
    mostrar_consumo_periodos(consumo_semanal, consumo_mensual)

def mostrar_consumo_periodos(consumo_semanal, consumo_mensual):
    """Muestra el consumo para los dos períodos en una tabla (Semanal y Mensual)."""
    ventana_consumo = tk.Toplevel(ventana)
    ventana_consumo.title("Consumo por Período")
    ventana_consumo.configure(bg="#A9A9A9")

    style = ttk.Style(ventana_consumo)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])

    
    tabla_consumo = ttk.Treeview(ventana_consumo, columns=("Departamento", "Código", "Producto", "Semanal", "Mensual", "Unidad Medida", "Porcentaje"), show="headings", style="Grid.Treeview")
    tabla_consumo.pack(fill=tk.BOTH, expand=True)

   
    tabla_consumo.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla_consumo.heading("Código", text="Código", anchor=tk.W)
    tabla_consumo.heading("Producto", text="Producto", anchor=tk.W)
    tabla_consumo.heading("Semanal", text="Semanal", anchor=tk.W) 
    tabla_consumo.heading("Mensual", text="Mensual", anchor=tk.W)
    tabla_consumo.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla_consumo.heading("Porcentaje", text="Porcentaje", anchor=tk.W)

   
    tabla_consumo.column("Departamento", width=150)
    tabla_consumo.column("Código", width=100)
    tabla_consumo.column("Producto", width=150)
    tabla_consumo.column("Semanal", width=80) 
    tabla_consumo.column("Mensual", width=80) 
    tabla_consumo.column("Unidad Medida", width=100)
    tabla_consumo.column("Porcentaje", width=100)

    datos_consumo_guardar = [] 

    departamentos = set()
    codigos_consumidos = set()
    consumo_total_general = 0

   
    for periodo_data, total_periodo in [consumo_semanal, consumo_mensual]:
        if periodo_data: 
            departamentos.update(periodo_data.keys())
            for productos_departamento in periodo_data.values():
                codigos_consumidos.update(productos_departamento.keys())
            consumo_total_general += total_periodo 

    mydb = conectar_mysql()
    if mydb:
        cursor = mydb.cursor()
        for departamento in sorted(list(departamentos)):
            for codigo in sorted(list(codigos_consumidos)):
               
                semanal = consumo_semanal[0].get(departamento, {}).get(codigo, 0)
                mensual = consumo_mensual[0].get(departamento, {}).get(codigo, 0)

               
                cursor.execute("SELECT Nombre, UnidadMedida FROM productos WHERE Codigo = %s", (codigo,))
                producto_info = cursor.fetchone()
                nombre_producto = producto_info[0] if producto_info else "N/A"
                unidad_medida = producto_info[1] if producto_info else "N/A"

               
                total_consumo_producto = semanal + mensual 

                
                porcentaje = (total_consumo_producto / consumo_total_general) * 100 if consumo_total_general > 0 else 0

                
                values = (departamento, codigo, nombre_producto, semanal, mensual, unidad_medida, f"{porcentaje:.2f}%")
                tabla_consumo.insert("", tk.END, values=values)
        cursor.close()
        mydb.close()


def calcular_consumo_periodo(periodo):
    """Calcula el consumo para un período específico desde la base de datos MySQL,
       utilizando el código del producto como clave, solo desde la tabla de salidas.
    """
    consumo_departamentos = {}
    total_consumo = 0
    fecha_actual = datetime.date.today()
    fecha_inicio = fecha_actual - periodo
    
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
        val = (fecha_inicio, fecha_actual)
        try:
            cursor.execute(query, val)
            salidas_periodo = cursor.fetchall()
            for nombre_departamento, codigo_producto, cantidad, fecha_salida, unidad_medida, nombre_producto in salidas_periodo:
                
                if nombre_departamento not in consumo_departamentos:
                    consumo_departamentos[nombre_departamento] = {}
                if codigo_producto not in consumo_departamentos[nombre_departamento]:
                    consumo_departamentos[nombre_departamento][codigo_producto] = 0
                try:
                    consumo_departamentos[nombre_departamento][codigo_producto] += int(cantidad)
                    total_consumo += int(cantidad)
                except ValueError:
                    print(f"Cantidad inválida en la salida para el producto con código {codigo_producto} en el departamento {nombre_departamento}")
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al calcular el consumo por período: {err}")
        finally:
            cursor.close()
            mydb.close()
    return consumo_departamentos, total_consumo


    




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
    """Genera un reporte del historial de entradas desde la base de datos MySQL con búsqueda y filtro por categoría."""
    # Asume que 'ventana' es la ventana principal de la aplicación, definida globalmente o pasada.
    # Si 'ventana' no es global, deberías pasarla como argumento a esta función.
    # Por ahora, usaré un placeholder si no está definida.
    try:
        global ventana # Intenta usar la ventana global
    except NameError:
        ventana = tk.Tk() # Crea una ventana principal si no existe para la prueba
        ventana.withdraw() # La esconde si es solo para que Toplevel funcione

    ventana_reporte = tk.Toplevel(ventana)
    ventana_reporte.title("Reporte de Entradas")
    ventana_reporte.geometry("1000x600")
    ventana_reporte.configure(bg="#A9A9A9")


    style = ttk.Style(ventana_reporte)
    style.theme_use('clam')
    style.configure("CustomLabel.TLabel", foreground="#ffffff", background="#A9A9A9", font=("Segoe UI", 10, "bold"))
    style.configure("CustomEntry.TEntry", foreground="#000000", background="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))
    style.configure("Grid.Treeview", foreground="#000000", background="#ffffff", font=("Segoe UI", 10))
    style.configure("Grid.Treeview.Heading", foreground="#000000", background="#d9d9d9", font=("Segoe UI", 10, "bold"))
    style.map("Grid.Treeview", background=[('selected', '#bddfff')], foreground=[('selected', '#000000')])
    style.configure("TCombobox", foreground="#000000", background="#ffffff", fieldbackground="#ffffff", insertcolor="#000000", font=("Segoe UI", 10))


    frame_controles = tk.Frame(ventana_reporte, bg="#A9A9A9")
    frame_controles.pack(pady=10, padx=10, fill=tk.X)


    ttk.Label(frame_controles, text="Buscar:", style="CustomLabel.TLabel").pack(side=tk.LEFT)
    entry_busqueda = ttk.Entry(frame_controles, style="CustomEntry.TEntry")
    entry_busqueda.pack(side=tk.LEFT, padx=(0, 10))


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

    categoria_seleccionada_reporte = tk.StringVar(frame_controles)
    categoria_seleccionada_reporte.set(categorias_mostrar[0])
    menu_categorias_reporte = ttk.Combobox(frame_controles,
                                           textvariable=categoria_seleccionada_reporte,
                                           values=categorias_mostrar,
                                           style="TCombobox",
                                           state="readonly")
    menu_categorias_reporte.pack(side=tk.LEFT, padx=(0, 10))

    # --- NUEVO: Botón para Exportar a PDF ---
    boton_exportar_pdf = ttk.Button(frame_controles, text="Exportar a PDF",
                                    command=lambda: exportar_tabla_pdf(tabla_entradas, "Historial de Entradas"))
    boton_exportar_pdf.pack(side=tk.RIGHT, padx=(10, 0))


    frame_tabla_contenedor = tk.Frame(ventana_reporte, bg="#A9A9A9")
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
                    p.UnidadMedida,
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


    def aplicar_filtro(*args):
        filtro_busqueda = entry_busqueda.get().strip()
        categoria_filtro = categoria_seleccionada_reporte.get()
        cargar_entradas(filtro_busqueda, categoria_filtro)


    entry_busqueda.bind("<KeyRelease>", aplicar_filtro)
    menu_categorias_reporte.bind("<<ComboboxSelected>>", aplicar_filtro)


    cargar_entradas()


    def mostrar_menu_contextual(event):
        """
        Muestra el menú contextual de clic derecho solo si el usuario es administrador.
        """
        global current_user_role_is_admin

        if current_user_role_is_admin:
            item = tabla_entradas.identify_row(event.y)
            if item:
                tabla_entradas.selection_set(item)
                # Aquí necesitarías definir 'menu_contextual' si aún no lo tienes
                # menu_contextual.post(event.x_root, event.y_root)
                messagebox.showinfo("Menú Contextual", "Menú contextual activado (simulado).", parent=ventana_reporte)
        else:
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones en el historial.", parent=ventana_reporte)


    tabla_entradas.bind("<Button-3>", mostrar_menu_contextual)
    ventana_reporte.mainloop()



                        #GENERA UNA VENTANA CON TODOS LOS PRODUCTOS QUE HAN SALIDO
def generar_reporte_salidas():
    """Genera un reporte del historial de salidas desde la base de datos MySQL."""
    ventana_reporte_salidas = tk.Toplevel(ventana)
    ventana_reporte_salidas.title("Reporte de Salidas")
    ventana_reporte_salidas.geometry("1000x600") 
    ventana_reporte_salidas.configure(bg="#A9A9A9")

    
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
            cursor.close()
            mydb.close()

    departamento_seleccionado_reporte = tk.StringVar(frame_controles_salidas)
    departamento_seleccionado_reporte.set(departamentos_mostrar[0])

    menu_departamentos_reporte = ttk.Combobox(frame_controles_salidas,
                                            textvariable=departamento_seleccionado_reporte,
                                            values=departamentos_mostrar,
                                            style="TCombobox",
                                            state="readonly")
    menu_departamentos_reporte.pack(side=tk.LEFT, padx=(0, 10))
    
    frame_tabla_contenedor_salidas = tk.Frame(ventana_reporte_salidas, bg="#A9A9A9")
    frame_tabla_contenedor_salidas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame_tabla_contenedor_salidas, columns=("Código", "Producto", "Cantidad", "Fecha", "Destino", "Requisición", "SalidaID"), show="headings", style="Grid.Treeview")
    tree.heading("Código", text="Código", anchor=tk.W)
    tree.heading("Producto", text="Producto", anchor=tk.W)
    tree.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tree.heading("Fecha", text="Fecha", anchor=tk.W)
    tree.heading("Destino", text="Destino", anchor=tk.W)
    tree.heading("Requisición", text="Requisición", anchor=tk.W)
    tree.column("SalidaID", width=0, stretch=tk.NO) 
    
    
    tree.column("Código", width=100)
    tree.column("Producto", width=180)
    tree.column("Cantidad", width=80)
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
                SELECT s.SalidaID, p.Codigo, p.Nombre, s.Cantidad, s.FechaSalida, d.NombreDepartamento, s.NumeroRequisicion
                FROM salidas s
                JOIN productos p ON s.ProductoID = p.ProductoID
                JOIN departamentos d ON s.DepartamentoID = d.DepartamentoID 
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
            for salida_id, codigo, producto, cantidad, fecha, destino_nombre, requisicion in salidas_db:
                tree.insert("", "end", values=(codigo, producto, cantidad, fecha.strftime("%Y-%m-%d"), destino_nombre, requisicion, salida_id))
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Error al cargar las salidas: {err}")
        finally:
            if mydb and mydb.is_connected():
                cursor.close()
                mydb.close()

    

   
    

    
    menu_contextual_salidas = tk.Menu(ventana_reporte_salidas, tearoff=0)
    
    
    
    def mostrar_menu_contextual_salidas(event):
        global current_user_role_is_admin 

        if current_user_role_is_admin: 
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
                menu_contextual_salidas.post(event.x_root, event.y_root)
        else:
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones en el historial de salidas.")
    
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
                SELECT spe.SalidaEsperaID, p.Codigo, p.Nombre, spe.Cantidad, d.NombreDepartamento
                FROM salidas_espera spe
                JOIN productos p ON spe.ProductoID = p.ProductoID
                JOIN departamentos d ON spe.DepartamentoID = d.DepartamentoID
                WHERE 1=1 -- Cláusula siempre verdadera para facilitar la adición de AND
            """
            params = []

            if filtro_busqueda:
                query += " AND (p.Codigo LIKE %s OR p.Nombre LIKE %s)"
                params.append(f"%{filtro_busqueda}%")
                params.append(f"%{filtro_busqueda}%")
            
           

            query += " ORDER BY spe.FechaSolicitud DESC"

            try:
                cursor.execute(query, tuple(params))
                salidas_espera_db = cursor.fetchall()
                for espera_id, codigo, producto, cantidad, departamento_nombre in salidas_espera_db: 
                    tabla_salidas_espera.insert("", tk.END, values=(codigo, producto, cantidad, departamento_nombre, espera_id))
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al actualizar la tabla de salidas en espera: {err}")
            finally:
                if mydb and mydb.is_connected():
                    cursor.close()
                    mydb.close()

def generar_reporte_salidas_espera():
    """Genera o trae al frente la ventana del reporte de salidas en espera desde la base de datos."""
    global ventana_reporte_salidas_espera, tabla_salidas_espera, entry_busqueda_espera, ventana # Asegúrate de que 'ventana' sea global

    if ventana_reporte_salidas_espera and ventana_reporte_salidas_espera.winfo_exists():
        ventana_reporte_salidas_espera.lift()
        # Asegúrate de que entry_busqueda_espera esté inicializado antes de usarlo
        if entry_busqueda_espera:
            filtro_actual = entry_busqueda_espera.get().strip()
            actualizar_tabla_salidas_espera(filtro_actual)
        return

    # Si la ventana no existe, crearla
    ventana_reporte_salidas_espera = tk.Toplevel(ventana)
    ventana_reporte_salidas_espera.title("Reporte de Salidas en Espera")
    ventana_reporte_salidas_espera.geometry("800x500")
    ventana_reporte_salidas_espera.configure(bg="#A9A9A9")


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

    # --- NUEVO: Botón de Exportar a PDF ---
    boton_exportar_pdf_espera = ttk.Button(frame_controles, text="Exportar a PDF",
                                           command=lambda: exportar_tabla_pdf(tabla_salidas_espera, "Reporte de Salidas en Espera"))
    boton_exportar_pdf_espera.pack(side=tk.RIGHT, padx=(10, 0))


    # Frame para la tabla y la scrollbar
    frame_tabla_contenedor = tk.Frame(ventana_reporte_salidas_espera, bg="#A9A9A9")
    frame_tabla_contenedor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Definición de la tabla
    tabla_salidas_espera = ttk.Treeview(frame_tabla_contenedor,
                                        columns=("Código", "Producto", "Cantidad", "Departamento", "EsperaID"),
                                        show="headings",
                                        style="Grid.Treeview")
    tabla_salidas_espera.column("EsperaID", width=0, stretch=tk.NO)

    tabla_salidas_espera.heading("Código", text="Código", anchor=tk.W)
    tabla_salidas_espera.heading("Producto", text="Producto", anchor=tk.W)
    tabla_salidas_espera.heading("Cantidad", text="Cantidad", anchor=tk.W)
    tabla_salidas_espera.heading("Departamento", text="Departamento", anchor=tk.W)

    tabla_salidas_espera.column("Código", width=100)
    tabla_salidas_espera.column("Producto", width=200)
    tabla_salidas_espera.column("Cantidad", width=100)
    tabla_salidas_espera.column("Departamento", width=200)

    scrollbar_vertical = ttk.Scrollbar(frame_tabla_contenedor, orient="vertical", command=tabla_salidas_espera.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_salidas_espera.configure(yscrollcommand=scrollbar_vertical.set)

    tabla_salidas_espera.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


    def agregar_requisicion():
        item_seleccionado = tabla_salidas_espera.selection()
        if item_seleccionado:
            item = item_seleccionado[0]
            values = tabla_salidas_espera.item(item, "values")

            # Asegurarse de que los índices de 'values' sean correctos
            # ("Código", "Producto", "Cantidad", "Departamento", "EsperaID")
            if len(values) >= 5:
                codigo_producto = values[0]
                producto_nombre = values[1]
                cantidad_salida = float(values[2])
                departamento_nombre = values[3]
                espera_id = values[4]

                def confirmar_requisicion():
                    numero_requisicion = entry_requisicion.get().strip()
                    if not numero_requisicion:
                        messagebox.showerror("Error", "El número de requisición no puede estar vacío.")
                        return

                    fecha_salida_str = entry_fecha.get()
                    try:
                        fecha_salida = datetime.datetime.strptime(fecha_salida_str, "%Y-%m-%d").date()
                    except ValueError:
                        messagebox.showerror("Error", "Formato de fecha incorrecto (YYYY-MM-DD).")
                        return

                    mydb = conectar_mysql()
                    if mydb:
                        cursor = mydb.cursor()
                        try:
                            # Obtener ProductoID y Stock
                            cursor.execute("SELECT ProductoID, Stock FROM productos WHERE Codigo = %s", (codigo_producto,))
                            resultado_prod = cursor.fetchone()
                            if not resultado_prod:
                                messagebox.showerror("Error", f"Producto con código '{codigo_producto}' no encontrado.")
                                return
                            producto_id_para_salida = resultado_prod[0]
                            stock_actual = resultado_prod[1]

                            # Validar stock
                            if stock_actual < cantidad_salida:
                                messagebox.showerror("Error de Stock", f"No hay suficiente stock para el producto '{producto_nombre}'. Stock actual: {stock_actual}. Cantidad solicitada: {cantidad_salida}.")
                                return

                            # Obtener DepartamentoID
                            cursor.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (departamento_nombre,))
                            resultado_dep = cursor.fetchone()
                            if not resultado_dep:
                                messagebox.showerror("Error", f"Departamento '{departamento_nombre}' no encontrado en la base de datos.")
                                return
                            departamento_id_para_salida = resultado_dep[0]

                            # Insertar en salidas
                            query_insert_salida = """
                                INSERT INTO salidas (ProductoID, CodigoProducto, Cantidad, FechaSalida, DepartamentoID, NumeroRequisicion)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(query_insert_salida, (producto_id_para_salida, codigo_producto, cantidad_salida, fecha_salida, departamento_id_para_salida, numero_requisicion))

                            # Actualizar stock en productos
                            query_update_producto = """
                                UPDATE productos
                                SET Stock = Stock - %s, FechaSalida = %s, DepartamentoID = %s
                                WHERE ProductoID = %s
                            """
                            cursor.execute(query_update_producto, (cantidad_salida, fecha_salida, departamento_id_para_salida, producto_id_para_salida))

                            # Eliminar de salidas_espera
                            query_eliminar_espera = "DELETE FROM salidas_espera WHERE SalidaEsperaID = %s"
                            cursor.execute(query_eliminar_espera, (espera_id,))

                            mydb.commit()
                            messagebox.showinfo("Salida Registrada", f"La salida del producto '{producto_nombre}' al departamento '{departamento_nombre}' ha sido registrada y el inventario actualizado.")

                            actualizar_tabla_salidas_espera(entry_busqueda_espera.get().strip()) # Recargar con el filtro actual
                            if ventana_requisicion.winfo_exists():
                                ventana_requisicion.destroy()

                        except mysql.connector.Error as err:
                            mydb.rollback()
                            messagebox.showerror("Error", f"Error al confirmar la requisición: {err}")
                        finally:
                            if mydb and mydb.is_connected():
                                cursor.close()
                                mydb.close()

                ventana_requisicion = tk.Toplevel(ventana_reporte_salidas_espera)
                ventana_requisicion.title("Agregar Requisición y Fecha")
                ventana_requisicion.configure(bg="#A9A9A9")

                tk.Label(ventana_requisicion, text="Número de Requisición:", fg="#ffffff", bg="#A9A9A9").grid(row=0, column=0, padx=5, pady=5)
                entry_requisicion = ttk.Entry(ventana_requisicion)
                entry_requisicion.grid(row=0, column=1, padx=5, pady=5)

                tk.Label(ventana_requisicion, text="Fecha de Salida:", fg="#ffffff", bg="#A9A9A9").grid(row=1, column=0, padx=5, pady=5)
                entry_fecha = ttk.Entry(ventana_requisicion)
                entry_fecha.grid(row=1, column=1, padx=5, pady=5)

                entry_fecha.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
                ttk.Button(ventana_requisicion, text="Calendario", command=lambda: abrir_calendario(ventana_requisicion, entry_fecha)).grid(row=1, column=2, padx=5, pady=5)

                ttk.Button(ventana_requisicion, text="Confirmar", command=confirmar_requisicion).grid(row=2, column=0, columnspan=3, pady=10)
            else:
                messagebox.showerror("Error", "Datos de producto incompletos. Asegúrese de seleccionar un producto válido.")
        else:
            messagebox.showerror("Error", "Seleccione un producto para agregar requisición.")

    def editar_salida_espera():
        seleccion = tabla_salidas_espera.selection()
        if seleccion:
            item_id = seleccion[0]
            values = tabla_salidas_espera.item(item_id, "values")
            codigo_actual = values[0]
            producto_actual = values[1]
            cantidad_actual = values[2]
            departamento_actual_nombre = values[3]
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
            entry_producto.config(state="readonly")

            tk.Label(ventana_edicion, text="Cantidad:", fg="#ffffff", bg="#A9A9A9").grid(row=2, column=0, padx=5, pady=5)
            entry_cantidad = ttk.Entry(ventana_edicion)
            entry_cantidad.grid(row=2, column=1, padx=5, pady=5)
            entry_cantidad.insert(0, cantidad_actual)

            tk.Label(ventana_edicion, text="Departamento:", fg="#ffffff", bg="#A9A9A9").grid(row=3, column=0, padx=5, pady=5)

            departamentos_disponibles = obtener_departamentos()
            combo_departamento = ttk.Combobox(ventana_edicion, values=departamentos_disponibles, state="readonly")
            combo_departamento.grid(row=3, column=1, padx=5, pady=5)
            combo_departamento.set(departamento_actual_nombre)

            def guardar_cambios():

                try:
                    cantidad_editada = float(entry_cantidad.get())
                except ValueError:
                    messagebox.showerror("Error", "Cantidad debe ser un número (entero o decimal).")
                    return
                departamento_nombre_editado = combo_departamento.get()

                mydb = conectar_mysql()
                if mydb:
                    cursor = mydb.cursor()
                    try:
                        # Obtener ProductoID (por si acaso el código_actual no es suficiente)
                        cursor.execute("SELECT ProductoID FROM productos WHERE Codigo = %s", (codigo_actual,))
                        resultado_prod_id = cursor.fetchone()
                        if not resultado_prod_id:
                            messagebox.showerror("Error", f"Producto con código '{codigo_actual}' no encontrado.")
                            return
                        producto_id_update = resultado_prod_id[0]

                        cursor.execute("SELECT DepartamentoID FROM departamentos WHERE NombreDepartamento = %s", (departamento_nombre_editado,))
                        resultado_dep = cursor.fetchone()
                        if not resultado_dep:
                            messagebox.showerror("Error", f"Departamento '{departamento_nombre_editado}' no encontrado en la base de datos.")
                            return
                        departamento_id_editado = resultado_dep[0]

                        query_actualizar = """
                            UPDATE salidas_espera
                            SET ProductoID = %s,
                                Cantidad = %s,
                                DepartamentoID = %s
                            WHERE SalidaEsperaID = %s
                        """
                        cursor.execute(query_actualizar, (producto_id_update, cantidad_editada, departamento_id_editado, espera_id))
                        mydb.commit()
                        actualizar_tabla_salidas_espera(entry_busqueda_espera.get().strip()) # Recargar con el filtro actual
                        ventana_edicion.destroy()
                        messagebox.showinfo("Solicitud Editada", "La solicitud ha sido actualizada.")
                    except mysql.connector.Error as err:
                        mydb.rollback()
                        messagebox.showerror("Error", f"Error al editar la solicitud: {err}")
                    except TypeError:
                        messagebox.showerror("Error", "Error al obtener ID de producto o departamento. Verifique los datos.")
                    finally:
                        if mydb and mydb.is_connected():
                            cursor.close()
                            mydb.close()

            ttk.Button(ventana_edicion, text="Guardar", command=guardar_cambios).grid(row=4, column=0, columnspan=2, pady=10)
        else:
            messagebox.showerror("Error", "Por favor, seleccione una solicitud para editar.")


    menu_contextual = tk.Menu(ventana_reporte_salidas_espera, tearoff=0)
    menu_contextual.add_command(label="Agregar Requisición", command=agregar_requisicion)
    # Aquí puedes añadir la opción de editar si quieres que esté en el menú contextual
    # menu_contextual.add_command(label="Editar Solicitud", command=editar_salida_espera)


    def mostrar_menu_contextual(event):
        global current_user_role_is_admin

        if current_user_role_is_admin:
            item = tabla_salidas_espera.identify_row(event.y)
            if item:
                tabla_salidas_espera.selection_set(item)
                menu_contextual.post(event.x_root, event.y_root)
        else:
            messagebox.showinfo("Permiso Denegado", "No tiene los permisos para realizar estas acciones en el historial de salidas en espera.")

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

    frame_filtros = ttk.Frame(main_frame, style="TFrame")
    frame_filtros.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    frame_tabla = ttk.Frame(main_frame, style="TFrame")
    frame_tabla.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    frame_tabla.grid_rowconfigure(0, weight=1)
    frame_tabla.grid_columnconfigure(0, weight=1)
    

    

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
    opciones_stock = ["Todos", "Bajo Stock (<= 2)", "Stock Medio (3-10)", "Stock Alto (>= 11-20)"]
    stock_seleccionado = ttk.Combobox(frame_filtros, values=opciones_stock, style="TCombobox", width=25)
    stock_seleccionado.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    stock_seleccionado.set("")

    global tabla_reporte
    tabla_reporte = ttk.Treeview(frame_tabla, style="Grid.Treeview")
    tabla_reporte.pack(fill="both", expand=True)

    def limpiar_tabla_reporte():
        tabla_reporte.delete(*tabla_reporte.get_children())
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

    boton_limpiar = ttk.Button(frame_tabla, text="Limpiar", command=limpiar_tabla_reporte, style="Small.TButton")
    boton_limpiar.pack(side="bottom", anchor="se", padx=10, pady=10)

    # --- Lógica de Generación de Reporte (MODIFICADA PARA FILTROS INDEPENDIENTES) ---
    def generar_reporte_filtrado():
        # Limpiar la tabla antes de generar un nuevo reporte
        tabla_reporte.delete(*tabla_reporte.get_children())
        tabla_reporte["columns"] = ()
        tabla_reporte.heading("#0", text="")

        categoria = categoria_seleccionada.get()
        departamento = departamento_seleccionado.get()
        stock = stock_seleccionado.get()

        fecha_inicio_cat_str = fecha_inicio_cat.get()
        fecha_fin_cat_str = fecha_fin_cat.get()
        fecha_inicio_dep_str = fecha_inicio_dep.get()
        fecha_fin_dep_str = fecha_fin_dep.get()

        print("\n--- INICIO DE GENERAR_REPORTE_FILTRADO ---")
        print(f"Valores RAW: Cat='{categoria}', Dep='{departamento}', Stock='{stock}', FechaICat='{fecha_inicio_cat_str}', FechaFCat='{fecha_fin_cat_str}', FechaIDep='{fecha_inicio_dep_str}', FechaFDep='{fecha_fin_dep_str}'")

        # Determinar si hay alguna selección específica (no "Todas"/"Todos" y no vacío)
        es_categoria_especifica = (categoria != "Todas" and categoria != "")
        es_departamento_especifico = (departamento != "Todos" and departamento != "")
        es_stock_especifico = (stock != "Todos" and stock != "")

        # Determinar si hay alguna selección en un filtro (incluyendo "Todas"/"Todos" o fechas)
        hay_filtro_categoria_o_fechas = (categoria != "" or (fecha_inicio_cat_str and fecha_fin_cat_str))
        hay_filtro_departamento_o_fechas = (departamento != "" or (fecha_inicio_dep_str and fecha_fin_dep_str))
        hay_filtro_stock = (stock != "") # Para stock, "" significa no seleccionado

        print(f"Banderas Específicas: CatEsp={es_categoria_especifica}, DepEsp={es_departamento_especifico}, StockEsp={es_stock_especifico}")
        print(f"Banderas Generales: HayCatOFechas={hay_filtro_categoria_o_fechas}, HayDepOFechas={hay_filtro_departamento_o_fechas}, HayStock={hay_filtro_stock}")


        # --- Lógica de Prioridad para Generar Reporte ---

        # 1. Mayor prioridad: Filtro combinado (Categoría ESPECÍFICA y Departamento ESPECÍFICO)
        # Si ambas son específicas, se activa el reporte combinado.
        if es_categoria_especifica and es_departamento_especifico:
            print("DEBUG: Detectado: Filtro combinado Categoria ESPECIFICA y Departamento ESPECIFICO.")
            generar_reporte_categoria_departamento(categoria, departamento, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte)
        
        # 2. Siguiente prioridad: Si hay alguna actividad en el filtro de Categoría
        # Esto incluye: una categoría específica, "Todas" en categoría, o fechas de categoría.
        elif hay_filtro_categoria_o_fechas:
            print("DEBUG: Detectado: Filtro de Categoria activo (específico, 'Todas', o con fechas).")
            # tus funciones de reporte deben manejar "" o "Todas" como "no filtrar por esto"
            generar_reporte_consumo_lapso_filtrado(categoria, fecha_inicio_cat_str, fecha_fin_cat_str, departamento, stock, tabla_reporte, ventana_reporte)
            
        # 3. Siguiente prioridad: Si hay alguna actividad en el filtro de Departamento
        # Esto incluye: un departamento específico, "Todos" en departamento, o fechas de departamento.
        elif hay_filtro_departamento_o_fechas:
            print("DEBUG: Detectado: Filtro de Departamento activo (específico, 'Todos', o con fechas).")
            # tus funciones de reporte deben manejar "" o "Todos" como "no filtrar por esto"
            generar_reporte_departamento(departamento, categoria, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte, stock)
            
        # 4. Siguiente prioridad: Si hay alguna actividad en el filtro de Stock
        # Esto incluye: un tipo de stock específico o "Todos" en stock.
        elif hay_filtro_stock:
            print("DEBUG: Detectado: Filtro de Stock activo (específico o 'Todos').")
            # tus funciones de reporte deben manejar "" o "Todos" como "no filtrar por esto"
            generar_reporte_de_stock(stock, categoria, departamento, fecha_inicio_dep_str, fecha_fin_dep_str, tabla_reporte, ventana_reporte)
            
        # 5. Ningún filtro significativo seleccionado
        else:
            print("DEBUG: Ningún filtro activo. Mostrando mensaje de información.")
            messagebox.showinfo("Selección de Filtros",
                                "Por favor, selecciona al menos un criterio en Categoría, Departamento o Stock para generar un reporte filtrado, o utiliza el botón 'Generar Inventario Completo'.",
                                parent=ventana_reporte)

        print("--- FIN DE GENERAR_REPORTE_FILTRADO ---")


    # --- Botón para Generar Reporte Filtrado ---
    boton_generar_filtrado = ttk.Button(frame_filtros, text="Generar Reporte Filtrado", command=generar_reporte_filtrado)
    boton_generar_filtrado.grid(row=3, column=0, columnspan=3, pady=10)

    # --- Botón para Generar Reporte de Inventario Completo ---
    boton_generar_completo = ttk.Button(frame_filtros, text="Generar Inventario Completo", command=lambda: generar_reporte_inventario_completo(tabla_reporte, ventana_reporte))
    boton_generar_completo.grid(row=3, column=3, columnspan=3, pady=10)

    boton_pdf = ttk.Button(main_frame, text="Exportar a PDF", command=lambda: exportar_tabla_pdf(tabla_reporte))
    boton_pdf.grid(row=2, column=0, pady=10)
    boton_pdf.anchor(tk.CENTER)

    for i in range(6):
        frame_filtros.grid_columnconfigure(i, weight=1)

    frame_tabla.grid_columnconfigure(0, weight=1)



def generar_reporte_inventario_completo(tabla, ventana):
    """
    Genera un reporte completo de todo el inventario existente,
    con las mismas columnas que la interfaz 'Mostrar Inventario'.
    """
    tabla.delete(*tabla.get_children()) # Limpiar tabla existente

    # Definir columnas para el Treeview, COINCIDIENDO con 'Mostrar Inventario'
    columnas = ("Código", "Categoría", "Producto", "Destino Entrada", "Destino Salida",
                "Entrada", "Salida", "Stock", "Unidad Medida", "Fecha Entrada", "Fecha Salida")
    tabla["columns"] = columnas
    tabla.heading("#0", text="") # Ocultar la primera columna por defecto

    # Configurar encabezados y anchos de columnas en el Treeview
    for col in columnas:
        tabla.heading(col, text=col, anchor=tk.W)
        if col == "Stock": tabla.column(col, width=80, anchor=tk.CENTER)
        elif col in ("Entrada", "Salida", "Código", "Unidad Medida"): tabla.column(col, width=100, anchor=tk.CENTER)
        elif col in ("Fecha Entrada", "Fecha Salida", "Destino Entrada", "Destino Salida"): tabla.column(col, width=120, anchor=tk.W)
        else: tabla.column(col, width=150, anchor=tk.W)
    tabla.column("#0", width=0, stretch=tk.NO) # Asegurar que la primera columna esté oculta

    mydb = conectar_mysql()
    if not mydb: return

    cursor = mydb.cursor()
    # Consulta para obtener todos los datos del inventario, simulando la vista 'Mostrar Inventario'
    query = """
        SELECT
            p.Codigo,
            c.NombreCategoria,
            p.Nombre AS NombreProducto,
            COALESCE(d_ent.NombreDepartamento, '') AS DestinoEntrada,
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
            departamentos d_ent ON e.DepartamentoID = d_ent.DepartamentoID
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
            return

        for row in inventario_data:
            formatted_row = tuple("" if item is None else str(item) for item in row)
            tabla.insert("", tk.END, values=formatted_row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de inventario completo: {err}", parent=ventana)
    finally:
        if cursor: cursor.close()
        if mydb and mydb.is_connected(): mydb.close()

def generar_reporte_consumo_lapso_filtrado(categoria_filtro, fecha_inicio_str, fecha_fin_str, departamento_filtro_ignorado, stock_filtro_ignorado, tabla, ventana):
    """
    Genera un reporte de consumo por categoría/lapso.
    Muestra: Categoría, Producto, Cantidad Consumida, Unidad Medida, Lapso (rango de fechas).
    """
    tabla.delete(*tabla.get_children()) # Limpiar tabla existente

    
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
    tabla.column("Cantidad Consumida", width=100, anchor=tk.W)
    tabla.column("Unidad Medida", width=100, anchor=tk.W) 
    tabla.column("Lapso", width=180, anchor=tk.W) 

    mydb = conectar_mysql()
    if not mydb:
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
    lapso_texto = ""

    if categoria_filtro != "Todas" and categoria_filtro != "":
        query += " AND cat.NombreCategoria = %s"
        params.append(categoria_filtro)

    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        lapso_texto = "Todo el Historial"

    query += " GROUP BY cat.NombreCategoria, p.Nombre, p.UnidadMedida"
    query += " ORDER BY cat.NombreCategoria, p.Nombre"

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron datos de consumo para los filtros de categoría seleccionados.", parent=ventana)
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            return

        
        for categoria_nombre, producto, cantidad_consumida, unidad_medida, _, _ in reporte_data:
            tabla.insert("", tk.END, values=(categoria_nombre, producto, cantidad_consumida, unidad_medida, lapso_texto))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de categoría/consumo: {err}", parent=ventana)
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
    tabla.column("Cantidad Consumida", width=100, anchor=tk.W)
    tabla.column("Unidad Medida", width=100, anchor=tk.W)
    tabla.column("Lapso", width=120, anchor=tk.W) 
    tabla.column("Número Requisición", width=120, anchor=tk.W) 

    mydb = conectar_mysql()
    if not mydb:
        return

    cursor = mydb.cursor()
    query = """
        SELECT
            d.NombreDepartamento,
            cat.NombreCategoria,
            p.Nombre,
            s.Cantidad,
            p.UnidadMedida, -- Añadido
            s.FechaSalida, -- Se usa para construir el lapso_texto si es necesario
            s.NumeroRequisicion -- Añadido
        FROM salidas s
        JOIN productos p ON s.ProductoID = p.ProductoID
        JOIN departamentos d ON s.DepartamentoID = d.DepartamentoID
        JOIN categorias cat ON p.CategoriaID = cat.CategoriaID
        WHERE 1=1 -- Siempre iniciar con 1=1 para condiciones dinámicas
    """
    params = []
    lapso_texto = ""

    
    if departamento_filtro != "Todos" and departamento_filtro != "":
        query += " AND d.NombreDepartamento = %s"
        params.append(departamento_filtro)

    
    if categoria_filtro != "Todas" and categoria_filtro != "":
        query += " AND cat.NombreCategoria = %s"
        params.append(categoria_filtro)

    
    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
        lapso_texto = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        lapso_texto = "Todo el Historial"
    
    if stock_filtro_texto != "Todos" and stock_filtro_texto != "":
        if stock_filtro_texto == "Bajo Stock (<= 2)":
            query += " AND p.Stock <= 2"
        elif stock_filtro_texto == "Stock Medio (3-10)":
            query += " AND p.Stock BETWEEN 3 AND 10"
        elif stock_filtro_texto == "Stock Alto (>= 11)":
            query += " AND p.Stock >= 11"
    
    query += " ORDER BY d.NombreDepartamento, s.FechaSalida DESC" 

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", "No se encontraron datos de consumo para los filtros de departamento seleccionados.", parent=ventana)
            
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            return

       
        for departamento_nombre, categoria_nombre, producto, cantidad, unidad_medida, fecha_salida, numero_requisicion in reporte_data:
            
            tabla.insert("", tk.END, values=(departamento_nombre, categoria_nombre, producto, cantidad, unidad_medida, lapso_texto, numero_requisicion))

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de departamento: {err}", parent=ventana)
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
            return

        for row in reporte_data:
            tabla.insert("", tk.END, values=row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de stock: {err}", parent=ventana)
    finally:
        if cursor:
            cursor.close()
        if mydb and mydb.is_connected():
            mydb.close()
def generar_reporte_inventario_completo(tabla, ventana):
    """
    Genera un reporte completo de todo el inventario existente,
    con las mismas columnas que la interfaz 'Mostrar Inventario'.
    """
    tabla.delete(*tabla.get_children()) # Limpiar tabla existente

    # Definir columnas para el Treeview, COINCIDIENDO con 'Mostrar Inventario'
    columnas = ("Código", "Categoría", "Producto", "Destino Entrada", "Destino Salida",
                "Entrada", "Salida", "Stock", "Unidad Medida", "Fecha Entrada", "Fecha Salida")
    tabla["columns"] = columnas
    tabla.heading("#0", text="") # Ocultar la primera columna por defecto

    # Configurar encabezados y anchos de columnas en el Treeview
    for col in columnas:
        tabla.heading(col, text=col, anchor=tk.W)
        if col == "Stock": tabla.column(col, width=80, anchor=tk.CENTER)
        elif col in ("Entrada", "Salida", "Código", "Unidad Medida"): tabla.column(col, width=100, anchor=tk.CENTER)
        elif col in ("Fecha Entrada", "Fecha Salida", "Destino Entrada", "Destino Salida"): tabla.column(col, width=120, anchor=tk.W)
        else: tabla.column(col, width=150, anchor=tk.W)
    tabla.column("#0", width=0, stretch=tk.NO) # Asegurar que la primera columna esté oculta

    mydb = conectar_mysql()
    if not mydb: return

    cursor = mydb.cursor()
    # Consulta para obtener todos los datos del inventario.
    # Usa e.Destino directamente para DestinoEntrada.
    # Usa s.DepartamentoID para unirse a 'departamentos' para DestinoSalida.
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
            return

        for row in inventario_data:
            formatted_row = tuple("" if item is None else str(item) for item in row)
            tabla.insert("", tk.END, values=formatted_row)

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte de inventario completo: {err}", parent=ventana)
    finally:
        if cursor: cursor.close()
        if mydb and mydb.is_connected(): mydb.close()
def generar_reporte_categoria_departamento(categoria_filtro, departamento_filtro, fecha_inicio_str, fecha_fin_str, tabla, ventana):
    """
    Genera un reporte de consumo de productos de una categoría específica por un departamento específico.
    Muestra: Categoría, Departamento, Producto, Cantidad Consumida, Unidad Medida, Lapso.
    Incluye un total de la cantidad consumida.
    """
    tabla.delete(*tabla.get_children()) # Limpiar tabla existente

    # Definir columnas para el Treeview del reporte combinado
    # Añadimos "Producto" para mostrar qué producto específico se consumió, y agruparemos por él.
    columnas_reporte = ("Categoría", "Departamento", "Producto", "Cantidad Consumida", "Unidad Medida", "Lapso")
    tabla["columns"] = columnas_reporte
    tabla.heading("#0", text="") # Ocultar la primera columna por defecto

    tabla.heading("Categoría", text="Categoría", anchor=tk.W)
    tabla.heading("Departamento", text="Departamento", anchor=tk.W)
    tabla.heading("Producto", text="Producto", anchor=tk.W) # Nueva columna
    tabla.heading("Cantidad Consumida", text="Cantidad Consumida", anchor=tk.W)
    tabla.heading("Unidad Medida", text="Unidad Medida", anchor=tk.W)
    tabla.heading("Lapso", text="Lapso", anchor=tk.W)

    # Configurar anchos de columnas
    tabla.column("#0", width=0, stretch=tk.NO)
    tabla.column("Categoría", width=120, anchor=tk.W)
    tabla.column("Departamento", width=120, anchor=tk.W)
    tabla.column("Producto", width=180, anchor=tk.W) # Ancho para el nombre del producto
    tabla.column("Cantidad Consumida", width=120, anchor=tk.CENTER)
    tabla.column("Unidad Medida", width=100, anchor=tk.W)
    tabla.column("Lapso", width=150, anchor=tk.W)


    mydb = conectar_mysql()
    if not mydb:
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

    # Añadir filtro por fechas si están presentes (usando las fechas de departamento, ya que es consumo)
    if fecha_inicio_str and fecha_fin_str:
        query += " AND s.FechaSalida BETWEEN %s AND %s"
        params.extend([fecha_inicio_str, fecha_fin_str])
        lapso_texto_display = f"{fecha_inicio_str} al {fecha_fin_str}"
    else:
        lapso_texto_display = "Todo el Historial" # Se usará este lapso para todas las filas si no hay fechas

    query += " GROUP BY cat.NombreCategoria, d.NombreDepartamento, p.Nombre, p.UnidadMedida"
    query += " ORDER BY cat.NombreCategoria, d.NombreDepartamento, p.Nombre"

    total_cantidad_consumida = 0

    try:
        cursor.execute(query, params)
        reporte_data = cursor.fetchall()

        if not reporte_data:
            messagebox.showinfo("Sin Resultados", f"No se encontraron productos de la categoría '{categoria_filtro}' consumidos por el departamento '{departamento_filtro}' para los filtros seleccionados.", parent=ventana)
            # Limpiar columnas si no hay datos
            tabla["columns"] = ()
            tabla.heading("#0", text="")
            return

        for row in reporte_data:
            categoria_nombre, departamento_nombre, producto_nombre, cantidad_consumida, unidad_medida, _, _ = row
            # La fecha de lapso es la misma para todas las filas si no se especificó un rango
            # Si se especificó un rango, se aplica ese lapso_texto_display a todas las filas
            tabla.insert("", tk.END, values=(categoria_nombre, departamento_nombre, producto_nombre, cantidad_consumida, unidad_medida, lapso_texto_display))
            total_cantidad_consumida += cantidad_consumida

        # Insertar la fila de total al final
        # Se pueden aplicar estilos para que se vea como un resumen
        tabla.insert("", tk.END, values=("", "", "TOTAL CONSUMIDO:", total_cantidad_consumida, "", ""), tags=('total_row',))
        tabla.tag_configure('total_row', background='#E0FFFF', font=('Segoe UI', 10, 'bold')) # Color y estilo para el total

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Error al generar el reporte combinado de categoría y departamento: {err}", parent=ventana)
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
        # Ajusta self.y_despues_membrete_superior para el título
        self.y_despues_membrete_superior = 5 + self.membrete_superior_altura + self.espacio_entre_tabla_y_membrete
        self.filas_por_pagina = self.calcular_filas_por_pagina()
        self.titulo_reporte = titulo_reporte # Nueva propiedad para el título

    def calcular_filas_por_pagina(self):
        # Altura disponible después del margen superior, margen inferior, membrete inferior y el espacio para el título y los encabezados de la tabla
        altura_disponible = self.h - self.t_margin - self.b_margin - self.membrete_inferior_altura - \
                           (self.membrete_superior_altura + self.espacio_entre_tabla_y_membrete + 10 + 5) - \
                           self.altura_encabezados - 5 # 10 para el título, 5 de padding
        return int(altura_disponible / self.altura_fila)

    def header(self):
        self.set_y(5)
        ancho_disponible = self.w - (self.l_margin + self.r_margin)
        try:
            # Asegúrate de que esta ruta sea accesible por PyInstaller
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
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, self.titulo_reporte, ln=1, align='C')
        self.set_font("Arial", size=10)

    def print_encabezados_tabla(self, headers, col_widths, x_start):
        self.set_x(x_start)
        self.set_font("Arial", 'B', 8)
        self.set_fill_color(200, 220, 255)
        self.set_text_color(0, 0, 0)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], self.altura_encabezados, txt=header, border=1, align='C', fill=True, new_x="RIGHT", new_y="TOP")
        self.ln()

# --- TU FUNCIÓN exportar_tabla_pdf (CORREGIDA Y AMPLIADA) ---
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
    # Ajusta el margen inferior para el auto page break para dejar espacio para el footer del membrete
    pdf.set_auto_page_break(auto=True, margin=pdf.membrete_inferior_altura + 10)
    pdf.set_font("Arial", size=7)
    pdf.add_page() # Esto llama a header() y print_titulo() automáticamente

    # --- Lógica para MANEJAR COLUMNAS A EXPORTAR Y SUS ENCABEZADOS ---
    all_cols_from_treeview = tabla_treeview["columns"]
    display_cols = [] # Nombres internos de las columnas del Treeview que queremos mostrar
    display_headers = [] # Textos de los encabezados para el PDF

    # Definir qué columnas queremos omitir de la exportación en el PDF
    columns_to_omit = ["EntradaID", "SalidaID", "EsperaID", "SolicitudID"] # Añade todos los IDs que no quieras en el PDF

    for col_name in all_cols_from_treeview:
        if col_name not in columns_to_omit:
            display_cols.append(col_name)
            header_text = tabla_treeview.heading(col_name)["text"]
            # Aquí puedes renombrar encabezados si es necesario para el PDF
            if header_text == "Stock Actual":
                display_headers.append("Stock")
            elif header_text == "Cantidad Consumida":
                display_headers.append("Cantidad")
            elif header_text == "Depto. Solicitante": # Para salidas en espera
                display_headers.append("Departamento")
            else:
                display_headers.append(header_text)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_widths = []

    # Ajustar col_widths basado en los *display_headers* (los que realmente irán en el PDF)
    # y no en los encabezados del Treeview original si tenían columnas ocultas.

    # Historial de Entradas (Código, Producto, Cantidad, Unidad Medida, Fecha, Destino)
    if tuple(display_headers) == ("Código", "Producto", "Cantidad", "Unidad Medida", "Fecha", "Destino"):
        col_widths = [
            available_width * 0.10, # Código
            available_width * 0.25, # Producto
            available_width * 0.10, # Cantidad
            available_width * 0.15, # Unidad Medida
            available_width * 0.15, # Fecha
            available_width * 0.25, # Destino
        ]
    # Historial de Salidas (ID Salida, Producto, Cantidad, Departamento, Fecha Salida)
    elif tuple(display_headers) == ("ID Salida", "Producto", "Cantidad", "Departamento", "Fecha Salida"):
        col_widths = [
            available_width * 0.10, # ID Salida
            available_width * 0.30, # Producto
            available_width * 0.10, # Cantidad
            available_width * 0.25, # Departamento
            available_width * 0.25, # Fecha Salida
        ]
    # Salidas en Espera (Código, Producto, Cantidad, Departamento)
    elif tuple(display_headers) == ("Código", "Producto", "Cantidad", "Departamento"):
         col_widths = [
            available_width * 0.15, # Código
            available_width * 0.35, # Producto
            available_width * 0.15, # Cantidad
            available_width * 0.35, # Departamento
        ]
    # Puedes añadir más condiciones elif para otros tipos de reportes:
    # Ejemplo para Reporte de Inventario (Departamento, Producto, Categoría, Cantidad, Lapso, Stock)
    elif tuple(display_headers) == ("Departamento", "Producto", "Categoría", "Cantidad", "Lapso", "Stock"):
        lapso_width_fixed = 50 # Un ejemplo de ancho fijo
        # Calculate remaining width for other columns
        remaining_width = available_width - lapso_width_fixed
        col_widths = [
            remaining_width * 0.15,
            remaining_width * 0.30,
            remaining_width * 0.15,
            remaining_width * 0.10,
            lapso_width_fixed, # Lapso
            remaining_width * 0.10,
        ]
    # Fallback genérico si no coincide con ninguna de las estructuras esperadas
    else:
        # Asegurarse de que len(display_headers) > 0 para evitar división por cero
        if len(display_headers) > 0:
            col_widths = [available_width / len(display_headers)] * len(display_headers)
        else:
            print("ADVERTENCIA: No hay columnas para mostrar en el PDF.")
            messagebox.showwarning("Advertencia", "No hay datos o columnas válidas para exportar.", parent=tabla_treeview)
            return

    total_width = sum(col_widths)
    x_start = (pdf.w - total_width) / 2
    row_height = pdf.altura_fila

    # Imprimir los encabezados de la tabla
    # Esto se hace aquí después de que el header() haya puesto el título.
    pdf.set_y(pdf.get_y() + 5) # Pequeño espacio después del título
    pdf.print_encabezados_tabla(display_headers, col_widths, x_start)

    current_y = pdf.get_y() # Obtener la posición Y actual después de los encabezados

    for i, child in enumerate(tabla_treeview.get_children()):
        # Verifica si hay espacio para la siguiente fila
        # Si no hay espacio, añadir una nueva página
        if current_y + row_height > pdf.h - pdf.b_margin - pdf.membrete_inferior_altura - 5:
            pdf.add_page()
            current_y = pdf.get_y() + 5 # Resetear Y después de la nueva página y título/header
            pdf.print_encabezados_tabla(display_headers, col_widths, x_start)
            current_y = pdf.get_y() # Actualizar Y después de imprimir los nuevos encabezados

        pdf.set_x(x_start)
        if i % 2 == 0:
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_fill_color(255, 255, 255)

        row_values = []
        for col_name in display_cols: # Ahora iteramos sobre display_cols
            value = tabla_treeview.set(child, col_name)
            row_values.append(str(value))

        # El check de desajuste ya no debería ser necesario si display_cols y col_widths están sincronizados
        # sin embargo, lo mantendremos para depuración
        if len(row_values) != len(col_widths):
            print(f"ADVERTENCIA: Desajuste en número de columnas para la fila {i}. Valores: {row_values}, Anchos: {col_widths}")
            continue # Salta esta fila si hay desajuste crítico

        for j, value in enumerate(row_values):
            pdf.cell(col_widths[j], row_height, txt=value, border=1, align='L', fill=True, new_x="RIGHT", new_y="TOP")
        pdf.ln()
        current_y = pdf.get_y() # Actualizar la posición Y después de cada fila

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

    
    if current_user_role_is_admin:
        boton_agregar = ttk.Button(frame_botones_menu, text="Agregar producto", image=ventana.logo_agregar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=agregar_producto)
        boton_agregar.image = ventana.logo_agregar_img
        boton_agregar.grid(row=0, column=0, padx=10, pady=10, sticky="ew") 

       
        boton_salida = ttk.Button(frame_botones_menu, text="Realizar salida en espera", image=ventana.logo_salida_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=realizar_salida)
        boton_salida.image = ventana.logo_salida_img
        boton_salida.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

   
    if not current_user_role_is_admin:
        
        boton_mostrar = ttk.Button(frame_botones_menu, text="Mostrar inventario", image=ventana.logo_mostrar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=lambda: mostrar_inventario(ventana))
        boton_mostrar.image = ventana.logo_mostrar_img
        boton_mostrar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        boton_consumo = ttk.Button(frame_botones_menu, text="Calcular consumo por departamento", image=ventana.logo_consumo_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=calcular_consumo_departamento)
        boton_consumo.image = ventana.logo_consumo_img
        boton_consumo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
    else:
       
        boton_mostrar = ttk.Button(frame_botones_menu, text="Mostrar inventario", image=ventana.logo_mostrar_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=lambda: mostrar_inventario(ventana))
        boton_mostrar.image = ventana.logo_mostrar_img
        boton_mostrar.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        boton_consumo = ttk.Button(frame_botones_menu, text="Calcular consumo por departamento", image=ventana.logo_consumo_img, compound=tk.TOP, style="MenuButtonDarkGrid.TButton", command=calcular_consumo_departamento)
        boton_consumo.image = ventana.logo_consumo_img
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

#  Ejecución de la aplicación 
cargar_datos()


iniciar_sesion()
