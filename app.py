import os
import requests
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF, XPos, YPos

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Keys from .env
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 3000))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

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

# PDF Generation Function
class PDF(FPDF):
    def header(self):
        try:
            self.set_font('DejaVu', 'B', 14)
        except RuntimeError:
            self.set_font('Arial', 'B', 14)
        # Corrected call to avoid deprecation warnings
        self.cell(0, 10, 'Your Personalized Ayurvedic Diet Plan', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        try:
            
            self.set_font('DejaVu', 'I', 8)
        except RuntimeError:
            self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf(plan_text):
    pdf = PDF()
    
    
    try:
        # Adding all three styles: Regular, Bold, and Italic (Oblique)
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf')
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf')
        pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf')
        pdf.set_font('DejaVu', '', 12)
    except RuntimeError as e:
        print(f"Font error: {e}. You may be missing font files. Falling back to Arial.")
        pdf.set_font('Arial', '', 12)

    pdf.add_page()

    
    for line in plan_text.split('\n'):
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
            
        if line.startswith('### '):
            pdf.set_font('DejaVu', 'B', 16)
            pdf.multi_cell(0, 10, line.replace('### ', '').strip())
            pdf.ln(4)
        elif line.startswith('#### '):
            pdf.set_font('DejaVu', 'B', 13)
            pdf.multi_cell(0, 8, line.replace('#### ', '').strip())
            pdf.ln(2)
        elif line.startswith('- '):
            pdf.set_font('DejaVu', '', 11)
            clean_line = line.replace('**', '').replace('- ', '', 1).strip()
            pdf.cell(5) 
            pdf.multi_cell(0, 7, f'\u2022 {clean_line}')
            pdf.ln(1)
        else:
            pdf.set_font('DejaVu', '', 11)
            pdf.multi_cell(0, 7, line)
            pdf.ln(2)
    
    
    return pdf.output()


# Email Sending Function 
def send_email_with_attachment(to_email, subject, body, pdf_content, filename="Ayurvedic_Diet_Plan.pdf"):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM]):
        logger.warning("SMTP settings are not fully configured. Skipping email.")
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
    
    # Add retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to send email to {to_email} (attempt {attempt + 1}/{max_retries})")
            
            # Create connection with timeout
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to SMTP server after {max_retries} attempts")
                return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"SMTP failed after {max_retries} attempts")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending email (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"Email sending failed after {max_retries} attempts")
                return False
        
        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            import time
            time.sleep(wait_time)
    
    return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health_check():
    """Health check endpoint with SMTP configuration status"""
    smtp_configured = all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM])
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "smtp_configured": smtp_configured,
        "smtp_host": SMTP_HOST if SMTP_HOST else "Not configured",
        "smtp_port": SMTP_PORT if SMTP_PORT else "Not configured",
        "openai_configured": bool(OPENAI_API_KEY),
        "openweather_configured": bool(OPENWEATHER_API_KEY)
    }
    
    return jsonify(health_status)


