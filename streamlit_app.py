import itertools
import json

import pandas as pd
import plotly.express as px
import streamlit as st

# Load dataset
with open('destination_research/data.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)
country_list = sorted(list(set(itertools.chain.from_iterable(df['countries']))))
month_list = sorted(list(set(itertools.chain.from_iterable(df['months']))))

for country in country_list:
    df[country] = df['countries'].apply(lambda country_field, c=country: c in country_field)

for month in month_list:
    df[month] = df['months'].apply(lambda month_field, m=month: m in month_field)

# Generate sidebar
starting_price_range = (df['starting_price'].min(), df['starting_price'].max())
starting_price_per_night_range = (
    df['starting_price_per_night'].min(),
    df['starting_price_per_night'].max(),
)
with st.sidebar:
    st.title('Filters')
    countries_selected = st.multiselect('Countries', country_list, default=country_list)
    months_selected = st.multiselect('Months', month_list, default=month_list)
    starting_price_slider = st.slider(
        'Starting S$', starting_price_range[0], starting_price_range[1], starting_price_range
    )
    starting_price_per_night_slider = st.slider(
        'Starting S$/night',
        starting_price_per_night_range[0],
        starting_price_per_night_range[1],
        starting_price_per_night_range,
    )
df_filtered = df[
    pd.Series([not set(countries_selected).isdisjoint(ls) for ls in df['countries']])
    & pd.Series([not set(months_selected).isdisjoint(ls) for ls in df['months']])
    & df['starting_price'].between(*starting_price_slider)
    & (
        df['starting_price_per_night'].between(*starting_price_per_night_slider)
        | df['starting_price_per_night'].isna()
    )
]

# Main content
st.set_page_config(layout='wide')
st.title('Destination Research Dashboard')
st.write("Data obtained from Chan Brothers' Package Tours to Europe accessed 23 Nov 2026")
grid = st.grid(2)

# Generate color-coded choropleth map
with grid.cell():
    st.header('Choropleth')
    choropleth_countries = [
        c
        for c in countries_selected
        if c in itertools.chain.from_iterable(df_filtered['countries'])
    ]
    countries_dict = {
        'Country': choropleth_countries,
        'Number of Tours': df_filtered[choropleth_countries].sum(),
        'Mean Starting S$': [
            df_filtered[df_filtered[c]]['starting_price'].mean() for c in choropleth_countries
        ],
        'Mean Starting S$/night': [
            df_filtered[df_filtered[c]]['starting_price_per_night'].mean()
            for c in choropleth_countries
        ],
    }
    chloropeth_option = st.selectbox(
        'Metric', [m for m in countries_dict if m != 'Country'], key='choropeth'
    )
    countries = pd.DataFrame(countries_dict)
    fig = px.choropleth(
        countries,
        color=chloropeth_option,
        locations='Country',
        locationmode='country names',
        color_continuous_scale=px.colors.sequential.Viridis,
    )
    fig.update_layout(
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            orientation='h',
            x=0.5,
            y=1.0,
            yanchor='bottom',
        ),
    )
    st.plotly_chart(fig)

# Create line chart of tours / average starting price / average starting price per night vs month
with grid.cell():
    st.header('Line Plot vs Months')
    x_axis = sorted(
        [m for m in months_selected if m in itertools.chain.from_iterable(df_filtered['months'])]
    )
    months_dict = {
        'Month': x_axis,
        'Number of Tours': df_filtered[x_axis].sum(),
        'Mean Starting S$': [df_filtered[df_filtered[x]]['starting_price'].mean() for x in x_axis],
        'Mean Starting S$/night': [
            df_filtered[df_filtered[x]]['starting_price_per_night'].mean() for x in x_axis
        ],
    }
    line_chart_option = st.selectbox(
        'Metric', [m for m in months_dict if m != 'Month'], key='line'
    )
    months = pd.DataFrame(months_dict)
    st.space('medium')
    st.line_chart(months, x='Month', y=line_chart_option)

# Generate list of cities listed for each country
with grid.cell():
    st.header('Cities')
    cities = {
        country: sorted(
            list(
                set(
                    itertools.chain.from_iterable(
                        cities[country]
                        for cities in df_filtered[
                            df_filtered[country] & ~df_filtered['cities'].isna()
                        ]['cities']
                    )
                )
            )
        )
        for country in choropleth_countries
    }
    for country in sorted(cities):
        if cities[country]:
            st.subheader(country)
            st.write(', '.join(cities[country]))

# Generate list of attractions listed for each country
with grid.cell():
    st.header('Attractions')
    attractions = {
        country: sorted(
            list(
                set(
                    itertools.chain.from_iterable(
                        attractions[country]
                        for attractions in df_filtered[
                            df_filtered[country] & ~df_filtered['attractions'].isna()
                        ]['attractions']
                    )
                )
            )
        )
        for country in choropleth_countries
    }
    for country in sorted(attractions):
        if attractions[country]:
            st.subheader(country)
            st.write(', '.join(attractions[country]))

with st.bottom:
    st.write(
        'Made with &nbsp; &#x2764; &nbsp; by JY with Streamlit'
        ' | '
        'Most importantly, keep learning =)'
    )
