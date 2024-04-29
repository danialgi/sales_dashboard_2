import streamlit as st
import pandas as pd
import plotly.express as px
import webbrowser as wb
import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import Alignment
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io
import calendar
from datetime import datetime

today_date = datetime.now().strftime('%Y-%m-%d')

st.set_page_config(page_title="Sales Dashboard", page_icon="📈", layout="wide")

@st.cache_data
def process_data_sheets(folder_path):
    # Helper function to process individual sheets
    def process_sheet(df):
        df.drop(df.index[:4], inplace=True)
        df.columns = df.iloc[0]
        df = df[1:]
        df.reset_index(drop=True, inplace=True)
        return df

    # This will hold the compiled data from all files
    compiled_data = pd.DataFrame()

    # List all Excel files in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.xlsx'):
            # Construct the full file path
            file_path = os.path.join(folder_path, file_name)

            # Read the sheets into DataFrames
            df1 = pd.read_excel(file_path, sheet_name="Web")
            df2 = pd.read_excel(file_path, sheet_name="Shopee")
            df3 = pd.read_excel(file_path, sheet_name="Lazada")
            df4 = pd.read_excel(file_path, sheet_name="TikTok")

            # Process each DataFrame
            df1 = process_sheet(df1)
            df2 = process_sheet(df2)
            df3 = process_sheet(df3)
            df4 = process_sheet(df4)

            # Concatenate the DataFrames from the current file
            df = pd.concat([df1, df2, df3, df4])

            # Compile data from all files
            compiled_data = pd.concat([compiled_data, df])

    return compiled_data

# Usage
folder_path = 'Sales Dashboard'  # Replace with the path to your folder containing Excel files
compiled_df = process_data_sheets(folder_path)
compiled_df.reset_index(drop=True, inplace=True)
#compiled_df

filled_df=compiled_df.copy()
filled_df.ffill(inplace=True)
#filled_df

filled_df['Date Added'] = pd.to_datetime(filled_df['Date Added'], errors='coerce')
filled_df['month_name'] = filled_df['Date Added'].dt.month
filled_df['month_name'] = filled_df['month_name'].apply(lambda x: calendar.month_name[int(x)])
filled_df['Unit Total'] = pd.to_numeric(filled_df['Unit Total'], errors='coerce')
filled_df['Margin Per Item'] = pd.to_numeric(filled_df['Margin Per Item'], errors='coerce')

