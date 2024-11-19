import streamlit as st
import googlemaps
import pandas as pd
import requests
from io import BytesIO
from PIL import Image

# Function to check if the API key is valid
def is_valid_key(api_key):
    try:
        gmaps = googlemaps.Client(key=api_key)
        # Test the key by trying to geocode a place
        geocode_result = gmaps.geocode('New York')
        return True
    except Exception as e:
        return False

# Function to get place details from Google Maps API
def get_place_details(gmaps, place_ids):
    places = []
    for place_id in place_ids:
        details = gmaps.place(place_id=place_id)
        result = details.get('result', {})
        places.append({
            'name': result.get('name'),
            'rating': result.get('rating', 'N/A'),
            'num_ranking': result.get('user_ratings_total', 'N/A'),
            'categories': ', '.join([category['name'] for category in result.get('types', [])])
        })
    return places

# Function to get photos of a place
def get_place_photos(gmaps, place_id):
    photos = gmaps.place_photos(place_id=place_id, maxwidth=400)
    photo_urls = []
    for photo in photos.get('result', {}).get('photos', []):
        photo_reference = photo.get('photo_reference')
        if photo_reference:
            photo_urls.append(f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={gmaps.api_key}")
    return photo_urls

# Streamlit UI
def app():
    # Ask user for API key
    api_key = st.text_input('Enter your Google Maps API Key', type='password')
    
    if api_key:
        # Validate API Key
        if is_valid_key(api_key):
            st.success('API Key is valid!')
            
            # Ask for place_ids input
            place_ids_input = st.text_area('Enter up to 10 Google Place IDs (comma separated)').strip()
            
            if place_ids_input:
                place_ids = place_ids_input.split(',')
                if len(place_ids) <= 10:
                    # Initialize Google Maps client
                    gmaps = googlemaps.Client(key=api_key)
                    
                    # Get place details
                    places = get_place_details(gmaps, place_ids)
                    df = pd.DataFrame(places)

                    # Display table on the left
                    st.sidebar.title('Place Information')
                    st.sidebar.dataframe(df)

                    # Display map and plot markers on the map
                    st.title('Google Places Map')
                    map_center = (37.7749, -122.4194)  # Default to San Francisco (you can adjust this)
                    map = st.map(df[['lat', 'lng']].dropna())

                    # If the user clicks on a place, show its photos
                    selected_place = st.selectbox('Select a place to view photos', df['name'].tolist())
                    selected_place_id = place_ids[df['name'].tolist().index(selected_place)]
                    
                    # Get photos
                    photos = get_place_photos(gmaps, selected_place_id)
                    if photos:
                        st.image([Image.open(BytesIO(requests.get(url).content)) for url in photos], width=400)
                    else:
                        st.write("No photos available.")
                else:
                    st.error("Please enter up to 10 place IDs.")
            else:
                st.warning("Please enter at least one Place ID.")
        else:
            st.error('Invalid API Key. Please try again.')
    else:
        st.info('Please enter your Google Maps API key above.')

if __name__ == "__main__":
    app()
