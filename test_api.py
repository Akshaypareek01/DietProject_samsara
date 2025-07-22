import requests
import json

url = "http://127.0.0.1:5050/generate-diet"  # ✅ Port 5050

# 🧾 Sample user input
input_text = """
Doshas – Pitta vata
	2.	Location – Ahmedabad (Gujarat)
	3.	Weather – Very Hot & Dry
	4.	Disease – Acidity/GERD
	5.	Water – 2L | BMI – 25 | Sleep – Interrupted
	6.	Thyroid-8
	7.	Appetite – Excessive, worsens with spices
"""

response = requests.post(url, json={"ayurvedic_input": input_text})

if response.ok:
    output_json = response.json()["diet_plan"]
    print("✅ Diet Plan:\n")
    print(output_json)

    # Optional: Save to file
    with open("output_diet_plan.json", "w") as f:
        f.write(output_json)

    print("\n📁 Saved to 'output_diet_plan.json'")
else:
    print("❌ Error:", response.text)
