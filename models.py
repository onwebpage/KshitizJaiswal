import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class DataManager:
    """Simple JSON-based data management"""
    
    @staticmethod
    def load_json(filename):
        """Load data from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
    
    @staticmethod
    def save_json(filename, data):
        """Save data to JSON file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def get_content():
        """Get website content"""
        default_content = {
            "hero": {
                "name": "Kshitiz Jaiswal",
                "tagline": "Unfiltered Commentator. The content here is selective, but the truth is never biased.",
                "banner_url": "https://pixabay.com/get/g533a6aa47eba4823795ce2e25fdfdbeab9c4946d039afcc8be299199aea4607bcead5e63e650f3598d32b8af6f69fa29cd392bcfe2db7bc9db577a352240b008_1280.jpg"
            },
            "reels": [
                {
                    "id": 1,
                    "title": "Truth Behind Politics",
                    "thumbnail": "https://pixabay.com/get/g416b51f98122f2039f5011acd9ab0634dad0d9388d5e5136fdbb12b908571c7f30ddd4b7caec430021aa833d16610f9a40b70e217d2491c5babdacc30b1bf885_1280.jpg",
                    "video_url": "",
                    "behind_thought": "The real story behind what you see on screen",
                    "sources": ["Source 1", "Source 2"],
                    "extra_context": "Additional context about this topic"
                },
                {
                    "id": 2,
                    "title": "Social Media Reality",
                    "thumbnail": "https://pixabay.com/get/g744ad2f390fdc8ef676303ed990164beb2f42bd75e30c9376504557dd369681741e6caa14455f04e04495e627f9d70c4d63f6650267b54b0d1361e3783a94813_1280.jpg",
                    "video_url": "",
                    "behind_thought": "What happens behind the viral content",
                    "sources": ["Research 1", "Study 2"],
                    "extra_context": "The deeper implications"
                }
            ],
            "opinions": [
                {
                    "id": 1,
                    "title": "Climate Change Policy",
                    "position": "Strong action needed now",
                    "description": "My stance on environmental policies",
                    "poll_question": "Do you support immediate climate action?",
                    "poll_options": ["Yes, absolutely", "Gradual approach", "Not a priority"],
                    "votes": [0, 0, 0]
                }
            ],
            "upcoming_shows": [
                {
                    "title": "Weekly Truth Bombs",
                    "description": "Unfiltered takes on current events",
                    "image": "https://pixabay.com/get/g51d3a9b60f5b304d6d9a2109588df26fa955fdad29b549ed6f2d44cdb714ef5b54d4b04df2f46da1bd05dede83422e909ae5403a8c87771e7130a78714c2e5df_1280.jpg",
                    "coming_soon": True
                }
            ],
            "resources": [
                {
                    "title": "Critical Thinking Course",
                    "description": "Learn to think independently",
                    "image": "https://pixabay.com/get/g1607648249e3d2cc886480cc481c2224cb52f7fd6b06e51d63e7c2ee7d304d71973191ec7388dc286501651899d7fd130bc378c50e5ab80727d452f099c3f672_1280.jpg",
                    "link": "#",
                    "price": "₹999"
                }
            ]
        }
        
        content = DataManager.load_json('data/content.json')
        if not content:
            DataManager.save_json('data/content.json', default_content)
            content = default_content
        
        return content
    
    @staticmethod
    def save_content(content):
        """Save website content"""
        DataManager.save_json('data/content.json', content)
    
    @staticmethod
    def add_subscriber(name, email, place, age):
        """Add newsletter subscriber"""
        subscribers = DataManager.load_json('data/subscribers.json')
        if 'subscribers' not in subscribers:
            subscribers['subscribers'] = []
        
        subscriber = {
            'name': name,
            'email': email,
            'place': place,
            'age': age,
            'subscribed_at': datetime.now().isoformat()
        }
        
        subscribers['subscribers'].append(subscriber)
        DataManager.save_json('data/subscribers.json', subscribers)
        return True
    
    @staticmethod
    def vote_poll(opinion_id, option_index):
        """Record poll vote"""
        content = DataManager.get_content()
        
        for opinion in content['opinions']:
            if opinion['id'] == opinion_id:
                if 0 <= option_index < len(opinion['votes']):
                    opinion['votes'][option_index] += 1
                    DataManager.save_content(content)
                    return True
        return False

class AdminUser:
    """Simple admin authentication"""
    
    @staticmethod
    def verify_admin(username, password):
        """Verify admin credentials"""
        # In production, use proper authentication
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'kshitiz2025')
        
        return username == admin_username and password == admin_password
