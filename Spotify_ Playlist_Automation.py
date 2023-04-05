"""
Spotify Playlist Automation 0.9.2

Spotify Playlist Automation is  little app/script to automat updating of a Spotify playlist.
A .csv is used as the Input to check when to add a new track to the playlist. Look up all the Spotify Track IDs and create a Spotify playlist with those IDs.
Automaticly remove old songs to prevent filling up the playlist to its maximum.

Author: Johannes Schnurrenberger 
Last Change 31.03.2023
"""


# Imports

import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from datetime import datetime
import time
import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import sys

# Logging

logfilehandler = TimedRotatingFileHandler(
    filename='runtime.log', # Path to logfile
    when='D',
    interval=1,
    backupCount=7,
    encoding='latin1',
    delay=False)

logging.basicConfig(
    level=logging.INFO, # Loglevels to choose from: DEBUG, INFO, WARNING, ERROR, CRITICAL
    handlers=[
        logfilehandler,
        logging.StreamHandler(sys.stdout)],
    format='%(asctime)s %(message)s',
        )


# Modules

def read_config(path_to_file):
    ''' 
    Reads the configuration file

    Parameters:
    __________
    Full path to file as a string

    Returns:
    All Variables deffined in the config file
    All fields in the config file must be filled
    All variables are returned as strings even if it is a numerical value
    '''
    
    logging.info("Loading config")
    if type(path_to_file) == str: 
        try:
            config = configparser.ConfigParser()
            config.read(path_to_file)

            username = config['Spotify']['username']
            sci = config['Spotify']['sci']
            scs = config['Spotify']['scs']
            uri = config['Spotify']['uri']
            playlist_id = config['Spotify']['playlist_id']
            csv = config['File']['csv']

        except FileNotFoundError as err:
            logging.ERROR(err)
            time.sleep(15)
    else:
        raise TypeError('path to file must be of type string')

    logging.debug(username, sci, scs, uri, playlist_id, csv)
    return username, sci, scs, uri, playlist_id, csv


def check_csv(path_to_file):
    '''
    Gets the time when the a file was last modify

    Parameters:
	__________
	path_to_file: Full path to file on local server as a string
	
	Returns:
    Last time the file was modified
    '''
    
    if type(path_to_file) == str: 
        logging.debug('{}: Checking {} for changes'.format(check_csv.__name__, path_to_file))
    else:
        raise TypeError('path to file must be of type string')

    logging.debug('Last change: {}'.format(datetime.fromtimestamp(os.path.getmtime(path_to_file))))
    return os.path.getmtime(path_to_file)


def read_dbc_export(path_to_file) -> str:
    '''
    Reads a csv file on a local server and extracts the data in a pandas dataframe

    Parameters:
	__________
    path_to_file: Full path to file on local server as a string

    Returns:
    A Pandas Dataframe
    '''
   
    if type(path_to_file) == str: 
        logging.info('{}: Reading input csv'.format(read_dbc_export.__name__))
        data = pd.read_csv(path_to_file, delimiter=';', header=None, encoding='latin1')
        data.columns = ['artist', 'title']
        logging.debug('{}: Data \n {}'.format(read_dbc_export.__name__, data))
    else:
        raise TypeError('path to file must be of type string')
    return data


