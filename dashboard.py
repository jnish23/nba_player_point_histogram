from nba_api.stats.endpoints import playergamelogs, leaguegamelog, teamgamelogs
import pandas as pd
import streamlit as st
import sqlite3
from pathlib import Path
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px
import time
from bokeh.plotting import figure, show
import numpy as np

current_season="2023-24"
st.set_page_config(page_title="NBA Player Point Distributions", layout="wide")

def load_data():
    db_path = Path.cwd().joinpath("nba_player.db")
    con = sqlite3.connect(db_path)
    df = pd.read_sql("""select SEASON_YEAR, PLAYER_NAME, GAME_DATE, PTS
                    from player_gamelogs
                    where SEASON_YEAR >= '2010-11'""", con)
    con.close()

    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    return df

df = load_data()


def filter_by_season(df, season):
    if season == 'All Seasons':
        df_filtered = df
    else:
        df_filtered = df[df["SEASON_YEAR"] == season]
    return df_filtered


# Sidebar for filters
st.sidebar.title("Filters")

season_select_box = list(df["SEASON_YEAR"].unique()) + ["All Seasons"]
selected_season = st.sidebar.selectbox("Season", season_select_box, index=len(season_select_box)-2)

@st.cache_data
def get_player_avg_pts(df):
    return df.groupby(['PLAYER_NAME'])['PTS'].mean().reset_index().sort_values('PTS', ascending=False)


df_seasons_filtered = filter_by_season(df=df, season=selected_season)
player_avg_pts = get_player_avg_pts(df_seasons_filtered)


selected_player_1 = st.sidebar.selectbox("Player 1", player_avg_pts["PLAYER_NAME"].unique())
selected_player_2 = st.sidebar.selectbox("Player 2", ['None'] + list(player_avg_pts["PLAYER_NAME"].unique()), index=0)
start_date = st.sidebar.date_input("Start Date", df.loc[df["SEASON_YEAR"]==selected_season, "GAME_DATE"].min())
end_date = st.sidebar.date_input("End Date", value="today")
bin_size = st.sidebar.slider("Bin Size", min_value=1, max_value=10, value=5, step=1)

