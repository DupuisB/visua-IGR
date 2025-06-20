import streamlit as st
import os

# Basic app to test deployment
st.title("French Baby Names Dashboard")
st.write("Testing Heroku deployment...")

# Show environment info for debugging
st.write(f"Python version: {os.environ.get('PYTHON_VERSION', 'Not set')}")
st.write(f"PORT: {os.environ.get('PORT', 'Not set')}")
st.write(f"Current directory: {os.getcwd()}")
st.write(f"Files in directory: {sorted(os.listdir('.'))}")

# Simple interface
st.success("If you can see this, the app is running correctly!")
def load_data():
    names = pd.read_csv("dpt2020.csv", sep=";")
    names.drop(names[names.preusuel == '_PRENOMS_RARES'].index, inplace=True)
    names.drop(names[names.dpt == 'XX'].index, inplace=True)
    names['annais'] = pd.to_numeric(names['annais'], errors='coerce')
    names['nombre'] = pd.to_numeric(names['nombre'], errors='coerce')
    return names.dropna(subset=['nombre', 'annais'])

@st.cache_data
def load_geo_data():
    return gpd.read_file('departements-version-simplifiee.geojson')

# Enable Altair to handle larger datasets
alt.data_transformers.enable('json')

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Choose Visualization", ["Home", "Top Names Over Time", "Regional Name Map", "Name Gender Distribution"])

# Load data
try:
    df = load_data()
    depts = load_geo_data()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Home page
if page == "Home":
    st.title("French Baby Names Visualization Dashboard")
    
    st.markdown("""
    This dashboard provides three interactive visualizations for exploring French baby name data:
    
    1. **Top Names Over Time**: Explore the most popular baby names in France from 1940 to 2020 using an interactive year slider.
    
    2. **Regional Name Map**: Discover which names are most popular in different French departments using an interactive map.
    
    3. **Name Gender Distribution**: Analyze how the gender distribution for specific names has changed over time in different regions.
    
    Use the sidebar to navigate between visualizations.
    """)

# Visualization 1: Top Names Over Time
elif page == "Top Names Over Time":
    st.title("Top Baby Names Over Time")
    st.write("Use the slider to explore the top 15 baby names for each year")
    
    # Group by year and name, sum the counts across all departments and genders
    df_grouped = df.groupby(['annais', 'preusuel'])['nombre'].sum().reset_index()
    
    # Function to get top names by year
    def get_top_names_by_year(data, top_n=15):
        result = []
        for year in data['annais'].unique():
            year_data = data[data['annais'] == year].nlargest(top_n, 'nombre')
            result.append(year_data)
        return pd.concat(result, ignore_index=True)
    
    df_top = get_top_names_by_year(df_grouped, top_n=15)
    
    # Create slider for year selection
    year = st.slider("Select Year", 
                     int(df_top['annais'].min()), 
                     int(df_top['annais'].max()), 
                     2000)
    
    # Filter data for selected year and get top 15
    year_data = df_top[df_top['annais'] == year]
    year_data = year_data.nlargest(15, 'nombre')
    
    # Create the chart
    chart = alt.Chart(year_data).mark_bar(
        color='steelblue',
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X('nombre:Q', title='Number of Births'),
        y=alt.Y('preusuel:N', title='Name', sort='-x'),
        tooltip=['preusuel:N', 'nombre:Q']
    ).properties(
        width=700,
        height=400,
        title=f"Top 15 Baby Names in {year}"
    )
    
    # Add text labels
    text = alt.Chart(year_data).mark_text(
        align='left',
        baseline='middle',
        dx=3,
        fontSize=10,
        color='black'
    ).encode(
        x=alt.X('nombre:Q'),
        y=alt.Y('preusuel:N', sort='-x'),
        text=alt.Text('nombre:Q', format='.0f')
    )
    
    # Display the chart
    st.altair_chart(chart + text, use_container_width=True)

# Visualization 2: Regional Name Map
elif page == "Regional Name Map":
    st.title("Regional Name Popularity Map")
    st.write("Hover over departments to see the most and least used names")
    
    # Merge names with map data
    names_with_geo = depts.merge(df, how='left', left_on='code', right_on='dpt')
    
    # Group by dpt, preusuel, sexe to get total numbers
    grouped = names_with_geo.groupby(['dpt', 'preusuel', 'sexe'], as_index=False).agg({'nombre': 'sum'})
    
    # For each department, find the name with max and min count
    def get_extremes(df):
        if len(df) == 0:
            return pd.Series({
                'max_name': 'No data',
                'max_nombre': 0,
                'min_name': 'No data',
                'min_nombre': 0,
            })
        max_row = df.loc[df['nombre'].idxmax()]
        min_row = df.loc[df['nombre'].idxmin()]
        return pd.Series({
            'max_name': max_row['preusuel'],
            'max_nombre': max_row['nombre'],
            'min_name': min_row['preusuel'],
            'min_nombre': min_row['nombre'],
        })
    
    extremes = grouped.groupby('dpt').apply(get_extremes).reset_index()
    
    # Merge extremes with department geometry
    merged = depts.merge(extremes, how='left', left_on='code', right_on='dpt')
    
    # Create color scheme options
    color_scheme = st.selectbox("Select Color Scheme", 
                                ["blues", "greens", "reds", "purples", "oranges"], 
                                index=0)
    
    # Create the map visualization
    map_chart = alt.Chart(merged).mark_geoshape(stroke='white').encode(
        tooltip=['nom:N', 'max_name:N', 'max_nombre:Q', 'min_name:N', 'min_nombre:Q'],
        color=alt.Color('max_nombre:Q', scale=alt.Scale(scheme=color_scheme))
    ).properties(
        width=700,
        height=600,
        title="Most Popular Baby Names by Department"
    )
    
    # Display the chart
    st.altair_chart(map_chart, use_container_width=True)

