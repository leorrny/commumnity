import streamlit as st
import googlemaps
from streamlit_folium import st_folium
import folium
import pandas as pd
from PIL import Image
import requests
from io import BytesIO
import urllib.parse
import json
import openai
import time

# Function to validate Google Maps API key
def is_valid_key(api_key):
    try:
        gmaps = googlemaps.Client(key=api_key)
        gmaps.geocode('New York')  # Test geocode request
        return True
    except Exception:
        return False

# Function to validate OpenAI API key
def is_valid_openai_key(api_key):
    try:
        openai.api_key = api_key
        openai.models.list()
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
                'reviews': details.get('reviews','N/A'),
                'status': "Open" if details.get('opening_hours', {}).get('open_now') else "Closed",
                'latitude': location.get('lat', 'N/A'),
                'longitude': location.get('lng', 'N/A'),
                'place_id': place_id,
                'photos': details.get('photos', []),
                'url': details.get('url','n/a')
            })
        except Exception:
            pass
    return places

def display_photos(places, gmaps):
    st.subheader("Photos of Places")
    for place in places:
        with st.expander(f"Photos for {place['name']} ({place['place_id']})"):
            photo_urls = get_place_photos(gmaps, place['place_id'])
            if photo_urls:
                for url in photo_urls:
                    st.image(url, caption=place['name'], use_column_width=True)
            else:
                st.write("No photos available for this place.")

# Function to display a map with multiple markers
def display_map(places):
    if places:
        map_center = [places[0]['latitude'], places[0]['longitude']] if places[0].get('latitude') != 'N/A' else [0, 0]
        map_view = folium.Map(location=map_center, tiles="CartoDB positron", zoom_start=12)
        for place in places:
            location = place
            if location.get('latitude') != 'N/A' and location.get('longitude') != 'N/A':
                folium.Marker(
                    [location['latitude'], location['longitude']],
                    popup=place.get('name', 'Location')
                ).add_to(map_view)
        st_folium(map_view, width=700)

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

# Function to categorize store with OpenAI
def categorize_store_with_openai(place_info, photo_urls, prompt, api_key):
    openai.api_key = api_key
    messages = [
        {
            "role": "system",
            "content": prompt
        },
        {
            "role": "user",
            "content": f"Store details from Google Maps:\n{json.dumps(place_info, indent=2)}",
        }
    ]
    for url in photo_urls:
        messages.append({"role": "user", "content": f"Photos of the place: {url}"})

    try:
        response = openai.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            max_tokens=10000,
            temperature =1,
        top_p=1,
        response_format={"type": "json_object"}
        )
        response_data = json.loads(response.choices[0].message.content)
        return response_data
    except Exception as e:
        return {"error": str(e)}

# Streamlit app
def app():
    st.title("Google Places Viewer with OpenAI Insights")
    
    # Step 1: Input Google Maps API Key
    gmaps_api_key = st.text_input("Enter your Google Maps API Key",type="password")
    gmaps_valid = False
    if gmaps_api_key:
        if is_valid_key(gmaps_api_key):
            st.success("Google Maps API Key is valid!")
            gmaps_valid = True
        else:
            st.error("Invalid Google Maps API Key. Please try again.")

    # Step 2: Optional: Input OpenAI API Key
    openai_api_key = st.text_input("Enter your OpenAI API Key (Optional)", type="password")
    openai_valid = False
    if openai_api_key:
        if is_valid_openai_key(openai_api_key):
            st.success("OpenAI API Key is valid!")
            openai_valid = True
        else:
            st.error("Invalid OpenAI API Key. Please try again.")

    # Step 3: Input Place IDs
    if gmaps_valid:
        place_ids_input = st.text_area("Enter up to 20 Google Place IDs (one per line)").strip()
        if place_ids_input:
            place_ids = place_ids_input.splitlines()
            if len(place_ids) > 20:
                st.error("Please enter up to 20 Place IDs.")
            else:
                gmaps = googlemaps.Client(key=gmaps_api_key)
                places = get_places_details(gmaps, place_ids)
                if places:
                    st.subheader("Locations on Map")
                    display_map(places)
                    
                    # Display Place Details
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
                            'Place ID': place['place_id'],
                            'url': place['url']
                        } for place in places
                    ])
                    st.dataframe(place_data)

                    display_photos(places, gmaps)
                    # Step 4: OpenAI Analysis
                    if openai_valid:
                        st.subheader("Analyze with OpenAI")
                        prompt = st.text_area("Modify the OpenAI query", value="""
                        Use more direct language. You're mentoring sales representatives of a grocery, beverages, and tobacco distributor. 
                        Analyze the store information and categorize it based on the following fields:
                        - **Store Description**: Describe the store based on photos and data.
                        - **Area Info**: Provide socio-demographic insights about the area.
                        - **Store Potential**: Rate the store potential on a scale of 1-10.
                        Return a structured JSON object containing 'Store Description', 'Area Info', and 'Store Potential'.
                        """, height=200)
                        
                        results = []
                        with st.spinner("Analyzing stores with OpenAI..."):
                            for idx, place in enumerate(places):
                                photo_urls = get_place_photos(gmaps, place['place_id'])
                                response = categorize_store_with_openai(place, photo_urls, prompt, openai_api_key)
                                results.append(response)
                                time.sleep(1)  # Avoid hitting rate limits

                        # Merge OpenAI results with place data
                        openai_data = pd.DataFrame(results)
                        combined_data = pd.concat([place_data, openai_data], axis=1)
                        st.dataframe(combined_data)
                        st.markdown("""
    <style>
        .stTable tr {
            height: 50px; # use this to adjust the height
        }
    </style>
""", unsafe_allow_html=True)
                        # Function to display photos with fold/unfold feature




                        # Export data
                        st.download_button(
                            label="Export Combined Data as CSV",
                            data=combined_data.to_csv(index=False),
                            file_name="places_with_analysis.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("No valid places found. Please check your Place IDs.")

if __name__ == "__main__":
    app()
