import folium
import networkx as nx
import csv
import plotly.graph_objects as go
from branca.element import Figure
import random

# Function to parse the CSV file
def parse_csv_file(file_path):
    with open(file_path, 'r') as input_file:
        reader = csv.reader(input_file)
        data = list(reader)
    entities = {}
    edges = []
    subtypes = set()
    all_start_times = []

    for row in data[1:]:
        entity = row[5]
        coords = [float(row[-2]), float(row[-1])]
        start_time = int(row[0])
        end_time = int(row[1])
        subtype = row[3]
        description = row[4]
        ID = row[-4]
        condition = row[-5]
        if entity not in entities:
            entities[entity] = []
        entities[entity].append({
            'name': entity+"_"+str(start_time),
            'coords': coords, 
            'start_time': start_time, 
            'end_time': end_time, 
            'subtype': subtype, 
            'description': description, 
            'ID': ID, 
            'condition': condition
        })
        edges.append(('center', entity+"_"+str(start_time)))
        subtypes.add(subtype)
        all_start_times.append(start_time)

    return entities, edges, list(subtypes), all_start_times



# Function to create the map visualization
def create_map_visualization(entities, edges, subtypes, all_start_times, map_center, zoom_start):
    # Create a base map
    map_obj = folium.Map(location=map_center, zoom_start=zoom_start)

    # Create a color map for the time periods
    color_map = folium.LinearColormap(
        colors=['green', 'yellow', 'red'],
        vmin=min(min(entity['start_time'] for entity in data) for data in entities.values()),
        vmax=max(max(entity['end_time'] for entity in data) for data in entities.values())
        
    )

    # Create a NetworkX graph from the entities and edges
    G = nx.Graph()
    G.add_node('center', pos=map_center)
    for entity, data in entities.items():
        for entity_data in data:
            G.add_node(f"{entity}_{entity_data['start_time']}", pos =entity_data['coords'])
    G.add_edges_from(edges)
    # print(edges)
    # print(len(edges))
    # print(counted)
    # print(G.nodes)
    # print(G.edges)
    # print(len(G.nodes))
    # print(len(G.edges))

    # Create a FeatureGroup for each subtype
    feature_groups = {subtype: folium.FeatureGroup(name=subtype) for subtype in subtypes}


    # Add entities and edges to the map
    used_markers = []
    for entity, data in entities.items():
        for entity_data in data:
            if entity_data['coords'] in used_markers:
                marker = folium.Marker(
                    location=[entity_data['coords'][0]+0.02, entity_data['coords'][1] + 0.02],
                    tooltip=f"{entity} ({entity_data['subtype']})<br>{entity_data['description']}<br>Time Period: {entity_data['start_time']} - {entity_data['end_time']}<br>Inscriptiones Graecae Source: {entity_data['ID']}<br>Condition of inscription: {entity_data['condition']}",
                    icon=folium.Icon(color='blue')
                )
                used_markers.append([entity_data['coords'][0]+0.02, entity_data['coords'][1] + 0.02])
                feature_groups[entity_data['subtype']].add_child(marker)
            else:
                marker = folium.Marker(
                    location=entity_data['coords'],
                    tooltip=f"{entity} ({entity_data['subtype']})<br>{entity_data['description']}<br>Time Period: {entity_data['start_time']} - {entity_data['end_time']}<br>Inscriptiones Graecae Source: {entity_data['ID']}<br>Condition of inscription: {entity_data['condition']}",
                    icon=folium.Icon(color='blue')
                )
                used_markers.append(entity_data['coords'])
                text_marker = folium.Marker(
                location=entity_data['coords'],
                icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: black;">{entity}</div>')
                )
                feature_groups[entity_data['subtype']].add_child(marker)
                feature_groups[entity_data['subtype']].add_child(text_marker)

    folium.Marker(
        location=map_center,
        tooltip='Athens',
        icon=folium.Icon(color='blue')
    ).add_to(map_obj)

    used_points = []
    for source, target in G.edges():
        source_coords = G.nodes[source]['pos']
        target_coords = G.nodes[target]['pos']
        for dictionary in entities[f'{target[:-4]}']:
            if dictionary['name'] == target:
                start_time = dictionary['start_time']
                end_time = dictionary['end_time']
                subtype = dictionary['subtype']
            else: pass
        color = color_map(start_time)
        line_style, line_weight = get_line_style(subtype)
        if target_coords in used_points:
            source_coords = [source_coords[0]+0.02, source_coords[1] + 0.02]
            target_coords = [target_coords[0]+0.02, target_coords[1] + 0.02]
            used_points.append(target_coords)
        else:
            used_points.append(target_coords)
        line = folium.PolyLine(
            locations=[source_coords, target_coords],
            color=color,
            weight=line_weight,
            dash_array=line_style,
            tooltip=f"{source} - {target} ({start_time} - {end_time})"
        )
        feature_groups[subtype].add_child(line)

    for fg in feature_groups.values():
        map_obj.add_child(fg)

    folium.LayerControl().add_to(map_obj)

    # Create time series visualization
    fig = create_time_series(entities, color_map)

    # Convert plotly figure to HTML
    time_series_html = fig.to_html(full_html=False)
    
    # Add time series to the map
    map_obj.get_root().html.add_child(folium.Element(time_series_html))
    return map_obj

