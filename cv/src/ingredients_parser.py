# ingredients_parser.py - ULTRA SIMPLIFIED
import json
import re
from ingredients_db import INGREDIENTS_DATABASE

def normalize_text(text):
    """Normalize text for comparison"""
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u'
    }
    text = text.lower().strip()
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def find_ingredient(gemini_text, database):
    """
    Find ingredient by keyword match
    Prioritizes longer (more specific) matches
    """
    normalized_text = normalize_text(gemini_text)
    
    # Get all ingredients and sort by length (longest first)
    ingredients = sorted(database.keys(), key=len, reverse=True)
    
    # Search for a match
    for ingredient in ingredients:
        normalized_ingredient = normalize_text(ingredient)
        
        # If the ingredient is contained within Gemini’s text
        if normalized_ingredient in normalized_text:
            return ingredient
    
    return None

def parse_gemini_response_with_coords(json_response):
    """
    Parse JSON with coordinates
    """
    try:
        # Clean markdown
        response = json_response.strip()
        
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        
        response = response.strip()
        
        # Parse JSON
        data = json.loads(response)
        
        detected = []
        seen = set()
        
        for item in data.get('ingredients', []):
            gemini_name = item.get('name', '').strip()
            database = INGREDIENTS_DATABASE
            
            # Search ingredient by keyword
            ingredient_id = find_ingredient(gemini_name, database)
            
            if ingredient_id and ingredient_id not in seen:
                info = database[ingredient_id]
                bbox = item.get('bounding_box', {})
                
                detected.append({
                    "id": ingredient_id,
                    "name": ingredient_id,
                    "emoji": info["emoji"],
                    "category": info["categoria"],
                    "quantity": float(item.get('quantity', 1.0)),
                    "unit": item.get('unit', info['unidad']),
                    "bounding_box": {
                        "x": max(0.0, min(1.0, bbox.get('x', 0.5))),
                        "y": max(0.0, min(1.0, bbox.get('y', 0.5))),
                        "width": max(0.0, min(1.0, bbox.get('width', 0.1))),
                        "height": max(0.0, min(1.0, bbox.get('height', 0.1)))
                    }
                })
                
                seen.add(ingredient_id)
        
        return detected
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response: {json_response[:500]}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
