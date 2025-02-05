import requests
from bs4 import BeautifulSoup
import json
import re
from config import BASE_URL

def fetch_anime_list(url):
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": "No se pudo obtener la información"}

    soup = BeautifulSoup(response.content, 'html.parser')
    anime_elements = soup.select('.Anime.alt.B')

    animes = []
    for anime in anime_elements:
        title = anime.select_one('h3.Title').text
        link = BASE_URL + anime.select_one('a')['href']
        poster = anime.select_one('figure img')['src']
        anime_type = anime.select_one('.Type').text if anime.select_one('.Type') else "Desconocido"

        if poster.startswith('/'):
            poster = BASE_URL + poster

        animes.append({
            "title": title,
            "link": link,
            "poster": poster,
            "type": anime_type
        })

    return animes

def fetch_anime_details(url, content_type):
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": "No se pudo obtener la información"}

    soup = BeautifulSoup(response.content, 'html.parser')

    title_alt = [alt.text for alt in soup.select('.TxtAlt')]
    description = soup.select_one('.Description p').text if soup.select_one('.Description p') else "No disponible"
    genres = [genre.text for genre in soup.select('.Nvgnrs a')]
    status = soup.select_one('.AnmStts span').text if soup.select_one('.AnmStts span') else "Desconocido"
    followers = soup.select_one('.WdgtCn .Title span').text if soup.select_one('.WdgtCn .Title span') else "0"
    rating = soup.select_one('#votes_prmd').text if soup.select_one('#votes_prmd') else "0.0"
    votes = soup.select_one('#votes_nmbr').text if soup.select_one('#votes_nmbr') else "0"

    next_episode_date = fetch_next_episode_date(soup) if "En emision" in status else "No disponible"

    episodes, download_links = fetch_episodes_and_downloads(soup, url, content_type)

    return {
        "title_alt": title_alt,
        "description": description,
        "genres": genres,
        "status": status,
        "type": content_type,
        "followers": followers,
        "rating": rating,
        "votes": votes,
        "next_episode_date": next_episode_date,
        "episodes": episodes,
        "download_links": download_links
    }

def fetch_next_episode_date(soup):
    """ Extrae la fecha del próximo episodio si está disponible en la variable anime_info """
    anime_info_script = soup.find('script', text=lambda t: t and 'var anime_info' in t)
    if anime_info_script:
        match = re.search(r'var anime_info = (\[.*?\]);', anime_info_script.string, re.DOTALL)
        if match:
            anime_info_data = json.loads(match.group(1))
            if len(anime_info_data) >= 4 and re.match(r'\d{4}-\d{2}-\d{2}', anime_info_data[3]):
                return anime_info_data[3]  # Devuelve la fecha del próximo episodio

    return "No disponible"

def fetch_episodes_and_downloads(soup, url, content_type):
    episodes = []
    download_links = []

    script = soup.find('script', text=lambda t: t and 'var episodes' in t)
    if script:
        match = re.search(r'var episodes = (\[.*?\]);', script.string, re.DOTALL)
        if match:
            episodes_data = json.loads(match.group(1))

            if content_type.lower() in ["anime", "ova"]:  # OVA también tiene varios episodios
                for ep in episodes_data:
                    episode_number = ep[0]
                    episode_id = ep[1]
                    episode_url = f"{BASE_URL}/ver/{url.split('/')[-1]}-{episode_number}"
                    episode_image, episode_download_links = fetch_episode_details(episode_url)
                    
                    episodes.append({
                        "episode": episode_number,
                        "id": episode_id,
                        "image": episode_image,
                        "download_links": episode_download_links
                    })

            elif content_type.lower() == "película" and episodes_data:
                episode_number = episodes_data[0][0]
                episode_id = episodes_data[0][1]
                episode_url = f"{BASE_URL}/ver/{url.split('/')[-1]}-{episode_number}"
                episode_image, episode_download_links = fetch_episode_details(episode_url)

                episodes.append({
                    "episode": episode_number,
                    "id": episode_id,
                    "image": episode_image,
                    "download_links": episode_download_links
                })

    return episodes, download_links

def fetch_episode_details(episode_url):
    """ Obtiene la imagen y enlaces de descarga de un episodio o película """
    response = requests.get(episode_url)
    if response.status_code != 200:
        return "", []

    soup = BeautifulSoup(response.content, 'html.parser')
    episode_image = soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image') else ""

    episode_download_links = []

    # Extraer enlaces desde la tabla HTML
    download_table = soup.select('.DwsldCnTbl tbody tr')
    if download_table:
        for row in download_table:
            columns = row.select('td')
            if len(columns) == 4:
                server = columns[0].text.strip()
                format_ = columns[1].text.strip()
                language = columns[2].text.strip()
                link = columns[3].select_one('a')['href'] if columns[3].select_one('a') else ""

                episode_download_links.append({
                    "server": server,
                    "format": format_,
                    "language": language,
                    "url": link
                })

    # Extraer enlaces desde la variable JavaScript "videos"
    script = soup.find("script", text=lambda t: t and "var videos" in t)
    if script:
        match = re.search(r'var videos = (\{.*?\});', script.string, re.DOTALL)
        if match:
            videos_data = json.loads(match.group(1))
            for quality, links in videos_data.items():
                for video in links:
                    if "url" in video:
                        episode_download_links.append({
                            "server": video.get("server", "Desconocido"),
                            "format": "MP4",
                            "language": "SUB",
                            "url": video["url"]
                        })

    return episode_image, episode_download_links

