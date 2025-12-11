import os
import sys
import subprocess
import importlib.util
import time
import shutil

# --- 1. GESTIÓN DE DEPENDENCIAS Y COLORES ---
REQUISITOS = ['mutagen', 'requests', 'tqdm', 'colorama']

def verificar_e_instalar():
    """Verifica si los paquetes necesarios están instalados."""
    faltantes = []
    for paquete in REQUISITOS:
        if importlib.util.find_spec(paquete) is None:
            faltantes.append(paquete)

    if not faltantes:
        return True

    print(f"Faltan paquetes necesarios: {', '.join(faltantes)}")
    respuesta = input("¿Desea instalarlos ahora? (s/n): ").strip().lower()

    if respuesta == 's':
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *faltantes])
            print("\n¡Instalación completada! Reiniciando script...")
            time.sleep(1)
            # Nota: Al reiniciar el script, las dependencias ya estarán disponibles
            # En un entorno real, aquí se usaría execv o se requeriría un reinicio manual.
            return True
        except subprocess.CalledProcessError:
            print("ERROR: No se pudieron instalar los paquetes.")
            return False
    else:
        return False

# Verificar dependencias antes de importar
if not verificar_e_instalar():
    sys.exit("Faltan dependencias. Saliendo.")

# Importaciones seguras
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TPE1, TIT2, USLT
from tqdm import tqdm
from colorama import init, Fore, Back, Style

# Inicializar colorama
init(autoreset=True)

# --- 2. FUNCIONES DE LÓGICA ---

def obtener_ruta():
    """
    Solicita la ruta de la carpeta al usuario.
    Si el usuario presiona Enter, toma la ruta del script como predeterminada.
    """
    # Obtener la ruta del directorio del script actual
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"\n{Fore.CYAN}--- SELECCIÓN DE CARPETA ---{Style.RESET_ALL}")
    print("Ingresa la ruta de la carpeta de música.")
    print(f"{Style.DIM}(Presiona Enter para usar la ruta del script: {script_dir}){Style.RESET_ALL}")
    print(f"{Style.DIM}(Ejemplo Android: /sdcard/Music/Telegram){Style.RESET_ALL}")
    print(f"{Style.DIM}(Ejemplo PC: C:\\Users\\Musica){Style.RESET_ALL}")
    
    ruta_input = input(f"{Fore.YELLOW}>> Ruta: {Style.RESET_ALL}").strip()
    
    if not ruta_input:
        # Usar la ruta del script si el input está vacío
        ruta = script_dir
        print(f"{Fore.YELLOW}Usando ruta predeterminada: {ruta}{Style.RESET_ALL}")
    else:
        # Limpiar comillas y usar la ruta introducida
        ruta = ruta_input.replace('"', '').replace("'", "")

    if os.path.exists(ruta):
        return ruta
    else:
        print(f"{Fore.RED}¡Error! La ruta no existe. Intenta de nuevo.{Style.RESET_ALL}")
        return None

def limpiar_nombre(texto):
    """Limpia caracteres inválidos para nombres de archivo."""
    caracteres_no_validos = '/\\:*?"<>|'
    for char in caracteres_no_validos:
        texto = texto.replace(char, '')
    return texto

