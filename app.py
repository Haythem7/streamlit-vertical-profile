import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import os

# Optional: Set your Mapbox token (you can get one for free from mapbox.com)
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoiaGdoYXJiaSIsImEiOiJjbWNicWdkb3owMDF6MmlzN2I3anB5Z2dlIn0.ljceQWywa9x-yh0cG0vcPQ"  # Remplace par ta vraie clé

# 1️⃣ Page Configuration
st.set_page_config(layout="wide")

# 2️⃣ Load Data
@st.cache_data
def load_data():
    df = pd.read_excel("VerticalProfiles_with_thermocline_chloro.xlsx")
    df = df.dropna(subset=["Latitude", "Longitude", "StationNewName"])
    df["StationNewName"] = df["StationNewName"].astype(str)
    df = df[~df["StationNewName"].isin(["2.75", "21.25", "21.75"])]
    return df

df = load_data()

st.title("🌊 Interactive Vertical Profile Visualization by Station")

# 3️⃣ Map and Station Selection
st.subheader("1️⃣ Click on a station or choose from the list")

# Utiliser la première latitude/longitude rencontrée par station
station_coords = df.groupby("StationNewName")[["Latitude", "Longitude"]].first().reset_index()

# Ajouter l'info sur FullCycle
station_coords = station_coords.merge(df[["StationNewName", "FullCycle"]].drop_duplicates(), on="StationNewName", how="left")
station_coords["FullCycle"] = station_coords["FullCycle"].fillna(0)

# Séparer les stations
fullcycle_stations = station_coords[station_coords["FullCycle"] == 1]
normal_stations = station_coords[station_coords["FullCycle"] == 0]

# Sélecteur de station
selected_station = st.selectbox("📍 Select a station:", station_coords["StationNewName"].unique())
selected_coords = station_coords[station_coords["StationNewName"] == selected_station].iloc[0]

# Afficher la carte avec pydeck
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=pdk.ViewState(
        latitude=selected_coords["Latitude"],
        longitude=selected_coords["Longitude"],
        zoom=9,
        pitch=0,
    ),
    layers=[
        pdk.Layer(
            "ScatterplotLayer",
            data=normal_stations,
            get_position='[Longitude, Latitude]',
            get_radius=1000,
            get_fill_color='[0, 0, 200, 160]',
            pickable=True,
            auto_highlight=True
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=fullcycle_stations,
            get_position='[Longitude, Latitude]',
            get_radius=1000,
            get_fill_color='[0, 255, 0, 160]',
            pickable=True,
            auto_highlight=True
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([selected_coords]),
            get_position='[Longitude, Latitude]',
            get_radius=1500,
            get_fill_color='[255, 0, 0, 200]',
            pickable=False,
        )
    ],
    tooltip={"text": "{StationNewName}"}
))

st.markdown("""
    **💡 Note:** The **green** circles on the map represent stations with Full Cycle measurements.
""")

# 4️⃣ Filtrage des données et sélection des paramètres
station_df = df[df["StationNewName"] == selected_station]

parameter_options = ["Temp", "pH", "ODO%", "ODO Conc", "Turbidity"]
parameter = st.selectbox("📊 Parameter:", parameter_options)

period_options = ["All", "LW", "RW", "HW", "FW"]
time_options = ["All", "AM", "PM"]

selected_water = st.selectbox("💧 Water Period:", period_options)
selected_day = st.selectbox("🕐 Day Period:", time_options)

show_thermocline = st.checkbox("Show Thermocline", value=False)
show_max_chloro = st.checkbox("Show Max Chloro", value=False)

# 5️⃣ Préparation des courbes verticales
available_periods = ["LW", "RW", "HW", "FW"]
available_day = ["AM", "PM"]

combinations = []
for wp in available_periods:
    for dp in available_day:
        subset = station_df[(station_df["WaterPeriod"] == wp) & (station_df["DayPeriod"] == dp)]
        if not subset.empty:
            chosen_sheetid = subset["SheetID"].unique()[0]
            subset_sheet = subset[subset["SheetID"] == chosen_sheetid]
            combinations.append(subset_sheet)

if combinations:
    filtered_combined_df = pd.concat(combinations)
else:
    filtered_combined_df = pd.DataFrame()

# Application des filtres
if selected_water != "All":
    filtered_combined_df = filtered_combined_df[filtered_combined_df["WaterPeriod"] == selected_water]
if selected_day != "All":
    filtered_combined_df = filtered_combined_df[filtered_combined_df["DayPeriod"] == selected_day]

if filtered_combined_df.empty:
    st.warning("❌ No data for this Water Period / Day Period combination.")
else:
    st.subheader("3️⃣ Vertical Profile Curve(s)")

    fig = go.Figure()

    for (wp, dp, sid), data in filtered_combined_df.groupby(["WaterPeriod", "DayPeriod", "SheetID"]):
        label = f"{wp} {dp} (SheetID {sid})"
        data = data.sort_values("Profondeur")

        fig.add_trace(go.Scatter(
            x=data[parameter],
            y=data["Profondeur"],
            mode='lines+markers',
            name=label
        ))

        if show_thermocline:
            thermo_value = data["Thermocline"].iloc[0]
            if pd.notna(thermo_value):
                fig.add_trace(go.Scatter(
                    x=[data[parameter].min(), data[parameter].max()],
                    y=[thermo_value, thermo_value],
                    mode='lines',
                    line=dict(dash='dash', color='red'),
                    name=f"Thermocline (SheetID {sid})"
                ))

        if show_max_chloro:
            chloro_value = data["Max Chloro"].iloc[0]
            if pd.notna(chloro_value):
                fig.add_trace(go.Scatter(
                    x=[data[parameter].min(), data[parameter].max()],
                    y=[chloro_value, chloro_value],
                    mode='lines',
                    line=dict(dash='dot', color='green'),
                    name=f"Max Chloro (SheetID {sid})"
                ))

    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title=parameter)
    fig.update_layout(title=f"{selected_station} | Parameter: {parameter}")

    st.plotly_chart(fig, use_container_width=True)
