import os
import json
import base64
from openai import OpenAI

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_differences(figma_img_path: str, ui_img_path: str, diff_img_path: str) -> list:
    """Uses LLM to analyze the visual differences and return structured JSON issues."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return [{"type": "error", "component": "system", "issue": "OpenAI API key missing.", "severity": "high"}]

    client = OpenAI(api_key=api_key)

    figma_base64 = encode_image(figma_img_path)
    ui_base64 = encode_image(ui_img_path)
    diff_base64 = encode_image(diff_img_path)

    prompt = '''You are an expert UI/UX designer and frontend engineer.
Analyze these three images:
1. The original Figma design.
2. The live UI screenshot.
3. The diff image highlighting mismatching pixels.

Detect visual bugs and discrepancies between the design and the live UI. Look for:
- spacing issues
- alignment issues
- font mismatch
- color differences
- missing components

Output your analysis as a structured JSON array. Each object must have:
- "type": (e.g., "alignment", "spacing", "color", "font", "missing")
- "component": The UI element affected (e.g., "navbar", "hero text", "primary button")
- "issue": A brief description of the issue.
- "severity": "critical" (completely missing component or totally wrong layout), "high", "medium", or "low"
- "bbox": Approximate bounding box of the affected area in the LIVE UI screenshot as fractional coordinates: {"x": 0.0-1.0, "y": 0.0-1.0, "w": 0.0-1.0, "h": 0.0-1.0} where (0,0) is the top-left corner and values are fractions of the image width/height. Estimate as accurately as possible.

Only return valid JSON array. Do not include markdown blocks or any other text.'''

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{figma_base64}"}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{ui_base64}"}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{diff_base64}"}
                        }
                    ],
                }
            ],
            max_tokens=3000,
        )

        response_content = response.choices[0].message.content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:-3]
        elif response_content.startswith("```"):
            response_content = response_content[3:-3]
            
        return json.loads(response_content)
    except Exception as e:
        return [{"type": "error", "component": "system", "issue": f"LLM analysis failed: {str(e)}", "severity": "high"}]