def opcion_renombrar(carpeta_ruta):
    """Lógica para renombrar archivos MP3 basados en sus tags ID3."""
    print(f"\n{Fore.BLUE}=== INICIANDO RENOMBRADO DE ARCHIVOS ==={Style.RESET_ALL}")
    print(f"Directorio: {Fore.MAGENTA}{carpeta_ruta}{Style.RESET_ALL}\n")

    archivos = [f for f in os.listdir(carpeta_ruta) if f.endswith('.mp3')]
    
    if not archivos:
        print(f"{Fore.YELLOW}No se encontraron archivos MP3.{Style.RESET_ALL}")
        return

    cont_exito = 0
    cont_error = 0
    cont_omitido = 0

    for nombre_archivo in tqdm(archivos, desc="Renombrando", unit="track", colour="cyan"):
        ruta_antigua = os.path.join(carpeta_ruta, nombre_archivo)
        
        try:
            audio = MP3(ruta_antigua, ID3=ID3)
            
            # Obtener tags con fallback
            artista = audio.tags.get('TPE1', ['Artista Desconocido'])[0]
            titulo = audio.tags.get('TIT2', ['Título Desconocido'])[0]

            artista = limpiar_nombre(artista)
            titulo = limpiar_nombre(titulo)
            
            nuevo_nombre = f"{artista} - {titulo}.mp3"
            ruta_nueva = os.path.join(carpeta_ruta, nuevo_nombre)
            
            if ruta_antigua != ruta_nueva and not os.path.exists(ruta_nueva):
                os.rename(ruta_antigua, ruta_nueva)
                tqdm.write(f"{Fore.GREEN}✔ Renombrado:{Style.RESET_ALL} {nombre_archivo} -> {Fore.CYAN}{nuevo_nombre}{Style.RESET_ALL}")
                cont_exito += 1
            elif os.path.exists(ruta_nueva) and ruta_antigua != ruta_nueva:
                tqdm.write(f"{Fore.YELLOW}⚠ Saltado (Ya existe):{Style.RESET_ALL} {nuevo_nombre}")
                cont_omitido += 1
            else:
                cont_omitido += 1
        
        except Exception as e:
            tqdm.write(f"{Fore.RED}✘ Error en '{nombre_archivo}':{Style.RESET_ALL} {e}")
            cont_error += 1

    print(f"\n{Fore.GREEN}Resumen Renombrado:{Style.RESET_ALL} {cont_exito} hechos, {cont_omitido} omitidos, {cont_error} errores.")
    return True # Devolvemos True para la opción combinada

def opcion_letras(carpeta_ruta):
    """Lógica para buscar e incrustar letras LRC en archivos MP3."""
    print(f"\n{Fore.MAGENTA}=== BUSCANDO E INCRUSTANDO LETRAS ==={Style.RESET_ALL}")
    print(f"Directorio: {Fore.CYAN}{carpeta_ruta}{Style.RESET_ALL}")

    try:
        archivos_mp3 = [f for f in os.listdir(carpeta_ruta) if f.endswith('.mp3')]
        if not archivos_mp3:
            print(f"{Fore.YELLOW}No hay archivos MP3 en esta carpeta.{Style.RESET_ALL}")
            return
    except Exception as e:
        print(f"{Fore.RED}Error leyendo directorio: {e}{Style.RESET_ALL}")
        return

    # Carpeta sin letras
    carpeta_sin_letras = os.path.join(carpeta_ruta, "sin letras")
    os.makedirs(carpeta_sin_letras, exist_ok=True)
    print(f"Los archivos fallidos se moverán a: {Fore.YELLOW}'sin letras/'{Style.RESET_ALL}\n")

    with tqdm(total=len(archivos_mp3), desc="Procesando", unit="track", colour="green") as pbar:
        for nombre_archivo in archivos_mp3:
            pbar.set_postfix_str(nombre_archivo[:20] + "...", refresh=True)
            ruta_completa = os.path.join(carpeta_ruta, nombre_archivo)
            
            try:
                audio = MP3(ruta_completa, ID3=ID3)
                
                # Check si ya tiene letra
                if audio.tags.get('USLT::und'):
                    tqdm.write(f"-> {Fore.BLUE}OMITIDO (Tiene letra):{Style.RESET_ALL} {nombre_archivo}")
                    pbar.update(1) 
                    continue
                    
                artista = audio.tags.get('TPE1', [''])[0]
                titulo = audio.tags.get('TIT2', [''])[0]

                # Mover si faltan tags básicos
                if not artista or not titulo:
                    tqdm.write(f"-> {Fore.YELLOW}TAGS INCOMPLETOS:{Style.RESET_ALL} {nombre_archivo}")
                    try:
                        shutil.move(ruta_completa, os.path.join(carpeta_sin_letras, nombre_archivo))
                        tqdm.write(f"   {Fore.CYAN}MOVIDO -> 'sin letras/'{Style.RESET_ALL}")
                    except Exception as e: pass
                    pbar.update(1)
                    continue

                time.sleep(0.5) # Pequeña pausa para no saturar API
                
                # Buscar en API
                params = {'track_name': titulo, 'artist_name': artista}
                try:
                    response = requests.get('https://lrclib.net/api/search', params=params, timeout=10)
                except requests.RequestException:
                    tqdm.write(f"-> {Fore.RED}ERROR DE RED:{Style.RESET_ALL} {titulo}")
                    pbar.update(1)
                    continue

                data = response.json()
                
                # Procesar respuesta
                letras_encontradas = None
                if data:
                    for cancion in data:
                        if cancion.get('syncedLyrics'):
                            letras_encontradas = cancion['syncedLyrics']
                            break
                
                # Si no hay letras o no hay resultados
                if not letras_encontradas:
                    tqdm.write(f"-> {Fore.RED}NO ENCONTRADO:{Style.RESET_ALL} {artista} - {titulo}")
                    try:
                        shutil.move(ruta_completa, os.path.join(carpeta_sin_letras, nombre_archivo))
                        tqdm.write(f"   {Fore.CYAN}MOVIDO -> 'sin letras/'{Style.RESET_ALL}")
                    except Exception as e: pass
                    pbar.update(1)
                    continue

                # Guardar
                audio.tags.add(USLT(encoding=3, lang='und', desc='Lyrics', text=letras_encontradas))
                audio.save()
                tqdm.write(f"-> {Fore.GREEN}¡ÉXITO!{Style.RESET_ALL} Letras añadidas a: {titulo}")

            except Exception as e:
                tqdm.write(f"-> {Fore.RED}ERROR FATAL:{Style.RESET_ALL} {e}")
            
            pbar.update(1)
    
    print(f"\n{Fore.GREEN}Proceso de letras finalizado.{Style.RESET_ALL}")
    return True # Devolvemos True para la opción combinada