def add_track_to_playlist(username, sci, scs, uri, playlist_id, songs_played) -> None:
    '''
    Takes two Strings (Artist, Title) and searches the Spotify Track ID via the Spotify API.
    Then Adds those Track IDs to a Spotify Playlist at the beginning of the playlist
    
    Parameters:
	__________
    username: the spotify username
    sci: spotify client ID
    scs: spotify client Secret
    uir: spotify return URI necessary for SpotifyOAuth
    playlist_id: ID of the playlist to update (can be found in the browser URL when the Playlist is open)
    songs_played: a Pandas Dataframe contaning a series of Artist - Title combinations to add
    
    Returns:
    Nothing
    '''
    
    logging.info('{}: Starting playlist update'.format(add_track_to_playlist.__name__))
    logging.debug('Updating Playlist with these parameters {}, {}, {}, {}'.format(username, sci, playlist_id, uri))
    
    scope = 'playlist-modify-public' # TODO Change to 'playlist-modify-public' for production
    playlist = []

    # Get connection to Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(username=username, client_id=sci,scope=scope ,client_secret=scs ,redirect_uri=uri))

    # Search  Spotify and get the track IDs
    for index, row in songs_played.iterrows():

        # Loop through the pandas df and extrackt artist and track
        artist, title = row['artist'], row['title'] 
        # Search the Track ID on Spotify and limit the results to 1
        result = sp.search(q='{}+{}'.format(artist, title), type='track', limit=1)
        # Add the track ID to the playlist list for later use
        try:
            playlist.append(result['tracks']['items'][0]['id'])
        except IndexError as err:
            logging.warning('Appanding list did not work with {}'.format())
            logging.error(err)

        logging.info('Found Track ID {} for {} - {}'.format(result['tracks']['items'][0]['id'], artist, title))
        
    # This is neccasary for some reason it won't work when directly inputing the username
    user_id = sp.me()['id']
    
    # Add tracks to palylist
    try:
        sp.user_playlist_add_tracks(user_id, playlist_id, playlist, position=0)
        logging.info('Playlist update succesfull')
    except err:
        logging.warning(err)    


def remove_track_from_playlist(username, sci, scs, uri, playlist_id) -> None:
    '''
    Removes the last Track of the a given Sotify playist

    Parameters:
	__________
    username: the spotify username
    sci: spotify client ID
    scs: spotify client Secret
    uir: spotify return URI necessary for SpotifyOAuth
    playlist_id: ID of the playlist to update (can be found in the browser URL when the Playlist is open)
    
    Returns:
    None
    '''

    logging.info('{}: Removing tracks from Playlist'.format(remove_track_from_playlist.__name__))
    logging.debug('Removing Tracks with these parameters {}, {}, {}'.format(username, sci, playlist_id))
    
    scope = 'playlist-modify-public' # TODO Change to 'playlist-modify-public' for production

    # Get connection to Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(username=username, client_id=sci,scope=scope ,client_secret=scs ,redirect_uri=uri))

    # Get all playlist tracks
    playlist_tracks = []
    results = sp.user_playlist_tracks(username,playlist_id)
    playlist_tracks = results['items']
    while results['next']:
        results = sp.next(results)
        playlist_tracks.extend(results['items'])

    # Get number of songs in playlist
    num_tracks = len(playlist_tracks)
    logging.info('{} tracks are in the playlist'.format(num_tracks))
    
    # Do nothing if playlist is less then 100 songs long
    if num_tracks <= 100:
        return

    # Get IDs of the last 100 Songs
    last_100_track_ids = []
    for i in range(100):
        last_100_track_ids.append(playlist_tracks[i]['track']['id'])

    # Delete all tracks besides the last 100
    for i in range(num_tracks - 101, -1, -1):
        if playlist_tracks[i]['track']['id'] not in last_100_track_ids:
            logging.info('{}: Removing tracks with Track ID {}'.format(remove_track_from_playlist.__name__, playlist_tracks[i]['track']['id']))
            sp.playlist_remove_all_occurrences_of_items(playlist_id, [playlist_tracks[i]['track']['id']])


def main():

    logging.info('Script startet')

    # Declare Variables
    username, sci, scs, uri, playlist_id, csv = read_config('./config.ini')
    
    while True:
        
        last_time_modified = check_csv(csv)
        time.sleep(1)

        # Check if the input csv has been changed
        if last_time_modified != check_csv(csv):

            logging.info('{}: {} has been changed.'.format(main.__name__, csv))

            # Read in the file with the broadcasted playlist
            try:
                songs_played = read_dbc_export(csv)
            except PermissionError as err:
                logging.warning('Cannot open file \n{}'.format(err))

            # Remove the last song from the playlist to make space
            try:
                remove_track_from_playlist(username, sci, scs, uri, playlist_id)
            except Exception as err:
                logging.warning(err)     

            # Add all tracks that were played to the playlist
            try:
                add_track_to_playlist(username, sci, scs, uri, playlist_id, songs_played)
            except Exception as err:
                logging.warning(err)            

        else:
            continue
            
            
if __name__ == "__main__":
    main()
   