states_coordinates = pd.DataFrame({
    'Shipping State': ['Johor', 'Kedah', 'Kelantan', 'Malacca', 'Negeri Sembilan', 'Pahang', 'Penang', 'Perak', 'Perlis', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu'],
    'lat': [1.4854, 6.1184, 6.1254, 2.1896, 2.7258, 3.8126, 5.4164, 4.5921, 6.4449, 5.9804, 1.5533, 3.0738, 5.3117],
    'lon': [103.7618, 100.3682, 102.2386, 102.2501, 101.9424, 103.3256, 100.3308, 101.0901, 100.2048, 116.0753, 110.3441, 101.5183, 103.1324]
})

filled_df.loc[(filled_df['Shipping State'] == "Kuala Lumpur") |
              (filled_df['Shipping State'] == "W.P. Kuala Lumpur") |
              (filled_df['Shipping State'] == "Wp Kuala Lumpur") |
              (filled_df['Shipping State'] == "Putrajaya") |
              (filled_df['Shipping State'] == "W.P. Putrajaya") |
              (filled_df['Shipping State'] == "Wp Putrajaya") |
              (filled_df['Shipping State'] == "Wilayah Persekutuan Putrajaya"), 'Shipping State'] = "Selangor"

filled_df.loc[(filled_df['Shipping State'] == "Labuan") |
              (filled_df['Shipping State'] == "W.P. Labuan") |
              (filled_df['Shipping State'] == "Wp Labuan"), 'Shipping State'] = "Sabah"

filled_df.loc[(filled_df['Shipping State'] == "Melaka"), 'Shipping State'] = "Malacca"

filled_df = filled_df.merge(states_coordinates, on='Shipping State', how='left')

def format_value(value):
    # Check if the original value is negative
    is_negative = value < 0
    # Work with the absolute value for formatting
    abs_value = abs(value)

    if abs_value >= 1000000:
        formatted_value = f"{abs_value/1000000:.1f}M"
    elif abs_value >= 1000:
        formatted_value = f"{abs_value/1000:.1f}K"
    else:
        formatted_value = str(abs_value)

    # Add the negative sign back if the original value was negative
    return f"-{formatted_value}" if is_negative else formatted_value

def get_latest_month(df):
    # Sort the DataFrame by the 'Date Added' column
    df.sort_values(by='Date Added', inplace=True)

    # Get the latest month as a datetime object
    latest_month = df['Date Added'].iloc[-1]

    # Subtract one day before subtracting MonthBegin to ensure we get the previous month
    month_before =  latest_month  - pd.DateOffset(months=1)

    # Convert back to month names
    latest_month_name = latest_month.strftime('%B')
    month_before_name = month_before.strftime('%B')

    return latest_month_name, month_before_name

def cal_total_sales(df):
    df['Unit Total'] = df['Unit Total'].replace('-', 0)
    total_sales = df['Unit Total'].sum()
    total_sales = int(total_sales)
    return total_sales

def cal_total_profit(df):
    df['Margin Per Item'] = df['Margin Per Item'].replace('-', 0)
    total_profit = df['Margin Per Item'].sum()
    total_profit = int(total_profit)
    return total_profit

def cal_average_margin(df):
    df['Order ID'].ffill(inplace=True)
    average_margin = df.groupby('Order ID')['Margin Per Item'].sum().reset_index()
    average_margin = round(average_margin['Margin Per Item'].mean(),2)
    return average_margin

#st.header(f":bar_chart: Dashboard")

# Get min and max dates, ensuring no NaT values
min_date = filled_df['Date Added'].min()
max_date = filled_df['Date Added'].max()

mode = st.sidebar.selectbox('Select Mode:', ['UptoDate', 'Range', 'Compare'])
st.sidebar.write("#")
st.sidebar.write("Filter")
# Create a form in the sidebar
with st.sidebar.form(key='filter_form'):

    # Select box for choosing the mode
    if mode == 'Range':
        start_date = st.date_input('Start date', value=min_date, min_value=min_date, max_value=max_date, key='start_date')
        end_date = st.date_input('End date', value=max_date, min_value=min_date, max_value=max_date, key='end_date')
        st.write('_____________')

    if mode == 'Compare':
        st.header('Period 1')
        start_date_1 = st.date_input('Start date', value=min_date, min_value=min_date, max_value=max_date, key='start_date_1')
        end_date_1 = st.date_input('End date', value=max_date, min_value=min_date, max_value=max_date, key='end_date_1')

        st.write("#")
        st.header('Period 2')
        start_date_2 = st.date_input('Start date', value=min_date, min_value=min_date, max_value=max_date, key='start_date_2')
        end_date_2 = st.date_input('End date', value=max_date, min_value=min_date, max_value=max_date, key='end_date_2')
        st.write('_____________')

    # Get a list of unique values for each category
    marketplaces = filled_df['Order Source'].unique().tolist()
    status = filled_df['Order Status'].unique().tolist()

    # Create multiselect widgets inside the form for each category
    selected_marketplaces = st.multiselect('Marketplace:', marketplaces, default=marketplaces)
    filled_df = filled_df[filled_df['Order Source'].isin(selected_marketplaces)]
    filled_df_return = filled_df.copy()
    selected_status = st.multiselect('Status:', status, default="Complete")
    filled_df = filled_df[filled_df['Order Status'].isin(selected_status)]

    focus = st.selectbox('Focus:', options=['Sales', 'Profit', 'Orders', 'Units'])

    # Every form must have a submit button
    st.write("#")
    submitted = st.form_submit_button('Apply')


def display_metrics(df, df_return, df_month):
    latest_month_name, month_before_name=get_latest_month(df)
    df_latest_month = df_month[df_month['month_name'].isin([latest_month_name])]
    df_prev_month = df_month[df_month['month_name'].isin([month_before_name])]

    total_sales=cal_total_sales(df)
    cur_total_sales=cal_total_sales(df_latest_month)
    prev_total_sales=cal_total_sales(df_prev_month)
    compare_sales= cur_total_sales - prev_total_sales
    if prev_total_sales is not None and prev_total_sales != 0 and not np.isnan(prev_total_sales):
        compare_sales_per= int(compare_sales/prev_total_sales*100)
    else:
        compare_sales_per=np.nan

    total_profit=cal_total_profit(df)
    cur_total_profit=cal_total_profit(df_latest_month)
    prev_total_profit=cal_total_profit(df_prev_month)
    compare_profit= cur_total_profit - prev_total_profit
    if prev_total_profit is not None and prev_total_profit != 0 and not np.isnan(prev_total_profit):
        compare_profit_per= int(compare_profit/prev_total_profit*100)
    else:
        compare_profit_per=np.nan

    total_orders=df['Order ID'].nunique()
    total_orders_cur = df_latest_month['Order ID'].nunique()
    total_orders_prev = df_prev_month['Order ID'].nunique()
    compare_total_orders= total_orders_cur  - total_orders_prev
    if total_orders_prev is not None and total_orders_prev != 0 and not np.isnan(total_orders_prev):
        compare_total_orders_per = "{:.2f}".format(compare_total_orders /total_orders_prev*100)
    else:
        compare_total_orders_per=np.nan

    total_qty = df['Quantity'].sum()
    total_qty_cur = df_latest_month['Quantity'].sum()
    total_qty_prev = df_prev_month['Quantity'].sum()
    compare_total_qty = total_qty_cur - total_qty_prev
    if total_qty_prev is not None and total_qty_prev != 0 and not np.isnan(total_qty_prev):
        compare_total_qty_per = "{:.2f}".format(compare_total_qty /prev_total_profit*100)
    else:
        compare_total_qty_per=np.nan

    average_margin=cal_average_margin(df)
    average_margin_cur=cal_average_margin(df_latest_month)
    average_margin_prev=cal_average_margin(df_prev_month)
    compare_average_margin = (average_margin_cur - average_margin_prev)
    if average_margin_prev is not None and average_margin_prev != 0 and not np.isnan(average_margin_prev):
        compare_average_margin_per = compare_average_margin/average_margin_prev*100
        if compare_average_margin_per is not None and compare_average_margin_per != 0 and not np.isnan(compare_average_margin_per):
            compare_average_margin_per = int(compare_average_margin_per)
    else:
        compare_average_margin_per=np.nan

    df_return_latest_month_name, df_return_month_before_name=get_latest_month(df_return)
    df_return_latest_month = df_month[df_month['month_name'].isin([latest_month_name])]
    df_return_prev_month = df_month[df_month['month_name'].isin([month_before_name])]
    df_return=df_return[df_return['Order Status'].isin(["Returned","Refunded"])]
    total_return= df_return['Order ID'].nunique()
    total_returns_cur = df_return_latest_month['Order ID'].nunique()
    total_return_prev = df_return_prev_month['Order ID'].nunique()
    compare_total_return = total_returns_cur - total_return_prev
    if total_return_prev is not None and total_return_prev != 0 and not np.isnan(total_return_prev):
        compare_total_return_per = "{:.2f}".format(compare_total_return/total_return_prev*100)
    else:
        compare_total_return_per=np.nan

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1.container():
        col1.metric("Sales:", f"RM {format_value(total_sales)}", f"{compare_sales_per}% ({format_value(compare_sales)})")
    with col2.container():
        col2.metric("Profit:", f"RM {format_value(total_profit)}", f"{compare_profit_per}% ({format_value(compare_profit)})")
    with col3.container():
        col3.metric("Total Orders:", f"{total_orders}", f"{compare_total_orders_per}% ({compare_total_orders})")
    with col4.container():
        col4.metric("Total Units Sold:", f"{total_qty}", f"{compare_total_qty_per}% ({compare_total_qty})")
    with col5.container():
        formatted_compare_average_margin = "{:.2f}".format(compare_average_margin)
        col5.metric("Average Margin per Order:", f"{average_margin}", f"{compare_average_margin_per}% ({formatted_compare_average_margin})")
    with col6.container():
        col6.metric("Returns/Refunds:", f"{total_return}", f"{compare_total_return_per}% ({compare_total_return})", "inverse")


def map_plot(df):
    df_state= df.groupby(['Shipping State', 'lat', 'lon'], as_index=False).agg({
        'Unit Total': 'sum',
        'Margin Per Item': 'sum',
        'Quantity': 'sum',
        'Order ID': pd.Series.nunique
    })
    df_state.rename(columns={
        'Unit Total': 'Sales',
        'Margin Per Item': 'Profit',
        'Quantity': 'Units',
        'Order ID': 'Orders'
    }, inplace=True)
    mapfig = px.scatter_geo(df_state,
                         lat='lat',
                         lon='lon',
                         size=focus,
                         color='Shipping State',  # Set the color based on the state
                         hover_name='Shipping State',
                         projection='natural earth',
                         color_discrete_sequence=px.colors.qualitative.Plotly
                         )

    # Ensure that the land and country borders are visible
    mapfig.update_geos(
        visible=True,  # This ensures that the geographic layout is visible
        showcountries=True,  # This shows country borders
        countrycolor="Black"  # You can customize the country border color
    )

    # Update the layout to focus on Malaysia
    mapfig.update_layout(
        geo=dict(
            scope='asia',  # Set the scope to 'asia'
            center={'lat': 4.2105, 'lon': 108.2},  # Center the map on Malaysia
            projection_scale=8.1,
            showland=True,  # Ensure the land is shown
            landcolor='rgb(217, 217, 217)',
            #showocean=True,  # Set the land color
            oceancolor='rgb(0, 0, 0)',
            countrywidth=0.1  # Set the country border width
        )
    )

    mapfig.add_trace(
    go.Scattergeo(
        lon=df_state['lon'],
        lat=df_state['lat'],
        text=df_state[focus].apply(format_value),  # The text labels
        mode='text',
        showlegend=False,  # Specify the mode as text
        textfont=dict(  # Set the font properties for the text
            color='black',
            #size=10
            )
        )
    )

    mapfig.update_layout(title=f'{focus} by State', height=400)
    st.plotly_chart(mapfig, use_container_width=True)

def line_chart(df,column_name):
    df_line= df.groupby([column_name], as_index=False).agg({
        'Unit Total': 'sum',
        'Margin Per Item': 'sum',
        'Quantity': 'sum',
        'Order ID': pd.Series.nunique
    })
    df_line.rename(columns={
        'Unit Total': 'Sales',
        'Margin Per Item': 'Profit',
        'Quantity': 'Units',
        'Order ID': 'Orders'
    }, inplace=True)

    # Define the correct order for the months
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    # Assuming 'df_line' is your DataFrame and 'month_name' is the column with month names
    # Create a categorical data type with the defined month order
    df_line['month_name'] = pd.Categorical(df_line['month_name'], categories=month_order, ordered=True)

    # Sort the DataFrame by 'month_name'
    df_line = df_line.sort_values('month_name')

    # Create subplots with shared x-axis
    barline_fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add bar traces for Sales and Profit
    barline_fig.add_trace(go.Bar(x=df_line['month_name'], y=df_line['Sales'], name='Sales', marker_color='rgb(0, 50, 200)', text=df_line['Sales'].apply(format_value), textposition='auto'), secondary_y=False)
    barline_fig.add_trace(go.Bar(x=df_line['month_name'], y=df_line['Profit'], name='Profit', marker_color='firebrick', text=df_line['Profit'].apply(format_value), textposition='auto'), secondary_y=False)

    # Add line traces for Units and Orders
    barline_fig.add_trace(go.Scatter(x=df_line['month_name'], y=df_line['Units'], mode='lines+markers', name='Units', line=dict(color='yellow'), text=df_line['Units'].apply(format_value), textposition='top center'), secondary_y=True)
    barline_fig.add_trace(go.Scatter(x=df_line['month_name'], y=df_line['Orders'], mode='lines+markers', name='Orders', line=dict(color='green'), text=df_line['Orders'].apply(format_value), textposition='top center'), secondary_y=True)

    max_value_df = (df_line['Units'].max())*2
    # Update layout
    barline_fig.update_layout(
        title='Monthly Sales, Profit, Orders, and Units',
        xaxis=dict(title='Month'),
        yaxis=dict(title='Sales and Profit', side='left', showgrid=True),
        yaxis2=dict(title='Units and Orders', side='right', overlaying='y', showgrid=False,  range=[0, max_value_df]),
        hovermode='closest',
        #barmode='stack',
        height=400
    )

    # Show the barline_figure
    st.plotly_chart(barline_fig, use_container_width=True)

def group_small_slices(df, value_column, category_column, threshold=0.05):
    # Calculate the total sum of the values
    total = df[value_column].sum()

    # Check if there are more than 5 categories
    if df[category_column].nunique() > 5:
        # Find the slices that are smaller than the threshold
        small_slices = df[df[value_column] / total < threshold]

        # Sum the values of the small slices to create the 'Others' category
        others_sum = small_slices[value_column].sum()

        # Remove the small slices from the DataFrame
        df = df[df[value_column] / total >= threshold]

        # Add the 'Others' category row if there are any small slices
        if not small_slices.empty:
            others_row = pd.DataFrame({category_column: ['Others'], value_column: [others_sum]})
            df = pd.concat([df, others_row], ignore_index=True)

    return df

def pie_chart(df, column_name, title):
    df_pie = df[column_name].value_counts().reset_index()
    df_pie = group_small_slices(df_pie, 'count', column_name)
    pie_fig = go.Figure(data=[go.Pie(labels=df_pie[column_name], values=df_pie['count'], hole=0.5, sort=False)])
    pie_fig.update_layout(showlegend=True, title=title, height=380)
    st.plotly_chart(pie_fig, use_container_width=True)

def bar_chart(df, column_name, title, legend):
    df_bar = df.groupby([column_name], as_index=False).agg({
        'Unit Total': 'sum',
        'Margin Per Item': 'sum',
        'Quantity': 'sum',
        'Order ID': pd.Series.nunique
    })
    df_bar.rename(columns={
        'Unit Total': 'Sales',
        'Margin Per Item': 'Profit',
        'Quantity': 'Units',
        'Order ID': 'Orders'
    }, inplace=True)

    df_bar = df_bar.sort_values(by=focus, ascending=True).tail(10)

    # Create subplots with shared x-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add bar traces for Sales and Profit
    fig.add_trace(go.Bar(x=df_bar[column_name], y=df_bar['Sales'], name='Sales', marker_color='firebrick'), secondary_y=False)
    fig.add_trace(go.Bar(x=df_bar[column_name], y=df_bar['Profit'], name='Profit', marker_color='rgb(0, 50, 200)'), secondary_y=False)

    # Add bar traces for Units and Orders (instead of line traces)
    fig.add_trace(go.Bar(x=df_bar[column_name], y=df_bar['Units'], name='Units', marker_color='yellow'), secondary_y=True)
    fig.add_trace(go.Bar(x=df_bar[column_name], y=df_bar['Orders'], name='Orders', marker_color='green'), secondary_y=True)


    max_value_df = (df_bar['Units'].max())*6
    # Update layout
    fig.update_layout(
        title=f'Top {title} by {focus}',
        xaxis=dict(title=title),
        yaxis=dict(title='Sales and Profit', side='left', showgrid=True),
        yaxis2=dict(title='Units and Orders', side='right', overlaying='y', showgrid=False, range=[0, max_value_df] ),
        hovermode='closest', barmode='stack',
    )

    # Show the figure
    #st.plotly_chart(fig, use_container_width=True)

    fig=make_subplots(
        specs=[[{"secondary_y": True}]],vertical_spacing=0)


    fig.update_layout(xaxis2= {'anchor': 'y', 'overlaying': 'x', 'side': 'top'},
                      yaxis_domain=[0, 1]);

    # Add bar traces for Sales and Profit
    fig.add_trace(go.Bar(x=df_bar['Sales'], y=df_bar[column_name], name='Sales', orientation='h', marker_color='firebrick'), secondary_y=False)
    fig.add_trace(go.Bar(x=df_bar['Profit'], y=df_bar[column_name], name='Profit', orientation='h', marker_color='rgb(0, 50, 200)'), secondary_y=False)

    # Add bar traces for Units and Orders
    fig.add_trace(go.Bar(x=df_bar['Units'], y=df_bar[column_name], name='Units', orientation='h', marker_color='yellow'), )
    fig.add_trace(go.Bar(x=df_bar['Orders'], y=df_bar[column_name], name='Orders', orientation='h', marker_color='green'), )

    fig.data[2].update(xaxis='x2')
    fig.data[3].update(xaxis='x2')
    max_value_df1 = (df_bar['Sales'].max())*1.5
    max_value_df2 = (df_bar['Units'].max())*6
    # Update layout
    fig.update_layout(
        title=f'Top {title} by {focus}',
        xaxis=dict(title='Sales and Profit', showgrid=False, range=[0, max_value_df1] ),
        xaxis2=dict(title='Units and Orders', side='top', overlaying='x', showgrid=False, range=[0, max_value_df2] ),
        yaxis=dict(title=title, side='left', showgrid=True),
        yaxis2=dict(overlaying='y'),
        hovermode='closest', barmode='stack',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True, use_container_height=True)

def dashboard_1(df, df_return, filled_df, compiled_df):
    display_metrics(df, df_return, filled_df)
    colB1, colB2 = st.columns([2.2,3])
    with colB1:
        map_plot(df)
    with colB2:
        line_chart(df, column_name='month_name')
    colC1, colC2, colC3 = st.columns(3)
    with colC1:
        bar_chart(df, column_name='Manufacturer', title='Brand',legend=False)
    with colC2:
        bar_chart(df, column_name='Category', title='Category',legend=False)
    with colC3:
        bar_chart(df, column_name='Model', title='Product',legend=True)

    colD1, colD2, colD3 = st.columns(3)
    with colD1:
        pie_chart(compiled_df, column_name='Order Source', title='Orders by Marketplace')
    with colD2:
        pie_chart(compiled_df, column_name='Payment Method', title='Preferred Payment Methods')
    with colD3:
        pie_chart(compiled_df, column_name='Courier', title='Shipping Courier')

def trend_chart(combined_df, column_name, title, color):
    trace1 = go.Scatter(
    x=combined_df.index,
    y=combined_df[f'{column_name}_x'],  # Update column names as per your combined_df
    mode='lines',
    text=combined_df['Date Added_x'],
    name='Period 1',
    line=dict(color=color[0])
    )

    trace2 = go.Scatter(
    x=combined_df.index,
    y=combined_df[f'{column_name}_y'],  # Update column names as per your combined_df
    mode='lines',
    text=combined_df['Date Added_y'],
    name='Period 2',
    line=dict(color=color[1])
    )

    # Combine all traces into a list
    data = [trace1, trace2]

    # Define the layout of the plot
    layout = go.Layout(
    xaxis=dict(title='Day'),
    yaxis=dict(title=title)
    )

    # Create the figure with data and layout
    trend_fig = go.Figure(data=data, layout=layout)

    # Plot the figure in Streamlit
    trend_fig.update_layout(height=340, title=f'{title} Trend')
    st.plotly_chart(trend_fig, use_container_width=True)

def totalgroup_chart(grouped_df_1, grouped_df_2):
    sum_grouped_df_1 = grouped_df_1[['Unit Total', 'Margin Per Item', 'Quantity', 'Order ID']].sum().rename('Grouped_DF_1')
    sum_grouped_df_2 = grouped_df_2[['Unit Total', 'Margin Per Item', 'Quantity', 'Order ID']].sum().rename('Grouped_DF_2')

    # Create a new dataframe for plotting
    plot_df = pd.DataFrame([sum_grouped_df_1, sum_grouped_df_2])

    # Define colors for each group, with Grouped_DF_1 being darker
    colors_df_1 = ['blue', 'red', 'Goldenrod', 'green']
    colors_df_2 = ['lightblue', 'lightpink', 'lightyellow', 'lightgreen']

    # Create the grouped bar chart with different colors and thicker bars
    totalbar_fig = go.Figure()

    # Define the bar width
    bar_width = 0.4

    # Add bars for Grouped_DF_1 with darker colors
    for i, col in enumerate(plot_df.columns):
        totalbar_fig.add_trace(go.Bar(name=f'Period 1 {col}',
                             x=[col.replace('Unit Total', 'Sales').replace('Margin Per Item', 'Profit').replace('Quantity', 'Units').replace('Order ID', 'Orders')], y=[plot_df[col][0]],
                             marker_color=colors_df_1[i], width=bar_width, text=format_value(plot_df[col][0]), textposition='auto'))

    # Add bars for Grouped_DF_2 with lighter colors
    for i, col in enumerate(plot_df.columns):
        totalbar_fig.add_trace(go.Bar(name=f'Period 2 {col}',
                             x=[col.replace('Unit Total', 'Sales').replace('Margin Per Item', 'Profit').replace('Quantity', 'Units').replace('Order ID', 'Orders')], y=[plot_df[col][1]],
                             marker_color=colors_df_2[i], width=bar_width, text=format_value(plot_df[col][1]), textposition='auto'))

    # Update the layout
    totalbar_fig.update_layout(barmode='group', title='Total Sales, Profit, Units and Orders',
                      #yaxis_title='Period Total',
                      legend_title_text='Legend', showlegend=True, height=400)
    st.plotly_chart(totalbar_fig, use_container_width=True)


def create_app(filled_df):
    compiled_df['Date Added'].ffill(inplace=True)
    compiled_df['Date Added'] = pd.to_datetime(compiled_df['Date Added'], errors='coerce')
    #st.title('Date Selection App')

    # Display filled_df if 'uptodate' is selected
    if mode == 'UptoDate':
        #st.write('Displaying all data up to date:')
        #st.dataframe(filled_df)
        dashboard_1(filled_df, filled_df_return, filled_df, compiled_df)

    # Show single date range selector if 'range' is selected
    elif mode == 'Range':

        # Filter the DataFrame based on the selected date range
        if start_date <= end_date:
            mask = (filled_df['Date Added'].dt.date >= start_date) & (filled_df['Date Added'].dt.date <= end_date)
            mask_return = (filled_df_return['Date Added'].dt.date >= start_date) & (filled_df_return['Date Added'].dt.date <= end_date)
            filtered_df = filled_df.loc[mask]
            filtered_df_return = filled_df_return.loc[mask_return]

            mask_compiled = (compiled_df['Date Added'].dt.date >= start_date) & (compiled_df['Date Added'].dt.date <= end_date)
            filtered_df_compiled = compiled_df.loc[mask_compiled]
            # Display the filtered DataFrame
            st.write('Data for selected date range:', start_date, 'to', end_date)
            #st.dataframe(filtered_df)
            #st.dataframe(filtered_df_return)
            dashboard_1(filtered_df, filtered_df_return, filled_df, filtered_df_compiled)
        else:
            mode
            st.error('Error: End date must fall after start date.')

    # Show dual date range selector if 'compare' is selected
    elif mode == 'Compare':

        # Filter the DataFrame based on the selected date ranges
        if start_date_1 <= end_date_1 and start_date_2 <= end_date_2:
            mask_1 = (filled_df['Date Added'].dt.date >= start_date_1) & (filled_df['Date Added'].dt.date <= end_date_1)
            filtered_df_1 = filled_df.loc[mask_1]

            mask_1_return = (filled_df_return['Date Added'].dt.date >= start_date_1) & (filled_df_return['Date Added'].dt.date <= end_date_1)
            filtered_df_1_return = filled_df_return.loc[mask_1_return]

            mask_2 = (filled_df['Date Added'].dt.date >= start_date_2) & (filled_df['Date Added'].dt.date <= end_date_2)
            filtered_df_2 = filled_df.loc[mask_2]

            mask_2_return = (filled_df_return['Date Added'].dt.date >= start_date_2) & (filled_df_return['Date Added'].dt.date <= end_date_2)
            filtered_df_2_return = filled_df_return.loc[mask_2_return]

            # Display the filtered DataFrames
            st.write('[Period 1:', start_date_1, 'to', end_date_1, '] [Period 2:', start_date_2, 'to', end_date_2, ']')
            #st.dataframe(filtered_df_1)
            #st.dataframe(filtered_df_2)
            st.write("___________________________________________________________________________________________________________________________________________")
            grouped_df_1 = filtered_df_1.groupby('Date Added').agg({'Unit Total':'sum', 'Margin Per Item':'sum', 'Quantity': 'sum', 'Order ID': pd.Series.nunique}).reset_index()
            grouped_df_1['Date Added'] = grouped_df_1['Date Added'].dt.date
            # Group by 'Date Added' and sum 'Unit Total' and 'Margin Per Item' for the second dataframe
            grouped_df_2 = filtered_df_2.groupby('Date Added').agg({'Unit Total':'sum', 'Margin Per Item':'sum', 'Quantity': 'sum', 'Order ID': pd.Series.nunique}).reset_index()
            grouped_df_2['Date Added'] = grouped_df_2['Date Added'].dt.date
            # Merge the two dataframes on the index
            combined_df = pd.merge(grouped_df_1, grouped_df_2, left_index=True, right_index=True, how='outer')

            # Handle missing values if necessary
            # For example, fill NaNs with 0
            combined_df.fillna(0, inplace=True)

            total_sales_1 = cal_total_sales(filtered_df_1)
            total_sales_2 = cal_total_sales(filtered_df_2)
            total_sales_diff= total_sales_2 - total_sales_1
            total_sales_diff_per= "{:.2f}".format(total_sales_diff/total_sales_1*100)

            total_profit_1 = cal_total_profit(filtered_df_1)
            total_profit_2 = cal_total_profit(filtered_df_2)
            total_profit_diff= total_profit_2 - total_profit_1
            total_profit_diff_per= "{:.2f}".format(total_profit_diff/total_profit_1*100)

            total_orders_1=filtered_df_1['Order ID'].nunique()
            total_orders_2=filtered_df_2['Order ID'].nunique()
            total_orders_diff= total_orders_2 - total_orders_1
            total_orders_diff_per= "{:.2f}".format(total_orders_diff/total_orders_1*100)

            total_qty_1 = filtered_df_1['Quantity'].sum()
            total_qty_2 = filtered_df_2['Quantity'].sum()
            total_qty_diff= total_qty_2 - total_qty_1
            total_qty_diff_per= "{:.2f}".format(total_qty_diff/total_qty_1*100)

            average_margin_1=cal_average_margin(filtered_df_1)
            average_margin_2=cal_average_margin(filtered_df_2)
            average_margin_diff= average_margin_2 - average_margin_1
            average_margin_diff_per= "{:.2f}".format(average_margin_diff/average_margin_1*100)

            filtered_df_1_return=filtered_df_1_return [filtered_df_1_return ['Order Status'].isin(["Returned","Refunded"])]
            total_return_1= filtered_df_1_return ['Order ID'].nunique()
            filtered_df_2_return=filtered_df_2_return [filtered_df_2_return ['Order Status'].isin(["Returned","Refunded"])]
            total_return_2= filtered_df_2_return ['Order ID'].nunique()
            total_return_diff= total_return_2 - total_return_1
            total_return_diff_per= "{:.2f}".format(total_return_diff/total_return_1*100)

            coln1, coln2, coln3, coln4, coln5, coln6 = st.columns(6)
            with coln1.container():
                coln1.metric("Sales:", f"RM {format_value(total_sales_1)}", f"{total_sales_diff_per}% ({format_value(total_sales_2)})")
            with coln2.container():
                coln2.metric("Profit:", f"RM {format_value(total_profit_1)}", f"{total_profit_diff_per}% ({format_value(total_profit_2)})")
            with coln3.container():
                coln3.metric("Total Orders:", f"{total_orders_1}", f"{total_orders_diff_per}% ({total_orders_1})")
            with coln4.container():
                coln4.metric("Total Units Sold:", f"{total_qty_1}", f"{total_qty_diff_per}% ({total_qty_1})")
            with coln5.container():
                #formatted_average_margin_diff = "{:.2f}".format(average_margin_diff)
                coln5.metric("Average Margin per Order:", f"{average_margin_1}", f"{average_margin_diff_per}% ({average_margin_2})")
            with coln6.container():
                coln6.metric("Returns/Refunds:", f"{total_return_1}", f"{total_return_diff_per}% ({total_return_2})", "inverse")

            st.write("(Period 1 above, Period 2 below)")

            #totalgroup_chart(grouped_df_1, grouped_df_2)
            col1, col2, col3 = st.columns([1,5,1])
            #with col1:
            with col2:
                totalgroup_chart(grouped_df_1, grouped_df_2)
            colA1, colA2 = st.columns(2)
            with colA1:
                trend_chart(combined_df, column_name='Unit Total', title='Sales', color=['blue','lightblue'])
            with colA2:
                trend_chart(combined_df, column_name='Margin Per Item', title='Profit', color=['red','lightpink'])
            colB1, colB2 = st.columns(2)
            with colB1:
                trend_chart(combined_df, column_name='Quantity', title='Orders', color=['green','lightgreen'])
            with colB2:
                trend_chart(combined_df, column_name='Order ID', title='Units', color=['Goldenrod','lightyellow'])

        else:
            mode
            st.error('Error: Please ensure that start dates are before end dates for both ranges.')

create_app(filled_df)
