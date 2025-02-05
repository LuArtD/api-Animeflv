import requests
import sys

def fetch_and_save(url, output_file):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verifica errores HTTP
        
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(response.text)
        
        print(f"Contenido guardado exitosamente en {output_file}")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener los datos: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python save_anime_links.py <URL> <archivo_salida.html>")
    else:
        url = sys.argv[1]
        output_file = sys.argv[2]
        fetch_and_save(url, output_file)