@app.route("/generate", methods=["POST"])
def generate_plan():
    try:
        # Log request start
        logger.info("=== DIET GENERATION REQUEST STARTED ===")
        logger.info(f"Request time: {datetime.now()}")
        
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

        # Log user inputs
        logger.info(f"User Inputs - Age: {age}, Gender: {gender}, Height: {height}cm, Weight: {weight}kg")
        logger.info(f"User Inputs - Dosha: {dosha}, Disease: {disease}, BMI: {bmi}, Water: {water}L")
        logger.info(f"User Inputs - Sleep: {sleep}, Appetite: {appetite}, Secondary: {secondary_condition}")
        logger.info(f"Location: {fallback_location}, Lat: {latitude}, Lon: {longitude}")
        logger.info(f"Email: {email_to}")

        location_name = fallback_location
        weather_desc = "Not available"

        # Weather API call
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
                    
                logger.info(f"Weather API Success - Location: {location_name}, Weather: {weather_desc}")
            except requests.exceptions.RequestException as ex:
                logger.warning(f"Weather API failed: {ex}")

        current_day = datetime.now().strftime("%A")
        logger.info(f"Current day: {current_day}")

        prompt_data = {
            "age": age, "gender": gender, "height": height, "weight": weight,
            "dosha": dosha, "location": location_name, "weather": weather_desc,
            "disease": disease, "water": water, "bmi": bmi, "sleep": sleep,
            "secondary_condition": secondary_condition, "appetite": appetite,
            "current_day": current_day,
        }
        user_prompt = PROMPT_TEMPLATE.format(**prompt_data)

        # Log prompt being sent
        logger.info(f"Prompt sent to OpenAI (first 200 chars): {user_prompt[:200]}...")

        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            return jsonify({"error": "API key for OpenAI is not configured."}), 500

        # Log API call
        logger.info("Calling OpenAI API...")
        
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
        
        # Log successful response
        logger.info("=== DIET PLAN GENERATED SUCCESSFULLY ===")
        logger.info(f"Plan length: {len(plan_text)} characters")
        logger.info(f"Plan preview: {plan_text[:300]}...")
        logger.info("=== END DIET GENERATION ===")

        # Generate PDF and Send Email 
        email_sent = False
        if plan_text and email_to:
            try:
                logger.info(f"Generating PDF and sending email to: {email_to}")
                pdf_content = create_pdf(plan_text)
                email_subject = "Your Personalized Ayurvedic Diet Plan"
                email_body = "Hello,\n\nPlease find your personalized 7-day Ayurvedic diet plan attached.\n\nBest regards,\nSamsara Wellness"
                
                email_sent = send_email_with_attachment(email_to, email_subject, email_body, pdf_content)
                if email_sent:
                    logger.info(f"Email sent successfully to {email_to}")
                else:
                    logger.warning(f"Failed to send email to {email_to}")
            except Exception as email_error:
                logger.error(f"Email sending failed with exception: {email_error}")
                email_sent = False
        else:
            logger.info("No email provided or plan text empty - skipping email")

        return jsonify({
            "plan": plan_text,
            "used_location": location_name,
            "used_weather": weather_desc,
            "current_day": current_day,
        })

    except Exception as e:
        logger.error(f"=== DIET GENERATION ERROR ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error("=== END ERROR ===")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/generate-diet-from-node-data", methods=["POST"])
