import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
app = Flask(__name__, static_folder="static", template_folder="templates")

#api
OPENAI_API_KEY =os.environ.get("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# prompt sent to the AI
PROMPT_TEMPLATE = """
**User Parameters:**
1.  **Dosha:** {dosha}
2.  **Location:** {location}
3.  **Weather:** {weather}
4.  **Primary Disease/Health Condition:** {disease}
5.  **Physiological Data:**
    * Daily Water Intake: {water}L
    * BMI: {bmi}
    * Sleep Quality: {sleep}
6.  **Secondary Condition:** {secondary_condition}
7.  **Appetite:** {appetite}
8.  **Current Day:** {current_day}
"""

# This is the system instruction that guides the AI's behavior and response format.
SYSTEM_INSTRUCTION = """
You are an expert clinical nutritionist and Ayurvedic specialist.

Task: Generate a **7-day Ayurvedic diet plan** starting from the provided Current Day.
If Current Day is Wednesday, Day 1 should be Wednesday and you should provide Day 1 → Day 7 consecutively.

Requirements:
- Prioritize foods that are locally available and seasonal for the provided Location and Weather.
- Use culturally appropriate and affordable items common to that city/region.
- For each day include sections: "General Recommendations", "Early Morning", "Breakfast",
  "Mid-Morning Snack", "Lunch", "Evening Snack", "Dinner", "Bedtime".
- Provide portion sizes for every food item in grams (g) or milliliters (ml).
- Briefly explain why each meal/item is suitable with respect to Dosha, Disease, BMI, Appetite and Weather.
- Adjust portion sizes based on BMI & Appetite (e.g., underweight → slightly larger portions; overweight → controlled portions).
- Avoid repeating the exact same full meal across multiple days; rotate where possible.
- Output using markdown headings, e.g. "### Day 1 (Wednesday)" and bullet lists for meals.
"""


# The main route that serves the webpage (index.html).
@app.route("/")
def index():
    # This function finds "index.html" in your "templates" folder and sends it to the browser.
    return render_template("index.html")


# This route handles the form submission from the frontend.
@app.route("/generate", methods=["POST"])
def generate_plan():
    try:
        # --- Collect data from the frontend form ---
        # Each `request.form.get()` corresponds to the `name` attribute of an input in index.html.
        dosha = request.form.get("dosha", "mixed")  # From the 'dosha' select dropdown
        disease = request.form.get("disease", "None")  # From the 'disease' input field
        water = request.form.get("water", "2")  # From the 'water' input field
        bmi = request.form.get("bmi", "22")  # From the 'bmi' input field
        sleep = request.form.get("sleep", "Good")  # From the 'sleep' select dropdown
        secondary_condition = request.form.get("secondary_condition", "None")  # From the 'secondary_condition' input
        appetite = request.form.get("appetite", "Normal")  # From the 'appetite' select dropdown

        # --- Handle Location Data ---
        # Get the manual location input, which is used if geolocation fails or isn't provided.
        fallback_location = request.form.get("location", "Unknown")

        # Get latitude and longitude from the hidden input fields filled by the script.js.
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        location_name = fallback_location
        weather_desc = "Not available"  # Default weather description

        # If we have coordinates and an API key, fetch real-time weather.
        if latitude and longitude and OPENWEATHER_API_KEY:
            try:
                weather_url = (
                    f"https://api.openweathermap.org/data/2.5/weather?"
                    f"lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
                )
                resp = requests.get(weather_url, timeout=10)
                resp.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
                w_data = resp.json()

                city = w_data.get("name", "")
                country = w_data.get("sys", {}).get("country", "")
                if city and country:
                    location_name = f"{city}, {country}"

                weather_main = w_data.get("weather", [{}])[0].get("description", "clear sky")
                temp = w_data.get("main", {}).get("temp")
                if temp is not None:
                    weather_desc = f"{weather_main.title()}, Temp: {temp}°C"
                else:
                    weather_desc = weather_main.title()
            except requests.exceptions.RequestException as ex:
                # If the weather API fails, we print a warning and use the manual location.
                print(f"Warning: Could not fetch weather data. {ex}")
                # location_name is already set to the fallback, so no change is needed.

        # Get the current day of the week to pass to the AI.
        current_day = datetime.now().strftime("%A")

        # --- Prepare and Send Prompt to OpenAI ---
        prompt_data = {
            "dosha": dosha,
            "location": location_name,
            "weather": weather_desc,
            "disease": disease,
            "water": water,
            "bmi": bmi,
            "sleep": sleep,
            "secondary_condition": secondary_condition,
            "appetite": appetite,
            "current_day": current_day,
        }

        user_prompt = PROMPT_TEMPLATE.format(**prompt_data)

        if not OPENAI_API_KEY:
            return jsonify({"error": "API key for OpenAI is not configured on the server."}), 500

        client = OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=3500, 
            temperature=0.3,  
        )

        plan_text = completion.choices[0].message.content

        return jsonify(
            {
                "plan": plan_text,
                "used_location": location_name,
                "used_weather": weather_desc,
                "current_day": current_day,
            }
        )

    except Exception as e:
        # Generic error handler for any other issues.
        print(f"An error occurred in /generate: {e}")
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500


if __name__ == "__main__":
    # To run in production, use a proper WSGI server like Gunicorn or uWSGI.
    # For development, debug=True is fine.
    app.run(host="0.0.0.0", port=3000, debug=True)
