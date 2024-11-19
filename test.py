import streamlit as st
import googlemaps
from streamlit_folium import st_folium
import folium
from PIL import Image
import requests
from io import BytesIO

# Function to check if the API key is valid
def is_valid_key(api_key):
    try:
        gmaps = googlemaps.Client(key=api_key)
        # Test the key by trying to geocode a place
        gmaps.geocode('New York')
        return True
    except Exception:
        return False

# Function to get place details
def get_place_details(gmaps, place_id):
    details = gmaps.place(place_id=place_id).get('result', {})
    return {
        'name': details.get('name', 'N/A'),
        'rating': details.get('rating', 'N/A'),
        'num_ranking': details.get('user_ratings_total', 'N/A'),
        'categories': ', '.join(details.get('types', [])),
        'geometry': details.get('geometry', {})
    }

# Function to get photos of a place
def get_place_photos(gmaps, place_id):
    details = gmaps.place(place_id=place_id).get('result', {})
    photos = details.get('photos', [])
    photo_urls = []
    for photo in photos:
        photo_reference = photo.get('photo_reference')
        if photo_reference:
            photo_urls.append(
                f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={gmaps.key}"
            )
    return photo_urls

# Function to display map using folium
def display_map(place_info):
    if "geometry" in place_info and "location" in place_info["geometry"]:
        latitude = place_info["geometry"]["location"]["lat"]
        longitude = place_info["geometry"]["location"]["lng"]
        map_view = folium.Map(location=[latitude, longitude], tiles="CartoDB positron", zoom_start=15)
        folium.Marker([latitude, longitude], popup=place_info.get("name", "Location")).add_to(map_view)
        st_folium(map_view, width=700)

# Streamlit app
def app():
    st.title("Google Place Viewer")

    # Step 1: Ask for the API key
    api_key = st.text_input("Enter your Google Maps API Key", type="password")
    
    if api_key:
        # Validate API Key
        if is_valid_key(api_key):
            st.success("API Key is valid!")
            
            # Step 2: Input a single place_id
            place_id = st.text_input("Enter a Google Place ID:")
            
            if place_id:
                # Initialize Google Maps client
                gmaps = googlemaps.Client(key=api_key)
                
                # Step 3: Fetch place details
                place_details = get_place_details(gmaps, place_id)
                st.subheader("Place Details")
                st.write(f"**Name:** {place_details['name']}")
                st.write(f"**Rating:** {place_details['rating']}")
                st.write(f"**Number of Reviews:** {place_details['num_ranking']}")
                st.write(f"**Categories:** {place_details['categories']}")
                
                # Step 4: Display location on map
                st.subheader("Location on Map")
                display_map(place_details)
                
                # Step 5: Display photos
                photos = get_place_photos(gmaps, place_id)
                st.subheader("Photos")
                if photos:
                    for photo_url in photos:
                        image = Image.open(BytesIO(requests.get(photo_url).content))
                        st.image(image, use_column_width=True)
                else:
                    st.write("No photos available.")
        else:
            st.error("Invalid API Key. Please try again.")
    else:
        st.info("Please enter your Google Maps API Key.")

if __name__ == "__main__":
    app()
