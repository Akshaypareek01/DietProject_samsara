from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ✅ Use your actual API key
client = OpenAI(
    api_key="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"
)

@app.route('/generate-diet', methods=['POST'])
def generate_diet():
    try:
        data = request.get_json()
        user_profile = data.get("ayurvedic_input")

        if not user_profile:
            return jsonify({"error": "Missing 'ayurvedic_input' in request."}), 400

        prompt = f"""
You are a certified Ayurvedic clinical dietician and nutritionist. Based on the following user profile, generate a **personalized Indian diet plan** with proper **food quantities**, **meal times**, and **Ayurvedic reasoning**.

🧾 User Profile:
{user_profile}

📌 Requirements:
- Consider diseases like PCOS, GERD, Thyroid, Hypertension, Diabetes, Anxiety, etc.
- Use dosha knowledge: Vata, Pitta, Kapha, or combinations.
- Adjust for climate, appetite, water intake, BMI, and sleep quality.
- Suggest real Indian foods with quantities in grams, ml, or cups.
- Avoid contraindicated foods (e.g., spicy for GERD, fried for PCOS, sugar for diabetes).
- Reduce total calories below 1800 for BMI > 28.
- Avoid generic answers. Use ayurvedic logic in 1–2 line notes per meal.
- Return output in **valid JSON only**.

🎯 Output Format:
{{
  "breakfast": {{
    "time": "08:00 AM",
    "items": [
      {{ "food": "Ragi porridge with almond milk", "quantity": "1 cup (200 ml)" }},
      {{ "food": "Steamed apple with cinnamon", "quantity": "1 medium (120 g)" }},
      {{ "food": "Fenugreek herbal tea", "quantity": "1 cup (150 ml)" }}
    ],
    "notes": "Balances Kapha and Pitta. Aids PCOS and reduces BP by avoiding salt and processed carbs."
  }},
  "lunch": {{
    "time": "01:00 PM",
    "items": [
      {{ "food": "Moong dal with lauki", "quantity": "1.5 cups (300 g)" }},
      {{ "food": "Carrot-cucumber salad with lemon", "quantity": "1 bowl (150 g)" }},
      {{ "food": "Jeera buttermilk", "quantity": "1 glass (200 ml)" }}
    ],
    "notes": "Easily digestible and cooling. Avoids spicy/oily foods for GERD and hypertension."
  }},
  "dinner": {{
    "time": "07:00 PM",
    "items": [
      {{ "food": "Pumpkin soup with ginger", "quantity": "1 bowl (250 ml)" }},
      {{ "food": "Bajra roti (no ghee)", "quantity": "2 small (100 g)" }},
      {{ "food": "Steamed palak", "quantity": "100 g" }}
    ],
    "notes": "Warm and grounding to calm Vata. No heavy items at night, helps thyroid and sleep."
  }}
}}

Return valid JSON only.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an Ayurvedic dietician and Indian food expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()

        return jsonify({"diet_plan": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5050)  # ⏹️ Changed port to 5050
