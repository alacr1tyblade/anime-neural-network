import requests
import csv
import pandas as pd
from bs4 import BeautifulSoup

def clean_html(raw_text):
    if not raw_text:
        return ''
    soup = BeautifulSoup(raw_text, 'html.parser')
    clean_text = soup.get_text(separator=' ')
    return ' '.join(clean_text.split())

url = "https://graphql.anilist.co"
query = """
{
  Page(page: 1, perPage: 50) {
    media(type: ANIME, sort: POPULARITY_DESC) {
      id
      title { english }
      description
      genres
    }
  }
}
"""
response = requests.post(url, json={'query': query})
data = response.json()
anime_list = data['data']['Page']['media']

with open('./dataset/anime_data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'title', 'genres', 'description'])
    
    for anime in anime_list:
        writer.writerow([
            anime['id'],
            anime['title']['english'],
            ', '.join(anime['genres']),
            clean_html(anime.get('description', '')) 
        ])
        
df = pd.read_csv('./dataset/anime_data.csv', encoding='utf-8')

first_row = df.iloc[0]
print(f"Название: {first_row['title']}")
print(f"Жанры: {first_row['genres']}")
print(f"Описание: {first_row['description']}")