import streamlit as st
import googlemaps
from streamlit_folium import st_folium
import folium
import pandas as pd
from PIL import Image
import requests
from io import BytesIO
import urllib.parse

# Function to validate API key
def is_valid_key(api_key):
    try:
        gmaps = googlemaps.Client(key=api_key)
        gmaps.geocode('New York')  # Test geocode request
        return True
    except Exception:
        return False

# Function to fetch details of multiple places
def get_places_details(gmaps, place_ids):
    places = []
    for place_id in place_ids:
        try:
            details = gmaps.place(place_id=place_id).get('result', {})
            location = details.get('geometry', {}).get('location', {})
            places.append({
                'name': details.get('name', 'N/A'),
                'rating': details.get('rating', 'N/A'),
                'num_ranking': details.get('user_ratings_total', 'N/A'),
                'categories': ', '.join(details.get('types', [])),
                'phone': details.get('formatted_phone_number', 'N/A'),
                'status': "Open" if details.get('opening_hours', {}).get('open_now') else "Closed",
                'latitude': location.get('lat', 'N/A'),
                'longitude': location.get('lng', 'N/A'),
                'place_id': place_id,
                'geometry': location,
                'photos': details.get('photos', [])
            })
        except Exception:
            pass  # Skip invalid place_ids
    return places

# Function to display a map with multiple markers
def display_map(places):
    if places:
        map_center = [places[0]['geometry']['lat'], places[0]['geometry']['lng']] if places[0].get('geometry') else [0, 0]
        map_view = folium.Map(location=map_center, tiles="CartoDB positron", zoom_start=12)
        for place in places:
            location = place.get('geometry')
            if location:
                folium.Marker(
                    [location['lat'], location['lng']],
                    popup=place.get('name', 'Location')
                ).add_to(map_view)
        st_folium(map_view, width=700)

# Function to generate Google My Maps link
def generate_google_maps_link(places):
    base_url = "https://www.google.com/maps/d/u/0/edit"
    markers = []
    for place in places:
        if place['latitude'] != 'N/A' and place['longitude'] != 'N/A':
            name_encoded = urllib.parse.quote(place['name'])
            markers.append(f"{place['latitude']},{place['longitude']},{name_encoded}")
    if markers:
        link = base_url + "?mid=1&ll=" + "&markers=".join(markers)
        return link
    return None

# Function to fetch photos for a place
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

# Streamlit app
def app():
    st.title("Google Places Viewer")
    
    # Step 1: Input API Key
    api_key = st.text_input("Enter your Google Maps API Key", type="password")
    
    if api_key:
        # Step 2: Validate API Key
        if is_valid_key(api_key):
            st.success("API Key is valid!")
            
            # Step 3: Input up to 10 Place IDs
            place_ids_input = st.text_area("Enter up to 20 Google Place IDs (one per line)").strip()
            if place_ids_input:
                place_ids = place_ids_input.splitlines()
                if len(place_ids) > 20:
                    st.error("Please enter up to 20 Place IDs.")
                else:
                    # Fetch details for the entered Place IDs
                    gmaps = googlemaps.Client(key=api_key)
                    places = get_places_details(gmaps, place_ids)
                    
                    if places:
                        # Step 4: Display map on the right
                        st.subheader("Locations on Map")
                        display_map(places)
                        
                        # Step 5: Display table on the left
                        st.subheader("Place Details")
                        place_data = pd.DataFrame([
                            {
                                'Name': place['name'],
                                'Rating': place['rating'],
                                'Number of Reviews': place['num_ranking'],
                                'Categories': place['categories'],
                                'Phone': place['phone'],
                                'Status': place['status'],
                                'Latitude': place['latitude'],
                                'Longitude': place['longitude'],
                                'Place ID': place['place_id']
                            } for place in places
                        ])
                        
                        # Interactive table
                        st.write("Interactive Table")
                        selected_rows = st.multiselect(
                            "Select rows to delete:",
                            place_data.index,
                            format_func=lambda x: place_data.iloc[x]['Name']
                        )
                        
                        if selected_rows:
                            st.write("Rows to delete:")
                            st.dataframe(place_data.loc[selected_rows])
                        
                        # Update the table after deleting selected rows
                        updated_place_data = place_data.drop(selected_rows)
                        st.write("Updated Table")
                        st.dataframe(updated_place_data)
                        
                        # Step 6: Export the updated data
                        st.download_button(
                            label="Export Data as CSV",
                            data=updated_place_data.to_csv(index=False),
                            file_name="updated_places.csv",
                            mime="text/csv"
                        )
                        
                        # Step 7: Show photos for selected places
                        for idx, row in updated_place_data.iterrows():
                            with st.expander(f"Show Photos for {row['Name']}"):
                                place_id = row['Place ID']
                                photos = get_place_photos(gmaps, place_id)
                                if photos:
                                    for photo_url in photos:
                                        image = Image.open(BytesIO(requests.get(photo_url).content))
                                        st.image(image, use_column_width=True)
                                else:
                                    st.write("No photos available.")

                        # Step 8: Generate and display Google My Maps link
                        st.subheader("Shareable Google My Maps Link")
                        my_maps_link = generate_google_maps_link(places)
                        if my_maps_link:
                            st.write("Use the link below to view or share the map:")
                            st.markdown(f"[View Map]({my_maps_link})", unsafe_allow_html=True)
                        else:
                            st.warning("Could not generate a map link. Ensure all places have valid coordinates.")
                    else:
                        st.warning("No valid places found. Please check your Place IDs.")
        else:
            st.error("Invalid API Key. Please try again.")
    else:
        st.info("Please enter your Google Maps API Key.")

if __name__ == "__main__":
    app()
