from flask import Flask, request, render_template, jsonify
import pandas as pd
import plotly.graph_objects as go
import io
import math
import base64

app = Flask(__name__)

COLOR_SCHEME = {
    'ARCB': 'rgba(160, 160, 160, 0.5)',  # Example colors
    'BCKL': 'rgba(255, 0, 0, 0.5)',
    'CAD': 'rgba(255, 165, 0, 0.5)',
    'CPOR': 'rgba(0, 255, 0, 0.5)',
    'CEC': 'rgba(0, 128, 0, 0.5)',
    'DNT': 'rgba(255, 255, 0, 0.5)',
    'EC': 'rgba(0, 0, 255, 0.5)',
    'EML': 'rgba(0, 128, 255, 0.5)',
    'IF': 'rgba(255, 0, 255, 0.5)',
    'ILI': 'rgba(128, 0, 128, 0.5)',
    'IML': 'rgba(108, 0, 128, 0.5)',  # Added IML color
    'LAM': 'rgba(128, 128, 128, 0.5)',
    'LIN': 'rgba(128, 0, 0, 0.5)',
    'MD': 'rgba(255, 192, 203, 0.5)',
    'MFR': 'rgba(0, 255, 255, 0.5)',
    'MILL': 'rgba(255, 255, 255, 0.5)',
    'PDW': 'rgba(0, 0, 0, 0.5)',
    'POR': 'rgba(128, 128, 0, 0.5)',
    'SCC': 'rgba(255, 128, 0, 0.5)',
    'UNC': 'rgba(128, 255, 0, 0.5)',
    'UNF': 'rgba(0, 255, 128, 0.5)',
    'WR': 'rgba(0, 128, 255, 0.5)',
    'WRNK': 'rgba(128, 0, 255, 0.5)',
    'WS': 'rgba(0, 255, 255, 0.5)',
 
}

def clean_data(df):
    required_columns = ['Indication Type', 'Indication Number', 'Axial Distance', 'Clock Position', 'Length', 'Width', 'Pipe Diameter']
    for col in required_columns:
        if col not in df.columns:
            raise KeyError(f"Required column '{col}' not found in the data. Available columns: {df.columns}")

    for col in required_columns[2:]:
        if col != 'Clock Position':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if pd.api.types.is_string_dtype(df['Clock Position']):
        df['Clock Position'] = pd.to_datetime(df['Clock Position'], format='%H:%M').dt.time
    elif pd.api.types.is_numeric_dtype(df['Clock Position']):
        df['Clock Position'] = df['Clock Position'].apply(lambda x: f"{int(x):02d}:00").apply(pd.to_datetime).dt.time

    df['Clock Position Numeric'] = df['Clock Position'].apply(lambda x: x.hour + x.minute / 60.0)
    df['Clock Position'] = df['Clock Position'].apply(lambda x: x.strftime('%H:%M'))

    df.dropna(subset=required_columns, inplace=True)
    
    if df.empty:
        raise ValueError("DataFrame is empty after cleaning. Please check the input data.")

    return df

def generate_chart(df, center_clock_position):
    pipe_diameter = df['Pipe Diameter'].iloc[0]  # Pipe diameter in inches
    circumference = math.pi * pipe_diameter  # Circumference in inches

    fig = go.Figure()

    if center_clock_position == 12:
        start_time = 6
    else:  # center_clock_position == 6
        start_time = 0
    
    tickvals = [(start_time + i * 0.5) % 12 for i in range(25)]
    ticktext = [f"{int(val // 1):02d}:{int((val % 1) * 60):02d}" for val in tickvals]

    for ind_type in df['Indication Type'].unique():
        subset = df[df['Indication Type'] == ind_type]
        for _, row in subset.iterrows():
            adjusted_clock_position = (row['Clock Position Numeric'] - start_time) % 12
            width_hours = row['Width'] / circumference * 24  # Convert width to clock hours for full pipe
            
            fig.add_shape(type="rect",
                          x0=row['Axial Distance'],
                          y0=adjusted_clock_position,
                          x1=row['Axial Distance'] + row['Length'] / 12,  # Convert length from inches to feet
                          y1=adjusted_clock_position + width_hours,
                          line=dict(color=COLOR_SCHEME[ind_type]),
                          fillcolor=COLOR_SCHEME[ind_type],
                          name=ind_type)

            fig.add_trace(go.Scatter(
                x=[(row['Axial Distance'] + row['Axial Distance'] + row['Length'] / 12) / 2],
                y=[(adjusted_clock_position + adjusted_clock_position + width_hours) / 2],
                text=f"Type: {row['Indication Type']}<br>"
                     f"Number: {row['Indication Number']}<br>"
                     f"Axial Distance: {row['Axial Distance']}<br>"
                     f"Clock Position: {row['Clock Position']}<br>"
                     f"Original Length: {row['Length']:.2f} in<br>"
                     f"Width: {row['Width']:.3f} in",
                mode='markers',
                marker=dict(size=1, color='rgba(0,0,0,0)'),
                hoverinfo="text",
                showlegend=False
            ))

    # Add legend items
    for ind_type, color in COLOR_SCHEME.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            legendgroup=ind_type,
            showlegend=True,
            name=ind_type
        ))

    fig.update_layout(
        title='Indication Map',
        xaxis=dict(title='Axial Distance (ft)'),
        yaxis=dict(
            title='Clock Position (hh:mm)',
            tickvals=tickvals,
            ticktext=ticktext,
            autorange='reversed'
        ),
        barmode='overlay',
        legend=dict(title='Indication Type'),
        height=800  # Increase the height of the chart
    )

    plot_html = fig.to_html(full_html=False)
    print("Generated chart HTML length:", len(plot_html))

    chart_data = fig.to_plotly_json()  # Extract chart data for dynamic plotting
    return plot_html, chart_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    data_df = pd.read_excel(file, sheet_name="Cleaned Data")
    try:
        cleaned_data = clean_data(data_df)
        chart_html, chart_data = generate_chart(cleaned_data, center_clock_position=12)  # Default to 12:00 view
        file.seek(0)
        encoded_file = base64.b64encode(file.read()).decode('utf-8')
        return render_template('chart.html', chart_html=chart_html, file=encoded_file, chart_data=chart_data)
    except Exception as e:
        return str(e)

@app.route('/update_chart', methods=['POST'])
def update_chart():
    data = request.json
    center_clock_position = int(data.get('center_clock_position', 12))  # Ensure this is an integer
    file_data = base64.b64decode(data.get('file'))
    print(f"Decoded file data length: {len(file_data)}")
    try:
        data_df = pd.read_excel(io.BytesIO(file_data), sheet_name="Cleaned Data")
        print("Data read from Excel file successfully.")
        cleaned_data = clean_data(data_df)
        print("Data cleaned successfully.")
        chart_html, chart_data = generate_chart(cleaned_data, center_clock_position=center_clock_position)
        print("Generated new chart HTML.")
        return jsonify({'chart_html': chart_html, 'chart_data': chart_data})
    except Exception as e:
        print(f"Error: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)

