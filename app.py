import os
from flask import Flask, session, redirect, url_for, request, render_template, jsonify, send_from_directory
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32)

client_id = '7518f6c967a34c8cb32a4a4047caf2c1'
client_secret = 'b1cdc53dc4ab476894845cc9597c538b'
redirect_uri = 'http://127.0.0.1:5000/callback'


scope = 'user-read-private, playlist-read-private, streaming, user-modify-playback-state, user-read-playback-state'


sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=FlaskSessionCacheHandler(session),
    show_dialog=True
)

@app.route('/')
def index():
    if 'token_info' in session:
        return render_template('index.html')
    return redirect('/login')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    token_info = sp_oauth.get_access_token(request.args['code'])
    session['token_info'] = token_info
    return redirect('/')

@app.route('/playlists')
def playlists():
    sp = Spotify(auth=session['token_info']['access_token'])
    results = sp.current_user_playlists()
    playlists = [{
        'name': p['name'],
        'id': p['id'],
        'image': p['images'][0]['url'] if p['images'] else ''
    } for p in results['items']]
    return jsonify(playlists)


@app.route('/resume_playback')
def resume_playback():
    sp = Spotify(auth=session['token_info']['access_token'])
    sp.start_playback()
    return jsonify({'status': 'resumed'})

@app.route('/current_song')
def current_song():
    sp = Spotify(auth=session['token_info']['access_token'])
    current = sp.current_playback()
    if current and current.get('item'):
        return jsonify({
            'name': current['item']['name'],
            'artists': [artist['name'] for artist in current['item']['artists']],
            'is_playing': current.get('is_playing', False)
        })
    return jsonify({'name': None, 'is_playing': False})


@app.route('/pause_playback')
def pause_playback():
    sp = Spotify(auth=session['token_info']['access_token'])
    sp.pause_playback()
    return jsonify({'status': 'paused'})



@app.route('/play_random/<playlist_id>')
def play_random(playlist_id):
    sp = Spotify(auth=session['token_info']['access_token'])
    tracks = sp.playlist_tracks(playlist_id)['items']
    track_uris = [item['track']['uri'] for item in tracks if item['track']]
    if track_uris:
        random_track = random.choice(track_uris)
        sp.start_playback(uris=[random_track])
        return jsonify({'status': 'playing', 'track_uri': random_track})
    return jsonify({'status': 'error', 'message': 'No tracks found'})

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
    'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(port=5000, debug=True)

