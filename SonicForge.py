import os
import sys
import subprocess
import importlib.util
import time
import shutil
import re
from io import BytesIO

# --- 1. GESTIÓN DE DEPENDENCIAS Y COLORES ---
# Mapeo: Nombre en PIP -> Nombre del Módulo en Python
DEPENDENCIAS = {
    'mutagen': 'mutagen',
    'requests': 'requests',
    'tqdm': 'tqdm',
    'colorama': 'colorama',
    'yt-dlp': 'yt_dlp'
}

AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.flac', '.ogg', '.wav') 

def verificar_e_instalar():
    """Verifica si los paquetes necesarios están instalados (sin usar colores aún)."""
    faltantes = []
    for paquete_pip, paquete_import in DEPENDENCIAS.items():
        if importlib.util.find_spec(paquete_import) is None:
            faltantes.append(paquete_pip)

    if not faltantes:
        return True

    print(f"Faltan paquetes necesarios: {', '.join(faltantes)}")
    print("Intentando instalar dependencias automáticamente...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *faltantes])
        print("\n¡Instalación completada! El script continuará.")
        return True 
    except subprocess.CalledProcessError as e:
        print("\nERROR: No se pudieron instalar los paquetes.")
        print(f"Detalles: {e}")
        return False
    except Exception as e:
        print(f"\nERROR inesperado durante la instalación: {e}")
        return False

# Verificar dependencias
if not verificar_e_instalar():
    sys.exit("Faltan dependencias críticas. Saliendo.")

# Importaciones seguras
try:
    import requests
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TPE1, TIT2, USLT, APIC
    from tqdm import tqdm
    from colorama import init, Fore, Back, Style
    import yt_dlp
except ImportError as e:
    print(f"\n[ERROR FATAL] Error importando librerías tras instalación: {e}")
    sys.exit(1)

# Inicializar colorama
init(autoreset=True)

# --- 2. FUNCIONES AUXILIARES ---

def obtener_ruta():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"\n{Fore.CYAN}--- SELECCIÓN DE CARPETA ---{Style.RESET_ALL}")
    print("Ingresa la ruta de la carpeta de música.")
    print(f"{Style.DIM}(Enter = Ruta del script: {script_dir}){Style.RESET_ALL}")
    
    ruta_input = input(f"{Fore.YELLOW}>> Ruta: {Style.RESET_ALL}").strip()
    
    if not ruta_input:
        ruta = script_dir
        print(f"{Fore.YELLOW}Usando ruta predeterminada: {ruta}{Style.RESET_ALL}")
    else:
        ruta = ruta_input.replace('"', '').replace("'", "")

    if os.path.exists(ruta):
        return ruta
    else:
        print(f"{Fore.RED}¡Error! La ruta no existe.{Style.RESET_ALL}")
        return None

def limpiar_string_basura(texto):
    """Elimina texto basura común de títulos de YouTube."""
    patrones = [
        r'\(official video\)', r'\(official audio\)', r'\(video\)', r'\(audio\)',
        r'\[official video\]', r'\[official audio\]', r'\[video\]', r'\[audio\]',
        r'\(lyrics\)', r'\[lyrics\]', r'\(letra\)', r'\[letra\]',
        r'\(videoclip\)', r'official video', r'official audio'
    ]
    
    texto_limpio = texto
    for patron in patrones:
        texto_limpio = re.sub(patron, '', texto_limpio, flags=re.IGNORECASE)
    
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    return texto_limpio

def limpiar_nombre(texto):
    """Limpia caracteres inválidos para sistema de archivos."""
    caracteres_no_validos = '/\\:*?"<>|'
    for char in caracteres_no_validos:
        texto = texto.replace(char, '')
    return texto

# --- 3. FUNCIONES PRINCIPALES ---

def obtener_url_imagen(artista, titulo):
    """Busca una URL de imagen de álbum usando Deezer API."""
    try:
        # Usamos la API de Deezer para obtener el track_id y luego el album cover
        search_url = f"https://api.deezer.com/search?q=artist:\"{artista}\" track:\"{titulo}\""
        response = requests.get(search_url, timeout=5).json()
        
        if response and response.get('data'):
            # El primer resultado suele ser el más relevante
            track = response['data'][0]
            # Devolvemos la imagen de mayor calidad disponible (xl)
            return track['album']['cover_xl']
    except Exception:
        return None
    return None