# Visualization 3: Name Gender Distribution
elif page == "Name Gender Distribution":
    st.title("Name Gender Distribution Over Time")
    
    # Get unique names and departments for dropdowns
    unique_names = sorted(df['preusuel'].unique())
    unique_depts = sorted(depts['nom'].unique())
    
    # Add "All" option for departments
    unique_depts = ["All"] + list(unique_depts)
    
    # Create selection widgets
    col1, col2 = st.columns(2)
    with col1:
        chosen_name = st.selectbox("Select Name", unique_names, index=unique_names.index("Sacha") if "Sacha" in unique_names else 0)
    with col2:
        chosen_department = st.selectbox("Select Department", unique_depts, index=0)
    
    # Merge names with map data
    names_with_geo = depts.merge(df, how='right', left_on='code', right_on='dpt')
    
    # Filter data for chosen name
    df_name = names_with_geo[names_with_geo['preusuel'].str.upper() == chosen_name.upper()]
    
    if chosen_department != 'All':
        df_name = df_name[df_name['nom'].str.upper() == chosen_department.upper()]
    
    # Group by year and gender
    grouped = df_name.groupby(['annais', 'sexe'])['nombre'].sum().reset_index()
    
    # Pivot data for percentage calculation
    pivot = grouped.pivot(index='annais', columns='sexe', values='nombre').fillna(0)
    pivot.columns = ['Boys', 'Girls']
    
    # Calculate percentages
    pivot['Total'] = pivot['Girls'] + pivot['Boys']
    pivot['% Girls'] = (pivot['Girls'] / pivot['Total']) * 100
    pivot['% Boys'] = (pivot['Boys'] / pivot['Total']) * 100
    
    # Prepare data for plotting
    plot_df = pivot.reset_index().melt(id_vars=['annais', 'Total', 'Girls', 'Boys'], 
                                      value_vars=['% Girls', '% Boys'], 
                                      var_name='Sex', 
                                      value_name='Percentage')
    
    plot_df['Sex'] = plot_df['Sex'].map({'% Girls': 'Girls', '% Boys': 'Boys'})
    
    # Set title based on selection
    if chosen_department == 'All':
        title_str = f"Percentage of Boys and Girls Named {chosen_name} Over Time in France"
    else:
        title_str = f"Percentage of Boys and Girls Named {chosen_name} Over Time in {chosen_department}"
    
    # Create the line chart
    if len(plot_df) > 0:
        tooltip = [
            alt.Tooltip('annais:O', title='Year'),
            alt.Tooltip('Percentage:Q', title='Percentage', format='.1f'),
            alt.Tooltip('Sex:N', title='Gender'),
            alt.Tooltip('Girls:Q', title='Girls Count', format=','),
            alt.Tooltip('Boys:Q', title='Boys Count', format=','),
            alt.Tooltip('Total:Q', title='Total', format=',')
        ]
        
        chart = alt.Chart(plot_df).mark_line(point=True).encode(
            x=alt.X('annais:O', title='Year'),
            y=alt.Y('Percentage:Q', title='Percentage (%)', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('Sex:N', scale=alt.Scale(domain=['Girls', 'Boys'], 
                                                  range=['pink', 'lightblue'])),
            tooltip=tooltip
        ).properties(
            title=title_str,
            width=700,
            height=400
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # Display the data table
        st.subheader("Data")
        display_data = pivot[['Girls', 'Boys', 'Total', '% Girls', '% Boys']].reset_index()
        display_data = display_data.sort_values('annais', ascending=False)
        st.dataframe(display_data)
    else:
        st.write(f"No data available for name '{chosen_name}' in the selected department.")
        
        chart = alt.Chart(plot_df).mark_line(point=True).encode(
            x=alt.X('annais:O', title='Year'),
            y=alt.Y('Percentage:Q', title='Percentage (%)', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('Sex:N', scale=alt.Scale(domain=['Girls', 'Boys'], 
                                                  range=['pink', 'lightblue'])),
            tooltip=tooltip
        ).properties(
            title=title_str,
            width=700,
            height=400
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # Display the data table
        st.subheader("Data")
        display_data = pivot[['Girls', 'Boys', 'Total', '% Girls', '% Boys']].reset_index()
        display_data = display_data.sort_values('annais', ascending=False)
        st.dataframe(display_data)

# Health check endpoint
elif page == "Health Check":
    st.title("Health Check")
    st.write("The application is running smoothly!")
