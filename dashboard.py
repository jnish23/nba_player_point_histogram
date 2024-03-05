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

start = time.time()

db_path = Path.cwd().joinpath("nba_player.db")
con = sqlite3.connect(db_path)
df = pd.read_sql("""select SEASON_YEAR, PLAYER_NAME, GAME_DATE, PTS
                    from player_gamelogs
                    where SEASON_YEAR >= '2010-11'""", con)
con.close()

end = time.time()

print("pulling data from db time:", end-start)

start = time.time()

df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])

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
selected_player_2 = st.sidebar.selectbox("Player 2", player_avg_pts["PLAYER_NAME"].unique(), index=1)

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
filtered_data_2 = apply_filters(df, selected_player_2, selected_season, start_date, end_date)

# Display the histogram

bins = list(range(0, max(filtered_data_1['PTS'].tolist()
                         + filtered_data_2['PTS'].tolist()) + bin_size , bin_size))
print(bins)

def get_hover_text(df, bins):
    counts, bins = np.histogram(df['PTS'], bins=bins)
    percentages = counts / df.shape[0] * 100
    hover_text = [f"{bin_start}-{bin_end}: {pct:.1f}% ({count})" for bin_start, bin_end, pct, count in zip(bins[:-1], bins[1:], percentages, counts) if pct!=0]
    return hover_text

hover_text_1 = get_hover_text(filtered_data_1, bins)
hover_text_2 = get_hover_text(filtered_data_2, bins)

hist_1 = go.Histogram(
    name = f"{selected_player_1}",
    x = filtered_data_1['PTS'],
    xbins=dict(start=bins[0], end=bins[-1], size=bin_size),
    hovertext=hover_text_1,
    opacity=0.7
)

fig = go.Figure(data=[hist_1])

fig.add_trace(go.Histogram(
        name = f"{selected_player_2}",
        x = filtered_data_2['PTS'],
        # xbins=dict(start=bins[0], end=bins[-1], size=bin_size),
        hovertext=hover_text_2,
        opacity=0.7))



fig.add_vline(x=np.median(filtered_data_1['PTS']), line_dash='dash', line_color='firebrick')

fig.update_xaxes(
    dtick=bin_size,  # Specify the spacing between tick marks
    tickvals=list(range(0, 100, bin_size))  # Specify the positions of the tick marks
)

fig.update_layout(bargap=0.06)

st.plotly_chart(fig, use_container_width=True, theme="streamlit")

st.title(f"{selected_player_1} and {selected_player_2} Points Distribution")

# Additional information (optional)
st.write(f"{selected_player_1} Total Games Played: {len(filtered_data_1)}")
st.write(f"{selected_player_2} Total Games Played: {len(filtered_data_2)}")


end = time.time()
print("building_histogram time:", end-start)