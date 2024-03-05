from nba_api.stats.endpoints import playergamelogs, leaguegamelog, teamgamelogs
import pandas as pd
import streamlit as st
import sqlite3
from pathlib import Path
import plotly.figure_factory as ff
import plotly.express as px
import time



def season_to_string(x):
    return str(x) + "-" + str(x+1)[-2:]

def get_player_gamelogs(start_season, end_season):

    df_holder = []
    for s in range(start_season, end_season+1):
        if s >= 2019:
            season_types = ['Regular Season', 'PlayIn', 'Playoffs']
        else:
            season_types = ['Regular Season', 'Playoffs']        
        for season_type in season_types:
            season = season_to_string(s)
            df = playergamelogs.PlayerGameLogs(season_nullable=season, season_type_nullable=season_type).get_data_frames()[0]
            df_holder.append(df)
        
        time.sleep(2)
            
    player_gls = pd.concat(df_holder)
    return player_gls


if __name__ == '__main__':
    path = Path().cwd().joinpath('nba_player.db')
    table_name = "player_gamelogs"
    con = sqlite3.connect(path)
    start_season = 2000
    end_season = 2023
    df = get_player_gamelogs(start_season, end_season)
    
    df.to_sql(table_name, con=con)
    con.close()