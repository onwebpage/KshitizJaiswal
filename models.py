import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Database Models
class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    thumbnail = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    behind_thought = db.Column(db.Text)
    sources = db.Column(db.Text)  # JSON string of sources list
    extra_context = db.Column(db.Text)
    category_tag = db.Column(db.String(50))  # trending, new, must_watch, fan_favourite, exclusive, behind_scenes
    topic_tag = db.Column(db.String(100))  # Topic for grouping/playlist (e.g., "Vote Chori Issue")
    view_count = db.Column(db.Integer, default=0)  # For popularity tracking
    is_featured = db.Column(db.Boolean, default=False)  # For homepage featured reels
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'thumbnail': self.thumbnail or '',
            'video_url': self.video_url or '',
            'behind_thought': self.behind_thought or '',
            'sources': json.loads(self.sources) if self.sources else [],
            'extra_context': self.extra_context or '',
            'category_tag': self.category_tag or '',
            'topic_tag': self.topic_tag or '',
            'view_count': self.view_count or 0,
            'is_featured': self.is_featured or False,
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }

class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Text)
    description = db.Column(db.Text)
    poll_question = db.Column(db.String(500))
    poll_options = db.Column(db.Text)  # JSON string of options list
    votes = db.Column(db.Text)  # JSON string of votes list
    topic_tag = db.Column(db.String(100))  # Topic tag for grouping/playlist
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'position': self.position or '',
            'description': self.description or '',
            'poll_question': self.poll_question or '',
            'poll_options': json.loads(self.poll_options) if self.poll_options else [],
            'votes': json.loads(self.votes) if self.votes else [],
            'topic_tag': self.topic_tag or ''
        }

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(100))
    age = db.Column(db.String(20))
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'place': self.place or '',
            'age': self.age or '',
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else ''
        }

class SiteContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_key = db.Column(db.String(50), unique=True, nullable=False)
    content_data = db.Column(db.Text)  # JSON string
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SubscriptionTier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # Price in rupees
    period = db.Column(db.String(20), default='week')  # week, month, year
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='fas fa-heart')  # Font Awesome icon class
    benefits = db.Column(db.Text)  # JSON string of benefits array
    is_popular = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'period': self.period,
            'description': self.description or '',
            'icon': self.icon or 'fas fa-heart',
            'benefits': json.loads(self.benefits) if self.benefits else [],
            'is_popular': self.is_popular,
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }

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
        """Get website content from database"""
        # Get reels from database
        reels = [reel.to_dict() for reel in Reel.query.all()]
        
        # Get opinions from database
        opinions = [opinion.to_dict() for opinion in Opinion.query.all()]
        
        # Get hero content
        hero_content = SiteContent.query.filter_by(content_key='hero').first()
        if hero_content:
            hero = json.loads(hero_content.content_data)
        else:
            hero = {
                "name": "Kshitiz Jaiswal",
                "tagline": "Unfiltered Commentator. The content here is selective, but the truth is never biased.",
                "banner_url": "https://pixabay.com/get/g533a6aa47eba4823795ce2e25fdfdbeab9c4946d039afcc8be299199aea4607bcead5e63e650f3598d32b8af6f69fa29cd392bcfe2db7bc9db577a352240b008_1280.jpg"
            }
            # Save default hero content
            hero_record = SiteContent(content_key='hero', content_data=json.dumps(hero))
            db.session.add(hero_record)
            db.session.commit()
        
        # Get other content sections
        shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
        if shows_content:
            upcoming_shows = json.loads(shows_content.content_data)
        else:
            upcoming_shows = [
                {
                    "title": "Weekly Truth Bombs",
                    "description": "Unfiltered takes on current events",
                    "image": "https://pixabay.com/get/g51d3a9b60f5b304d6d9a2109588df26fa955fdad29b549ed6f2d44cdb714ef5b54d4b04df2f46da1bd05dede83422e909ae5403a8c87771e7130a78714c2e5df_1280.jpg",
                    "coming_soon": True
                }
            ]
            shows_record = SiteContent(content_key='upcoming_shows', content_data=json.dumps(upcoming_shows))
            db.session.add(shows_record)
            db.session.commit()
        
        resources_content = SiteContent.query.filter_by(content_key='resources').first()
        if resources_content:
            resources = json.loads(resources_content.content_data)
        else:
            resources = [
                {
                    "title": "Critical Thinking Course",
                    "description": "Learn to think independently",
                    "image": "https://pixabay.com/get/g1607648249e3d2cc886480cc481c2224cb52f7fd6b06e51d63e7c2ee7d304d71973191ec7388dc286501651899d7fd130bc378c50e5ab80727d452f099c3f672_1280.jpg",
                    "link": "#",
                    "price": "₹999"
                }
            ]
            resources_record = SiteContent(content_key='resources', content_data=json.dumps(resources))
            db.session.add(resources_record)
            db.session.commit()
        
        # If no content exists, create default reels and opinions
        if not reels and not opinions:
            DataManager._create_default_content()
            reels = [reel.to_dict() for reel in Reel.query.all()]
            opinions = [opinion.to_dict() for opinion in Opinion.query.all()]
        
        return {
            "hero": hero,
            "reels": reels,
            "opinions": opinions,
            "upcoming_shows": upcoming_shows,
            "resources": resources
        }
    
    @staticmethod
    def save_content(content):
        """Save website content to database (legacy method for backward compatibility)"""
        # This method is kept for backward compatibility but data is now in database
        pass
    
    @staticmethod
    def _create_default_content():
        """Create default reels and opinions"""
        # Create default reels
        reel1 = Reel(
            title="Truth Behind Politics",
            thumbnail="https://pixabay.com/get/g416b51f98122f2039f5011acd9ab0634dad0d9388d5e5136fdbb12b908571c7f30ddd4b7caec430021aa833d16610f9a40b70e217d2491c5babdacc30b1bf885_1280.jpg",
            video_url="",
            behind_thought="The real story behind what you see on screen",
            sources=json.dumps(["Source 1", "Source 2"]),
            extra_context="Additional context about this topic"
        )
        
        reel2 = Reel(
            title="Social Media Reality",
            thumbnail="https://pixabay.com/get/g744ad2f390fdc8ef676303ed990164beb2f42bd75e30c9376504557dd369681741e6caa14455f04e04495e627f9d70c4d63f6650267b54b0d1361e3783a94813_1280.jpg",
            video_url="",
            behind_thought="What happens behind the viral content",
            sources=json.dumps(["Research 1", "Study 2"]),
            extra_context="The deeper implications"
        )
        
        # Create default opinion
        opinion1 = Opinion(
            title="Climate Change Policy",
            position="Strong action needed now",
            description="My stance on environmental policies",
            poll_question="Do you support immediate climate action?",
            poll_options=json.dumps(["Yes, absolutely", "Gradual approach", "Not a priority"]),
            votes=json.dumps([0, 0, 0])
        )
        
        db.session.add_all([reel1, reel2, opinion1])
        db.session.commit()
    
    @staticmethod
    def add_subscriber(name, email, place, age):
        """Add newsletter subscriber to database"""
        subscriber = Subscriber(
            name=name,
            email=email,
            place=place,
            age=age
        )
        db.session.add(subscriber)
        db.session.commit()
        return True
    
    @staticmethod
    def vote_poll(opinion_id, option_index):
        """Record poll vote in database"""
        opinion = Opinion.query.get(opinion_id)
        if opinion:
            votes = json.loads(opinion.votes) if opinion.votes else []
            if 0 <= option_index < len(votes):
                votes[option_index] += 1
                opinion.votes = json.dumps(votes)
                db.session.commit()
                return True
        return False

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    thumbnail = db.Column(db.String(500))
    price = db.Column(db.Integer, nullable=False)  # Price in rupees
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    modules = db.relationship('Module', backref='course', lazy=True, cascade='all, delete-orphan', order_by='Module.sort_order')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description or '',
            'thumbnail': self.thumbnail or '',
            'price': self.price,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'modules': [module.to_dict() for module in self.modules]
        }

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lessons = db.relationship('Lesson', backref='module', lazy=True, cascade='all, delete-orphan', order_by='Lesson.sort_order')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description or '',
            'sort_order': self.sort_order,
            'lessons': [lesson.to_dict() for lesson in self.lessons]
        }

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500))  # YouTube unlisted/private URL
    notes = db.Column(db.Text)  # Lesson notes/resources
    duration = db.Column(db.String(20))  # e.g., "15:30"
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'description': self.description or '',
            'video_url': self.video_url or '',
            'notes': self.notes or '',
            'duration': self.duration or '',
            'sort_order': self.sort_order
        }

class UserCourseAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clerk_user_id = db.Column(db.String(100), nullable=False)  # Clerk user ID
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    payment_id = db.Column(db.String(200))  # Razorpay payment ID
    amount_paid = db.Column(db.Integer)  # Amount paid in rupees
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Optional expiration date
    
    course = db.relationship('Course', backref='user_accesses')
    
    def to_dict(self):
        return {
            'id': self.id,
            'clerk_user_id': self.clerk_user_id,
            'course_id': self.course_id,
            'payment_id': self.payment_id or '',
            'amount_paid': self.amount_paid,
            'granted_at': self.granted_at.isoformat() if self.granted_at else '',
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @staticmethod
    def has_access(clerk_user_id, course_id):
        """Check if a user has access to a course"""
        if not clerk_user_id:
            return False
        access = UserCourseAccess.query.filter_by(
            clerk_user_id=clerk_user_id,
            course_id=course_id
        ).first()
        if access:
            if access.expires_at is None or access.expires_at > datetime.utcnow():
                return True
        return False
    
    @staticmethod
    def get_user_courses(clerk_user_id):
        """Get all courses a user has access to"""
        if not clerk_user_id:
            return []
        accesses = UserCourseAccess.query.filter_by(clerk_user_id=clerk_user_id).all()
        valid_accesses = []
        for access in accesses:
            if access.expires_at is None or access.expires_at > datetime.utcnow():
                valid_accesses.append(access)
        return valid_accesses

class AdminUser:
    """Simple admin authentication"""
    
    @staticmethod
    def verify_admin(username, password):
        """Verify admin credentials"""
        # In production, use proper authentication
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'kshitiz2025')
        
        return username == admin_username and password == admin_password
    
    @staticmethod
    def get_subscription_tiers():
        """Get all active subscription tiers"""
        return [tier.to_dict() for tier in SubscriptionTier.query.filter_by(is_active=True).order_by(SubscriptionTier.sort_order, SubscriptionTier.price).all()]
    
    @staticmethod
    def create_default_tiers():
        """Create default subscription tiers if none exist"""
        if SubscriptionTier.query.count() == 0:
            # Create default tiers based on current hardcoded values
            tier1 = SubscriptionTier(
                name="Chai Buddy",
                price=10,
                period="week",
                description="Support with a weekly chai and keep the conversations flowing",
                icon="fas fa-coffee",
                benefits=json.dumps(["Weekly newsletter access", "Community member status"]),
                is_popular=False,
                sort_order=1
            )
            
            tier2 = SubscriptionTier(
                name="True Friend",
                price=20,
                period="week",
                description="Show genuine support and be part of the inner circle",
                icon="fas fa-heart",
                benefits=json.dumps(["Everything in Chai Buddy", "Early access to content", "Behind-the-scenes updates"]),
                is_popular=True,
                sort_order=2
            )
            
            tier3 = SubscriptionTier(
                name="Super Supporter",
                price=50,
                period="week",
                description="Maximum support for the cause of unfiltered truth",
                icon="fas fa-star",
                benefits=json.dumps(["Everything in True Friend", "Monthly video calls", "Special mention in content"]),
                is_popular=False,
                sort_order=3
            )
            
            db.session.add_all([tier1, tier2, tier3])
            db.session.commit()
            return True
        return False
