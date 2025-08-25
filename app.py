import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv   

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

# 🔑 API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# ⚙️ Flask Config from .env
FLASK_PORT = int(os.environ.get("FLASK_PORT", 3000))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

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
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate_plan():
    try:
        # --- Collect form data ---
        dosha = request.form.get("dosha", "mixed")
        disease = request.form.get("disease", "None")
        water = request.form.get("water", "2")
        bmi = request.form.get("bmi", "22")
        sleep = request.form.get("sleep", "Good")
        secondary_condition = request.form.get("secondary_condition", "None")
        appetite = request.form.get("appetite", "Normal")

        fallback_location = request.form.get("location", "Unknown")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        location_name = fallback_location
        weather_desc = "Not available"

        # --- Weather API ---
        if latitude and longitude and OPENWEATHER_API_KEY:
            try:
                weather_url = (
                    f"https://api.openweathermap.org/data/2.5/weather?"
                    f"lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
                )
                resp = requests.get(weather_url, timeout=10)
                resp.raise_for_status()
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
                print(f"Warning: Could not fetch weather data. {ex}")

        # Current day
        current_day = datetime.now().strftime("%A")

        # --- Prepare prompt ---
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
            return jsonify({"error": "API key for OpenAI is not configured."}), 500

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
        print(f"An error occurred in /generate: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