# Filter data based on selections
@st.cache_data
def apply_filters(df, player, season, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    if season == 'All Seasons':
        df_filtered = df.loc[(df["PLAYER_NAME"] == player) 
                         & (df["GAME_DATE"] >= start_date) 
                         & (df["GAME_DATE"] <= end_date) ]
    else:
               
        df_filtered = df.loc[(df["PLAYER_NAME"] == player) 
                         & (df["SEASON_YEAR"] == season)
                         & (df["GAME_DATE"] >= start_date) 
                         & (df["GAME_DATE"] <= end_date)]
    return df_filtered


filtered_data_1 = apply_filters(df, selected_player_1, selected_season, start_date, end_date)

if selected_player_2 != 'None':
    filtered_data_2 = apply_filters(df, selected_player_2, selected_season, start_date, end_date)
    point_line = st.slider("Point Line", min_value = 0, max_value = max(filtered_data_1['PTS'].max(), filtered_data_2['PTS'].max())+bin_size, value=int(np.median(filtered_data_1['PTS'])), step=1)

else:
    filtered_data_2 = pd.DataFrame(columns=df.columns)
    point_line = st.slider("Point Line", min_value = 0, max_value = filtered_data_1['PTS'].max()+bin_size, value=int(np.median(filtered_data_1['PTS'])), step=1)


bins = list(range(0, max(filtered_data_1['PTS'].tolist()
                         + filtered_data_2['PTS'].tolist()) + bin_size+1, bin_size))

print("bins:", bins)

# Function to generate hover text for histogram bars

def get_hover_text(df, bins):
    counts, _ = np.histogram(df['PTS'], bins=bins)
    percentages = counts / df.shape[0] * 100
    hover_text = [f"{bin_start}-{bin_end}: {pct:.1f}% ({count})" for bin_start, bin_end, pct, count in zip(bins[:-1], bins[1:], percentages, counts) if pct!=0]
    return hover_text

# Display the histogram
def plot_histogram(data1, data2, bin_size, selected_player_1, selected_player_2):
    bins = list(range(0, max(data1['PTS'].max(), data2['PTS'].max() if not data2.empty else 0) + bin_size+1, bin_size))
    print(selected_player_1, bins)
    print(data1['PTS'].tolist())

    hover_text_1 = get_hover_text(data1, bins)
    hover_text_2 = get_hover_text(data2, bins) if not data2.empty else []

    
    fig = go.Figure()
    fig.add_trace(go.Histogram(name=selected_player_1
                               , x=data1['PTS']
                               , xbins=dict(start=bins[0], end=bins[-1], size=bin_size)
                               , hovertext=hover_text_1
                               , opacity=0.7))
    player_1_over_freq = np.sum(data1['PTS'] >= point_line)
    player_1_over_pct = np.mean(data1['PTS'] >= point_line) 
    fig.add_vline(x=point_line, line_dash='dash', line_color='firebrick')
    fig.add_annotation(x=point_line+10, y=13, 
                    text=f"{selected_player_1} scored at least {point_line} points...<br> {player_1_over_freq}/{data1.shape[0]} times ({player_1_over_pct:.1%})",
                    showarrow=False,
                    font=dict(size=16))
    
    if selected_player_2 != 'None':
        fig.add_trace(go.Histogram(name=selected_player_2
                                   , x=data2['PTS']
                                   , xbins=dict(start=bins[0], end=bins[-1], size=bin_size)
                                   , hovertext=hover_text_2
                                   , opacity=0.7))
        player_2_over_freq = np.sum(filtered_data_2['PTS'] >= point_line)
        player_2_over_pct = np.mean(filtered_data_2['PTS'] >= point_line)

        fig.add_annotation(x=point_line+10, y=9, 
                        text=f"{selected_player_2} scored at least {point_line} points...<br> {player_2_over_freq}/{data2.shape[0]} times ({player_2_over_pct:.1%})",
                        showarrow=False,
                        font=dict(size=16))
        
        fig.update_xaxes(range=[0, max(data1['PTS'].max(), data2['PTS'].max()) + bin_size])

    fig.update_layout(bargap=0.1, barmode='overlay', xaxis_title="Points", yaxis_title="Frequency", width=1600, height=500)
    fig.update_xaxes(dtick=bin_size  # Specify the spacing between tick marks
            ,tickvals=list(range(0, 100, bin_size))  # Specify the positions of the tick marks
            ,title_text = "Points"  
            ,range=[0, data1['PTS'].max() + bin_size]
            )
    fig.update_yaxes(title_text = "Frequency")

    fig.update_layout(bargap=0.06
                    , barmode='overlay'
                    , width = 1600
                    , height = 500
                    , legend = dict(yanchor='top',
                                    y=0.99,
                                    xanchor='left',
                                    x=0.01))
    
    st.plotly_chart(fig, use_container_width=True)
    return None

plot_histogram(filtered_data_1, filtered_data_2, bin_size, selected_player_1, selected_player_2)

player_1_median = np.median(filtered_data_1['PTS'])
player_2_median = np.median(filtered_data_2['PTS'])


if selected_player_2 != 'None':
    st.title(f"{selected_player_1} and {selected_player_2} Points Distribution")
    st.write(f"{selected_player_1} Total Games Played: {len(filtered_data_1)}, Median: {player_1_median}")
    st.write(f"{selected_player_2} Total Games Played: {len(filtered_data_2)}, Median: {player_2_median}")

else:
    st.title(f"{selected_player_1}'s Points Distribution")
    st.write(f"{selected_player_1} Total Games Played: {len(filtered_data_1)}, Median: {player_1_median}")
