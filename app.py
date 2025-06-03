import os
from flask import Flask, session, redirect, url_for, request, render_template, jsonify, send_from_directory
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.exceptions import SpotifyException
import random
import time

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

def get_token(): #top
    token_info = session.get('token_info', None)
    if token_info:
        if token_info['expires_at'] - int(time.time()) < 60:
            sp_oauth = create_spotify_oauth()
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
    return token_info

@app.route('/')
def index():
    if 'token_info' in session:
        access_token = session['token_info']['access_token']
        return render_template('index.html', access_token=access_token)
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

@app.route('/resume_playback', methods=['PUT'])
def resume_playback():
    token_info = get_token()
    if not token_info:
        return jsonify({'error': 'No access token found'}), 401
    

    access_token = token_info['access_token']
    sp = Spotify(auth=access_token)
    device_id = request.args.get('device_id')
    try:
        if device_id:
            sp.start_playback(device_id=device_id)
        else:
            sp.start_playback()
        return jsonify({'status': 'resumed'})
    
    except Exception as e:
        return jsonify({'error': 'Failed to resume playback', 'details': str(e)}), 500



@app.route('/pause_playback', methods=['PUT'])
def pause_playback():
    access_token = session.get('token_info', {}).get('access_token')
    if not access_token:
        return jsonify({'error': 'No access token available'}), 401

    sp = Spotify(auth=access_token)
    try:
        sp.pause_playback()
        return jsonify({'status': 'paused'})
    except SpotifyException as e:
        return jsonify({'error': 'Failed to pause playback', 'details': str(e)}), 400


@app.route('/play_random/<playlist_id>')
def play_random(playlist_id):
    sp = Spotify(auth=session['token_info']['access_token'])
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    random_track = random.choice(tracks)['track']
    return jsonify({
        'track_uri': random_track['uri'],
        'name': random_track['name'],
        'album_image': random_track['album']['images'][0]['url']
    })

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
    'favicon.ico', mimetype='image/vnd.microsoft.icon')




if __name__ == '__main__':
    app.run(port=5000, debug=True)

