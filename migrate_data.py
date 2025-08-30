#!/usr/bin/env python3
"""
Data migration script to transfer JSON data to PostgreSQL database
Run this once to migrate existing data
"""

import json
import os
from app import app, db
from models import Reel, Opinion, Subscriber, SiteContent
from datetime import datetime

def migrate_json_to_database():
    """Migrate data from JSON files to PostgreSQL database"""
    
    with app.app_context():
        print("Starting data migration...")
        
        # Check if data already exists in database
        existing_reels = Reel.query.count()
        existing_opinions = Opinion.query.count()
        existing_subscribers = Subscriber.query.count()
        
        if existing_reels > 0 or existing_opinions > 0 or existing_subscribers > 0:
            print(f"Database already has data:")
            print(f"  - Reels: {existing_reels}")
            print(f"  - Opinions: {existing_opinions}")  
            print(f"  - Subscribers: {existing_subscribers}")
            
            response = input("Do you want to continue and potentially add duplicate data? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return
        
        # Migrate content.json
        if os.path.exists('data/content.json'):
            print("Migrating content.json...")
            with open('data/content.json', 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # Migrate reels
            if 'reels' in content_data:
                for reel_data in content_data['reels']:
                    reel = Reel(
                        title=reel_data.get('title', ''),
                        thumbnail=reel_data.get('thumbnail', ''),
                        video_url=reel_data.get('video_url', ''),
                        behind_thought=reel_data.get('behind_thought', ''),
                        sources=json.dumps(reel_data.get('sources', [])),
                        extra_context=reel_data.get('extra_context', '')
                    )
                    db.session.add(reel)
                print(f"Migrated {len(content_data['reels'])} reels")
            
            # Migrate opinions
            if 'opinions' in content_data:
                for opinion_data in content_data['opinions']:
                    opinion = Opinion(
                        title=opinion_data.get('title', ''),
                        position=opinion_data.get('position', ''),
                        description=opinion_data.get('description', ''),
                        poll_question=opinion_data.get('poll_question', ''),
                        poll_options=json.dumps(opinion_data.get('poll_options', [])),
                        votes=json.dumps(opinion_data.get('votes', []))
                    )
                    db.session.add(opinion)
                print(f"Migrated {len(content_data['opinions'])} opinions")
            
            # Migrate other content sections (hero, upcoming_shows, resources)
            for section in ['hero', 'upcoming_shows', 'resources']:
                if section in content_data:
                    site_content = SiteContent(
                        content_key=section,
                        content_data=json.dumps(content_data[section])
                    )
                    db.session.add(site_content)
                    print(f"Migrated {section} content")
        
        # Migrate subscribers.json
        if os.path.exists('data/subscribers.json'):
            print("Migrating subscribers.json...")
            with open('data/subscribers.json', 'r', encoding='utf-8') as f:
                subscriber_data = json.load(f)
            
            if 'subscribers' in subscriber_data:
                for sub_data in subscriber_data['subscribers']:
                    # Parse date if available
                    subscribed_at = datetime.utcnow()
                    if 'subscribed_at' in sub_data:
                        try:
                            subscribed_at = datetime.fromisoformat(sub_data['subscribed_at'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    subscriber = Subscriber(
                        name=sub_data.get('name', ''),
                        email=sub_data.get('email', ''),
                        place=sub_data.get('place', ''),
                        age=sub_data.get('age', ''),
                        subscribed_at=subscribed_at
                    )
                    db.session.add(subscriber)
                print(f"Migrated {len(subscriber_data['subscribers'])} subscribers")
        
        # Commit all changes
        try:
            db.session.commit()
            print("✅ Migration completed successfully!")
            
            # Print final counts
            print(f"Final database counts:")
            print(f"  - Reels: {Reel.query.count()}")
            print(f"  - Opinions: {Opinion.query.count()}")
            print(f"  - Subscribers: {Subscriber.query.count()}")
            print(f"  - Site Content: {SiteContent.query.count()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")

if __name__ == '__main__':
    migrate_json_to_database()