def generate_diet_from_node_data():
    try:
        # Log request start
        logger.info("=== DIET GENERATION FROM NODE DATA REQUEST STARTED ===")
        logger.info(f"Request time: {datetime.now()}")
        
        # Get data from JSON body
        data = request.get_json()
        if not data:
            logger.error("No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
        
        email_to = data.get("email")
        metadata = data.get("metadata", {})
        
        # Log received data
        logger.info(f"Email: {email_to}")
        logger.info(f"Metadata received: {metadata}")
        
        # Extract location data for weather API (if available)
        location_name = "Unknown"
        weather_desc = "Not available"
        latitude = None
        longitude = None
        
        # Try to extract location from metadata (check various possible locations)
        if "basicInfo" in metadata and "location" in metadata["basicInfo"]:
            location_name = metadata["basicInfo"]["location"]
        elif "location" in metadata:
            location_name = metadata["location"]
        
        # Try to extract coordinates from metadata
        if "basicInfo" in metadata:
            if "latitude" in metadata["basicInfo"]:
                latitude = metadata["basicInfo"]["latitude"]
            if "longitude" in metadata["basicInfo"]:
                longitude = metadata["basicInfo"]["longitude"]
        elif "latitude" in metadata:
            latitude = metadata["latitude"]
        elif "longitude" in metadata:
            longitude = metadata["longitude"]

        # Weather API call
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
                    
                logger.info(f"Weather API Success - Location: {location_name}, Weather: {weather_desc}")
            except requests.exceptions.RequestException as ex:
                logger.warning(f"Weather API failed: {ex}")

        current_day = datetime.now().strftime("%A")
        logger.info(f"Current day: {current_day}")
        logger.info(f"Location: {location_name}, Weather: {weather_desc}")

        # Add current day and weather info to metadata
        enhanced_metadata = metadata.copy()
        enhanced_metadata["current_day"] = current_day
        enhanced_metadata["location_info"] = {
            "location_name": location_name,
            "weather": weather_desc,
            "latitude": latitude,
            "longitude": longitude
        }
        
        # Create user prompt with entire metadata
        user_prompt = f"""
**Complete User Data:**
{enhanced_metadata}

**Instructions:**
Based on the complete user data provided above, generate a personalized 7-day Ayurvedic diet plan starting from {current_day}.

**Requirements:**
- Analyze all the user data including basic info, health data, diet preferences, and tracking information
- Consider the user's location ({location_name}) and weather ({weather_desc}) for seasonal recommendations
- Generate a 7-day plan with sections: "General Recommendations", "Early Morning", "Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack", "Dinner", and "Bedtime"
- Provide portion sizes for every food item in grams (g) or milliliters (ml)
- Explain why each meal is suitable based on the user's complete profile
- Use markdown formatting with headings like "### Day 1 ({current_day})"
- Prioritize locally available and seasonal foods for the user's location
"""

        # Log prompt being sent
        logger.info(f"Prompt sent to OpenAI (first 200 chars): {user_prompt[:200]}...")

        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            return jsonify({"error": "API key for OpenAI is not configured."}), 500

        # Create system instruction for metadata-based generation
        system_instruction = """
You are an expert clinical nutritionist and Ayurvedic specialist. Your task is to generate a highly personalized 7-day Ayurvedic diet plan based on complete user data.

**CRITICAL INSTRUCTIONS:**
1. **Analyze Complete User Data:** Carefully examine all provided user data including:
   - Basic information (age, gender, height, weight, body shape, goals, focus areas)
   - Health data (dosha assessments, water tracking, sleep tracking, weight tracking, health issues)
   - Diet preferences and notes
   - Location and weather information

2. **Extract Key Information:**
   - Calculate BMI from height and weight if not provided
   - Determine dominant dosha from assessments
   - Consider water intake targets and sleep patterns
   - Factor in health issues and goals
   - Use location and weather for seasonal recommendations

3. **Generate Personalized Plan:**
   - Create a 7-day plan starting from the specified current day
   - Adjust portion sizes based on user's age, gender, weight, and goals
   - Consider body shape (Ectomorph, Mesomorph, Endomorph) for meal timing and composition
   - Factor in focus areas and goals (strength, flexibility, weight management, etc.)
   - Address any health issues mentioned

4. **Format Requirements:**
   - Use markdown headings for each day
   - Include all meal sections: General Recommendations, Early Morning, Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner, Bedtime
   - Provide portion sizes in grams (g) or milliliters (ml)
   - Explain the reasoning for each recommendation
   - Prioritize locally available and seasonal foods

5. **Personalization:**
   - Tailor recommendations to the user's specific demographic and health profile
   - Consider their tracking data and progress
   - Address their specific goals and focus areas
   - Factor in any health conditions or medications
"""

        # Log API call
        logger.info("Calling OpenAI API...")
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        plan_text = completion.choices[0].message.content
        
        # Log successful response
        logger.info("=== DIET PLAN GENERATED SUCCESSFULLY FROM NODE DATA ===")
        logger.info(f"Plan length: {len(plan_text)} characters")
        logger.info(f"Plan preview: {plan_text[:300]}...")
        logger.info("=== END DIET GENERATION FROM NODE DATA ===")

        # Generate PDF and Send Email 
        email_sent = False
        if plan_text and email_to:
            try:
                logger.info(f"Generating PDF and sending email to: {email_to}")
                pdf_content = create_pdf(plan_text)
                email_subject = "Your Personalized Ayurvedic Diet Plan"
                email_body = "Hello,\n\nPlease find your personalized 7-day Ayurvedic diet plan attached.\n\nBest regards,\nSamsara Wellness"
                
                email_sent = send_email_with_attachment(email_to, email_subject, email_body, pdf_content)
                if email_sent:
                    logger.info(f"Email sent successfully to {email_to}")
                else:
                    logger.warning(f"Failed to send email to {email_to}")
            except Exception as email_error:
                logger.error(f"Email sending failed with exception: {email_error}")
                email_sent = False
        else:
            logger.info("No email provided or plan text empty - skipping email")

        return jsonify({
            "success": True,
            "message": "Diet plan generated successfully",
            "plan": plan_text,
            "used_location": location_name,
            "used_weather": weather_desc,
            "current_day": current_day,
            "email_sent": email_to is not None and plan_text is not None
        })

    except Exception as e:
        logger.error(f"=== DIET GENERATION FROM NODE DATA ERROR ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error("=== END ERROR ===")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)