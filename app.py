import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

# API Keys & SMTP Config from .env
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM")

# Flask Config from .env
FLASK_PORT = int(os.environ.get("FLASK_PORT", 3000))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# (Your PROMPT_TEMPLATE and SYSTEM_INSTRUCTION remain the same)
PROMPT_TEMPLATE = """
**User Parameters:**
1.  **Age:** {age}
2.  **Gender:** {gender}
3.  **Height:** {height} cm
4.  **Weight:** {weight} kg
5.  **Dosha:** {dosha}
6.  **Location:** {location}
7.  **Weather:** {weather}
8.  **Primary Disease/Health Condition:** {disease}
9.  **Physiological Data:**
    * Daily Water Intake: {water}L
    * BMI: {bmi}  
    * Sleep Quality: {sleep}
10. **Secondary Condition:** {secondary_condition}
11. **Appetite:** {appetite}
12. **Current Day:** {current_day}
"""

SYSTEM_INSTRUCTION = """
You are an expert clinical nutritionist and Ayurvedic specialist. Your task is to generate a highly personalized 7-day Ayurvedic diet plan.

**CRITICAL INSTRUCTIONS:**
1.  **Analyze the User's Full Profile:** Pay close attention to the user's age, gender, height, weight, and BMI. Use this data to estimate their daily caloric needs.
2.  **Adjust Portion Sizes:** The portion sizes you recommend must be appropriate for the user's estimated caloric needs. A 25-year-old active male will have different needs than a 50-year-old sedentary female.
3.  **Personalize for Age and Gender:** Recommendations should be suitable for the user's specific demographic. For example, a plan for a younger person might focus on energy, while a plan for an older person might focus on joint health and digestion.
4.  **Standard Requirements:**
    - Generate a 7-day plan starting from the provided Current Day.
    - Prioritize locally available and seasonal foods for the user's Location and Weather.
    - For each day, include sections: "General Recommendations", "Early Morning", "Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack", "Dinner", and "Bedtime".
    - Provide portion sizes for every food item in grams (g) or milliliters (ml).
    - Briefly explain why each meal is suitable for the user's complete profile (Dosha, Disease, BMI, Age, etc.).
    - Output using Markdown headings.
"""

# --- UPDATED PDF Generation Function ---
class PDF(FPDF):
    def header(self):
        # Use a font that supports a wider range of characters
        try:
            self.set_font('DejaVu', 'B', 14)
        except RuntimeError:
            self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Your Personalized Ayurvedic Diet Plan', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font('DejaVu', 'I', 8)
        except RuntimeError:
            self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(plan_text):
    pdf = PDF()
    # Add a Unicode font that supports more characters.
    # This is the key part of the fix.
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
        pdf.set_font('DejaVu', '', 12)
    except RuntimeError:
        print("DejaVu font not found, falling back to Arial. Special characters may not render correctly.")
        pdf.set_font('Arial', '', 12)
    
    pdf.add_page()
    
    # Write the text to the PDF, handling potential encoding issues
    # The 'replace' error handler will prevent crashes on unmappable characters
    clean_text = plan_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, clean_text)
    
    # Return the PDF content as bytes
    return pdf.output(dest='S').encode('latin-1')


# --- Email Sending Function (No changes needed) ---
def send_email_with_attachment(to_email, subject, body, pdf_content, filename="Ayurvedic_Diet_Plan.pdf"):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM]):
        print("SMTP settings are not fully configured. Skipping email.")
        return False
        
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEApplication(pdf_content, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate_plan():
    try:
        # (Your existing code to collect form data remains the same)
        email_to = request.form.get("email")
        age = request.form.get("age", "30")
        gender = request.form.get("gender", "Female")
        height = request.form.get("height", "165")
        weight = request.form.get("weight", "60")
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

        # (Your existing weather logic remains the same)

        current_day = datetime.now().strftime("%A")

        # (Your existing OpenAI call remains the same)
        prompt_data = {
            "age": age, "gender": gender, "height": height, "weight": weight,
            "dosha": dosha, "location": location_name, "weather": weather_desc,
            "disease": disease, "water": water, "bmi": bmi, "sleep": sleep,
            "secondary_condition": secondary_condition, "appetite": appetite,
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

        # --- Generate PDF and Send Email ---
        if plan_text and email_to:
            pdf_content = create_pdf(plan_text)
            email_subject = "Your Personalized Ayurvedic Diet Plan"
            email_body = "Hello,\n\nPlease find your personalized 7-day Ayurvedic diet plan attached.\n\nBest regards,\nSamsara Wellness"
            
            send_email_with_attachment(email_to, email_subject, email_body, pdf_content)

        return jsonify({
            "plan": plan_text,
            "used_location": location_name,
            "used_weather": weather_desc,
            "current_day": current_day,
        })

    except Exception as e:
        print(f"An error occurred in /generate: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