def opcion_convertir(carpeta_ruta):
    print(f"\n{Fore.YELLOW}=== [1] CONVERSIÓN A MP3 ==={Style.RESET_ALL}")
    archivos_a_convertir = [f for f in os.listdir(carpeta_ruta) if f.lower().endswith(AUDIO_EXTENSIONS) and not f.lower().endswith('.mp3')]

    if not archivos_a_convertir:
        print(f"{Fore.GREEN}No hay archivos para convertir.{Style.RESET_ALL}")
        return True
    
    cont_exito = 0
    for nombre_archivo in tqdm(archivos_a_convertir, desc="Convirtiendo", unit="file", colour="yellow"):
        ruta_entrada = os.path.join(carpeta_ruta, nombre_archivo)
        nombre_base, _ = os.path.splitext(nombre_archivo)
        ruta_salida = os.path.join(carpeta_ruta, f"{nombre_base}.mp3")

        comando = ['ffmpeg', '-i', ruta_entrada, '-vn', '-c:a', 'libmp3lame', '-b:a', '320k', '-y', ruta_salida]
        try:
            subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(ruta_entrada)
            cont_exito += 1
        except:
            tqdm.write(f"{Fore.RED}✘ Error convirtiendo:{Style.RESET_ALL} {nombre_archivo}")

    print(f"\n{Fore.YELLOW}Convertidos: {cont_exito}{Style.RESET_ALL}")
    return True

def opcion_renombrar(carpeta_ruta):
    print(f"\n{Fore.GREEN}=== [2] RENOMBRANDO ARCHIVOS ==={Style.RESET_ALL}")
    archivos = [f for f in os.listdir(carpeta_ruta) if f.lower().endswith('.mp3')]
    
    if not archivos: 
        print(f"{Fore.YELLOW}No se encontraron archivos MP3.{Style.RESET_ALL}")
        return False

    cont_exito = 0
    for nombre_archivo in tqdm(archivos, desc="Renombrando", unit="track", colour="green"):
        ruta_antigua = os.path.join(carpeta_ruta, nombre_archivo)
        try:
            audio = MP3(ruta_antigua, ID3=ID3)
            audio.tags.load(ruta_antigua)
            
            artista = audio.tags.get('TPE1', ['Artista Desconocido'])[0]
            titulo = audio.tags.get('TIT2', ['Título Desconocido'])[0]

            nuevo_nombre = f"{limpiar_nombre(artista)} - {limpiar_nombre(titulo)}.mp3"
            ruta_nueva = os.path.join(carpeta_ruta, nuevo_nombre)
            
            if ruta_antigua != ruta_nueva and not os.path.exists(ruta_nueva):
                os.rename(ruta_antigua, ruta_nueva)
                cont_exito += 1
        except: pass
    
    print(f"\n{Fore.GREEN}Renombrados: {cont_exito}{Style.RESET_ALL}")
    return True 

def opcion_letras(carpeta_ruta):
    print(f"\n{Fore.MAGENTA}=== [3] INCRUSTANDO LETRAS ==={Style.RESET_ALL}")
    try:
        archivos = [f for f in os.listdir(carpeta_ruta) if f.lower().endswith('.mp3')]
    except: return

    carpeta_sin_letras = os.path.join(carpeta_ruta, "sin letras")
    if not os.path.exists(carpeta_sin_letras): os.makedirs(carpeta_sin_letras)

    for nombre_archivo in tqdm(archivos, desc="Procesando", unit="track", colour="magenta"):
        ruta = os.path.join(carpeta_ruta, nombre_archivo)
        try:
            audio = MP3(ruta, ID3=ID3)
            # Revisa si la letra ya existe
            if audio.tags.get('USLT::und'): continue
            
            artista = str(audio.tags.get('TPE1', [''])[0])
            titulo = str(audio.tags.get('TIT2', [''])[0])
            
            if not artista or not titulo: continue

            time.sleep(0.3)
            res = requests.get('https://lrclib.net/api/search', params={'track_name': titulo, 'artist_name': artista}, timeout=5).json()
            
            letra = None
            if res:
                for t in res:
                    if t.get('syncedLyrics'):
                        letra = t['syncedLyrics']
                        break
            
            if letra:
                audio.tags.add(USLT(encoding=3, lang='und', desc='Lyrics', text=letra))
                audio.save()
        except Exception as e:
            tqdm.write(f"{Fore.RED}✘ Error letra en {nombre_archivo}: {e}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}Letras finalizadas.{Style.RESET_ALL}")
    return True

