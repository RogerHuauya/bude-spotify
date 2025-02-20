import csv
import os
import requests

from django.core.management.base import BaseCommand
from inverted_index.models import Song
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Load songs from a CSV file into the database'

    def handle(self, *args, **kwargs):
        csv_file = 'spotify_songs.csv'
        batch_size = 100

        songs_to_create = []
        songs_to_update = []

        # check if csv exist else download from url
        if not os.path.exists(csv_file):
            print("Downloading CSV file")
            url = "https://storage.googleapis.com/rogers-bucket/spotify_songs.csv"
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))

            with open(csv_file, 'wb') as f:
                for data in tqdm(response.iter_content(1024), total=total_size//1024, unit='KB'):
                    f.write(data)

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            existing_songs = {song.track_id: song for song in
                              Song.objects.all()}
            for row in reader:
                song_data = {
                    'track_id': row['track_id'],
                    'track_name': row['track_name'],
                    'track_artist': row['track_artist'],
                    'lyrics': row['lyrics']
                }
                if row['track_id'] in existing_songs:
                    existing_song = existing_songs[row['track_id']]
                    existing_song.track_name = song_data['track_name']
                    existing_song.track_artist = song_data['track_artist']
                    existing_song.lyrics = song_data['lyrics']
                    songs_to_update.append(existing_song)
                else:
                    songs_to_create.append(Song(**song_data))

                if len(songs_to_create) >= batch_size:
                    Song.objects.bulk_create(songs_to_create,
                                             batch_size=batch_size)
                    songs_to_create = []

                if len(songs_to_update) >= batch_size:
                    Song.objects.bulk_update(songs_to_update,
                                             ['track_name', 'track_artist',
                                              'lyrics'], batch_size=batch_size)
                    songs_to_update = []

        # Create or update any remaining songs
        if songs_to_create:
            Song.objects.bulk_create(songs_to_create, batch_size=batch_size)
        if songs_to_update:
            Song.objects.bulk_update(songs_to_update,
                                     ['track_name', 'track_artist', 'lyrics'],
                                     batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS('Successfully loaded songs from CSV'))