def get_line_style(subtype):
    if subtype == 'Non Agression':
        return '10, 10', 2
    elif subtype == 'Individual Honour' or subtype == 'Collective Honour':
        return '2, 5', 2
    elif subtype == 'Proxenos':
        return '10, 5, 2, 5', 2
    elif subtype == 'Alliance':
        return None, 5
    else:
        return None, 2

def create_time_series(entities, color_map):
    # Collect all start times and their associated information
    time_data = []
    for entity, data_list in entities.items():
        for data in data_list:
            time_data.append({
                'entity': entity,
                'start_time': data['start_time'],
                'subtype': data['subtype'],
                'description': data['description'],
                'end_time': data['end_time'],
                'ID': data['ID'], 
                'condition': data['condition']
            })
    # Sort time_data by start_time in descending order
    time_data.sort(key=lambda x: x['start_time'], reverse=True)
    
    # Extract sorted times and create hover texts
    sorted_times = [data['start_time'] for data in time_data]
    hover_texts = [
        f"{data['entity']} ({data['subtype']})<br>{data['description']}<br>Time Period: {data['start_time']} - {data['end_time']}<br>Inscriptiones Graecae Source: {data['ID']}<br>Condition of inscription: {data['condition']}"
        for data in time_data
    ]
    
    # Create the time series plot
    fig = go.Figure()
    
    # Add lines connecting the markers
    fig.add_trace(go.Scatter(
        x=sorted_times,
        y=[1]*len(sorted_times),
        mode='lines',
        line=dict(color='lightgray', width=1),
        hoverinfo='none'
    ))
    
    # Add markers for each start time
    fig.add_trace(go.Scatter(
        x=sorted_times,
        y=[1 + random.uniform(-0.1, 0.1) for _ in sorted_times],  # Add jitter,
        mode='markers',
        marker=dict(
            size=8,
            color=sorted_times,
            colorscale=['green', 'yellow', 'red'],
            showscale=True
        ),
        text=hover_texts,
        hoverinfo='text'
    ))
    
    # Update layout
    fig.update_layout(
        title='Athenian Diplomatic Decrees 458-404',
        yaxis_visible=False,
        height=100,  # Reduced height
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    
    # Reverse x-axis so highest number is on the left
    fig.update_xaxes(autorange="reversed")
    
    return fig


# Example usage
entities, edges, subtypes, all_start_times= parse_csv_file('458-404_All_Decrees.csv')
map_center = [37.975504201, 23.72264864]  # Athens coordinates
zoom_start = 6

map_obj = create_map_visualization(entities, edges, subtypes, all_start_times, map_center, zoom_start)
map_obj.save('458-404_All_Decrees.html')
