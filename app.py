import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import os

# Set Mapbox token
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoiaGdoYXJiaSIsImEiOiJjbWNicWdkb3owMDF6MmlzN2I3anB5Z2dlIn0.ljceQWywa9x-yh0cG0vcPQ"

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_excel("Filtered_dataset.xlsx")
    df = df.dropna(subset=["Latitude", "Longitude", "Station"])
    df["Station"] = df["Station"].astype(str)
    return df

df = load_data()

st.title("🌊 Interactive Vertical Profile Visualization by Station")
st.subheader("1️⃣ Click on a station or choose from the list")

station_coords = df.groupby("Station")[["Latitude", "Longitude"]].first().reset_index()
station_coords = station_coords.merge(df[["Station", "FullCycle"]].drop_duplicates(), on="Station", how="left")
station_coords["FullCycle"] = station_coords["FullCycle"].fillna(0)

fullcycle_stations = station_coords[station_coords["FullCycle"] == 1]
normal_stations = station_coords[station_coords["FullCycle"] == 0]

selected_station = st.selectbox("📍 Select a station:", station_coords["Station"].unique())
selected_coords = station_coords[station_coords["Station"] == selected_station].iloc[0]

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
    tooltip={"text": "{Station}"}
))

st.markdown("**💡 Note:** The **green** circles on the map represent stations with Full Cycle measurements.")

# 📊 Parameters and Filters
station_df = df[df["Station"] == selected_station]
parameter = st.selectbox("📊 Parameter:", ["Temp", "pH", "ODO%", "ODO Conc", "Turbidity"])

# ✅ Multiselect for Water Period and Day Period
water_periods = st.multiselect("💧 Water Period(s):", ["LW", "RW", "HW", "FW"], default=["LW", "RW", "HW", "FW"])
day_periods = st.multiselect("🕐 Day Period(s):", ["AM", "PM"], default=["AM", "PM"])

# 📈 Optional lines with color mapping
optional_lines = [
    "Thermocline", "thermoInd", "epilimnion", "hypolimnion", "hML",
    "buoyancy_freq", "depth_of_buoyancy", "wedderburn", "Schmidt_stability",
    "heat_content", "seiche_period", "Lake_number", "Max Chloro"
]
selected_lines = st.multiselect("📈 Show Additional Horizontal Lines:", optional_lines)

# Assign unique colors to each line
line_colors = {
    "Thermocline": "red",
    "thermoInd": "blue",
    "epilimnion": "green",
    "hypolimnion": "orange",
    "hML": "purple",
    "buoyancy_freq": "pink",
    "depth_of_buoyancy": "brown",
    "wedderburn": "cyan",
    "Schmidt_stability": "gray",
    "heat_content": "black",
    "seiche_period": "gold",
    "Lake_number": "magenta",
    "Max Chloro": "darkgreen"
}

# Prepare data
filtered_df = station_df[(station_df["WaterPeriod"].isin(water_periods)) & (station_df["DayPeriod"].isin(day_periods))]
grouped = filtered_df.groupby(["WaterPeriod", "DayPeriod", "SheetID"])

if filtered_df.empty:
    st.warning("❌ No data for the selected combination.")
else:
    st.subheader("3️⃣ Vertical Profile Curve(s)")
    fig = go.Figure()

    for (wp, dp, sid), data in grouped:
        label = f"{wp} {dp} (SheetID {sid})"
        data = data.sort_values("Profondeur")

        fig.add_trace(go.Scatter(
            x=data[parameter],
            y=data["Profondeur"],
            mode='lines+markers',
            name=label
        ))

        for line_var in selected_lines:
            if line_var in data.columns:
                val = data[line_var].iloc[0]
                if pd.notna(val):
                    fig.add_trace(go.Scatter(
                        x=[data[parameter].min(), data[parameter].max()],
                        y=[val, val],
                        mode='lines',
                        line=dict(dash='dot', color=line_colors.get(line_var, "gray")),
                        name=f"{line_var} (SheetID {sid})"
                    ))

    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title=parameter)
    fig.update_layout(title=f"{selected_station} | Parameter: {parameter}")

    st.plotly_chart(fig, use_container_width=True)