def opcion_combinada(carpeta_ruta):
    """Ejecuta las opciones de renombrado y letras secuencialmente."""
    print(f"\n{Fore.YELLOW}--- INICIANDO PROCESO COMBINADO (Renombrar + Letras) ---{Style.RESET_ALL}")
    
    # 1. Renombrar
    if opcion_renombrar(carpeta_ruta):
        print(f"\n{Fore.YELLOW}*** RENOMBRADO COMPLETADO. CONTINUANDO CON LETRAS... ***{Style.RESET_ALL}")
    
    # 2. Incrustar Letras (se beneficia de los nombres ya corregidos)
    opcion_letras(carpeta_ruta)
    
    input(f"{Style.DIM}\nPresiona ENTER para volver al menú...{Style.RESET_ALL}")

# --- 3. MENÚ PRINCIPAL ---

def mostrar_logo():
    # El estilo de fondo y texto: solo Cian Brillante.
    style = f"{Fore.CYAN}{Style.BRIGHT}"

    # Se usa una única cadena para todo el banner.
    logo = f"""
{style}  ███████╗ ██████╗ ███╗   ██╗██╗ ██████╗ 
{style}  ██╔════╝██╔═══██╗████╗  ██║██║██╔════╝ 
{style}  ███████╗██║   ██║██╔██╗ ██║██║██║      
{style}  ╚════██║██║   ██║██║╚██╗██║██║██║      
{style}  ███████║╚██████╔╝██║ ╚████║██║╚██████╗ 
{style}  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝ 
                                             
{style}  ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
{style}  ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
{style}  █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
{style}  ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
{style}  ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
{style}  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
{style}
{style}--- Tu navaja suiza para archivos MP3 ---{Style.RESET_ALL}
    """
    print(logo)

def main():
    while True:
        # Limpiar consola (compatible con Windows y Linux/Mac)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        mostrar_logo()
        
        print(f"{Fore.WHITE}Selecciona una opción:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Renombrar {Style.DIM}(Artista - Título.mp3){Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}[2]{Style.RESET_ALL} Incrustar Letras {Style.DIM}(Busca letras LRC y las guarda){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[3]{Style.RESET_ALL} PROCESO COMPLETO {Style.DIM}(1 + 2 en secuencia){Style.RESET_ALL}")
        
        opcion = input(f"\n{Fore.CYAN}>> Opción: {Style.RESET_ALL}").strip()
        
        if opcion == '1':
            ruta = obtener_ruta()
            if ruta:
                opcion_renombrar(ruta)
                input(f"{Style.DIM}\nPresiona ENTER para volver al menú...{Style.RESET_ALL}")
        elif opcion == '2':
            ruta = obtener_ruta()
            if ruta:
                opcion_letras(ruta)
                input(f"{Style.DIM}\nPresiona ENTER para volver al menú...{Style.RESET_ALL}")
        elif opcion == '3':
            ruta = obtener_ruta()
            if ruta:
                opcion_combinada(ruta)
        else:
            input(f"{Fore.RED}Opción no válida. Presiona ENTER.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}Programa finalizado por el usuario (KeyboardInterrupt). ¡Gracias por usar Sonic Forge!{Style.RESET_ALL}")
        sys.exit()