def opcion_incrustar_imagen(carpeta_ruta):
    print(f"\n{Fore.CYAN}=== [4] INCRUSTANDO CARÁTULAS ==={Style.RESET_ALL}")
    archivos = [f for f in os.listdir(carpeta_ruta) if f.lower().endswith('.mp3')]

    if not archivos: 
        print(f"{Fore.YELLOW}No se encontraron archivos MP3.{Style.RESET_ALL}")
        return False

    cont_exito = 0
    cont_omitido = 0
    cont_error = 0

    for nombre_archivo in tqdm(archivos, desc="Procesando imágenes", unit="track", colour="cyan"):
        ruta = os.path.join(carpeta_ruta, nombre_archivo)
        
        try:
            audio = MP3(ruta, ID3=ID3)
            try: audio.add_tags()
            except: pass
            
            # Revisar si ya tiene carátula
            if audio.tags.get('APIC:'):
                cont_omitido += 1
                continue 

            artista = str(audio.tags.get('TPE1', [''])[0])
            titulo = str(audio.tags.get('TIT2', [''])[0])
            
            if not artista or not titulo:
                cont_error += 1
                continue

            time.sleep(0.3)
            imagen_url = obtener_url_imagen(artista, titulo)
            
            if imagen_url:
                imagen_data = requests.get(imagen_url, timeout=5).content
                mime_type = 'image/jpeg' if imagen_url.lower().endswith('.jpg') or imagen_url.lower().endswith('.jpeg') else 'image/png'
                
                # Incrustar la imagen
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3, # 3 es para Front Cover
                        desc='Cover',
                        data=imagen_data
                    )
                )
                audio.save()
                cont_exito += 1
            else:
                cont_error += 1
                
        except Exception:
            cont_error += 1
    
    print(f"\n{Fore.CYAN}Resumen Imágenes:{Style.RESET_ALL} {cont_exito} añadidas, {cont_omitido} omitidas, {cont_error} errores.")
    return True


def opcion_descargar_cancion(carpeta_ruta):
    print(f"\n{Fore.BLUE}=== [5] DESCARGA CANCIÓN ==={Style.RESET_ALL}")
    busqueda = input(f"{Fore.YELLOW}>> Artista y Título (o URL): {Style.RESET_ALL}").strip()
    if not busqueda: return

    print(f"\n{Fore.CYAN}Buscando, descargando y procesando...{Style.RESET_ALL}")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(carpeta_ruta, '%(title)s.%(ext)s'),
            'writethumbnail': True,
            'noplaylist': True,
            'default_search': 'ytsearch1',
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail'},
                {'key': 'FFmpegMetadata'},
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(busqueda, download=True)
            meta = info['entries'][0] if 'entries' in info else info
            
            nombre_original = meta['title']
            filename_generado = ydl.prepare_filename(meta)
            filename_mp3 = os.path.splitext(filename_generado)[0] + ".mp3"

        # --- POST-PROCESAMIENTO: LIMPIEZA Y TAGS ---
        if os.path.exists(filename_mp3):
            nombre_limpio = limpiar_string_basura(nombre_original)
            nombre_limpio = limpiar_nombre(nombre_limpio)
            ruta_final = os.path.join(carpeta_ruta, f"{nombre_limpio}.mp3")
            
            # Renombrar archivo físico
            if filename_mp3 != ruta_final:
                os.rename(filename_mp3, ruta_final)
                print(f"{Fore.GREEN}✔ Nombre limpiado:{Style.RESET_ALL} {os.path.basename(ruta_final)}")
            
            # Actualizar Tags ID3
            try:
                audio = MP3(ruta_final, ID3=ID3)
                try: audio.add_tags()
                except: pass
                
                if " - " in nombre_limpio:
                    partes = nombre_limpio.split(" - ")
                    artista_tag = partes[0].strip()
                    titulo_tag = " - ".join(partes[1:]).strip()
                else:
                    artista_tag = meta.get('uploader', 'Unknown')
                    titulo_tag = nombre_limpio
                
                audio.tags.add(TPE1(encoding=3, text=artista_tag))
                audio.tags.add(TIT2(encoding=3, text=titulo_tag))
                audio.save()
                print(f"{Fore.GREEN}✔ Tags actualizados:{Style.RESET_ALL} {artista_tag} - {titulo_tag}")
                print(f"{Fore.GREEN}✔ Carátula:{Style.RESET_ALL} Incrustada (Descargada de YouTube).")

            except Exception as e:
                print(f"{Fore.RED}⚠ Error actualizando tags:{Style.RESET_ALL} {e}")

        print(f"\n{Fore.GREEN}¡DESCARGA FINALIZADA!{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}ERROR DE DESCARGA:{Style.RESET_ALL} {e}")

    input(f"{Style.DIM}\nPresiona ENTER para volver al menú...{Style.RESET_ALL}")

