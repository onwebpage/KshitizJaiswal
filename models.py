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
    video_type = db.Column(db.String(20), default='auto')  # 'youtube', 'instagram', 'auto'
    card_layout = db.Column(db.String(20), default='standard')  # 'standard', 'portrait', 'landscape'
    sort_order = db.Column(db.Integer, default=0)
    is_visible = db.Column(db.Boolean, default=True)
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
            'video_type': self.video_type or 'auto',
            'card_layout': self.card_layout or 'standard',
            'sort_order': self.sort_order or 0,
            'is_visible': self.is_visible if self.is_visible is not None else True,
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

class ColumnVisibility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), unique=True, nullable=False)
    hidden_columns = db.Column(db.Text)  # JSON string of hidden column names
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_hidden_columns(table_name):
        """Get list of hidden columns for a table"""
        from utils import normalize_table_name, get_legacy_table_name_mapping
        # Normalize table name to handle legacy plural names
        normalized_table = normalize_table_name(table_name)
        
        # Try normalized name first
        visibility = ColumnVisibility.query.filter_by(table_name=normalized_table).first()
        
        # If not found, try to find a legacy plural name that maps to this table
        if not visibility:
            legacy_mapping = get_legacy_table_name_mapping()
            # Reverse lookup: find the plural name that maps to our normalized table
            for legacy_name, actual_name in legacy_mapping.items():
                if actual_name == normalized_table:
                    visibility = ColumnVisibility.query.filter_by(table_name=legacy_name).first()
                    if visibility:
                        break
        
        if visibility and visibility.hidden_columns:
            return json.loads(visibility.hidden_columns)
        return []
    
    @staticmethod
    def is_column_visible(table_name, column_name):
        """Check if a column should be visible"""
        from utils import normalize_table_name
        # Normalize table name to handle legacy plural names
        normalized_table = normalize_table_name(table_name)
        hidden_columns = ColumnVisibility.get_hidden_columns(normalized_table)
        return column_name not in hidden_columns
    
    @staticmethod
    def set_hidden_columns(table_name, columns):
        """Set hidden columns for a table"""
        from utils import normalize_table_name, get_legacy_table_name_mapping
        # Normalize table name to handle legacy plural names
        normalized_table = normalize_table_name(table_name)
        
        # Try to find existing record with normalized name first
        visibility = ColumnVisibility.query.filter_by(table_name=normalized_table).first()
        
        # If not found, check for legacy name and migrate it
        if not visibility:
            legacy_mapping = get_legacy_table_name_mapping()
            # Reverse lookup: find the plural name that maps to our normalized table
            for legacy_name, actual_name in legacy_mapping.items():
                if actual_name == normalized_table:
                    legacy_visibility = ColumnVisibility.query.filter_by(table_name=legacy_name).first()
                    if legacy_visibility:
                        # Migrate: update the legacy record to use the normalized name
                        legacy_visibility.table_name = normalized_table
                        visibility = legacy_visibility
                        break
        
        if visibility:
            visibility.hidden_columns = json.dumps(columns)
            visibility.updated_at = datetime.utcnow()
        else:
            visibility = ColumnVisibility(
                table_name=normalized_table,
                hidden_columns=json.dumps(columns)
            )
            db.session.add(visibility)
        db.session.commit()
    
    @staticmethod
    def get_all_table_settings():
        """Get all table column visibility settings"""
        settings = {}
        all_visibility = ColumnVisibility.query.all()
        for vis in all_visibility:
            settings[vis.table_name] = json.loads(vis.hidden_columns) if vis.hidden_columns else []
        return settings

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
        """Get website content from database with error handling"""
        try:
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
        except Exception as e:
            # If database is unavailable, return default content
            import logging
            logging.error(f"Database error in get_content: {e}")
            return {
                "hero": {
                    "name": "Kshitiz Jaiswal",
                    "tagline": "Unfiltered Commentator. The content here is selective, but the truth is never biased.",
                    "banner_url": "https://pixabay.com/get/g533a6aa47eba4823795ce2e25fdfdbeab9c4946d039afcc8be299199aea4607bcead5e63e650f3598d32b8af6f69fa29cd392bcfe2db7bc9db577a352240b008_1280.jpg"
                },
                "reels": [],
                "opinions": [],
                "upcoming_shows": [],
                "resources": []
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
    def get_page_content():
        """Get page content from database with defaults"""
        # Default content to return if database fails
        default_content = {
            'reels_section_title': 'Beyond The Reel',
            'reels_section_subtitle': '"Reel to sirf ek hissa tha, kahani bahut badi hai."',
            'support_section_title': 'Friends of Kshitiz — Support Now',
            'support_section_subtitle': 'Aapki marzi, aapka support. Jitna chaho, utna.',
            'custom_support_button_text': 'Custom Supporter — Aapki marzi, aapka support. Jitna chaho, utna.',
            'custom_support_subtitle': 'Aapki marzi, aapka support. Jitna chaho, utna.',
            'support_stats_count': 127,
            'support_stats_amount': 2340
        }
        
        try:
            page_content_record = SiteContent.query.filter_by(content_key='page_content').first()
            
            if page_content_record:
                return json.loads(page_content_record.content_data)
            else:
                # Try to save default content to database
                try:
                    page_content_record = SiteContent(content_key='page_content', content_data=json.dumps(default_content))
                    db.session.add(page_content_record)
                    db.session.commit()
                except:
                    pass  # If save fails, just return defaults
                return default_content
        except:
            # If database fails, return defaults
            return default_content
    
    @staticmethod
    def save_page_content(content_dict):
        """Save page content to database"""
        try:
            page_content_record = SiteContent.query.filter_by(content_key='page_content').first()
            
            if page_content_record:
                page_content_record.content_data = json.dumps(content_dict)
                page_content_record.updated_at = datetime.utcnow()
            else:
                page_content_record = SiteContent(content_key='page_content', content_data=json.dumps(content_dict))
                db.session.add(page_content_record)
            
            db.session.commit()
        except Exception as e:
            raise Exception(f"Failed to save page content: {str(e)}")
    
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

class SiteConfig(db.Model):
    """Key-value store for site-wide configuration flags"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        try:
            config = SiteConfig.query.filter_by(key=key).first()
            return config.value if config else default
        except Exception:
            return default

    @staticmethod
    def set(key, value):
        try:
            config = SiteConfig.query.filter_by(key=key).first()
            if config:
                config.value = str(value)
            else:
                config = SiteConfig(key=key, value=str(value))
                db.session.add(config)
            db.session.commit()
        except Exception:
            db.session.rollback()


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

class SocialLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(500))
    icon_class = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'url': self.url or '#',
            'icon_class': self.icon_class or 'fab fa-link',
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }
    
    @staticmethod
    def get_active_links():
        """Get all active social links ordered by sort_order"""
        return SocialLink.query.filter_by(is_active=True).order_by(SocialLink.sort_order).all()
    
    @staticmethod
    def create_default_links():
        """Create default social media links if none exist"""
        if SocialLink.query.count() == 0:
            links = [
                SocialLink(platform='YouTube', url='', icon_class='fab fa-youtube', sort_order=1),
                SocialLink(platform='Instagram', url='', icon_class='fab fa-instagram', sort_order=2),
                SocialLink(platform='Twitter', url='', icon_class='fab fa-twitter', sort_order=3),
                SocialLink(platform='LinkedIn', url='', icon_class='fab fa-linkedin', sort_order=4),
                SocialLink(platform='Facebook', url='', icon_class='fab fa-facebook', sort_order=5),
            ]
            db.session.add_all(links)
            db.session.commit()
            return True
        return False

class UserActivity(db.Model):
    """Track user activity and data usage across the website"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))  # Clerk user ID or session ID for anonymous users
    user_email = db.Column(db.String(120))  # User email if available
    activity_type = db.Column(db.String(50), nullable=False)  # page_view, reel_view, poll_vote, download, etc.
    resource_type = db.Column(db.String(50))  # reel, opinion, course, lesson, etc.
    resource_id = db.Column(db.Integer)  # ID of the resource accessed
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.Text)  # Browser/device information
    page_url = db.Column(db.String(500))  # URL accessed
    referrer = db.Column(db.String(500))  # Referrer URL
    session_id = db.Column(db.String(100))  # Session identifier
    data_size = db.Column(db.Integer, default=0)  # Estimated data size in bytes
    duration = db.Column(db.Integer, default=0)  # Time spent in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id or 'Anonymous',
            'user_email': self.user_email or 'N/A',
            'activity_type': self.activity_type,
            'resource_type': self.resource_type or 'N/A',
            'resource_id': self.resource_id or 0,
            'ip_address': self.ip_address or 'N/A',
            'page_url': self.page_url or 'N/A',
            'data_size': self.data_size or 0,
            'duration': self.duration or 0,
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }
    
    @staticmethod
    def log_activity(user_id=None, user_email=None, activity_type='page_view', 
                    resource_type=None, resource_id=None, request_obj=None, 
                    data_size=0, duration=0):
        """Log user activity"""
        try:
            activity = UserActivity(
                user_id=user_id,
                user_email=user_email,
                activity_type=activity_type,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=request_obj.remote_addr if request_obj else None,
                user_agent=request_obj.headers.get('User-Agent') if request_obj else None,
                page_url=request_obj.url if request_obj else None,
                referrer=request_obj.referrer if request_obj else None,
                session_id=request_obj.cookies.get('session') if request_obj else None,
                data_size=data_size,
                duration=duration
            )
            db.session.add(activity)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error logging activity: {e}")
            return False
    
    @staticmethod
    def get_user_stats(user_id=None, days=30):
        """Get user statistics for the last N days"""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = UserActivity.query.filter(UserActivity.created_at >= cutoff_date)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        stats = {
            'total_activities': query.count(),
            'total_data_usage': db.session.query(func.sum(UserActivity.data_size)).filter(
                UserActivity.created_at >= cutoff_date,
                UserActivity.user_id == user_id if user_id else True
            ).scalar() or 0,
            'total_duration': db.session.query(func.sum(UserActivity.duration)).filter(
                UserActivity.created_at >= cutoff_date,
                UserActivity.user_id == user_id if user_id else True
            ).scalar() or 0,
            'page_views': query.filter_by(activity_type='page_view').count(),
            'reel_views': query.filter_by(activity_type='reel_view').count(),
            'poll_votes': query.filter_by(activity_type='poll_vote').count(),
        }
        
        return stats
    
    @staticmethod
    def get_top_users(limit=10, days=30):
        """Get top users by activity"""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        top_users = db.session.query(
            UserActivity.user_id,
            UserActivity.user_email,
            func.count(UserActivity.id).label('activity_count'),
            func.sum(UserActivity.data_size).label('total_data'),
            func.sum(UserActivity.duration).label('total_time')
        ).filter(
            UserActivity.created_at >= cutoff_date,
            UserActivity.user_id.isnot(None)
        ).group_by(
            UserActivity.user_id,
            UserActivity.user_email
        ).order_by(
            func.count(UserActivity.id).desc()
        ).limit(limit).all()
        
        return [{
            'user_id': user.user_id,
            'user_email': user.user_email or 'N/A',
            'activity_count': user.activity_count,
            'total_data': user.total_data or 0,
            'total_time': user.total_time or 0
        } for user in top_users]
    
    @staticmethod
    def get_activity_by_type(days=30):
        """Get activity breakdown by type"""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        activities = db.session.query(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.created_at >= cutoff_date
        ).group_by(
            UserActivity.activity_type
        ).all()
        
        return [{
            'activity_type': activity.activity_type,
            'count': activity.count
        } for activity in activities]