def opcion_accion_combinada(carpeta_ruta):
    """Permite al usuario seleccionar múltiples acciones a ejecutar en secuencia."""
    OPCIONES_DISPONIBLES = {
        '1': ("CONVERTIR a MP3", opcion_convertir),
        '2': ("Renombrar (Artista - Título)", opcion_renombrar),
        '3': ("Incrustar Letras", opcion_letras),
        '4': ("Incrustar Carátulas", opcion_incrustar_imagen),
    }

    print(f"\n{Fore.YELLOW}=== [6] ACCIÓN COMBINADA ==={Style.RESET_ALL}")
    print(f"Directorio de trabajo: {Fore.CYAN}{carpeta_ruta}{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}Selecciona las acciones a ejecutar (separadas por comas, ej: 1, 3):{Style.RESET_ALL}")
    
    for key, (nombre, _) in OPCIONES_DISPONIBLES.items():
        print(f"  {Fore.YELLOW}[{key}]{Style.RESET_ALL} {nombre}")

    seleccion_input = input(f"\n{Fore.CYAN}>> Selecciones: {Style.RESET_ALL}").strip()
    
    if not seleccion_input:
        print(f"{Fore.RED}Selección cancelada.{Style.RESET_ALL}")
        return

    # Validar y ordenar las selecciones
    selecciones = [s.strip() for s in seleccion_input.split(',')]
    acciones_a_ejecutar = []

    for sel in sorted(selecciones):
        if sel in OPCIONES_DISPONIBLES:
            acciones_a_ejecutar.append(OPCIONES_DISPONIBLES[sel])
        else:
            print(f"{Fore.RED}Advertencia:{Style.RESET_ALL} Opción '{sel}' no válida y será ignorada.")
    
    if not acciones_a_ejecutar:
        print(f"{Fore.RED}No hay acciones válidas para ejecutar.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.YELLOW}--- Iniciando secuencia de acciones ({len(acciones_a_ejecutar)}) ---{Style.RESET_ALL}")
    for nombre, funcion in acciones_a_ejecutar:
        print(f"\n{Fore.CYAN}*** EJECUTANDO: {nombre} ***{Style.RESET_ALL}")
        funcion(carpeta_ruta)
        
    print(f"\n{Fore.GREEN}--- SECUENCIA COMBINADA FINALIZADA ---{Style.RESET_ALL}")
    input(f"{Style.DIM}\nPresiona ENTER para volver al menú...{Style.RESET_ALL}")


# --- 4. INTERFAZ ---

def mostrar_logo():
    style = f"{Fore.CYAN}{Style.BRIGHT}"
    logo = f"""
{style}  ███████╗ ██████╗ ███╗   ██╗██╗ ██████╗ 
{style}  ██╔════╝██╔═══██╗████╗  ██║██║██╔════╝ 
{style}  ███████╗██║   ██║██╔██╗ ██║██║██║      
{style}  ╚════██║██║   ██║██║╚██╗██║██║██║      
{style}  ███████║╚██████╔╝██║ ╚████║██║╚██████╗ 
{style}  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚══════╝ 
                                             
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
        os.system('cls' if os.name == 'nt' else 'clear')
        mostrar_logo()
        
        print(f"{Fore.WHITE}Selecciona una opción:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[1]{Style.RESET_ALL} CONVERTIR a MP3 {Style.DIM}(M4A, FLAC, OGG, WAV -> MP3){Style.RESET_ALL}")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Renombrar {Style.DIM}(Artista - Título.mp3){Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}[3]{Style.RESET_ALL} Incrustar Letras {Style.DIM}(Busca letras LRC){Style.RESET_ALL}")
        print(f"{Fore.CYAN}[4]{Style.RESET_ALL} Incrustar Carátulas {Style.DIM}(Busca imagen por metadatos){Style.RESET_ALL}")
        print(f"{Fore.BLUE}[5]{Style.RESET_ALL} DESCARGAR CANCIÓN {Style.DIM}(Descarga limpia + Cover + Tags){Style.RESET_ALL}")
        print(f"{Fore.RED}[6]{Style.RESET_ALL} ACCIÓN COMBINADA {Style.DIM}(Selecciona varias acciones en lote){Style.RESET_ALL}")
        
        opcion = input(f"\n{Fore.CYAN}>> Opción: {Style.RESET_ALL}").strip()
        
        ruta = None 
        if opcion in ('1', '2', '3', '4', '5', '6'):
            ruta = obtener_ruta()
            if not ruta: continue

        if opcion == '1': opcion_convertir(ruta); input(f"{Style.DIM}\nPresiona ENTER...{Style.RESET_ALL}")
        elif opcion == '2': opcion_renombrar(ruta); input(f"{Style.DIM}\nPresiona ENTER...{Style.RESET_ALL}")
        elif opcion == '3': opcion_letras(ruta); input(f"{Style.DIM}\nPresiona ENTER...{Style.RESET_ALL}")
        elif opcion == '4': opcion_incrustar_imagen(ruta); input(f"{Style.DIM}\nPresiona ENTER...{Style.RESET_ALL}")
        elif opcion == '5': opcion_descargar_cancion(ruta)
        elif opcion == '6': opcion_accion_combinada(ruta)
        else: input(f"{Fore.RED}Opción no válida. Presiona ENTER.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}¡Hasta la próxima! Keep rocking. 🎸{Style.RESET_ALL}")
        sys.exit()
