from flask import render_template, request, jsonify, redirect, url_for, flash, session, abort
from app import app, db, _error_log, log_app_error
from models import DataManager, AdminUser, SiteContent, Reel, Opinion, Subscriber, SubscriptionTier, UserSubscription, Course, Module, Lesson, UserCourseAccess, SocialLink, ColumnVisibility, UserActivity, SiteConfig, CourseUser, ChatbotFAQ, ChatbotInquiry
from forms import NewsletterForm, PollVoteForm, AdminLoginForm, ReelForm, OpinionForm, HeroContentForm, PaymentSettingsForm, SubscriptionTierForm, CourseForm, ModuleForm, LessonForm, SocialLinkForm
from utils import save_uploaded_file, calculate_poll_percentages, get_youtube_embed_url, get_video_info, slugify
from clerk_auth import clerk_auth_required, get_clerk_user, get_clerk_user_id
import razorpay
import os
import json
import hmac
import hashlib
import logging
from datetime import datetime

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(
    os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummy_key'),
    os.environ.get('RAZORPAY_KEY_SECRET', 'dummy_secret')
))


def get_razorpay_client():
    """Return a Razorpay client using env-var credentials (preferred) or DB settings."""
    env_key_id = os.environ.get('RAZORPAY_KEY_ID', '')
    env_key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    if env_key_id and env_key_secret:
        return razorpay.Client(auth=(env_key_id, env_key_secret))
    try:
        payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
        if payment_content:
            ps = json.loads(payment_content.content_data)
            k, s = ps.get('razorpay_key_id', ''), ps.get('razorpay_key_secret', '')
            if k and s:
                return razorpay.Client(auth=(k, s))
    except Exception:
        pass
    return razorpay_client

def get_course_user_id():
    """Return the logged-in CourseUser's ID from session, or None."""
    return session.get('course_user_id')


def get_course_user():
    """Return the logged-in CourseUser object, or None."""
    uid = session.get('course_user_id')
    if uid:
        try:
            return CourseUser.query.get(uid)
        except Exception:
            pass
    return None


@app.context_processor
def inject_section_visibility():
    """Inject section visibility flags and site settings into all templates"""
    import json
    try:
        section_vis = {
            'hero': SiteConfig.get('section_hero_visible', 'true').lower() != 'false',
            'reels': SiteConfig.get('section_reels_visible', 'true').lower() != 'false',
            'support': SiteConfig.get('section_support_visible', 'true').lower() != 'false',
            'statistics': SiteConfig.get('section_statistics_visible', 'true').lower() != 'false',
            'testimonials': SiteConfig.get('section_testimonials_visible', 'true').lower() != 'false',
            'newsletter': SiteConfig.get('section_newsletter_visible', 'true').lower() != 'false',
            'courses': SiteConfig.get('section_courses_visible', 'true').lower() != 'false',
            'footer': SiteConfig.get('section_footer_visible', 'true').lower() != 'false',
        }
    except Exception:
        section_vis = {k: True for k in ['hero', 'reels', 'support', 'statistics', 'testimonials', 'newsletter', 'courses', 'footer']}

    try:
        settings_record = SiteContent.query.filter_by(content_key='site_settings').first()
        site_settings = json.loads(settings_record.content_data) if settings_record else {}
    except Exception:
        site_settings = {}

    # WhatsApp support phone for in-dashboard support button
    wa_support_phone = ''
    try:
        import re as _re
        wa_rec = SiteContent.query.filter_by(content_key='whatsapp_settings').first()
        if wa_rec:
            wa_data = json.loads(wa_rec.content_data)
            raw = wa_data.get('support_phone', '')
            digits = _re.sub(r'[^0-9]', '', raw)
            if len(digits) == 10:
                digits = '91' + digits
            wa_support_phone = digits
    except Exception:
        pass

    try:
        chatbot_enabled      = SiteConfig.get('chatbot_enabled', 'true').lower() != 'false'
        chatbot_name         = SiteConfig.get('chatbot_name', 'Kshitiz Assistant')
        chatbot_greeting     = SiteConfig.get('chatbot_greeting', '')
        try:
            chatbot_quick_replies = json.loads(SiteConfig.get('chatbot_quick_replies', '[]'))
        except Exception:
            chatbot_quick_replies = []
    except Exception:
        chatbot_enabled = True
        chatbot_name = 'Kshitiz Assistant'
        chatbot_greeting = ''
        chatbot_quick_replies = []

    # Announcement banner
    try:
        announcement_active = SiteConfig.get('announcement_active', '0') == '1'
        if announcement_active:
            _ann_text = SiteConfig.get('announcement_text', '')
            _ann_id   = str(abs(hash(_ann_text)) % 1000000) if _ann_text else 'x'
            announcement = {
                'active':    True,
                'text':      _ann_text,
                'link_url':  SiteConfig.get('announcement_link_url', ''),
                'link_text': SiteConfig.get('announcement_link_text', 'Learn More'),
                'style':     SiteConfig.get('announcement_style', 'info'),
                'id':        _ann_id,
            }
        else:
            announcement = None
    except Exception:
        announcement = None

    # SEO config — keyed by Flask endpoint name
    try:
        _seo_pages = ['index', 'reels_library', 'polls_archive', 'courses', 'upcoming_shows', 'contact']
        seo_config = {p: {
            'title':       SiteConfig.get(f'seo_{p}_title', ''),
            'description': SiteConfig.get(f'seo_{p}_description', ''),
        } for p in _seo_pages}
        seo_config['og_image']        = SiteConfig.get('seo_og_image', '')
        seo_config['twitter_handle']  = SiteConfig.get('seo_twitter_handle', '')
    except Exception:
        seo_config = {}

    return {
        'section_vis': section_vis,
        'site_settings': site_settings,
        'course_user': get_course_user(),
        'wa_support_phone': wa_support_phone,
        'chatbot_enabled': chatbot_enabled,
        'chatbot_name': chatbot_name,
        'chatbot_greeting': chatbot_greeting,
        'chatbot_quick_replies': chatbot_quick_replies,
        'announcement': announcement,
        'seo_config': seo_config,
    }


@app.route('/')
def index():
    """Homepage"""
    # Track page view
    try:
        user_id = get_clerk_user_id()
        user = get_clerk_user()
        user_email = user.get('email_addresses', [{}])[0].get('email_address') if user else None
        UserActivity.log_activity(
            user_id=user_id,
            user_email=user_email,
            activity_type='page_view',
            resource_type='homepage',
            request_obj=request,
            data_size=5000  # Estimated page size in bytes
        )
    except Exception:
        pass  # Skip activity logging if database unavailable
    
    content = DataManager.get_content()
    newsletter_form = NewsletterForm()
    poll_form = PollVoteForm()
    
    # Show only top 10 featured/visible reels on homepage ordered by sort_order
    try:
        featured_reels = Reel.query.filter_by(is_featured=True, is_visible=True).order_by(
            Reel.sort_order.asc(), Reel.created_at.desc()).limit(10).all()
        if not featured_reels:
            featured_reels = Reel.query.filter_by(is_visible=True).order_by(
                Reel.sort_order.asc(), Reel.created_at.desc()).limit(10).all()
        content['reels'] = [reel.to_dict() for reel in featured_reels]
    except Exception as e:
        import logging
        logging.error(f"Database error fetching featured reels: {e}")
        # content['reels'] already set by DataManager.get_content()

    # Calculate poll percentages
    for opinion in content['opinions']:
        opinion['percentages'] = calculate_poll_percentages(opinion['votes'])
        opinion['total_votes'] = sum(opinion['votes'])
    
    # Get subscription tiers from database
    try:
        AdminUser.create_default_tiers()  # Create default tiers if none exist
        subscription_tiers = AdminUser.get_subscription_tiers()
    except Exception as e:
        import logging
        logging.error(f"Database error fetching subscription tiers: {e}")
        subscription_tiers = []
    
    # Get Razorpay key — env var takes priority, fallback to DB admin setting
    import json
    razorpay_key = os.environ.get('RAZORPAY_KEY_ID', '')
    if not razorpay_key:
        try:
            payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
            if payment_content:
                payment_settings = json.loads(payment_content.content_data)
                db_key = payment_settings.get('razorpay_key_id', '')
                if db_key:
                    razorpay_key = db_key
        except Exception as e:
            import logging
            logging.error(f"Database error fetching payment settings: {e}")
    
    # Get page content
    page_content = DataManager.get_page_content()
    
    # Get featured courses for homepage teaser (up to 3)
    try:
        featured_courses = Course.query.filter_by(is_active=True).order_by(Course.sort_order, Course.id).limit(3).all()
        homepage_courses = []
        for c in featured_courses:
            cd = c.to_dict()
            cd['module_count'] = len(c.modules)
            cd['lesson_count'] = sum([len(m.lessons) for m in c.modules])
            homepage_courses.append(cd)
    except Exception:
        homepage_courses = []

    # Load statistics section data
    DEFAULT_STATS_DATA = {
        'title': 'By the Numbers',
        'subtitle': 'The reach keeps growing — thanks to you.',
        'stats': [
            {'icon': 'fas fa-rupee-sign', 'label': 'Total Support',   'value': '₹0',   'auto': ''},
            {'icon': 'fas fa-receipt',    'label': 'Donations',        'value': '0',    'auto': ''},
            {'icon': 'fas fa-users',      'label': 'Supporters',       'value': '0',    'auto': 'subscriber_count'},
            {'icon': 'fas fa-film',       'label': 'Reels Published',  'value': '0',    'auto': 'reel_count'},
            {'icon': 'fas fa-eye',        'label': 'Total Views',      'value': '1.2M+','auto': ''},
            {'icon': 'fas fa-heart',      'label': 'Followers',        'value': '50K+', 'auto': ''},
        ]
    }
    try:
        stats_record = SiteContent.query.filter_by(content_key='statistics_data').first()
        stats_data = json.loads(stats_record.content_data) if stats_record else DEFAULT_STATS_DATA
        if 'stats' not in stats_data:
            stats_data['stats'] = DEFAULT_STATS_DATA['stats']
        # Resolve auto values at render time
        for stat in stats_data['stats']:
            if stat.get('auto') == 'subscriber_count':
                stat['resolved_value'] = str(Subscriber.query.count())
            elif stat.get('auto') == 'reel_count':
                stat['resolved_value'] = str(Reel.query.filter_by(is_visible=True).count())
            else:
                stat['resolved_value'] = stat.get('value', '')
    except Exception:
        stats_data = DEFAULT_STATS_DATA
        for stat in stats_data['stats']:
            stat['resolved_value'] = stat.get('value', '')

    return render_template('index.html',
                         content=content,
                         newsletter_form=newsletter_form,
                         poll_form=poll_form,
                         subscription_tiers=subscription_tiers,
                         razorpay_key=razorpay_key,
                         page_content=page_content,
                         homepage_courses=homepage_courses,
                         stats_data=stats_data,
                         testimonials_list=_get_testimonials_list())

@app.route('/reels')
def reels_library():
    """Full library view with search and filters"""
    # Get filter parameters
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'latest')  # latest, oldest, popular
    category = request.args.get('category', '')
    topic = request.args.get('topic', '')
    page = request.args.get('page', 1, type=int)
    per_page = 24  # Show 24 reels per page (grid layout)
    
    # Base query
    query = Reel.query
    
    # Apply search filter
    if search:
        query = query.filter(Reel.title.ilike(f'%{search}%'))
    
    # Apply category filter
    if category:
        query = query.filter_by(category_tag=category)
    
    # Apply topic filter
    if topic:
        query = query.filter_by(topic_tag=topic)
    
    # Apply sorting
    if sort_by == 'oldest':
        query = query.order_by(Reel.created_at.asc())
    elif sort_by == 'popular':
        query = query.order_by(Reel.view_count.desc())
    else:  # latest
        query = query.order_by(Reel.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reels = [reel.to_dict() for reel in pagination.items]
    
    # Get all topics for filter dropdown
    topics = db.session.query(Reel.topic_tag).filter(Reel.topic_tag != None, Reel.topic_tag != '').distinct().all()
    topic_list = [t[0] for t in topics]
    
    # Get all categories for filter
    categories = db.session.query(Reel.category_tag).filter(Reel.category_tag != None, Reel.category_tag != '').distinct().all()
    category_list = [c[0] for c in categories]
    
    return render_template('reels_library.html',
                         reels=reels,
                         pagination=pagination,
                         topics=topic_list,
                         categories=category_list,
                         current_search=search,
                         current_sort=sort_by,
                         current_category=category,
                         current_topic=topic)

@app.route('/reel/<int:reel_id>')
def reel_detail(reel_id):
    """Reel detail page"""
    reel = Reel.query.get_or_404(reel_id)
    
    # Track reel view
    user_id = get_clerk_user_id()
    user = get_clerk_user()
    user_email = user.get('email_addresses', [{}])[0].get('email_address') if user else None
    UserActivity.log_activity(
        user_id=user_id,
        user_email=user_email,
        activity_type='reel_view',
        resource_type='reel',
        resource_id=reel_id,
        request_obj=request,
        data_size=10000  # Estimated size for reel page
    )
    
    # Increment view count
    if reel.view_count is None:
        reel.view_count = 0
    reel.view_count += 1
    db.session.commit()
    
    # Get reel data
    reel_data = reel.to_dict()

    # Process video URL — get embed URL, original URL, and type
    if reel_data.get('video_url'):
        vinfo = get_video_info(reel_data['video_url'], reel_data.get('video_type', 'auto'))
        reel_data['embed_url'] = vinfo['embed_url']
        reel_data['original_url'] = vinfo['original_url']
        reel_data['detected_type'] = vinfo['video_type']
        reel_data['is_instagram'] = vinfo['video_type'] == 'instagram'
    else:
        reel_data['embed_url'] = None
        reel_data['original_url'] = ''
        reel_data['detected_type'] = 'unknown'
        reel_data['is_instagram'] = False

    # Get related reels from same topic
    related_reels = []
    if reel.topic_tag:
        related_reels = Reel.query.filter(
            Reel.topic_tag == reel.topic_tag,
            Reel.id != reel_id
        ).order_by(Reel.created_at.desc()).limit(6).all()
        related_reels = [r.to_dict() for r in related_reels]
    
    return render_template('reel_detail.html', reel=reel_data, related_reels=related_reels)

@app.route('/contact')
def contact():
    """Contact page"""
    contact_emails = {
        'general': 'ask@kshitizjaiswal.in',
        'sources': 'sources@kshitizjaiswal.in',
        'collaborate': 'invite@kshitizjaiswal.in',
        'feedback': 'feedback@kshitizjaiswal.in'
    }
    return render_template('contact.html', emails=contact_emails)

@app.route('/resources')
def resources():
    """Learning & Resources page"""
    # already imported - SiteContent
    import json
    
    # Get resources from database
    resources_content = SiteContent.query.filter_by(content_key='resources').first()
    resources = json.loads(resources_content.content_data) if resources_content else []
    
    return render_template('resources.html', resources=resources)

@app.route('/resource/<slug>')
def resource_detail(slug):
    """Individual resource detail page"""
    import json
    
    # Get resources from database
    resources_content = SiteContent.query.filter_by(content_key='resources').first()
    resources = json.loads(resources_content.content_data) if resources_content else []
    
    # Find resource by slug
    resource = None
    for r in resources:
        resource_slug = r['link'].split('/')[-1] if r['link'] else ''
        if resource_slug == slug:
            resource = r
            break
    
    if not resource:
        abort(404)
    
    return render_template('resource_detail.html', resource=resource)

@app.route('/upcoming-shows')
def upcoming_shows():
    """Upcoming Shows page"""
    import json
    
    # Get upcoming shows from database
    shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
    shows = json.loads(shows_content.content_data) if shows_content else []
    
    return render_template('upcoming_shows.html', shows=shows)

@app.route('/newsletter', methods=['POST'])
def newsletter_subscribe():
    """Newsletter subscription — supports both form POST and AJAX (JSON) requests"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Accept', '').startswith('application/json')

    form = NewsletterForm()

    if form.validate_on_submit():
        try:
            DataManager.add_subscriber(
                form.name.data,
                form.email.data,
                form.place.data or '',
                form.age.data or 0
            )
            if is_ajax:
                return jsonify({'success': True, 'message': 'Successfully subscribed to newsletter!'})
            flash('Successfully subscribed to newsletter!', 'success')
        except Exception as e:
            if is_ajax:
                return jsonify({'success': False, 'message': 'You may already be subscribed, or an error occurred.'})
            flash('Error subscribing to newsletter. Please try again.', 'error')
    else:
        errors = '; '.join([f for field in form for f in field.errors])
        if is_ajax:
            return jsonify({'success': False, 'message': errors or 'Please fill all fields correctly.'})
        flash('Please fill all fields correctly.', 'error')

    return redirect(url_for('index') + '#newsletter')

@app.route('/vote', methods=['POST'])
def vote_poll():
    """Handle poll voting"""
    form = PollVoteForm()
    
    if form.validate_on_submit():
        # Track poll vote
        user_id = get_clerk_user_id()
        user = get_clerk_user()
        user_email = user.get('email_addresses', [{}])[0].get('email_address') if user else None
        UserActivity.log_activity(
            user_id=user_id,
            user_email=user_email,
            activity_type='poll_vote',
            resource_type='opinion',
            resource_id=form.opinion_id.data,
            request_obj=request,
            data_size=500  # Small data for vote
        )
        
        success = DataManager.vote_poll(form.opinion_id.data, form.option_index.data)
        if success:
            return jsonify({'status': 'success', 'message': 'Vote recorded!'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid vote'})
    
    return jsonify({'status': 'error', 'message': 'Invalid request'})

@app.route('/polls')
def polls_archive():
    """Poll Archive Page with Search and Filters"""
    # Get filter parameters
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'latest')
    topic = request.args.get('topic', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Base query
    query = Opinion.query
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Opinion.title.ilike(f'%{search}%'),
                Opinion.description.ilike(f'%{search}%'),
                Opinion.poll_question.ilike(f'%{search}%')
            )
        )
    
    # Apply topic filter
    if topic:
        query = query.filter_by(topic_tag=topic)
    
    # Apply date range filter
    if date_from:
        from datetime import datetime
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(Opinion.created_at >= date_from_obj)
    
    if date_to:
        from datetime import datetime
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
        query = query.filter(Opinion.created_at <= date_to_obj)
    
    # Apply sorting
    if sort_by == 'oldest':
        query = query.order_by(Opinion.created_at.asc())
    elif sort_by == 'popular':
        # Sort by total votes (calculate from votes JSON)
        opinions_list = query.all()
        opinions_list.sort(key=lambda x: sum(json.loads(x.votes) if x.votes else []), reverse=True)
        # Handle pagination manually for popular sort
        total = len(opinions_list)
        start = (page - 1) * per_page
        end = start + per_page
        opinions = opinions_list[start:end]
        
        # Format opinions
        formatted_opinions = []
        for opinion in opinions:
            formatted_opinion = opinion.to_dict()
            formatted_opinion['formatted_date'] = opinion.created_at.strftime("%B %d, %Y")
            formatted_opinion['short_description'] = (opinion.description[:100] + '...' 
                                                     if opinion.description and len(opinion.description) > 100 
                                                     else opinion.description or '')
            formatted_opinions.append(formatted_opinion)
        
        # Get topics for filter
        topics = db.session.query(Opinion.topic_tag).filter(Opinion.topic_tag != None, Opinion.topic_tag != '').distinct().all()
        topic_list = [t[0] for t in topics]
        
        return render_template('polls_archive.html',
                             opinions=formatted_opinions,
                             current_search=search,
                             current_sort=sort_by,
                             current_topic=topic,
                             current_date_from=date_from,
                             current_date_to=date_to,
                             topics=topic_list,
                             page=page,
                             total_pages=(total + per_page - 1) // per_page)
    else:  # latest
        query = query.order_by(Opinion.created_at.desc())
    
    # Paginate if not already handled
    if sort_by != 'popular':
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        opinions = pagination.items
        total_pages = pagination.pages
        
        # Format opinions
        formatted_opinions = []
        for opinion in opinions:
            formatted_opinion = opinion.to_dict()
            formatted_opinion['formatted_date'] = opinion.created_at.strftime("%B %d, %Y")
            formatted_opinion['short_description'] = (opinion.description[:100] + '...' 
                                                     if opinion.description and len(opinion.description) > 100 
                                                     else opinion.description or '')
            formatted_opinions.append(formatted_opinion)
    
    # Get topics for filter
    topics = db.session.query(Opinion.topic_tag).filter(Opinion.topic_tag != None, Opinion.topic_tag != '').distinct().all()
    topic_list = [t[0] for t in topics]
    
    return render_template('polls_archive.html',
                         opinions=formatted_opinions,
                         current_search=search,
                         current_sort=sort_by,
                         current_topic=topic,
                         current_date_from=date_from,
                         current_date_to=date_to,
                         topics=topic_list,
                         page=page,
                         total_pages=total_pages if sort_by != 'popular' else (len(opinions_list) + per_page - 1) // per_page)

@app.route('/poll/<int:poll_id>')
def poll_detail(poll_id):
    """Individual Poll Detail Page with Related Polls"""
    opinion = Opinion.query.get_or_404(poll_id)
    poll_form = PollVoteForm()
    
    # Convert to dict and calculate percentages
    formatted_opinion = opinion.to_dict()
    from utils import calculate_poll_percentages
    formatted_opinion['percentages'] = calculate_poll_percentages(formatted_opinion['votes'])
    formatted_opinion['total_votes'] = sum(formatted_opinion['votes'])
    formatted_opinion['formatted_date'] = opinion.created_at.strftime("%B %d, %Y")
    
    # Get related polls from same topic
    related_polls = []
    if opinion.topic_tag:
        related_polls_query = Opinion.query.filter(
            Opinion.topic_tag == opinion.topic_tag,
            Opinion.id != poll_id
        ).order_by(Opinion.created_at.desc()).limit(6).all()
        
        for related in related_polls_query:
            related_dict = related.to_dict()
            related_dict['formatted_date'] = related.created_at.strftime("%B %d, %Y")
            related_dict['total_votes'] = sum(json.loads(related.votes) if related.votes else [])
            related_polls.append(related_dict)
    
    return render_template('poll_detail.html', opinion=formatted_opinion, poll_form=poll_form, related_polls=related_polls)

@app.route('/create_payment', methods=['POST'])
def create_payment():
    """Create Razorpay payment order for support payments"""
    try:
        import json
        payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
        
        env_key_id = os.environ.get('RAZORPAY_KEY_ID', '')
        env_key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
        if env_key_id and env_key_secret:
            dynamic_client = razorpay.Client(auth=(env_key_id, env_key_secret))
        elif payment_content:
            payment_settings = json.loads(payment_content.content_data)
            razorpay_key_id = payment_settings.get('razorpay_key_id')
            razorpay_key_secret = payment_settings.get('razorpay_key_secret')
            if razorpay_key_id and razorpay_key_secret:
                dynamic_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
            else:
                dynamic_client = razorpay_client
        else:
            dynamic_client = razorpay_client

        data = request.json or {}
        amount = int(data.get('amount', 10)) * 100  # Convert to paise
        buyer_name = data.get('name', '')
        buyer_email = data.get('email', '')
        buyer_phone = data.get('phone', '')
        
        order_data = {
            'amount': amount,
            'currency': 'INR',
            'receipt': f'support_{amount//100}',
            'payment_capture': 1,
            'notes': {
                'type': 'support',
                'buyer_name': buyer_name,
                'buyer_email': buyer_email,
                'buyer_phone': buyer_phone
            }
        }
        
        order = dynamic_client.order.create(data=order_data)
        return jsonify({
            'status': 'success',
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency']
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Subscriber
    content = DataManager.get_content()
    subscribers = [s.to_dict() for s in Subscriber.query.all()]
    
    return render_template('admin/dashboard.html', 
                         content=content, 
                         subscribers=subscribers)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    form = AdminLoginForm()
    
    if form.validate_on_submit():
        if AdminUser.verify_admin(form.username.data, form.password.data):
            session['admin_logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Successfully logged out!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/fetch-video-meta')
def admin_fetch_video_meta():
    """Fetch title, thumbnail, and description from a YouTube/Instagram URL."""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'})

    import re as _re
    import requests as _req

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    title = ''
    thumbnail = ''
    description = ''

    def _og(html, prop):
        """Extract og/meta tag content — handles both property= and name= variants."""
        m = _re.search(
            r'<meta[^>]+(?:property|name)=["\']' + _re.escape(prop) + r'["\'][^>]+content=["\'](.*?)["\']',
            html, _re.IGNORECASE
        ) or _re.search(
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:property|name)=["\']' + _re.escape(prop) + r'["\']',
            html, _re.IGNORECASE
        )
        return m.group(1).strip() if m else ''

    try:
        # ── YouTube ──────────────────────────────────────────────────
        yt_id = None
        for pat in [
            r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
            r'youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})',
            r'youtu\.be/([A-Za-z0-9_-]{11})',
        ]:
            m = _re.search(pat, url)
            if m:
                yt_id = m.group(1)
                break

        if yt_id:
            # oEmbed → reliable title + thumbnail
            oembed = _req.get(
                f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json',
                timeout=8
            )
            if oembed.status_code == 200:
                od = oembed.json()
                title = od.get('title', '')
                thumbnail = od.get('thumbnail_url', '')

            # Fall back to maxresdefault if oEmbed thumbnail missing
            if not thumbnail:
                thumbnail = f'https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg'

            # Fetch page for og:description
            page = _req.get(
                f'https://www.youtube.com/watch?v={yt_id}',
                headers=headers, timeout=8
            )
            if page.status_code == 200:
                description = _og(page.text, 'og:description')
                if not title:
                    title = _og(page.text, 'og:title')

        # ── Instagram ────────────────────────────────────────────────
        elif 'instagram.com' in url:
            ig_m = _re.search(r'instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)', url)
            try:
                oembed = _req.get(
                    f'https://www.instagram.com/oembed/?url={url}',
                    headers=headers, timeout=8
                )
                if oembed.status_code == 200:
                    od = oembed.json()
                    title = od.get('title', '')
                    thumbnail = od.get('thumbnail_url', '')
            except Exception:
                pass

            # Page scrape fallback
            if not title or not description:
                page = _req.get(url, headers=headers, timeout=8)
                if page.status_code == 200:
                    if not title:
                        title = _og(page.text, 'og:title')
                    if not thumbnail:
                        thumbnail = _og(page.text, 'og:image')
                    description = _og(page.text, 'og:description')

        # ── Generic fallback ─────────────────────────────────────────
        else:
            page = _req.get(url, headers=headers, timeout=8)
            if page.status_code == 200:
                title = _og(page.text, 'og:title')
                thumbnail = _og(page.text, 'og:image')
                description = _og(page.text, 'og:description')

        if not title and not thumbnail:
            return jsonify({'success': False, 'error': 'Could not find metadata for this URL. The platform may block automated access.'})

        return jsonify({
            'success': True,
            'title': title,
            'thumbnail': thumbnail,
            'description': description,
        })

    except Exception as exc:
        return jsonify({'success': False, 'error': f'Request failed: {exc}'})


@app.route('/admin/reel/add', methods=['GET', 'POST'])
def admin_add_reel():
    """Add new reel"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = ReelForm()
    
    if form.validate_on_submit():
        # already imported - Reel, db
        import json
        
        # Handle thumbnail upload
        thumbnail_url = None
        if form.thumbnail.data:
            thumbnail_url = save_uploaded_file(form.thumbnail.data, 'reels')
        
        # Process sources
        sources = [s.strip() for s in form.sources.data.split('\n') if s.strip()]
        
        # Handle thumbnail URL fallback
        if not thumbnail_url and form.thumbnail_url.data:
            thumbnail_url = form.thumbnail_url.data

        new_reel = Reel(
            title=form.title.data,
            thumbnail=thumbnail_url or '',
            video_url=form.video_url.data or '',
            video_type=form.video_type.data or 'auto',
            card_layout=form.card_layout.data or 'standard',
            sort_order=form.sort_order.data or 0,
            behind_thought=form.behind_thought.data,
            sources=json.dumps(sources),
            extra_context=form.extra_context.data or '',
            category_tag=form.category_tag.data or '',
            topic_tag=form.topic_tag.data or '',
            is_featured=bool(int(form.is_featured.data)),
            is_visible=bool(int(form.is_visible.data)),
            view_count=0
        )
        
        db.session.add(new_reel)
        db.session.commit()
        
        flash('Reel added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/reel_form.html', form=form, title='Add New Reel')

@app.route('/admin/opinion/add', methods=['GET', 'POST'])
def admin_add_opinion():
    """Add new opinion"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = OpinionForm()
    
    if form.validate_on_submit():
        # already imported - Opinion, db
        import json
        
        poll_options = [form.poll_option1.data, form.poll_option2.data]
        if form.poll_option3.data:
            poll_options.append(form.poll_option3.data)
        
        new_opinion = Opinion(
            title=form.title.data,
            position=form.position.data,
            description=form.description.data or '',
            topic_tag=form.topic_tag.data or '',
            poll_question=form.poll_question.data,
            poll_options=json.dumps(poll_options),
            votes=json.dumps([0] * len(poll_options))
        )
        
        db.session.add(new_opinion)
        db.session.commit()
        
        flash('Opinion added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/opinion_form.html', form=form, title='Add New Opinion')

# Edit and Delete Routes
@app.route('/admin/reel/<int:reel_id>/edit', methods=['GET', 'POST'])
def admin_edit_reel(reel_id):
    """Edit reel"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Reel, db
    import json
    
    reel = Reel.query.get_or_404(reel_id)
    form = ReelForm()
    
    if form.validate_on_submit():
        # Handle thumbnail upload
        if form.thumbnail.data:
            reel.thumbnail = save_uploaded_file(form.thumbnail.data, 'reels')
        
        # Process sources
        sources = [s.strip() for s in form.sources.data.split('\n') if s.strip()]
        
        # Handle thumbnail URL fallback on edit
        if not reel.thumbnail and form.thumbnail_url.data:
            reel.thumbnail = form.thumbnail_url.data

        reel.title = form.title.data
        reel.video_url = form.video_url.data or ''
        reel.video_type = form.video_type.data or 'auto'
        reel.card_layout = form.card_layout.data or 'standard'
        reel.sort_order = form.sort_order.data or 0
        reel.behind_thought = form.behind_thought.data
        reel.sources = json.dumps(sources)
        reel.extra_context = form.extra_context.data or ''
        reel.category_tag = form.category_tag.data or ''
        reel.topic_tag = form.topic_tag.data or ''
        reel.is_featured = bool(int(form.is_featured.data))
        reel.is_visible = bool(int(form.is_visible.data))
        
        db.session.commit()
        
        flash('Reel updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Pre-populate form with existing data
    if request.method == 'GET':
        form.title.data = reel.title
        form.video_url.data = reel.video_url
        form.video_type.data = reel.video_type or 'auto'
        form.card_layout.data = reel.card_layout or 'standard'
        form.sort_order.data = reel.sort_order or 0
        form.behind_thought.data = reel.behind_thought
        form.sources.data = '\n'.join(json.loads(reel.sources) if reel.sources else [])
        form.extra_context.data = reel.extra_context
        form.category_tag.data = reel.category_tag or ''
        form.topic_tag.data = reel.topic_tag or ''
        form.is_featured.data = '1' if reel.is_featured else '0'
        form.is_visible.data = '0' if reel.is_visible is False else '1'
    
    return render_template('admin/reel_form.html', form=form, title='Edit Reel', reel=reel)

@app.route('/admin/reel/<int:reel_id>/delete', methods=['POST'])
def admin_delete_reel(reel_id):
    """Delete reel"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    reel = Reel.query.get_or_404(reel_id)
    db.session.delete(reel)
    db.session.commit()
    flash('Reel deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reel/<int:reel_id>/toggle-visible', methods=['POST'])
def admin_toggle_reel_visible(reel_id):
    """Toggle per-reel visibility"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    reel = Reel.query.get_or_404(reel_id)
    reel.is_visible = not reel.is_visible
    db.session.commit()
    return jsonify({'is_visible': reel.is_visible, 'id': reel.id})


@app.route('/admin/reels/reorder', methods=['POST'])
def admin_reorder_reels():
    """Save new sort order for reels (array of IDs in desired order)"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    ordered_ids = data.get('ids', [])
    for idx, reel_id in enumerate(ordered_ids):
        Reel.query.filter_by(id=int(reel_id)).update({'sort_order': idx})
    db.session.commit()
    return jsonify({'status': 'ok', 'count': len(ordered_ids)})


@app.route('/admin/reels/toggle-section', methods=['POST'])
def admin_toggle_reels_section():
    """Toggle whole reels section on/off on homepage (legacy — now uses section_reels_visible)"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    current = SiteConfig.get('section_reels_visible', 'true')
    new_val = 'false' if current.lower() == 'true' else 'true'
    SiteConfig.set('section_reels_visible', new_val)
    return jsonify({'reels_section_visible': new_val == 'true'})


@app.route('/admin/section-visibility', methods=['GET', 'POST'])
def admin_section_visibility():
    """Admin page: Show/Hide toggles for all major website sections"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    SECTIONS = [
        {'key': 'hero',         'label': 'Hero Banner',        'icon': 'fas fa-image',          'desc': 'The top banner with name, tagline and CTA buttons.'},
        {'key': 'reels',        'label': 'Reels Section',       'icon': 'fas fa-film',           'desc': 'Scrolling reel cards on the homepage.'},
        {'key': 'support',      'label': 'Support Section',     'icon': 'fas fa-heart',          'desc': 'Subscription tiers and donation area.'},
        {'key': 'statistics',   'label': 'Statistics Bar',      'icon': 'fas fa-chart-bar',      'desc': 'Key numbers — views, followers, supporters.'},
        {'key': 'testimonials', 'label': 'Testimonials',        'icon': 'fas fa-quote-left',     'desc': 'What viewers say about the commentary.'},
        {'key': 'newsletter',   'label': 'Newsletter Section',  'icon': 'fas fa-envelope',       'desc': 'Email signup CTA on the homepage.'},
        {'key': 'courses',      'label': 'Courses Teaser',      'icon': 'fas fa-graduation-cap', 'desc': 'Featured courses preview on the homepage.'},
        {'key': 'footer',       'label': 'Footer',              'icon': 'fas fa-layer-group',    'desc': 'Site-wide footer with links and social icons.'},
    ]

    if request.method == 'POST':
        for s in SECTIONS:
            val = 'true' if request.form.get(f"section_{s['key']}_visible") else 'false'
            SiteConfig.set(f"section_{s['key']}_visible", val)
        flash('Section visibility settings saved!', 'success')
        return redirect(url_for('admin_section_visibility'))

    visibility = {}
    for s in SECTIONS:
        visibility[s['key']] = SiteConfig.get(f"section_{s['key']}_visible", 'true').lower() != 'false'

    return render_template('admin/section_visibility.html', sections=SECTIONS, visibility=visibility)


@app.route('/admin/section-visibility/toggle/<section>', methods=['POST'])
def admin_toggle_section(section):
    """AJAX toggle for a single section — returns new state as JSON"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    allowed = ['hero', 'reels', 'support', 'statistics', 'testimonials', 'newsletter', 'courses', 'footer']
    if section not in allowed:
        return jsonify({'error': 'Invalid section'}), 400
    current = SiteConfig.get(f'section_{section}_visible', 'true')
    new_val = 'false' if current.lower() == 'true' else 'true'
    SiteConfig.set(f'section_{section}_visible', new_val)
    return jsonify({'visible': new_val == 'true', 'section': section})

@app.route('/admin/statistics-section', methods=['GET', 'POST'])
def admin_statistics_section():
    """Admin: Manage statistics section data and visibility"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    from datetime import datetime as _dt

    DEFAULT_STATS = {
        'title': 'By the Numbers',
        'subtitle': 'The reach keeps growing — thanks to you.',
        'stats': [
            {'icon': 'fas fa-rupee-sign',          'label': 'Total Support',   'value': '₹0',   'auto': ''},
            {'icon': 'fas fa-receipt',              'label': 'Donations',       'value': '0',    'auto': ''},
            {'icon': 'fas fa-users',               'label': 'Supporters',       'value': '0',    'auto': 'subscriber_count'},
            {'icon': 'fas fa-film',                'label': 'Reels Published',  'value': '0',    'auto': 'reel_count'},
            {'icon': 'fas fa-eye',                 'label': 'Total Views',      'value': '1.2M+','auto': ''},
            {'icon': 'fas fa-heart',               'label': 'Followers',        'value': '50K+', 'auto': ''},
        ]
    }

    # Live DB values for display / auto-sync
    try:
        live_subscriber_count = Subscriber.query.count()
    except Exception:
        live_subscriber_count = 0
    try:
        live_reel_count = Reel.query.filter_by(is_visible=True).count()
    except Exception:
        live_reel_count = 0

    if request.method == 'POST':
        title    = request.form.get('title', 'By the Numbers').strip()
        subtitle = request.form.get('subtitle', '').strip()

        stats = []
        idx = 0
        while True:
            icon = request.form.get(f'stat_icon_{idx}')
            if icon is None:
                break
            label = request.form.get(f'stat_label_{idx}', '').strip()
            value = request.form.get(f'stat_value_{idx}', '').strip()
            auto  = request.form.get(f'stat_auto_{idx}', '')
            # keep rows that have at least an icon or label
            if icon.strip() or label:
                stats.append({'icon': icon.strip(), 'label': label, 'value': value, 'auto': auto})
            idx += 1

        data = {'title': title, 'subtitle': subtitle, 'stats': stats}
        record = SiteContent.query.filter_by(content_key='statistics_data').first()
        if record:
            record.content_data = json.dumps(data)
            record.updated_at   = _dt.utcnow()
        else:
            record = SiteContent(content_key='statistics_data', content_data=json.dumps(data))
            db.session.add(record)
        db.session.commit()
        flash('Statistics section saved successfully!', 'success')
        return redirect(url_for('admin_statistics_section'))

    record = SiteContent.query.filter_by(content_key='statistics_data').first()
    data   = json.loads(record.content_data) if record else DEFAULT_STATS
    if 'stats' not in data:
        data['stats'] = DEFAULT_STATS['stats']

    is_visible = SiteConfig.get('section_statistics_visible', 'true').lower() != 'false'

    return render_template('admin/statistics_section.html',
                           data=data,
                           is_visible=is_visible,
                           live_subscriber_count=live_subscriber_count,
                           live_reel_count=live_reel_count)


@app.route('/admin/opinion/<int:opinion_id>/edit', methods=['GET', 'POST'])
def admin_edit_opinion(opinion_id):
    """Edit opinion"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Opinion, db
    import json
    
    opinion = Opinion.query.get_or_404(opinion_id)
    form = OpinionForm()
    
    if form.validate_on_submit():
        poll_options = [form.poll_option1.data, form.poll_option2.data]
        if form.poll_option3.data:
            poll_options.append(form.poll_option3.data)
        
        # Preserve existing votes if options haven't changed significantly
        current_votes = json.loads(opinion.votes) if opinion.votes else []
        current_options = json.loads(opinion.poll_options) if opinion.poll_options else []
        
        # Keep existing votes or reset if options changed
        if len(poll_options) == len(current_options):
            new_votes = current_votes
        else:
            new_votes = [0] * len(poll_options)
        
        opinion.title = form.title.data
        opinion.position = form.position.data
        opinion.description = form.description.data or ''
        opinion.topic_tag = form.topic_tag.data or ''
        opinion.poll_question = form.poll_question.data
        opinion.poll_options = json.dumps(poll_options)
        opinion.votes = json.dumps(new_votes)
        
        db.session.commit()
        
        flash('Opinion updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Pre-populate form with existing data
    if request.method == 'GET':
        form.title.data = opinion.title
        form.position.data = opinion.position
        form.description.data = opinion.description
        form.topic_tag.data = opinion.topic_tag
        form.poll_question.data = opinion.poll_question
        
        poll_options = json.loads(opinion.poll_options) if opinion.poll_options else []
        if len(poll_options) >= 1:
            form.poll_option1.data = poll_options[0]
        if len(poll_options) >= 2:
            form.poll_option2.data = poll_options[1]
        if len(poll_options) >= 3:
            form.poll_option3.data = poll_options[2]
    
    return render_template('admin/opinion_form.html', form=form, title='Edit Opinion', opinion=opinion)

@app.route('/admin/opinion/<int:opinion_id>/delete', methods=['POST'])
def admin_delete_opinion(opinion_id):
    """Delete opinion"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Opinion, db
    
    opinion = Opinion.query.get_or_404(opinion_id)
    db.session.delete(opinion)
    db.session.commit()
    
    flash('Opinion deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/opinion/<int:opinion_id>/results')
def admin_opinion_results(opinion_id):
    """View poll results"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Opinion
    import json
    
    opinion = Opinion.query.get_or_404(opinion_id)
    poll_options = json.loads(opinion.poll_options) if opinion.poll_options else []
    votes = json.loads(opinion.votes) if opinion.votes else []
    
    total_votes = sum(votes)
    results = []
    for i, option in enumerate(poll_options):
        vote_count = votes[i] if i < len(votes) else 0
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        results.append({
            'option': option,
            'votes': vote_count,
            'percentage': round(percentage, 1)
        })
    
    return render_template('admin/poll_results.html', opinion=opinion, results=results, total_votes=total_votes)

@app.route('/admin/hero-content', methods=['GET', 'POST'])
def admin_hero_content():
    """Manage hero section content"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent, db
    import json
    
    form = HeroContentForm()
    
    # Get current hero content
    hero_content = SiteContent.query.filter_by(content_key='hero').first()
    current_hero = json.loads(hero_content.content_data) if hero_content else {
        "name": "Kshitiz Jaiswal",
        "tagline": "Unfiltered Commentator. The content here is selective, but the truth is never biased.",
        "banner_url": "https://pixabay.com/get/g533a6aa47eba4823795ce2e25fdfdbeab9c4946d039afcc8be299199aea4607bcead5e63e650f3598d32b8af6f69fa29cd392bcfe2db7bc9db577a352240b008_1280.jpg"
    }
    
    if form.validate_on_submit():
        # Keep existing URLs as fallback if no new file is uploaded
        existing_desktop = current_hero.get('desktop_url', '')
        existing_mobile  = current_hero.get('mobile_url', '')
        existing_banner  = current_hero.get('banner_url', '')

        # Handle desktop image upload
        desktop_url = save_uploaded_file(form.desktop_image.data, 'hero') or existing_desktop

        # Handle mobile image upload
        mobile_url = save_uploaded_file(form.mobile_image.data, 'hero') or existing_mobile

        # Handle legacy banner image upload
        banner_uploaded = save_uploaded_file(form.banner_image.data, 'hero')
        banner_url = banner_uploaded or existing_banner
        # If no desktop/mobile set yet, promote banner to both
        if banner_uploaded:
            if not desktop_url:
                desktop_url = banner_uploaded
            if not mobile_url:
                mobile_url = banner_uploaded

        # Update hero content
        updated_hero = {
            "name": form.name.data,
            "tagline": form.tagline.data,
            "banner_url": banner_url,
            "desktop_url": desktop_url,
            "mobile_url": mobile_url
        }

        if hero_content:
            hero_content.content_data = json.dumps(updated_hero)
        else:
            hero_content = SiteContent(content_key='hero', content_data=json.dumps(updated_hero))
            db.session.add(hero_content)

        db.session.commit()
        flash('Hero content updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    # Pre-populate text fields; file inputs cannot be pre-populated
    if request.method == 'GET':
        form.name.data = current_hero.get('name', '')
        form.tagline.data = current_hero.get('tagline', '')
    
    return render_template('admin/hero_form.html', form=form, title='Hero Content', current_hero=current_hero)

@app.route('/admin/payment-settings', methods=['GET', 'POST'])
def admin_payment_settings():
    """Manage Razorpay payment settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent, db
    import json
    
    form = PaymentSettingsForm()
    
    # Get current payment settings
    payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
    current_settings = json.loads(payment_content.content_data) if payment_content else {
        "razorpay_key_id": "",
        "razorpay_key_secret": ""
    }
    
    if form.validate_on_submit():
        # Update payment settings
        updated_settings = {
            "razorpay_key_id": form.razorpay_key_id.data,
            "razorpay_key_secret": form.razorpay_key_secret.data
        }
        
        if payment_content:
            payment_content.content_data = json.dumps(updated_settings)
        else:
            payment_content = SiteContent(content_key='payment_settings', content_data=json.dumps(updated_settings))
            db.session.add(payment_content)
        
        db.session.commit()
        flash('Payment settings updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Pre-populate form with current data (hide secret for security)
    if request.method == 'GET':
        form.razorpay_key_id.data = current_settings.get('razorpay_key_id', '')
        # Don't pre-populate secret for security
    
    return render_template('admin/payment_form.html', form=form, title='Payment Settings')

@app.route('/admin/subscription-tiers')
def admin_subscription_tiers():
    """Manage subscription tiers"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SubscriptionTier
    # Create default tiers if none exist
    AdminUser.create_default_tiers()
    
    tiers = SubscriptionTier.query.order_by(SubscriptionTier.sort_order, SubscriptionTier.price).all()
    return render_template('admin/subscription_tiers.html', tiers=tiers)

@app.route('/admin/subscription-tier/add', methods=['GET', 'POST'])
def admin_add_subscription_tier():
    """Add new subscription tier"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = SubscriptionTierForm()
    
    if form.validate_on_submit():
        # already imported - SubscriptionTier, db
        import json
        
        # Collect benefits
        benefits = []
        if form.benefit1.data: benefits.append(form.benefit1.data)
        if form.benefit2.data: benefits.append(form.benefit2.data)
        if form.benefit3.data: benefits.append(form.benefit3.data)
        if form.benefit4.data: benefits.append(form.benefit4.data)
        
        # Clear other popular tiers if this one is marked as popular
        if form.is_popular.data == '1':
            SubscriptionTier.query.update({'is_popular': False})
        
        new_tier = SubscriptionTier(
            name=form.name.data,
            price=form.price.data,
            period=form.period.data,
            description=form.description.data,
            icon=form.icon.data or 'fas fa-heart',
            benefits=json.dumps(benefits),
            is_popular=(form.is_popular.data == '1'),
            sort_order=form.sort_order.data
        )
        
        db.session.add(new_tier)
        db.session.commit()
        
        flash('Subscription tier added successfully!', 'success')
        return redirect(url_for('admin_subscription_tiers'))
    
    return render_template('admin/subscription_tier_form.html', form=form, title='Add Subscription Tier')

@app.route('/admin/subscription-tier/<int:tier_id>/edit', methods=['GET', 'POST'])
def admin_edit_subscription_tier(tier_id):
    """Edit subscription tier"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SubscriptionTier, db
    import json
    
    tier = SubscriptionTier.query.get_or_404(tier_id)
    form = SubscriptionTierForm(obj=tier)
    
    if form.validate_on_submit():
        # Collect benefits
        benefits = []
        if form.benefit1.data: benefits.append(form.benefit1.data)
        if form.benefit2.data: benefits.append(form.benefit2.data)
        if form.benefit3.data: benefits.append(form.benefit3.data)
        if form.benefit4.data: benefits.append(form.benefit4.data)
        
        # Clear other popular tiers if this one is marked as popular
        if form.is_popular.data == '1' and not tier.is_popular:
            SubscriptionTier.query.filter(SubscriptionTier.id != tier_id).update({'is_popular': False})
        
        # If price or period changed, invalidate the cached Razorpay plan so a new one is created next time
        if tier.price != form.price.data or tier.period != form.period.data:
            tier.razorpay_plan_id = None

        # Update tier
        tier.name = form.name.data
        tier.price = form.price.data
        tier.period = form.period.data
        tier.description = form.description.data
        tier.icon = form.icon.data or 'fas fa-heart'
        tier.benefits = json.dumps(benefits)
        tier.is_popular = (form.is_popular.data == '1')
        tier.sort_order = form.sort_order.data
        
        db.session.commit()
        
        flash('Subscription tier updated successfully!', 'success')
        return redirect(url_for('admin_subscription_tiers'))
    
    # Pre-populate form
    if request.method == 'GET':
        benefits = json.loads(tier.benefits) if tier.benefits else []
        form.benefit1.data = benefits[0] if len(benefits) > 0 else ''
        form.benefit2.data = benefits[1] if len(benefits) > 1 else ''
        form.benefit3.data = benefits[2] if len(benefits) > 2 else ''
        form.benefit4.data = benefits[3] if len(benefits) > 3 else ''
        form.is_popular.data = '1' if tier.is_popular else '0'
    
    return render_template('admin/subscription_tier_form.html', form=form, title='Edit Subscription Tier', tier=tier)

@app.route('/admin/subscription-tier/<int:tier_id>/delete', methods=['POST'])
def admin_delete_subscription_tier(tier_id):
    """Delete subscription tier"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SubscriptionTier, db
    
    tier = SubscriptionTier.query.get_or_404(tier_id)
    tier_name = tier.name
    
    db.session.delete(tier)
    db.session.commit()
    
    flash(f'Subscription tier "{tier_name}" deleted successfully!', 'success')
    return redirect(url_for('admin_subscription_tiers'))

@app.route('/admin/subscription-tier/<int:tier_id>/toggle', methods=['POST'])
def admin_toggle_subscription_tier(tier_id):
    """Toggle subscription tier active status"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SubscriptionTier, db
    
    tier = SubscriptionTier.query.get_or_404(tier_id)
    tier.is_active = not tier.is_active
    
    db.session.commit()
    
    status = "activated" if tier.is_active else "deactivated"
    flash(f'Subscription tier "{tier.name}" {status} successfully!', 'success')
    return redirect(url_for('admin_subscription_tiers'))

@app.route('/admin/social-links')
def admin_social_links():
    """Manage social media links"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    SocialLink.create_default_links()
    SocialLink.seed_missing_platforms()
    links = SocialLink.query.order_by(SocialLink.sort_order).all()

    # Brand colour map for the admin UI (keyed by lowercase platform name)
    platform_colors = {
        name.lower(): color
        for name, _icon, color, _order in SocialLink.DEFAULT_PLATFORMS
    }

    return render_template('admin/social_links.html', links=links, platform_colors=platform_colors)

@app.route('/admin/social-link/add', methods=['GET', 'POST'])
def admin_add_social_link():
    """Add new social link"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = SocialLinkForm()
    
    if form.validate_on_submit():
        link = SocialLink(
            platform=form.platform.data,
            url=form.url.data,
            icon_class=form.icon_class.data,
            is_active=form.is_active.data == '1',
            sort_order=form.sort_order.data
        )
        
        db.session.add(link)
        db.session.commit()
        
        flash(f'Social link "{link.platform}" added successfully!', 'success')
        return redirect(url_for('admin_social_links'))
    
    return render_template('admin/social_link_form.html', form=form, title='Add Social Link')

@app.route('/admin/social-link/<int:link_id>/edit', methods=['GET', 'POST'])
def admin_edit_social_link(link_id):
    """Edit social link"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    link = SocialLink.query.get_or_404(link_id)
    form = SocialLinkForm()
    
    if form.validate_on_submit():
        link.platform = form.platform.data
        link.url = form.url.data
        link.icon_class = form.icon_class.data
        link.is_active = form.is_active.data == '1'
        link.sort_order = form.sort_order.data
        
        db.session.commit()
        
        flash(f'Social link "{link.platform}" updated successfully!', 'success')
        return redirect(url_for('admin_social_links'))
    
    if request.method == 'GET':
        form.platform.data = link.platform
        form.url.data = link.url
        form.icon_class.data = link.icon_class
        form.is_active.data = '1' if link.is_active else '0'
        form.sort_order.data = link.sort_order
    
    return render_template('admin/social_link_form.html', form=form, title='Edit Social Link', link=link)

@app.route('/admin/social-link/<int:link_id>/delete', methods=['POST'])
def admin_delete_social_link(link_id):
    """Delete social link"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    link = SocialLink.query.get_or_404(link_id)
    platform = link.platform
    
    db.session.delete(link)
    db.session.commit()
    
    flash(f'Social link "{platform}" deleted successfully!', 'success')
    return redirect(url_for('admin_social_links'))

@app.route('/admin/social-link/<int:link_id>/toggle', methods=['POST'])
def admin_toggle_social_link(link_id):
    """Toggle social link active status"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    link = SocialLink.query.get_or_404(link_id)
    link.is_active = not link.is_active
    
    db.session.commit()
    
    status = "enabled" if link.is_active else "disabled"
    flash(f'{link.platform} {status} — changes are live on the website.', 'success')
    return redirect(url_for('admin_social_links'))

@app.route('/admin/social-link/<int:link_id>/update-url', methods=['POST'])
def admin_update_social_url(link_id):
    """Inline URL update — no full edit form needed."""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    link = SocialLink.query.get_or_404(link_id)
    url = request.form.get('url', '').strip()
    link.url = url
    db.session.commit()

    flash(f'{link.platform} URL saved successfully!', 'success')
    return redirect(url_for('admin_social_links'))

@app.route('/admin/resources')
def admin_resources():
    """Manage Learning Resources"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent
    import json
    
    resources_content = SiteContent.query.filter_by(content_key='resources').first()
    resources = json.loads(resources_content.content_data) if resources_content else []
    
    return render_template('admin/resources.html', resources=resources)

@app.route('/admin/resource/add', methods=['GET', 'POST'])
def admin_add_resource():
    """Add new learning resource"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from forms import ResourceForm
    # already imported - SiteContent
    import json
    
    form = ResourceForm()
    
    if form.validate_on_submit():
        # Get current resources
        resources_content = SiteContent.query.filter_by(content_key='resources').first()
        resources = json.loads(resources_content.content_data) if resources_content else []
        
        # Handle image upload
        uploaded_image = save_uploaded_file(form.image.data, 'resources')

        # Add new resource
        new_resource = {
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'link': form.link.data,
            'image': uploaded_image or 'https://pixabay.com/get/g1607648249e3d2cc886480cc481c2224cb52f7fd6b06e51d63e7c2ee7d304d71973191ec7388dc286501651899d7fd130bc378c50e5ab80727d452f099c3f672_1280.jpg'
        }
        resources.append(new_resource)
        
        # Save to database
        if resources_content:
            resources_content.content_data = json.dumps(resources)
        else:
            resources_content = SiteContent(content_key='resources', content_data=json.dumps(resources))
            db.session.add(resources_content)
        
        db.session.commit()
        flash('Learning resource added successfully!', 'success')
        return redirect(url_for('admin_resources'))
    
    return render_template('admin/resource_form.html', form=form, title='Add Learning Resource')

@app.route('/admin/resource/edit/<int:resource_index>', methods=['GET', 'POST'])
def admin_edit_resource(resource_index):
    """Edit learning resource"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from forms import ResourceForm
    # already imported - SiteContent
    import json
    
    # Get current resources
    resources_content = SiteContent.query.filter_by(content_key='resources').first()
    resources = json.loads(resources_content.content_data) if resources_content else []
    
    if resource_index >= len(resources):
        flash('Resource not found!', 'error')
        return redirect(url_for('admin_resources'))
    
    resource = resources[resource_index]
    form = ResourceForm()
    
    if form.validate_on_submit():
        # Handle image upload — keep existing if no new file uploaded
        uploaded_image = save_uploaded_file(form.image.data, 'resources')

        resources[resource_index] = {
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'link': form.link.data,
            'image': uploaded_image or resource.get('image', '')
        }
        
        resources_content.content_data = json.dumps(resources)
        db.session.commit()
        
        flash('Learning resource updated successfully!', 'success')
        return redirect(url_for('admin_resources'))
    
    # Populate form with current data (image is FileField — do not set .data)
    form.title.data = resource.get('title', '')
    form.description.data = resource.get('description', '')
    form.price.data = resource.get('price', '')
    form.link.data = resource.get('link', '')
    current_image = resource.get('image', '')
    
    return render_template('admin/resource_form.html', form=form, title='Edit Learning Resource',
                           resource=resource, current_image=current_image)

@app.route('/admin/resource/delete/<int:resource_index>')
def admin_delete_resource(resource_index):
    """Delete learning resource"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent
    import json
    
    # Get current resources
    resources_content = SiteContent.query.filter_by(content_key='resources').first()
    resources = json.loads(resources_content.content_data) if resources_content else []
    
    if resource_index < len(resources):
        resource_title = resources[resource_index].get('title', 'Resource')
        del resources[resource_index]
        
        # Save to database
        resources_content.content_data = json.dumps(resources)
        db.session.commit()
        
        flash(f'Learning resource "{resource_title}" deleted successfully!', 'success')
    else:
        flash('Resource not found!', 'error')
    
    return redirect(url_for('admin_resources'))

@app.route('/admin/shows')
def admin_shows():
    """Manage Upcoming Shows"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent
    import json
    
    shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
    shows = json.loads(shows_content.content_data) if shows_content else []
    
    return render_template('admin/shows.html', shows=shows)

@app.route('/admin/show/add', methods=['GET', 'POST'])
def admin_add_show():
    """Add new upcoming show"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from forms import ShowForm
    # already imported - SiteContent
    import json
    
    form = ShowForm()
    
    if form.validate_on_submit():
        # Get current shows
        shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
        shows = json.loads(shows_content.content_data) if shows_content else []
        
        # Handle image upload
        uploaded_image = save_uploaded_file(form.image.data, 'shows')

        # Add new show
        new_show = {
            'title': form.title.data,
            'description': form.description.data,
            'image': uploaded_image or 'https://pixabay.com/get/g51d3a9b60f5b304d6d9a2109588df26fa955fdad29b549ed6f2d44cdb714ef5b54d4b04df2f46da1bd05dede83422e909ae5403a8c87771e7130a78714c2e5df_1280.jpg',
            'coming_soon': bool(int(form.coming_soon.data)),
            'notify_link': form.notify_link.data
        }
        shows.append(new_show)
        
        # Save to database
        if shows_content:
            shows_content.content_data = json.dumps(shows)
        else:
            shows_content = SiteContent(content_key='upcoming_shows', content_data=json.dumps(shows))
            db.session.add(shows_content)
        
        db.session.commit()
        flash('Upcoming show added successfully!', 'success')
        return redirect(url_for('admin_shows'))
    
    return render_template('admin/show_form.html', form=form, title='Add Upcoming Show')

@app.route('/admin/show/edit/<int:show_index>', methods=['GET', 'POST'])
def admin_edit_show(show_index):
    """Edit upcoming show"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from forms import ShowForm
    # already imported - SiteContent
    import json
    
    # Get current shows
    shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
    shows = json.loads(shows_content.content_data) if shows_content else []
    
    if show_index >= len(shows):
        flash('Show not found!', 'error')
        return redirect(url_for('admin_shows'))
    
    show = shows[show_index]
    form = ShowForm()
    
    if form.validate_on_submit():
        # Handle image upload — keep existing if no new file uploaded
        uploaded_image = save_uploaded_file(form.image.data, 'shows')

        shows[show_index] = {
            'title': form.title.data,
            'description': form.description.data,
            'image': uploaded_image or show.get('image', ''),
            'coming_soon': bool(int(form.coming_soon.data)),
            'notify_link': form.notify_link.data
        }
        
        shows_content.content_data = json.dumps(shows)
        db.session.commit()
        
        flash('Upcoming show updated successfully!', 'success')
        return redirect(url_for('admin_shows'))
    
    # Populate form with current data (image is FileField — do not set .data)
    form.title.data = show.get('title', '')
    form.description.data = show.get('description', '')
    form.coming_soon.data = '1' if show.get('coming_soon', True) else '0'
    form.notify_link.data = show.get('notify_link', '')
    current_image = show.get('image', '')
    
    return render_template('admin/show_form.html', form=form, title='Edit Upcoming Show',
                           show=show, current_image=current_image)

@app.route('/admin/show/delete/<int:show_index>')
def admin_delete_show(show_index):
    """Delete upcoming show"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - SiteContent
    import json
    
    # Get current shows
    shows_content = SiteContent.query.filter_by(content_key='upcoming_shows').first()
    shows = json.loads(shows_content.content_data) if shows_content else []
    
    if show_index < len(shows):
        show_title = shows[show_index].get('title', 'Show')
        del shows[show_index]
        
        # Save to database
        shows_content.content_data = json.dumps(shows)
        db.session.commit()
        
        flash(f'Upcoming show "{show_title}" deleted successfully!', 'success')
    else:
        flash('Show not found!', 'error')
    
    return redirect(url_for('admin_shows'))

# Admin Course Management Routes
def _get_curriculum_settings():
    """Return curriculum display settings dict with defaults."""
    record = SiteContent.query.filter_by(content_key='curriculum_display').first()
    defaults = {
        'display_mode': 'full',
        'show_video_duration': True,
    }
    if record:
        try:
            stored = json.loads(record.content_data)
            defaults.update(stored)
        except Exception:
            pass
    return defaults

@app.route('/admin/courses')
def admin_courses():
    """Admin courses listing"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    content = DataManager.get_content()
    subscribers = [s.to_dict() for s in Subscriber.query.all()]
    courses = Course.query.order_by(Course.sort_order, Course.id).all()
    curriculum_settings = _get_curriculum_settings()
    return render_template('admin/courses.html', courses=courses, content=content, subscribers=subscribers, curriculum_settings=curriculum_settings)

@app.route('/admin/curriculum-settings', methods=['POST'])
def admin_save_curriculum_settings():
    """Save curriculum display settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    display_mode = request.form.get('display_mode', 'full')
    show_video_duration = request.form.get('show_video_duration') == 'on'
    
    settings = {
        'display_mode': display_mode,
        'show_video_duration': show_video_duration,
    }
    
    record = SiteContent.query.filter_by(content_key='curriculum_display').first()
    if record:
        record.content_data = json.dumps(settings)
    else:
        record = SiteContent(content_key='curriculum_display', content_data=json.dumps(settings))
        db.session.add(record)
    db.session.commit()
    
    flash('Curriculum display settings saved successfully.', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/course/add', methods=['GET', 'POST'])
def admin_add_course():
    """Add new course"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = CourseForm()
    
    if form.validate_on_submit():
        thumbnail_path = ''
        if form.thumbnail.data:
            thumbnail_path = save_uploaded_file(form.thumbnail.data, 'courses')
        elif form.thumbnail_url.data:
            thumbnail_path = form.thumbnail_url.data
        
        course = Course(
            title=form.title.data,
            description=form.description.data,
            thumbnail=thumbnail_path,
            preview_video_url=form.preview_video_url.data or '',
            price=form.price.data,
            is_active=bool(int(form.is_active.data)),
            sort_order=form.sort_order.data
        )
        db.session.add(course)
        db.session.commit()
        
        flash(f'Course "{course.title}" added successfully!', 'success')
        return redirect(url_for('admin_courses'))
    
    return render_template('admin/course_form.html', form=form, title='Add New Course')

@app.route('/admin/course/<int:course_id>/edit', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    """Edit course"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    course = Course.query.get_or_404(course_id)
    form = CourseForm()
    
    if form.validate_on_submit():
        if form.thumbnail.data:
            course.thumbnail = save_uploaded_file(form.thumbnail.data, 'courses')
        elif form.thumbnail_url.data:
            course.thumbnail = form.thumbnail_url.data
        
        course.title = form.title.data
        course.description = form.description.data
        course.preview_video_url = form.preview_video_url.data or ''
        course.price = form.price.data
        course.is_active = bool(int(form.is_active.data))
        course.sort_order = form.sort_order.data
        
        db.session.commit()
        flash(f'Course "{course.title}" updated successfully!', 'success')
        return redirect(url_for('admin_courses'))
    
    form.title.data = course.title
    form.description.data = course.description
    form.preview_video_url.data = course.preview_video_url or ''
    form.price.data = course.price
    form.is_active.data = '1' if course.is_active else '0'
    form.sort_order.data = course.sort_order
    
    return render_template('admin/course_form.html', form=form, course=course, title='Edit Course')

@app.route('/admin/course/<int:course_id>/delete', methods=['POST'])
def admin_delete_course(course_id):
    """Delete course"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    course = Course.query.get_or_404(course_id)
    course_title = course.title
    
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course "{course_title}" deleted successfully!', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/modules')
def admin_modules():
    """Admin modules listing"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    content = DataManager.get_content()
    subscribers = [s.to_dict() for s in Subscriber.query.all()]
    modules = Module.query.order_by(Module.course_id, Module.sort_order).all()
    return render_template('admin/modules.html', modules=modules, content=content, subscribers=subscribers)

@app.route('/admin/module/add', methods=['GET', 'POST'])
def admin_add_module():
    """Add new module"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = ModuleForm()
    form.course_id.choices = [(c.id, c.title) for c in Course.query.order_by(Course.title).all()]
    
    if form.validate_on_submit():
        module = Module(
            title=form.title.data,
            description=form.description.data,
            course_id=form.course_id.data,
            sort_order=form.sort_order.data
        )
        db.session.add(module)
        db.session.commit()
        
        flash(f'Module "{module.title}" added successfully!', 'success')
        return redirect(url_for('admin_modules'))
    
    return render_template('admin/module_form.html', form=form, title='Add New Module')

@app.route('/admin/module/<int:module_id>/edit', methods=['GET', 'POST'])
def admin_edit_module(module_id):
    """Edit module"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    module = Module.query.get_or_404(module_id)
    form = ModuleForm()
    form.course_id.choices = [(c.id, c.title) for c in Course.query.order_by(Course.title).all()]
    
    if form.validate_on_submit():
        module.title = form.title.data
        module.description = form.description.data
        module.course_id = form.course_id.data
        module.sort_order = form.sort_order.data
        
        db.session.commit()
        flash(f'Module "{module.title}" updated successfully!', 'success')
        return redirect(url_for('admin_modules'))
    
    form.title.data = module.title
    form.description.data = module.description
    form.course_id.data = module.course_id
    form.sort_order.data = module.sort_order
    
    return render_template('admin/module_form.html', form=form, module=module, title='Edit Module')

@app.route('/admin/module/<int:module_id>/delete', methods=['POST'])
def admin_delete_module(module_id):
    """Delete module"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    module = Module.query.get_or_404(module_id)
    module_title = module.title
    
    db.session.delete(module)
    db.session.commit()
    
    flash(f'Module "{module_title}" deleted successfully!', 'success')
    return redirect(url_for('admin_modules'))

@app.route('/admin/lessons')
def admin_lessons():
    """Admin lessons listing"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    content = DataManager.get_content()
    subscribers = [s.to_dict() for s in Subscriber.query.all()]
    lessons = Lesson.query.join(Module).order_by(Module.course_id, Module.sort_order, Lesson.sort_order).all()
    return render_template('admin/lessons.html', lessons=lessons, content=content, subscribers=subscribers)

@app.route('/admin/lesson/add', methods=['GET', 'POST'])
def admin_add_lesson():
    """Add new lesson"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    form = LessonForm()
    form.module_id.choices = [(m.id, f"{m.course.title} - {m.title}") for m in Module.query.join(Course).order_by(Course.title, Module.sort_order).all()]
    
    if form.validate_on_submit():
        lesson = Lesson(
            title=form.title.data,
            description=form.description.data,
            module_id=form.module_id.data,
            video_url=form.video_url.data,
            notes=form.notes.data,
            duration=form.duration.data,
            sort_order=form.sort_order.data
        )
        db.session.add(lesson)
        db.session.commit()
        
        flash(f'Lesson "{lesson.title}" added successfully!', 'success')
        return redirect(url_for('admin_lessons'))
    
    return render_template('admin/lesson_form.html', form=form, title='Add New Lesson')

@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
def admin_edit_lesson(lesson_id):
    """Edit lesson"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    form = LessonForm()
    form.module_id.choices = [(m.id, f"{m.course.title} - {m.title}") for m in Module.query.join(Course).order_by(Course.title, Module.sort_order).all()]
    
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.description = form.description.data
        lesson.module_id = form.module_id.data
        lesson.video_url = form.video_url.data
        lesson.notes = form.notes.data
        lesson.duration = form.duration.data
        lesson.sort_order = form.sort_order.data
        
        db.session.commit()
        flash(f'Lesson "{lesson.title}" updated successfully!', 'success')
        return redirect(url_for('admin_lessons'))
    
    form.title.data = lesson.title
    form.description.data = lesson.description
    form.module_id.data = lesson.module_id
    form.video_url.data = lesson.video_url
    form.notes.data = lesson.notes
    form.duration.data = lesson.duration
    form.sort_order.data = lesson.sort_order
    
    return render_template('admin/lesson_form.html', form=form, lesson=lesson, title='Edit Lesson')

@app.route('/admin/lesson/<int:lesson_id>/delete', methods=['POST'])
def admin_delete_lesson(lesson_id):
    """Delete lesson"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    lesson_title = lesson.title
    
    db.session.delete(lesson)
    db.session.commit()
    
    flash(f'Lesson "{lesson_title}" deleted successfully!', 'success')
    return redirect(url_for('admin_lessons'))

# ── Course Builder ────────────────────────────────────────────────────────────

@app.route('/admin/course/<int:course_id>/builder')
def admin_course_builder(course_id):
    """Drag-drop course builder with module/lesson visibility and status controls"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    course = Course.query.get_or_404(course_id)
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.sort_order).all()
    return render_template('admin/course_builder.html', course=course, modules=modules)

# ── AJAX: Reorder ─────────────────────────────────────────────────────────────

@app.route('/admin/api/modules/reorder', methods=['POST'])
def admin_api_reorder_modules():
    """Reorder modules via drag-drop. Body: {course_id, order: [id, ...]}"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    order = data.get('order', [])
    for idx, module_id in enumerate(order):
        Module.query.filter_by(id=module_id).update({'sort_order': idx})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/api/lessons/reorder', methods=['POST'])
def admin_api_reorder_lessons():
    """Reorder lessons within a module. Body: {module_id, order: [id, ...]}"""
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    order = data.get('order', [])
    for idx, lesson_id in enumerate(order):
        Lesson.query.filter_by(id=lesson_id).update({'sort_order': idx})
    db.session.commit()
    return jsonify({'ok': True})

# ── AJAX: Toggle visibility ───────────────────────────────────────────────────

@app.route('/admin/module/<int:module_id>/toggle-visibility', methods=['POST'])
def admin_toggle_module_visibility(module_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    module = Module.query.get_or_404(module_id)
    module.is_visible = not module.is_visible
    db.session.commit()
    return jsonify({'ok': True, 'is_visible': module.is_visible})

@app.route('/admin/lesson/<int:lesson_id>/toggle-visibility', methods=['POST'])
def admin_toggle_lesson_visibility(lesson_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_visible = not lesson.is_visible
    db.session.commit()
    return jsonify({'ok': True, 'is_visible': lesson.is_visible})

# ── AJAX: Toggle status (draft / published) ───────────────────────────────────

@app.route('/admin/module/<int:module_id>/toggle-status', methods=['POST'])
def admin_toggle_module_status(module_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    module = Module.query.get_or_404(module_id)
    module.status = 'draft' if module.status == 'published' else 'published'
    db.session.commit()
    return jsonify({'ok': True, 'status': module.status})

@app.route('/admin/lesson/<int:lesson_id>/toggle-status', methods=['POST'])
def admin_toggle_lesson_status(lesson_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.status = 'draft' if lesson.status == 'published' else 'published'
    db.session.commit()
    return jsonify({'ok': True, 'status': lesson.status})

# NEW ADMIN FEATURES

@app.route('/admin/analytics')
def admin_analytics():
    """Analytics Dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Get statistics
    total_reels = Reel.query.count()
    total_opinions = Opinion.query.count()
    total_subscribers = Subscriber.query.count()
    total_courses = Course.query.count()
    total_course_enrollments = UserCourseAccess.query.count()
    
    # Most viewed reels
    top_reels = Reel.query.order_by(Reel.view_count.desc()).limit(10).all()
    
    # Recent subscribers (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_subscribers = Subscriber.query.filter(Subscriber.subscribed_at >= thirty_days_ago).count()
    
    # Poll engagement
    opinions_with_votes = Opinion.query.all()
    total_votes = sum([sum(json.loads(op.votes) if op.votes else []) for op in opinions_with_votes])
    
    # Topic distribution
    topic_distribution = db.session.query(
        Opinion.topic_tag,
        func.count(Opinion.id).label('count')
    ).filter(Opinion.topic_tag.isnot(None), Opinion.topic_tag != '').group_by(Opinion.topic_tag).all()
    
    # Category distribution for reels
    category_distribution = db.session.query(
        Reel.category_tag,
        func.count(Reel.id).label('count')
    ).filter(Reel.category_tag.isnot(None), Reel.category_tag != '').group_by(Reel.category_tag).all()
    
    return render_template('admin/analytics.html',
                         total_reels=total_reels,
                         total_opinions=total_opinions,
                         total_subscribers=total_subscribers,
                         total_courses=total_courses,
                         total_course_enrollments=total_course_enrollments,
                         top_reels=[r.to_dict() for r in top_reels],
                         recent_subscribers=recent_subscribers,
                         total_votes=total_votes,
                         topic_distribution=topic_distribution,
                         category_distribution=category_distribution)

@app.route('/admin/users')
def admin_users():
    """User Management - View course enrollments"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    enrollments = UserCourseAccess.query.join(Course).order_by(UserCourseAccess.granted_at.desc()).all()
    
    enrollment_data = []
    for enrollment in enrollments:
        enrollment_data.append({
            'id': enrollment.id,
            'clerk_user_id': enrollment.clerk_user_id,
            'course_title': enrollment.course.title,
            'amount_paid': enrollment.amount_paid,
            'payment_id': enrollment.payment_id,
            'granted_at': enrollment.granted_at.strftime('%Y-%m-%d %H:%M'),
            'expires_at': enrollment.expires_at.strftime('%Y-%m-%d') if enrollment.expires_at else 'Never'
        })
    
    return render_template('admin/users.html', enrollments=enrollment_data)

@app.route('/admin/bulk-operations')
def admin_bulk_operations():
    """Bulk Operations Interface"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    reels = Reel.query.all()
    opinions = Opinion.query.all()
    
    return render_template('admin/bulk_operations.html',
                         reels=[r.to_dict() for r in reels],
                         opinions=[o.to_dict() for o in opinions])

@app.route('/admin/bulk-delete-reels', methods=['POST'])
def admin_bulk_delete_reels():
    """Bulk delete reels"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    reel_ids = request.form.getlist('reel_ids[]')
    if reel_ids:
        Reel.query.filter(Reel.id.in_(reel_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'{len(reel_ids)} reels deleted successfully!', 'success')
    
    return redirect(url_for('admin_bulk_operations'))

@app.route('/admin/bulk-feature-reels', methods=['POST'])
def admin_bulk_feature_reels():
    """Bulk feature/unfeature reels"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    reel_ids = request.form.getlist('reel_ids[]')
    action = request.form.get('action', 'feature')
    
    if reel_ids:
        reels = Reel.query.filter(Reel.id.in_(reel_ids)).all()
        for reel in reels:
            reel.is_featured = (action == 'feature')
        db.session.commit()
        flash(f'{len(reel_ids)} reels updated successfully!', 'success')
    
    return redirect(url_for('admin_bulk_operations'))

@app.route('/admin/site-settings', methods=['GET', 'POST'])
def admin_site_settings():
    """Site Settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        settings = {
            'site_title': request.form.get('site_title', 'Kshitiz Jaiswal'),
            'site_tagline': request.form.get('site_tagline', 'Unfiltered Commentator'),
            'contact_email': request.form.get('contact_email', ''),
            'social_facebook': request.form.get('social_facebook', ''),
            'social_twitter': request.form.get('social_twitter', ''),
            'social_instagram': request.form.get('social_instagram', ''),
            'social_youtube': request.form.get('social_youtube', ''),
            'meta_description': request.form.get('meta_description', ''),
            'meta_keywords': request.form.get('meta_keywords', ''),
            'google_analytics_id': request.form.get('google_analytics_id', ''),
            'facebook_pixel_id': request.form.get('facebook_pixel_id', ''),
            'clarity_id': request.form.get('clarity_id', '')
        }
        
        settings_record = SiteContent.query.filter_by(content_key='site_settings').first()
        if settings_record:
            settings_record.content_data = json.dumps(settings)
            settings_record.updated_at = datetime.utcnow()
        else:
            settings_record = SiteContent(content_key='site_settings', content_data=json.dumps(settings))
            db.session.add(settings_record)
        
        db.session.commit()
        flash('Site settings updated successfully!', 'success')
        return redirect(url_for('admin_site_settings'))
    
    # Load current settings
    settings_record = SiteContent.query.filter_by(content_key='site_settings').first()
    if settings_record:
        settings = json.loads(settings_record.content_data)
    else:
        settings = {}
    
    return render_template('admin/site_settings.html', settings=settings)

@app.route('/admin/page-content', methods=['GET', 'POST'])
def admin_page_content():
    """Manage page content sections"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from forms import PageContentForm
    
    form = PageContentForm()
    
    if form.validate_on_submit():
        content_data = {
            'reels_section_title': form.reels_section_title.data,
            'reels_section_subtitle': form.reels_section_subtitle.data,
            'support_section_title': form.support_section_title.data,
            'support_section_subtitle': form.support_section_subtitle.data,
            'custom_support_button_text': form.custom_support_button_text.data,
            'custom_support_subtitle': form.custom_support_subtitle.data,
            'support_stats_count': form.support_stats_count.data,
            'support_stats_amount': form.support_stats_amount.data
        }
        
        try:
            DataManager.save_page_content(content_data)
            flash('Page content updated successfully!', 'success')
        except Exception as e:
            flash(f'Error saving page content: {str(e)}. Please check your database connection.', 'error')
        
        return redirect(url_for('admin_page_content'))
    
    # Pre-populate form with current data
    if request.method == 'GET':
        current_content = DataManager.get_page_content()
        form.reels_section_title.data = current_content.get('reels_section_title', '')
        form.reels_section_subtitle.data = current_content.get('reels_section_subtitle', '')
        form.support_section_title.data = current_content.get('support_section_title', '')
        form.support_section_subtitle.data = current_content.get('support_section_subtitle', '')
        form.custom_support_button_text.data = current_content.get('custom_support_button_text', '')
        form.custom_support_subtitle.data = current_content.get('custom_support_subtitle', '')
        form.support_stats_count.data = current_content.get('support_stats_count', 0)
        form.support_stats_amount.data = current_content.get('support_stats_amount', 0)
    
    return render_template('admin/page_content.html', form=form, title='Page Content')


@app.route('/admin/content-manager', methods=['GET', 'POST'])
def admin_content_manager():
    """Unified Content Manager — edit all homepage sections from one place"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    from datetime import datetime as _dt

    if request.method == 'POST':
        action = request.form.get('action', '')
        pc = DataManager.get_page_content()

        if action == 'reels':
            pc.update({
                'reels_section_title':    request.form.get('reels_section_title', '').strip(),
                'reels_section_subtitle': request.form.get('reels_section_subtitle', '').strip(),
                'reels_button_text':      request.form.get('reels_button_text', '').strip(),
            })
            DataManager.save_page_content(pc)
            SiteConfig.set('section_reels_visible', 'true' if request.form.get('section_reels_visible') else 'false')
            flash('Reels section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#reels')

        elif action == 'support':
            pc.update({
                'support_section_title':      request.form.get('support_section_title', '').strip(),
                'support_section_subtitle':   request.form.get('support_section_subtitle', '').strip(),
                'custom_support_button_text': request.form.get('custom_support_button_text', '').strip(),
                'custom_support_subtitle':    request.form.get('custom_support_subtitle', '').strip(),
                'support_stats_count':        request.form.get('support_stats_count', '127').strip(),
                'support_stats_amount':       request.form.get('support_stats_amount', '2340').strip(),
            })
            DataManager.save_page_content(pc)
            SiteConfig.set('section_support_visible', 'true' if request.form.get('section_support_visible') else 'false')
            flash('Support section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#support')

        elif action == 'statistics':
            title    = request.form.get('stats_title', 'By the Numbers').strip()
            subtitle = request.form.get('stats_subtitle', '').strip()
            stats = []
            idx = 0
            while True:
                icon = request.form.get(f'stat_icon_{idx}')
                if icon is None:
                    break
                label   = request.form.get(f'stat_label_{idx}', '').strip()
                value   = request.form.get(f'stat_value_{idx}', '').strip()
                auto    = request.form.get(f'stat_auto_{idx}', '').strip()
                visible = request.form.get(f'stat_visible_{idx}', '1')
                if icon.strip() or label:
                    stats.append({'icon': icon.strip(), 'label': label, 'value': value, 'auto': auto, 'visible': visible})
                idx += 1
            data   = {'title': title, 'subtitle': subtitle, 'stats': stats}
            record = SiteContent.query.filter_by(content_key='statistics_data').first()
            if record:
                record.content_data = json.dumps(data)
                record.updated_at   = _dt.utcnow()
            else:
                record = SiteContent(content_key='statistics_data', content_data=json.dumps(data))
                db.session.add(record)
            db.session.commit()
            SiteConfig.set('section_statistics_visible', 'true' if request.form.get('section_statistics_visible') else 'false')
            flash('Statistics section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#statistics')

        elif action == 'testimonials':
            pc.update({
                'testimonials_section_title':    request.form.get('testimonials_section_title', '').strip(),
                'testimonials_section_subtitle': request.form.get('testimonials_section_subtitle', '').strip(),
                'testimonial1_text': request.form.get('testimonial1_text', '').strip(),
                'testimonial1_name': request.form.get('testimonial1_name', '').strip(),
                'testimonial1_role': request.form.get('testimonial1_role', '').strip(),
                'testimonial2_text': request.form.get('testimonial2_text', '').strip(),
                'testimonial2_name': request.form.get('testimonial2_name', '').strip(),
                'testimonial2_role': request.form.get('testimonial2_role', '').strip(),
                'testimonial3_text': request.form.get('testimonial3_text', '').strip(),
                'testimonial3_name': request.form.get('testimonial3_name', '').strip(),
                'testimonial3_role': request.form.get('testimonial3_role', '').strip(),
            })
            DataManager.save_page_content(pc)
            SiteConfig.set('section_testimonials_visible', 'true' if request.form.get('section_testimonials_visible') else 'false')
            flash('Testimonials section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#testimonials')

        elif action == 'courses':
            pc.update({
                'courses_section_title':    request.form.get('courses_section_title', '').strip(),
                'courses_section_subtitle': request.form.get('courses_section_subtitle', '').strip(),
                'courses_button_text':      request.form.get('courses_button_text', '').strip(),
            })
            DataManager.save_page_content(pc)
            SiteConfig.set('section_courses_visible', 'true' if request.form.get('section_courses_visible') else 'false')
            flash('Courses section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#courses')

        elif action == 'newsletter':
            pc.update({
                'newsletter_section_title':    request.form.get('newsletter_section_title', '').strip(),
                'newsletter_section_subtitle': request.form.get('newsletter_section_subtitle', '').strip(),
                'newsletter_button_text':      request.form.get('newsletter_button_text', '').strip(),
                'newsletter_privacy_text':     request.form.get('newsletter_privacy_text', '').strip(),
            })
            DataManager.save_page_content(pc)
            SiteConfig.set('section_newsletter_visible', 'true' if request.form.get('section_newsletter_visible') else 'false')
            flash('Newsletter section saved!', 'success')
            return redirect(url_for('admin_content_manager') + '#newsletter')

        flash('Unknown action.', 'error')
        return redirect(url_for('admin_content_manager'))

    # GET — load all data
    pc = DataManager.get_page_content()

    stats_record = SiteContent.query.filter_by(content_key='statistics_data').first()
    stats_data   = json.loads(stats_record.content_data) if stats_record else {
        'title': 'By the Numbers', 'subtitle': 'The reach keeps growing — thanks to you.', 'stats': []
    }
    if 'stats' not in stats_data:
        stats_data['stats'] = []

    try:
        live_subscriber_count = Subscriber.query.count()
    except Exception:
        live_subscriber_count = 0
    try:
        live_reel_count = Reel.query.filter_by(is_visible=True).count()
    except Exception:
        live_reel_count = 0

    visibility = {
        s: SiteConfig.get(f'section_{s}_visible', 'true').lower() != 'false'
        for s in ['reels', 'support', 'statistics', 'testimonials', 'courses', 'newsletter']
    }
    subscription_tiers = SubscriptionTier.query.order_by(SubscriptionTier.sort_order).all()

    return render_template('admin/content_manager.html',
                           pc=pc,
                           stats_data=stats_data,
                           visibility=visibility,
                           subscription_tiers=subscription_tiers,
                           live_subscriber_count=live_subscriber_count,
                           live_reel_count=live_reel_count)


@app.route('/admin/column-visibility', methods=['GET', 'POST'])
def admin_column_visibility():
    """Column Visibility Settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from models import ColumnVisibility
    from utils import get_table_columns, get_all_database_tables, get_readable_table_name
    
    if request.method == 'POST':
        table_name = request.form.get('table_name')
        hidden_columns = request.form.getlist('hidden_columns')
        
        if table_name:
            ColumnVisibility.set_hidden_columns(table_name, hidden_columns)
            readable_name = get_readable_table_name(table_name)
            flash(f'Column visibility settings updated for {readable_name}!', 'success')
            return redirect(url_for('admin_column_visibility'))
    
    # Get all database tables dynamically
    all_tables = get_all_database_tables()
    
    # Build tables dictionary with readable names
    tables = {}
    for table_name in all_tables:
        tables[table_name] = get_readable_table_name(table_name)
    
    # Get current visibility settings for all tables
    table_settings = {}
    for table_key, table_label in tables.items():
        all_columns = get_table_columns(table_key)
        hidden_columns = ColumnVisibility.get_hidden_columns(table_key)
        table_settings[table_key] = {
            'label': table_label,
            'all_columns': all_columns,
            'hidden_columns': hidden_columns
        }
    
    return render_template('admin/column_visibility.html', 
                         tables=tables,
                         table_settings=table_settings)

@app.route('/admin/email-broadcast', methods=['GET', 'POST'])
def admin_email_broadcast():
    """Email Broadcast to Subscribers"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        subscribers = Subscriber.query.all()
        subscriber_emails = [s.email for s in subscribers]
        
        # Note: This would require email service integration (SendGrid, etc.)
        # For now, we'll just show the preview
        flash(f'Email preview ready! Would send to {len(subscriber_emails)} subscribers. (Email service integration required)', 'info')
        
        return render_template('admin/email_broadcast.html',
                             subject=subject,
                             message=message,
                             subscriber_count=len(subscriber_emails),
                             preview_mode=True)
    
    subscriber_count = Subscriber.query.count()
    return render_template('admin/email_broadcast.html', subscriber_count=subscriber_count)

@app.route('/admin/activity-logs')
def admin_activity_logs():
    """Activity Logs - Track admin actions"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # Get recent database changes
    recent_reels = Reel.query.order_by(Reel.created_at.desc()).limit(10).all()
    recent_opinions = Opinion.query.order_by(Opinion.created_at.desc()).limit(10).all()
    recent_subscribers = Subscriber.query.order_by(Subscriber.subscribed_at.desc()).limit(10).all()
    recent_courses = Course.query.order_by(Course.created_at.desc()).limit(10).all()
    
    activities = []
    
    for reel in recent_reels:
        activities.append({
            'type': 'reel',
            'action': 'created',
            'title': reel.title,
            'timestamp': reel.created_at,
            'icon': 'fa-video',
            'color': 'primary'
        })
    
    for opinion in recent_opinions:
        activities.append({
            'type': 'opinion',
            'action': 'created',
            'title': opinion.title,
            'timestamp': opinion.created_at,
            'icon': 'fa-poll',
            'color': 'success'
        })
    
    for subscriber in recent_subscribers:
        activities.append({
            'type': 'subscriber',
            'action': 'joined',
            'title': subscriber.name,
            'timestamp': subscriber.subscribed_at,
            'icon': 'fa-user-plus',
            'color': 'info'
        })
    
    for course in recent_courses:
        activities.append({
            'type': 'course',
            'action': 'created',
            'title': course.title,
            'timestamp': course.created_at,
            'icon': 'fa-book',
            'color': 'warning'
        })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('admin/activity_logs.html', activities=activities[:50])

@app.route('/admin/error-logs')
def admin_error_logs():
    """Admin error log viewer"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin/error_logs.html', errors=list(_error_log))

@app.route('/admin/error-logs/clear', methods=['POST'])
def admin_error_logs_clear():
    """Clear admin error log"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    _error_log.clear()
    flash('Error log cleared.', 'success')
    return redirect(url_for('admin_error_logs'))

@app.route('/admin/database-export')
def admin_database_export():
    """Database Export Tools"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    return render_template('admin/database_export.html')

@app.route('/admin/export-data/<data_type>')
def admin_export_data(data_type):
    """Export data as JSON"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from flask import Response
    
    data = {}
    filename = f'{data_type}_export.json'
    
    if data_type == 'reels':
        data = {'reels': [r.to_dict() for r in Reel.query.all()]}
    elif data_type == 'opinions':
        data = {'opinions': [o.to_dict() for o in Opinion.query.all()]}
    elif data_type == 'subscribers':
        data = {'subscribers': [s.to_dict() for s in Subscriber.query.all()]}
    elif data_type == 'courses':
        courses = Course.query.all()
        data = {'courses': [c.to_dict() for c in courses]}
    elif data_type == 'all':
        data = {
            'reels': [r.to_dict() for r in Reel.query.all()],
            'opinions': [o.to_dict() for o in Opinion.query.all()],
            'subscribers': [s.to_dict() for s in Subscriber.query.all()],
            'courses': [c.to_dict() for c in Course.query.all()],
            'subscription_tiers': [t.to_dict() for t in SubscriptionTier.query.all()]
        }
        filename = 'full_database_export.json'
    
    return Response(
        json.dumps(data, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

@app.route('/admin/media-library')
def admin_media_library():
    """Media Library - View all uploaded files"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    import os
    
    media_files = []
    upload_folder = app.config['UPLOAD_FOLDER']
    
    # Scan upload directories
    for root, dirs, files in os.walk(upload_folder):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, 'static')
                file_size = os.path.getsize(file_path)
                
                media_files.append({
                    'name': file,
                    'path': relative_path,
                    'url': url_for('static', filename=relative_path),
                    'size': round(file_size / 1024, 2),  # KB
                    'type': 'image' if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) else 'video'
                })
    
    # Sort by name
    media_files.sort(key=lambda x: x['name'])
    
    return render_template('admin/media_library.html', media_files=media_files)

@app.route('/admin/user-data-usage')
def admin_user_data_usage():
    """View user data usage statistics"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # Get time range from request
    days = request.args.get('days', 30, type=int)
    
    # Get top users by activity
    top_users = UserActivity.get_top_users(limit=50, days=days)
    
    # Get activity breakdown by type
    activity_breakdown = UserActivity.get_activity_by_type(days=days)
    
    # Get overall stats
    from datetime import timedelta
    from sqlalchemy import func
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    total_activities = UserActivity.query.filter(UserActivity.created_at >= cutoff_date).count()
    total_unique_users = db.session.query(func.count(func.distinct(UserActivity.user_id))).filter(
        UserActivity.created_at >= cutoff_date,
        UserActivity.user_id.isnot(None)
    ).scalar() or 0
    total_data_usage = db.session.query(func.sum(UserActivity.data_size)).filter(
        UserActivity.created_at >= cutoff_date
    ).scalar() or 0
    total_time = db.session.query(func.sum(UserActivity.duration)).filter(
        UserActivity.created_at >= cutoff_date
    ).scalar() or 0
    
    # Format data size
    def format_bytes(bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"
    
    # Format time
    def format_time(seconds):
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    stats = {
        'total_activities': total_activities,
        'total_unique_users': total_unique_users,
        'total_data_usage': format_bytes(total_data_usage),
        'total_time': format_time(total_time),
        'days': days
    }
    
    # Add formatted data to top users
    for user in top_users:
        user['total_data_formatted'] = format_bytes(user['total_data'])
        user['total_time_formatted'] = format_time(user['total_time'])
    
    return render_template('admin/user_data_usage.html', 
                         top_users=top_users,
                         activity_breakdown=activity_breakdown,
                         stats=stats)

@app.route('/admin/user-activity/<user_id>')
def admin_user_activity_detail(user_id):
    """View detailed activity for a specific user"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # Get time range from request
    days = request.args.get('days', 30, type=int)
    
    # Get user stats
    user_stats = UserActivity.get_user_stats(user_id=user_id, days=days)
    
    # Get recent activities
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    recent_activities = UserActivity.query.filter(
        UserActivity.user_id == user_id,
        UserActivity.created_at >= cutoff_date
    ).order_by(UserActivity.created_at.desc()).limit(100).all()
    
    activities = [activity.to_dict() for activity in recent_activities]
    
    # Get user info from first activity
    user_email = recent_activities[0].user_email if recent_activities else 'N/A'
    
    # Format data size
    def format_bytes(bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"
    
    user_stats['total_data_formatted'] = format_bytes(user_stats['total_data_usage'])
    
    return render_template('admin/user_activity_detail.html',
                         user_id=user_id,
                         user_email=user_email,
                         user_stats=user_stats,
                         activities=activities,
                         days=days)

# Static pages routes
@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Terms of Service page"""
    return render_template('terms_of_service.html')

@app.route('/disclaimer')
def disclaimer():
    """Disclaimer page"""
    return render_template('disclaimer.html')

@app.route('/cookies-policy')
def cookies_policy():
    """Cookies Policy page"""
    return render_template('cookies_policy.html')

@app.route('/refund-policy')
def refund_policy():
    """Refund and Cancellation Policy page"""
    return render_template('refund_policy.html')

@app.route('/return-policy')
def return_policy():
    """Return Policy page"""
    return render_template('return_policy.html')

@app.route('/shipping-policy')
def shipping_policy():
    """Shipping Policy page"""
    return render_template('shipping_policy.html')

# Clerk authentication routes
@app.route('/login')
def clerk_login():
    """Clerk login page"""
    from urllib.parse import urljoin
    
    # Get next URL from query parameter or session
    next_url = request.args.get('next') or session.pop('next_url', None)
    if not next_url:
        next_url = url_for('index', _external=True)
    elif not next_url.startswith('http'):
        # If it's a relative URL, convert to absolute using current host
        next_url = urljoin(request.host_url, next_url)
    return render_template('clerk_login.html', next_url=next_url)

@app.route('/signup')
def clerk_signup():
    """Clerk signup page"""
    after_signup_url = url_for('index', _external=True)
    return render_template('clerk_signup.html', after_signup_url=after_signup_url)

@app.route('/clerk/callback')
def clerk_callback():
    """Callback route after Clerk authentication"""
    next_url = session.pop('next_url', url_for('index'))
    return redirect(next_url)


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """Course user login — by email or mobile number"""
    if get_course_user():
        return redirect(url_for('my_courses'))

    error = None
    next_url = request.args.get('next', '')

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            error = 'Please enter your login ID and password.'
        else:
            user = CourseUser.get_by_identifier(identifier)
            if user and user.check_password(password):
                session['course_user_id'] = user.id
                first = user.name.split()[0]
                flash(f'Welcome back, {first}!', 'success')
                if user.must_change_password:
                    flash('Please change your auto-generated password for security.', 'warning')
                    return redirect(url_for('change_password'))
                return redirect(next_url or url_for('my_courses'))
            else:
                error = 'Invalid login ID or password. Please try again.'

    return render_template('user_login.html', error=error, next_url=next_url)


@app.route('/user/logout')
def user_logout():
    """Course user logout"""
    session.pop('course_user_id', None)
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


@app.route('/user/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password for course user"""
    course_user = get_course_user()
    if not course_user:
        flash('Please sign in first.', 'warning')
        return redirect(url_for('user_login'))

    error = None

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([current_password, new_password, confirm_password]):
            error = 'All fields are required.'
        elif not course_user.check_password(current_password):
            error = 'Current password is incorrect.'
        elif len(new_password) < 6:
            error = 'New password must be at least 6 characters.'
        elif new_password != confirm_password:
            error = 'New passwords do not match.'
        else:
            course_user.set_password(new_password)
            course_user.must_change_password = False
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('my_courses'))

    return render_template('change_password.html', error=error, course_user=course_user)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/archives')
def archives():
    """Archives page with all poll groups and search"""
    search_query = request.args.get('search', '').strip()
    
    # Get all unique topic tags from opinions (polls)
    topics_query = db.session.query(
        Opinion.topic_tag,
        db.func.count(Opinion.id).label('count'),
        db.func.max(Opinion.created_at).label('latest_date')
    ).filter(
        Opinion.topic_tag.isnot(None),
        Opinion.topic_tag != ''
    ).group_by(Opinion.topic_tag)
    
    # Apply search filter if provided
    if search_query:
        topics_query = topics_query.filter(Opinion.topic_tag.ilike(f'%{search_query}%'))
    
    topics = topics_query.order_by(db.desc('latest_date')).all()
    
    # Format archives data
    archives_list = []
    for topic, count, latest_date in topics:
        # Create SEO-friendly slug using proper slugify function
        slug = slugify(topic)
        year = latest_date.year if latest_date else ''
        
        archives_list.append({
            'title': topic,
            'slug': slug,
            'year': year,
            'count': count,
            'latest_date': latest_date
        })
    
    return render_template('archives.html', archives=archives_list, search_query=search_query)

@app.route('/archives/<slug>')
def archive_detail(slug):
    """Individual archive group page with SEO-friendly URL"""
    # Get all topics and match by slug
    all_topics = db.session.query(Opinion.topic_tag).filter(
        Opinion.topic_tag.isnot(None),
        Opinion.topic_tag != ''
    ).distinct().all()
    
    # Find the topic that matches this slug
    actual_topic = None
    for (topic,) in all_topics:
        if slugify(topic) == slug:
            actual_topic = topic
            break
    
    if not actual_topic:
        abort(404)
    
    # Get opinions for this exact topic
    opinions = Opinion.query.filter(Opinion.topic_tag == actual_topic).order_by(Opinion.created_at.desc()).all()
    
    if not opinions:
        abort(404)
    
    opinions_data = []
    for opinion in opinions:
        opinion_dict = opinion.to_dict()
        opinion_dict['percentages'] = calculate_poll_percentages(opinion_dict['votes'])
        opinion_dict['total_votes'] = sum(opinion_dict['votes'])
        opinions_data.append(opinion_dict)
    
    return render_template('archive_detail.html', 
                         topic=actual_topic, 
                         slug=slug,
                         opinions=opinions_data)

@app.route('/poll-groups')
def poll_groups():
    """Poll Groups/Playlists Library Page"""
    # Get all topics with polls grouped
    topics_query = db.session.query(
        Opinion.topic_tag,
        db.func.count(Opinion.id).label('poll_count'),
        db.func.sum(db.func.length(Opinion.votes)).label('total_engagement'),
        db.func.max(Opinion.created_at).label('latest_poll_date')
    ).filter(
        Opinion.topic_tag != None,
        Opinion.topic_tag != ''
    ).group_by(Opinion.topic_tag).all()
    
    # Format groups data
    groups = []
    for topic in topics_query:
        # Get latest poll from this group
        latest_poll = Opinion.query.filter_by(topic_tag=topic.topic_tag).order_by(Opinion.created_at.desc()).first()
        
        # Calculate total votes for this group
        group_polls = Opinion.query.filter_by(topic_tag=topic.topic_tag).all()
        total_votes = sum([sum(json.loads(poll.votes) if poll.votes else []) for poll in group_polls])
        
        groups.append({
            'topic': topic.topic_tag,
            'poll_count': topic.poll_count,
            'total_votes': total_votes,
            'latest_poll_date': topic.latest_poll_date.strftime("%B %d, %Y") if topic.latest_poll_date else '',
            'latest_poll_title': latest_poll.title if latest_poll else ''
        })
    
    # Sort by latest activity
    groups.sort(key=lambda x: x['latest_poll_date'], reverse=True)
    
    return render_template('poll_groups.html', groups=groups)

@app.route('/poll-group/<string:topic>')
def poll_group_detail(topic):
    """Poll Group Detail Page - Timeline of polls in a topic"""
    # Get all polls in this topic
    polls = Opinion.query.filter_by(topic_tag=topic).order_by(Opinion.created_at.desc()).all()
    
    if not polls:
        abort(404)
    
    # Format polls for display
    formatted_polls = []
    total_group_votes = 0
    
    for poll in polls:
        poll_dict = poll.to_dict()
        poll_dict['formatted_date'] = poll.created_at.strftime("%B %d, %Y")
        poll_votes = sum(json.loads(poll.votes) if poll.votes else [])
        poll_dict['total_votes'] = poll_votes
        total_group_votes += poll_votes
        poll_dict['percentages'] = calculate_poll_percentages(json.loads(poll.votes) if poll.votes else [])
        formatted_polls.append(poll_dict)
    
    # Group analytics
    analytics = {
        'total_polls': len(polls),
        'total_votes': total_group_votes,
        'avg_votes_per_poll': total_group_votes // len(polls) if len(polls) > 0 else 0,
        'date_range': f"{polls[-1].created_at.strftime('%B %Y')} - {polls[0].created_at.strftime('%B %Y')}" if len(polls) > 1 else polls[0].created_at.strftime('%B %Y')
    }
    
    return render_template('poll_group_detail.html', 
                         topic=topic, 
                         polls=formatted_polls, 
                         analytics=analytics)

@app.route('/courses')
def courses():
    """Courses listing page"""
    all_courses = Course.query.filter_by(is_active=True).order_by(Course.sort_order, Course.id).all()
    
    clerk_user_id = get_clerk_user_id()
    user_course_ids = []
    if clerk_user_id:
        user_accesses = UserCourseAccess.get_user_courses(clerk_user_id)
        user_course_ids = [access.course_id for access in user_accesses]
    
    courses_data = []
    for course in all_courses:
        course_dict = course.to_dict()
        course_dict['has_access'] = course.id in user_course_ids
        course_dict['module_count'] = len(course.modules)
        course_dict['lesson_count'] = sum([len(module.lessons) for module in course.modules])
        courses_data.append(course_dict)
    
    razorpay_key = os.environ.get('RAZORPAY_KEY_ID', '')
    if not razorpay_key:
        payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
        if payment_content:
            payment_settings = json.loads(payment_content.content_data)
            db_key = payment_settings.get('razorpay_key_id', '')
            if db_key:
                razorpay_key = db_key
    
    return render_template('courses.html', courses=courses_data, razorpay_key=razorpay_key)

@app.route('/my-courses')
def my_courses():
    """My Courses page - shows courses the user has purchased"""
    clerk_user_id = get_clerk_user_id()
    course_user = get_course_user()

    if not clerk_user_id and not course_user:
        flash('Please sign in to view your courses.', 'warning')
        return redirect(url_for('user_login', next=request.url))

    my_courses_data = []
    seen_course_ids = set()

    if clerk_user_id:
        for access in UserCourseAccess.get_user_courses(clerk_user_id):
            course = Course.query.get(access.course_id)
            if course and course.is_active and course.id not in seen_course_ids:
                course_dict = course.to_dict()
                course_dict['has_access'] = True
                course_dict['module_count'] = len(course.modules)
                course_dict['lesson_count'] = sum([len(m.lessons) for m in course.modules])
                course_dict['purchased_at'] = access.granted_at.strftime('%B %d, %Y') if access.granted_at else ''
                my_courses_data.append(course_dict)
                seen_course_ids.add(course.id)

    if course_user:
        for access in course_user.get_course_accesses():
            if access.course_id not in seen_course_ids:
                course = Course.query.get(access.course_id)
                if course and course.is_active:
                    course_dict = course.to_dict()
                    course_dict['has_access'] = True
                    course_dict['module_count'] = len(course.modules)
                    course_dict['lesson_count'] = sum([len(m.lessons) for m in course.modules])
                    course_dict['purchased_at'] = access.granted_at.strftime('%B %d, %Y') if access.granted_at else ''
                    my_courses_data.append(course_dict)
                    seen_course_ids.add(access.course_id)

    return render_template('my_courses.html', courses=my_courses_data)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Course detail page with modules and lessons"""
    course = Course.query.get_or_404(course_id)
    
    if not course.is_active:
        abort(404)
    
    clerk_user_id = get_clerk_user_id()
    
    # Free courses (price = 0) are accessible to everyone without login
    if course.price == 0:
        has_access = True
    else:
        has_access = False
        if clerk_user_id:
            has_access = UserCourseAccess.has_access(clerk_user_id, course_id)
        if not has_access:
            _cu = get_course_user()
            if _cu:
                has_access = _cu.has_course_access(course_id)

    course_data = course.to_dict()
    course_data['has_access'] = has_access

    razorpay_key = os.environ.get('RAZORPAY_KEY_ID', '')
    if not razorpay_key:
        payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
        if payment_content:
            payment_settings = json.loads(payment_content.content_data)
            db_key = payment_settings.get('razorpay_key_id', '')
            if db_key:
                razorpay_key = db_key
    
    curriculum_settings = _get_curriculum_settings()
    
    return render_template('course_detail.html', course=course_data, razorpay_key=razorpay_key, curriculum_settings=curriculum_settings)

@app.route('/course/<int:course_id>/lesson/<int:lesson_id>')
def lesson_view(course_id, lesson_id):
    """Lesson viewing page with embedded video"""
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if not course.is_active:
        abort(404)
    
    clerk_user_id = get_clerk_user_id()

    # Free courses (price = 0) are accessible to everyone without login
    if course.price == 0:
        has_access = True
    else:
        has_access = False
        if clerk_user_id:
            has_access = UserCourseAccess.has_access(clerk_user_id, course_id)
        if not has_access:
            _cu = get_course_user()
            if _cu:
                has_access = _cu.has_course_access(course_id)

        if not has_access:
            if not clerk_user_id and not get_course_user():
                flash('Please sign in to access this course.', 'warning')
                return redirect(url_for('user_login', next=request.url))
            flash('You need to purchase this course to access lessons.', 'warning')
            return redirect(url_for('course_detail', course_id=course_id))
    
    lesson_data = lesson.to_dict()
    # Removed YouTube embed URL conversion - now using custom video player with direct video files
    # lesson_data['embed_url'] = get_youtube_embed_url(lesson.video_url) if lesson.video_url else None
    
    module = Module.query.get(lesson.module_id)
    course_data = course.to_dict()
    
    current_lesson_index = None
    prev_lesson = None
    next_lesson = None
    
    all_lessons = []
    for mod in course.modules:
        for les in mod.lessons:
            all_lessons.append(les)
    
    for idx, les in enumerate(all_lessons):
        if les.id == lesson_id:
            current_lesson_index = idx
            if idx > 0:
                prev_lesson = all_lessons[idx - 1]
            if idx < len(all_lessons) - 1:
                next_lesson = all_lessons[idx + 1]
            break
    
    return render_template('lesson_view.html', 
                         course=course_data,
                         module=module.to_dict(),
                         lesson=lesson_data,
                         prev_lesson=prev_lesson.to_dict() if prev_lesson else None,
                         next_lesson=next_lesson.to_dict() if next_lesson else None)

@app.route('/course/<int:course_id>/purchase', methods=['POST'])
def purchase_course(course_id):
    """Initiate course purchase — no login required"""
    course = Course.query.get_or_404(course_id)
    
    data = request.get_json() or {}
    guest_name = data.get('name', '').strip()
    guest_email = data.get('email', '').strip()
    guest_phone = data.get('phone', '').strip()
    
    clerk_user_id = get_clerk_user_id()
    
    # Check if already has access (by Clerk ID or by email)
    if clerk_user_id and UserCourseAccess.has_access(clerk_user_id, course_id):
        return jsonify({'success': False, 'message': 'You already have access to this course'}), 400
    if guest_email and UserCourseAccess.has_access_by_email(guest_email, course_id):
        return jsonify({'success': False, 'message': 'This email already has access to this course'}), 400
    
    try:
        amount = course.price * 100
        order = razorpay_client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'course_id': str(course_id),
                'buyer_name': guest_name,
                'buyer_email': guest_email,
                'buyer_phone': guest_phone
            }
        })
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': amount,
            'course_id': course_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/course/payment/verify', methods=['POST'])
def verify_course_payment():
    """Verify course payment and grant access — no login required"""
    data = request.get_json()
    
    payment_id = data.get('razorpay_payment_id')
    order_id = data.get('razorpay_order_id')
    signature = data.get('razorpay_signature')
    course_id = data.get('course_id')
    guest_name = data.get('name', '').strip()
    guest_email = data.get('email', '').strip()
    guest_phone = data.get('phone', '').strip()
    
    clerk_user_id = get_clerk_user_id()
    
    try:
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'success': False, 'message': 'Course not found'}), 404
        
        access = UserCourseAccess(
            clerk_user_id=clerk_user_id,
            course_id=course_id,
            payment_id=payment_id,
            amount_paid=course.price,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone
        )
        db.session.add(access)
        db.session.commit()

        # Auto-create CourseUser account if not already exists
        try:
            if guest_email or guest_phone:
                existing_user = None
                if guest_email:
                    existing_user = CourseUser.get_by_identifier(guest_email)
                if not existing_user and guest_phone:
                    existing_user = CourseUser.get_by_identifier(guest_phone)

                if not existing_user:
                    auto_password = CourseUser.generate_password(guest_name, guest_phone)
                    new_user = CourseUser(
                        name=guest_name or 'User',
                        email=guest_email or None,
                        phone=guest_phone or None,
                        must_change_password=True
                    )
                    new_user.set_password(auto_password)
                    db.session.add(new_user)
                    db.session.commit()

                    import logging as _log
                    _log.info(f"CourseUser created for {guest_email or guest_phone}")

                    # Send WhatsApp + Email credentials
                    from utils import send_whatsapp_credentials, send_email_credentials
                    login_id = guest_email or guest_phone
                    _login_url = url_for('user_login', _external=True)
                    send_whatsapp_credentials(
                        phone=guest_phone,
                        name=guest_name or 'User',
                        login_id=login_id,
                        password=auto_password,
                        login_url=_login_url
                    )
                    if guest_email:
                        send_email_credentials(
                            email=guest_email,
                            name=guest_name or 'User',
                            login_id=login_id,
                            password=auto_password,
                            login_url=_login_url
                        )
        except Exception as _e:
            import logging as _log
            _log.error(f"CourseUser creation error after payment: {_e}")

        return jsonify({
            'success': True,
            'message': 'Payment successful! Your account credentials have been sent to your WhatsApp.',
            'redirect_url': url_for('course_detail', course_id=course_id)
        })
    
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/payment/success')
def payment_success():
    """Dedicated payment success page"""
    return render_template('payment_success.html',
        payment_type=request.args.get('type', ''),
        message=request.args.get('message', ''),
        course_title=request.args.get('course_title', ''),
        redirect_url=request.args.get('redirect', ''),
        email=request.args.get('email', ''),
        is_logged_in=bool(get_clerk_user_id() or get_course_user())
    )

@app.route('/payment/failed')
def payment_failed():
    """Dedicated payment failed page"""
    return render_template('payment_failed.html',
        message=request.args.get('message', '')
    )

@app.route('/admin/whatsapp-settings', methods=['GET', 'POST'])
def admin_whatsapp_settings():
    """Manage WhatsApp + Email credential delivery settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    import json

    wa_content = SiteContent.query.filter_by(content_key='whatsapp_settings').first()
    current_wa = json.loads(wa_content.content_data) if wa_content else {
        'enabled': False, 'phone_number_id': '', 'access_token': '', 'support_phone': ''
    }

    email_content = SiteContent.query.filter_by(content_key='email_settings').first()
    current_email = json.loads(email_content.content_data) if email_content else {
        'enabled': False, 'smtp_host': '', 'smtp_port': '587',
        'smtp_user': '', 'smtp_password': '', 'from_name': 'Kshitiz Jaiswal Courses', 'from_email': ''
    }

    if request.method == 'POST':
        action = request.form.get('action', 'whatsapp')

        if action == 'whatsapp':
            new_token = request.form.get('access_token', '').strip()
            updated_wa = {
                'enabled': request.form.get('enabled') == 'on',
                'phone_number_id': request.form.get('phone_number_id', '').strip(),
                'access_token': new_token if new_token else current_wa.get('access_token', ''),
                'support_phone': request.form.get('support_phone', '').strip(),
            }
            if wa_content:
                wa_content.content_data = json.dumps(updated_wa)
            else:
                wa_content = SiteContent(content_key='whatsapp_settings', content_data=json.dumps(updated_wa))
                db.session.add(wa_content)
            db.session.commit()
            flash('WhatsApp settings updated!', 'success')
            current_wa = updated_wa

        elif action == 'email':
            new_smtp_pwd = request.form.get('smtp_password', '').strip()
            updated_email = {
                'enabled': request.form.get('email_enabled') == 'on',
                'smtp_host': request.form.get('smtp_host', '').strip(),
                'smtp_port': request.form.get('smtp_port', '587').strip(),
                'smtp_user': request.form.get('smtp_user', '').strip(),
                'smtp_password': new_smtp_pwd if new_smtp_pwd else current_email.get('smtp_password', ''),
                'from_name': request.form.get('from_name', 'Kshitiz Jaiswal Courses').strip(),
                'from_email': request.form.get('from_email', '').strip(),
            }
            if email_content:
                email_content.content_data = json.dumps(updated_email)
            else:
                email_content = SiteContent(content_key='email_settings', content_data=json.dumps(updated_email))
                db.session.add(email_content)
            db.session.commit()
            flash('Email settings updated!', 'success')
            current_email = updated_email

    course_user_count = CourseUser.query.count()
    return render_template('admin/whatsapp_settings.html',
                           settings=current_wa,
                           email_settings=current_email,
                           course_user_count=course_user_count)


@app.route('/support/payment/verify', methods=['POST'])
def verify_support_payment():
    """Verify Razorpay signature for support/donation payments"""
    try:
        data = request.get_json() or {}
        payment_id = data.get('razorpay_payment_id', '')
        order_id = data.get('razorpay_order_id', '')
        signature = data.get('razorpay_signature', '')

        if not all([payment_id, order_id, signature]):
            return jsonify({'success': False, 'message': 'Missing payment details'}), 400

        client = get_razorpay_client()

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        client.utility.verify_payment_signature(params_dict)

        UserActivity.log_activity(
            activity_type='support_payment',
            resource_type='support',
            resource_id=None,
            request_obj=request
        )

        return jsonify({'success': True, 'message': 'Thank you for your support!'})

    except razorpay.errors.SignatureVerificationError:
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AUTOPAY — Razorpay Subscriptions
# ─────────────────────────────────────────────────────────────────────────────

_PERIOD_MAP = {'week': 'weekly', 'month': 'monthly', 'year': 'yearly'}
_TOTAL_COUNT_MAP = {'week': 260, 'month': 120, 'year': 10}  # ~5yr / 10yr / 10yr


@app.route('/create_subscription', methods=['POST'])
def create_subscription():
    """Create a Razorpay recurring subscription (AutoPay) for a support tier."""
    try:
        data = request.get_json() or {}
        tier_id = data.get('tier_id')
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        phone = (data.get('phone') or '').strip()

        tier = SubscriptionTier.query.get(tier_id)
        if not tier or not tier.is_active:
            return jsonify({'status': 'error', 'message': 'Invalid or inactive subscription tier'}), 400

        client = get_razorpay_client()
        rz_period = _PERIOD_MAP.get(tier.period, 'monthly')
        total_count = _TOTAL_COUNT_MAP.get(tier.period, 120)
        amount_paise = tier.price * 100

        # Create (or reuse) a Razorpay Plan for this tier
        if not tier.razorpay_plan_id:
            plan_payload = {
                'period': rz_period,
                'interval': 1,
                'item': {
                    'name': f'{tier.name} – {tier.period.capitalize()} AutoPay',
                    'amount': amount_paise,
                    'currency': 'INR',
                    'description': (tier.description or tier.name)[:255],
                },
                'notes': {'tier_id': str(tier.id)},
            }
            plan = client.plan.create(data=plan_payload)
            tier.razorpay_plan_id = plan['id']
            db.session.commit()
            logging.info(f"Created Razorpay plan {plan['id']} for tier {tier.id}")

        # Build subscription
        sub_payload = {
            'plan_id': tier.razorpay_plan_id,
            'total_count': total_count,
            'quantity': 1,
            'customer_notify': 1,
            'notes': {
                'tier_name': tier.name,
                'subscriber_name': name,
                'subscriber_email': email,
                'subscriber_phone': phone,
            },
        }
        subscription = client.subscription.create(data=sub_payload)

        # Persist a pending record so webhooks can update it later
        record = UserSubscription(
            name=name or None,
            email=email or None,
            phone=phone or None,
            tier_id=tier.id,
            tier_name=tier.name,
            razorpay_subscription_id=subscription['id'],
            status='created',
            amount_paise=amount_paise,
            total_count=total_count,
            paid_count=0,
        )
        db.session.add(record)
        db.session.commit()
        logging.info(f"Created UserSubscription {record.id} → Razorpay {subscription['id']}")

        return jsonify({
            'status': 'success',
            'subscription_id': subscription['id'],
            'tier_name': tier.name,
            'amount': amount_paise,
            'period': tier.period,
        })

    except Exception as e:
        logging.error(f"create_subscription error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/subscription/verify', methods=['POST'])
def verify_subscription_payment():
    """Verify Razorpay signature after the user completes AutoPay mandate setup."""
    try:
        data = request.get_json() or {}
        payment_id = data.get('razorpay_payment_id', '')
        subscription_id = data.get('razorpay_subscription_id', '')
        signature = data.get('razorpay_signature', '')

        if not all([payment_id, subscription_id, signature]):
            return jsonify({'success': False, 'message': 'Missing payment details'}), 400

        client = get_razorpay_client()

        # Verify HMAC signature (subscription flow uses payment_id + subscription_id)
        params = {
            'razorpay_payment_id': payment_id,
            'razorpay_subscription_id': subscription_id,
            'razorpay_signature': signature,
        }
        client.utility.verify_payment_signature(params)

        # Update our record
        sub = UserSubscription.query.filter_by(
            razorpay_subscription_id=subscription_id
        ).first()
        if sub:
            sub.razorpay_payment_id = payment_id
            sub.status = 'authenticated'
            sub.paid_count = max(sub.paid_count or 0, 1)
            sub.updated_at = datetime.utcnow()
            db.session.commit()
            logging.info(f"Subscription {subscription_id} authenticated (payment {payment_id})")

        UserActivity.log_activity(
            activity_type='autopay_subscription',
            resource_type='subscription',
            resource_id=None,
            request_obj=request
        )

        return jsonify({'success': True, 'message': 'AutoPay activated! Thank you for your recurring support.'})

    except razorpay.errors.SignatureVerificationError:
        logging.warning(f"Subscription verify: signature mismatch for {subscription_id}")
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400
    except Exception as e:
        logging.error(f"verify_subscription error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/razorpay/webhook', methods=['POST'])
def razorpay_webhook():
    """
    Handle Razorpay webhook events for subscriptions and payments.
    Set RAZORPAY_WEBHOOK_SECRET in Replit Secrets to enable signature verification.
    """
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get('X-Razorpay-Signature', '')

    # Verify signature if secret is configured
    if webhook_secret:
        if not signature:
            logging.warning("Razorpay webhook: missing signature header")
            return jsonify({'error': 'Missing signature'}), 400
        expected = hmac.new(
            webhook_secret.encode('utf-8'),
            raw_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logging.warning("Razorpay webhook: signature mismatch — rejected")
            return jsonify({'error': 'Invalid signature'}), 400

    try:
        payload = json.loads(raw_body)
        event = payload.get('event', '')
        logging.info(f"Razorpay webhook received: {event}")

        event_payload = payload.get('payload', {})

        if event == 'subscription.charged':
            # Recurring charge succeeded
            sub_entity = event_payload.get('subscription', {}).get('entity', {})
            pay_entity = event_payload.get('payment', {}).get('entity', {})
            sub_id = sub_entity.get('id', '')
            payment_id = pay_entity.get('id', '')
            paid_count = sub_entity.get('paid_count', 0)

            sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
            if sub:
                sub.razorpay_payment_id = payment_id
                sub.status = 'active'
                sub.paid_count = paid_count or (sub.paid_count or 0) + 1
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logging.info(f"Subscription {sub_id}: charged (payment {payment_id}, count={sub.paid_count})")

        elif event == 'subscription.activated':
            sub_entity = event_payload.get('subscription', {}).get('entity', {})
            sub_id = sub_entity.get('id', '')
            sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
            if sub:
                sub.status = 'active'
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logging.info(f"Subscription {sub_id}: activated")

        elif event == 'subscription.halted':
            sub_entity = event_payload.get('subscription', {}).get('entity', {})
            sub_id = sub_entity.get('id', '')
            sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
            if sub:
                sub.status = 'halted'
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logging.warning(f"Subscription {sub_id}: halted (payment failure)")

        elif event == 'subscription.cancelled':
            sub_entity = event_payload.get('subscription', {}).get('entity', {})
            sub_id = sub_entity.get('id', '')
            sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
            if sub:
                sub.status = 'cancelled'
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logging.info(f"Subscription {sub_id}: cancelled")

        elif event in ('subscription.completed', 'subscription.expired'):
            sub_entity = event_payload.get('subscription', {}).get('entity', {})
            sub_id = sub_entity.get('id', '')
            terminal_status = 'completed' if event == 'subscription.completed' else 'expired'
            sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
            if sub:
                sub.status = terminal_status
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logging.info(f"Subscription {sub_id}: {terminal_status}")

        elif event == 'payment.failed':
            # Log failed payments for subscriptions
            pay_entity = event_payload.get('payment', {}).get('entity', {})
            sub_id = pay_entity.get('subscription_id', '')
            if sub_id:
                sub = UserSubscription.query.filter_by(razorpay_subscription_id=sub_id).first()
                if sub and sub.status == 'active':
                    sub.status = 'pending'
                    sub.updated_at = datetime.utcnow()
                    db.session.commit()
                logging.warning(f"Payment failed for subscription {sub_id}")

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        logging.error(f"Webhook processing error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/admin/subscriptions')
def admin_subscriptions():
    """View and manage AutoPay subscriptions."""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    status_filter = request.args.get('status', '')
    q = UserSubscription.query.order_by(UserSubscription.created_at.desc())
    if status_filter:
        q = q.filter(UserSubscription.status == status_filter)

    subscriptions = q.all()

    # Summary counts
    counts = {}
    for s in ['created', 'authenticated', 'active', 'pending', 'halted', 'cancelled', 'completed', 'expired']:
        counts[s] = UserSubscription.query.filter_by(status=s).count()
    counts['total'] = UserSubscription.query.count()
    counts['active_revenue'] = sum(
        (sub.amount_paise or 0) // 100
        for sub in UserSubscription.query.filter_by(status='active').all()
    )

    return render_template(
        'admin/subscriptions.html',
        subscriptions=subscriptions,
        counts=counts,
        status_filter=status_filter,
    )


@app.route('/admin/subscription/<int:sub_id>/cancel', methods=['POST'])
def admin_cancel_subscription(sub_id):
    """Cancel a Razorpay subscription via admin panel."""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    sub = UserSubscription.query.get_or_404(sub_id)

    if sub.status in ('cancelled', 'completed', 'expired'):
        flash(f'Subscription is already {sub.status}.', 'warning')
        return redirect(url_for('admin_subscriptions'))

    try:
        client = get_razorpay_client()
        client.subscription.cancel(sub.razorpay_subscription_id, {'cancel_at_cycle_end': 0})
        sub.status = 'cancelled'
        sub.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Subscription {sub.razorpay_subscription_id} cancelled successfully.', 'success')
        logging.info(f"Admin cancelled subscription {sub.razorpay_subscription_id}")
    except Exception as e:
        logging.error(f"Admin cancel subscription error: {e}")
        flash(f'Failed to cancel: {e}', 'error')

    return redirect(url_for('admin_subscriptions'))


# ═════════════════════════════════════════════════════════════════════════════
# CHATBOT — Public API
# ═════════════════════════════════════════════════════════════════════════════

def _chatbot_match(user_msg):
    """Return (ChatbotFAQ, score) for best active FAQ match, or (None, 0)."""
    import re as _re
    msg = user_msg.lower().strip()
    msg_clean = _re.sub(r'[^\w\s]', ' ', msg)
    words = set(msg_clean.split())
    best_score, best_faq = 0, None
    try:
        faqs = ChatbotFAQ.query.filter_by(is_active=True).order_by(ChatbotFAQ.priority.desc()).all()
    except Exception:
        return None, 0
    for faq in faqs:
        score = 0
        if faq.question_pattern.lower() in msg:
            score += 8
        for kw in faq.kw_list():
            kw = kw.lower().strip()
            if not kw:
                continue
            if kw in msg:
                score += 3
            elif kw in words:
                score += 1
        score += faq.priority * 0.3
        if score > best_score:
            best_score = score
            best_faq = faq
    return best_faq, best_score


def _chatbot_build_response(user_msg):
    """Build a response dict for the chatbot given a user message."""
    msg = user_msg.lower()
    fallback = SiteConfig.get('chatbot_fallback', "I'm not sure about that. You can reach Kshitiz's team on WhatsApp or browse the website!")
    wa_num  = SiteConfig.get('chatbot_whatsapp', '')
    wa_url  = f'https://wa.me/{wa_num}' if wa_num else ''
    def_qr  = ['\U0001f4da View Courses', '\U0001f4b0 Course Pricing', '\U0001f3ac Watch Reels', '\U0001f4e9 Subscribe', '\U0001f4ac Get Support']

    # ── 1. High-confidence FAQ match (score >= 3) ──────────────────────
    faq, score = _chatbot_match(user_msg)
    if faq and score >= 3:
        return {'message': faq.answer, 'quick_replies': faq.qr_list() or def_qr}

    # ── 2. Built-in keyword handlers ───────────────────────────────────

    # Greetings
    if any(g in msg for g in ['hello', 'hi', 'hey', 'namaste', 'namaskar', 'hii', 'helo', 'good morning', 'good evening', 'sup']):
        greeting = SiteConfig.get('chatbot_greeting', '') or "Namaste! \U0001f64f I'm Kshitiz's assistant. Ask me anything about courses, content, or how to support Kshitiz!"
        return {'message': greeting, 'quick_replies': def_qr}

    # Courses list (no price sub-intent)
    price_words = ['price', 'cost', 'fee', 'fees', 'how much', 'kitna', 'charge', 'rate', '₹', 'rupee', 'pricing']
    course_words = ['course', 'courses', 'class', 'classes', 'learn', 'learning', 'training', 'curriculum', 'syllabus']
    if any(w in msg for w in course_words) and not any(w in msg for w in price_words):
        courses = Course.query.filter_by(is_published=True).limit(6).all()
        course_list = [{'title': c.title, 'price': c.price or 0} for c in courses]
        if course_list:
            lines = ['Here are our available courses:\n']
            for c in course_list:
                p = 'FREE' if c['price'] == 0 else f'\u20b9{c["price"]}'
                lines.append(f'\u2022 **{c["title"]}** \u2014 {p}')
            lines.append('\nTap a course card to learn more and enroll!')
            return {'message': '\n'.join(lines), 'courses': course_list, 'quick_replies': ['\U0001f4b0 Course Pricing', '\U0001f4dd How to Enroll?', '\U0001f4ac Get Support']}
        return {'message': 'Courses are coming soon! Subscribe to the newsletter to be the first to know.', 'quick_replies': ['\U0001f4e9 Subscribe', '\U0001f4ac Get Support']}

    # Pricing
    if any(w in msg for w in price_words):
        courses = Course.query.filter_by(is_published=True).limit(6).all()
        course_list = [{'title': c.title, 'price': c.price or 0} for c in courses]
        if course_list:
            lines = ['Here is our current course pricing:\n']
            for c in course_list:
                p = 'FREE' if c['price'] == 0 else f'\u20b9{c["price"]}'
                lines.append(f'\u2022 **{c["title"]}** \u2014 {p}')
            lines.append('\nAll courses include lifetime access!')
            return {'message': '\n'.join(lines), 'courses': course_list, 'quick_replies': ['\U0001f4dd How to Enroll?', '\U0001f4ac Get Support', '\U0001f4da View All Courses']}
        return {'message': 'Check the Courses page for current pricing. All plans are designed to be accessible!', 'quick_replies': ['\U0001f4da View Courses', '\U0001f4ac Get Support']}

    # Enrollment / Purchase
    if any(w in msg for w in ['buy', 'purchase', 'enroll', 'join', 'register', 'kaise', 'how to', 'sign up', 'payment', 'pay']):
        resp = 'Enrolling in a course is quick and easy!\n\n1. **Go to Courses** \u2014 click the Courses link in the menu\n2. **Choose your course** \u2014 browse what interests you\n3. **Click Enroll** \u2014 follow the secure payment steps\n4. **Start learning** \u2014 instant access after payment!\n\nNeed help? Our team is on WhatsApp!'
        obj = {'message': resp, 'quick_replies': ['\U0001f4da View Courses', '\U0001f4ac Get Support on WhatsApp']}
        if wa_url:
            obj['show_whatsapp'] = True
            obj['whatsapp_url'] = wa_url
        return obj

    # Support / Contact
    if any(w in msg for w in ['support', 'help', 'contact', 'whatsapp', 'problem', 'issue', 'query', 'doubt', 'confused', 'assist', 'talk']):
        resp = 'Happy to help! Here are the fastest ways to reach us:\n\n\u2022 **WhatsApp** \u2014 chat with Kshitiz\'s team directly (fastest!)\n\u2022 **Contact page** \u2014 send a detailed inquiry\n\nOr share your details below and we\'ll call you back:'
        obj = {'message': resp, 'quick_replies': ['\U0001f4da View Courses', '\U0001f3e0 Go to Homepage'], 'show_contact_form': True}
        if wa_url:
            obj['show_whatsapp'] = True
            obj['whatsapp_url'] = wa_url
        return obj

    # Reels / Videos
    if any(w in msg for w in ['reel', 'video', 'watch', 'content', 'latest', 'episode', 'shorts']):
        return {'message': 'Kshitiz creates powerful reels on current affairs, social commentary, and news analysis! \U0001f3ac\n\nClick **Beyond the Reels** in the navigation to watch all content.', 'quick_replies': ['\U0001f4da View Courses', '\U0001f4e9 Subscribe for Updates', '\U0001f4ac Get Support']}

    # Newsletter
    if any(w in msg for w in ['newsletter', 'subscribe', 'subscription', 'email', 'notification', 'update', 'alert']):
        return {'message': 'Join Kshitiz\'s Inner Circle! \U0001f4e9\n\nGet unfiltered commentary, behind-the-reel insights, and exclusive updates straight to your inbox. Scroll to the **Newsletter section** on the homepage to subscribe \u2014 it\'s completely **FREE!**', 'quick_replies': ['\U0001f4da View Courses', '\U0001f4ac Get Support', '\U0001f3ac Watch Reels']}

    # About / Who is Kshitiz
    if any(w in msg for w in ['about', 'who is', 'kshitiz', 'commentator', 'unfiltered', 'what do you do', 'introduce']):
        return {'message': 'Kshitiz Jaiswal is an **Unfiltered Commentator** \U0001f3a4\n\nHe creates sharp, honest commentary on current affairs, politics, and social issues \u2014 cutting through the noise to deliver the truth.\n\n**"The truth is never biased."**\n\nWatch his reels or enroll in a course to experience his unique perspective!', 'quick_replies': ['\U0001f4da View Courses', '\U0001f3ac Watch Reels', '\U0001f4e9 Subscribe']}

    # Free courses
    if any(w in msg for w in ['free', 'muft', 'zero cost', 'no cost', 'without paying']):
        free_courses = Course.query.filter_by(is_published=True, price=0).all()
        if free_courses:
            names = ', '.join([c.title for c in free_courses[:3]])
            return {'message': f'Great news! \U0001f389 We have free courses available!\n\nFree: **{names}**\n\nEnroll now at zero cost!', 'quick_replies': ['\U0001f4da View All Courses', '\U0001f4b0 Paid Course Pricing', '\U0001f4ac Get Support']}
        return {'message': 'We occasionally offer free courses and workshops. Subscribe to the newsletter to be notified when free content drops!', 'quick_replies': ['\U0001f4e9 Subscribe', '\U0001f4da View Courses']}

    # Navigation
    if any(w in msg for w in ['navigate', 'navigation', 'where', 'find', 'go to', 'home', 'homepage', 'page', 'section', 'menu']):
        return {'message': 'Here\'s a quick guide to the website:\n\n\U0001f3e0 **Home** \u2014 reels, stats, support\n\U0001f3ac **Beyond the Reels** \u2014 all video content\n\U0001f3a4 **Kshitiz Ki Rai** \u2014 opinion polls\n\U0001f4da **Courses** \u2014 learn from Kshitiz\n\U0001f4c5 **Upcoming Shows** \u2014 live events\n\U0001f4de **Contact** \u2014 reach out', 'quick_replies': ['\U0001f4da View Courses', '\U0001f3ac Watch Reels', '\U0001f4ac Get Support']}

    # ── 3. Low-threshold FAQ fallback (score >= 1) ────────────────────
    if faq and score >= 1:
        return {'message': faq.answer, 'quick_replies': faq.qr_list() or def_qr}

    # ── 4. Default fallback ───────────────────────────────────────────
    obj = {'message': fallback, 'quick_replies': def_qr}
    if wa_url:
        obj['show_whatsapp'] = True
        obj['whatsapp_url'] = wa_url
    return obj


@app.route('/chatbot/message', methods=['POST'])
def chatbot_message():
    """Public chatbot message endpoint — returns JSON response."""
    if SiteConfig.get('chatbot_enabled', 'true').lower() == 'false':
        return jsonify({'message': 'Chatbot is currently unavailable.', 'quick_replies': []})
    data     = request.get_json(silent=True) or {}
    user_msg = (data.get('message') or '').strip()[:500]
    if not user_msg:
        return jsonify({'message': 'Please type something!', 'quick_replies': []})
    try:
        response = _chatbot_build_response(user_msg)
    except Exception as e:
        response = {'message': "Sorry, I'm having trouble right now. Please try again!", 'quick_replies': ['\U0001f4ac Get Support']}
    return jsonify(response)


@app.route('/chatbot/inquiry', methods=['POST'])
def chatbot_inquiry():
    """Save a lead inquiry captured from the chatbot widget."""
    data = request.get_json(silent=True) or {}
    try:
        inq = ChatbotInquiry(
            name    = (data.get('name')    or '').strip()[:120],
            email   = (data.get('email')   or '').strip()[:200],
            phone   = (data.get('phone')   or '').strip()[:30],
            message = (data.get('message') or '').strip()[:1000],
        )
        db.session.add(inq)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception:
        return jsonify({'ok': False}), 500


# ═════════════════════════════════════════════════════════════════════════════
# CHATBOT — Admin Panel
# ═════════════════════════════════════════════════════════════════════════════

_CHATBOT_DEFAULT_FAQS = [
    {'category': 'courses',    'question_pattern': 'Tell me about your courses',      'keywords': ['course','courses','learn','learning','class'], 'answer': 'We offer structured courses on media literacy, political commentary, and social analysis. Each course is designed by Kshitiz to help you think critically about the world around you.\n\nVisit the **Courses** page to browse all available programs and enroll!', 'quick_replies': ['\U0001f4b0 Course Pricing','\U0001f4dd How to Enroll?','\U0001f4ac Get Support'], 'priority': 5},
    {'category': 'pricing',    'question_pattern': 'What is the course fee',           'keywords': ['price','fee','fees','cost','how much','kitna','₹'], 'answer': 'Our courses are priced to be accessible for everyone. Prices range from **FREE** to ₹1,499. Each course includes:\n\n✔ Lifetime access\n✔ Certificate of completion\n✔ Community support\n\nCheck the Courses page for current pricing!', 'quick_replies': ['\U0001f4da View Courses','\U0001f4dd How to Enroll?','\U0001f4ac Get Support'], 'priority': 5},
    {'category': 'support',    'question_pattern': 'How do I contact Kshitiz',         'keywords': ['contact','reach','email','phone','connect','kshitiz'], 'answer': 'You can reach Kshitiz\'s team through:\n\n\u2022 **WhatsApp** \u2014 fastest response\n\u2022 **Contact page** \u2014 for detailed inquiries\n\u2022 **Social media** \u2014 Instagram, YouTube, Twitter\n\nWe typically respond within a few hours!', 'quick_replies': ['\U0001f4da View Courses','\U0001f3ac Watch Reels'], 'priority': 4},
    {'category': 'general',    'question_pattern': 'What is this website about',       'keywords': ['website','about','what is','purpose','kshitiz jaiswal'], 'answer': 'This is the official website of **Kshitiz Jaiswal** \u2014 Unfiltered Commentator.\n\nHere you can:\n\U0001f3ac Watch powerful reels on current affairs\n\U0001f4da Enroll in courses on media & commentary\n\U0001f3a4 Read Kshitiz Ki Rai \u2014 his unfiltered opinions\n\U0001f4e7 Subscribe for exclusive updates\n\U0001f49d Support independent commentary', 'quick_replies': ['\U0001f4da View Courses','\U0001f3ac Watch Reels','\U0001f4e9 Subscribe'], 'priority': 3},
    {'category': 'navigation', 'question_pattern': 'How do I subscribe to the newsletter', 'keywords': ['subscribe','newsletter','email updates','inner circle','signup'], 'answer': 'Subscribing is easy and free! \U0001f4e7\n\n1. Scroll to the **Newsletter section** on the homepage\n2. Enter your name and email\n3. Click **Subscribe Free**\n\nYou\'ll get exclusive updates, behind-the-reel insights, and Kshitiz\'s unfiltered thoughts straight to your inbox!', 'quick_replies': ['\U0001f4da View Courses','\U0001f3ac Watch Reels'], 'priority': 3},
]


def _seed_default_faqs():
    """Seed default FAQs if the table is empty."""
    try:
        if ChatbotFAQ.query.count() == 0:
            for f in _CHATBOT_DEFAULT_FAQS:
                faq = ChatbotFAQ(
                    category         = f['category'],
                    question_pattern = f['question_pattern'],
                    answer           = f['answer'],
                    keywords         = json.dumps(f['keywords']),
                    quick_replies    = json.dumps(f['quick_replies']),
                    priority         = f['priority'],
                    is_active        = True,
                )
                db.session.add(faq)
            db.session.commit()
    except Exception:
        pass


@app.route('/admin/chatbot', methods=['GET', 'POST'])
def admin_chatbot():
    """Chatbot admin — settings, FAQ management, inquiries."""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    _seed_default_faqs()

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'settings':
            SiteConfig.set('chatbot_enabled',  'true' if request.form.get('chatbot_enabled') else 'false')
            SiteConfig.set('chatbot_name',     request.form.get('chatbot_name', 'Kshitiz Assistant').strip())
            SiteConfig.set('chatbot_greeting', request.form.get('chatbot_greeting', '').strip())
            SiteConfig.set('chatbot_fallback', request.form.get('chatbot_fallback', '').strip())
            SiteConfig.set('chatbot_whatsapp', request.form.get('chatbot_whatsapp', '').strip())
            raw_qr = request.form.get('chatbot_quick_replies', '')
            qr_list = [q.strip() for q in raw_qr.split('\n') if q.strip()]
            SiteConfig.set('chatbot_quick_replies', json.dumps(qr_list))
            flash('Chatbot settings saved!', 'success')
            return redirect(url_for('admin_chatbot') + '#settings')

        elif action == 'add_faq':
            kw_raw = request.form.get('keywords', '')
            qr_raw = request.form.get('quick_replies', '')
            kw_list = [k.strip() for k in kw_raw.split(',') if k.strip()]
            qr_list = [q.strip() for q in qr_raw.split('\n') if q.strip()]
            faq = ChatbotFAQ(
                category         = request.form.get('category', 'general').strip(),
                question_pattern = request.form.get('question_pattern', '').strip(),
                answer           = request.form.get('answer', '').strip(),
                keywords         = json.dumps(kw_list),
                quick_replies    = json.dumps(qr_list),
                priority         = int(request.form.get('priority', 0) or 0),
                is_active        = bool(request.form.get('is_active')),
            )
            db.session.add(faq)
            db.session.commit()
            flash('FAQ added!', 'success')
            return redirect(url_for('admin_chatbot') + '#faqs')

        elif action == 'edit_faq':
            faq_id = int(request.form.get('faq_id', 0))
            faq = ChatbotFAQ.query.get(faq_id)
            if faq:
                kw_raw = request.form.get('keywords', '')
                qr_raw = request.form.get('quick_replies', '')
                kw_list = [k.strip() for k in kw_raw.split(',') if k.strip()]
                qr_list = [q.strip() for q in qr_raw.split('\n') if q.strip()]
                faq.category         = request.form.get('category', 'general').strip()
                faq.question_pattern = request.form.get('question_pattern', '').strip()
                faq.answer           = request.form.get('answer', '').strip()
                faq.keywords         = json.dumps(kw_list)
                faq.quick_replies    = json.dumps(qr_list)
                faq.priority         = int(request.form.get('priority', 0) or 0)
                faq.is_active        = bool(request.form.get('is_active'))
                from datetime import datetime as _dt
                faq.updated_at       = _dt.utcnow()
                db.session.commit()
                flash('FAQ updated!', 'success')
            return redirect(url_for('admin_chatbot') + '#faqs')

        elif action == 'delete_faq':
            faq_id = int(request.form.get('faq_id', 0))
            faq = ChatbotFAQ.query.get(faq_id)
            if faq:
                db.session.delete(faq)
                db.session.commit()
                flash('FAQ deleted.', 'success')
            return redirect(url_for('admin_chatbot') + '#faqs')

        elif action == 'delete_inquiry':
            inq_id = int(request.form.get('inquiry_id', 0))
            inq = ChatbotInquiry.query.get(inq_id)
            if inq:
                db.session.delete(inq)
                db.session.commit()
                flash('Inquiry deleted.', 'success')
            return redirect(url_for('admin_chatbot') + '#inquiries')

        elif action == 'mark_read':
            inq_id = int(request.form.get('inquiry_id', 0))
            inq = ChatbotInquiry.query.get(inq_id)
            if inq:
                inq.is_read = True
                db.session.commit()
            return redirect(url_for('admin_chatbot') + '#inquiries')

        elif action == 'seed_faqs':
            try:
                for f in _CHATBOT_DEFAULT_FAQS:
                    faq = ChatbotFAQ(
                        category=f['category'], question_pattern=f['question_pattern'],
                        answer=f['answer'], keywords=json.dumps(f['keywords']),
                        quick_replies=json.dumps(f['quick_replies']), priority=f['priority'], is_active=True,
                    )
                    db.session.add(faq)
                db.session.commit()
                flash('Default FAQs seeded successfully!', 'success')
            except Exception as e:
                flash(f'Error seeding FAQs: {e}', 'error')
            return redirect(url_for('admin_chatbot') + '#faqs')

        flash('Unknown action.', 'error')
        return redirect(url_for('admin_chatbot'))


# ── SEO MANAGER ────────────────────────────────────────────────────────────────

@app.route('/admin/seo', methods=['GET', 'POST'])
def admin_seo():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    pages = [
        {'key': 'index',          'label': 'Home Page',              'url': '/'},
        {'key': 'reels_library',  'label': 'Beyond the Reels',       'url': '/reels'},
        {'key': 'polls_archive',  'label': 'Kshitiz Ki Rai (Polls)', 'url': '/polls'},
        {'key': 'courses',        'label': 'Courses',                'url': '/courses'},
        {'key': 'upcoming_shows', 'label': 'Upcoming Shows',         'url': '/upcoming-shows'},
        {'key': 'contact',        'label': 'Contact',                'url': '/contact'},
    ]

    if request.method == 'POST':
        for page in pages:
            key   = page['key']
            title = request.form.get(f'seo_{key}_title', '').strip()
            desc  = request.form.get(f'seo_{key}_description', '').strip()
            if title:
                SiteConfig.set(f'seo_{key}_title', title)
            if desc:
                SiteConfig.set(f'seo_{key}_description', desc)

        og_image       = request.form.get('seo_og_image', '').strip()
        twitter_handle = request.form.get('seo_twitter_handle', '').strip()
        if og_image:
            SiteConfig.set('seo_og_image', og_image)
        if twitter_handle:
            SiteConfig.set('seo_twitter_handle', twitter_handle)

        flash('SEO settings saved successfully!', 'success')
        return redirect(url_for('admin_seo'))

    seo_data = {}
    for page in pages:
        key = page['key']
        seo_data[f'seo_{key}_title']       = SiteConfig.get(f'seo_{key}_title', '')
        seo_data[f'seo_{key}_description'] = SiteConfig.get(f'seo_{key}_description', '')
    seo_data['seo_og_image']       = SiteConfig.get('seo_og_image', '')
    seo_data['seo_twitter_handle'] = SiteConfig.get('seo_twitter_handle', '')

    return render_template('admin/seo_manager.html', pages=pages, seo_data=seo_data, title='SEO Manager')


# ── TESTIMONIALS MANAGER ───────────────────────────────────────────────────────

def _get_testimonials_list():
    import json
    rec = SiteContent.query.filter_by(content_key='testimonials_list').first()
    try:
        return json.loads(rec.content_data) if rec else []
    except Exception:
        return []

def _save_testimonials_list(testimonials):
    import json
    rec = SiteContent.query.filter_by(content_key='testimonials_list').first()
    data = json.dumps(testimonials)
    if rec:
        rec.content_data = data
    else:
        db.session.add(SiteContent(content_key='testimonials_list', content_data=data))
    db.session.commit()

@app.route('/admin/testimonials')
def admin_testimonials():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin/testimonials.html',
                           testimonials=_get_testimonials_list(),
                           title='Testimonials Manager')

@app.route('/admin/testimonial/add', methods=['GET', 'POST'])
def admin_add_testimonial():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    from forms import TestimonialForm
    form = TestimonialForm()
    if form.validate_on_submit():
        testimonials = _get_testimonials_list()
        testimonials.append({
            'name':       form.name.data.strip(),
            'role':       form.role.data.strip(),
            'text':       form.text.data.strip(),
            'rating':     int(form.rating.data),
            'is_visible': form.is_visible.data == '1',
            'sort_order': form.sort_order.data or 0,
        })
        testimonials.sort(key=lambda x: x.get('sort_order', 0))
        _save_testimonials_list(testimonials)
        flash(f'Testimonial by "{form.name.data}" added!', 'success')
        return redirect(url_for('admin_testimonials'))
    return render_template('admin/testimonial_form.html', form=form, title='Add Testimonial')

@app.route('/admin/testimonial/<int:idx>/edit', methods=['GET', 'POST'])
def admin_edit_testimonial(idx):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    from forms import TestimonialForm
    testimonials = _get_testimonials_list()
    if idx >= len(testimonials):
        flash('Testimonial not found.', 'error')
        return redirect(url_for('admin_testimonials'))
    t = testimonials[idx]
    form = TestimonialForm()
    if form.validate_on_submit():
        testimonials[idx] = {
            'name':       form.name.data.strip(),
            'role':       form.role.data.strip(),
            'text':       form.text.data.strip(),
            'rating':     int(form.rating.data),
            'is_visible': form.is_visible.data == '1',
            'sort_order': form.sort_order.data or 0,
        }
        _save_testimonials_list(testimonials)
        flash('Testimonial updated!', 'success')
        return redirect(url_for('admin_testimonials'))
    # Pre-populate
    if not form.is_submitted():
        form.name.data       = t.get('name', '')
        form.role.data       = t.get('role', '')
        form.text.data       = t.get('text', '')
        form.rating.data     = str(t.get('rating', 5))
        form.is_visible.data = '1' if t.get('is_visible', True) else '0'
        form.sort_order.data = t.get('sort_order', 0)
    return render_template('admin/testimonial_form.html', form=form, title='Edit Testimonial', idx=idx)

@app.route('/admin/testimonial/<int:idx>/delete', methods=['POST'])
def admin_delete_testimonial(idx):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    testimonials = _get_testimonials_list()
    if idx < len(testimonials):
        name = testimonials[idx].get('name', 'Testimonial')
        del testimonials[idx]
        _save_testimonials_list(testimonials)
        flash(f'Testimonial by "{name}" deleted.', 'success')
    else:
        flash('Testimonial not found.', 'error')
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/testimonial/<int:idx>/toggle', methods=['POST'])
def admin_toggle_testimonial(idx):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    testimonials = _get_testimonials_list()
    if idx < len(testimonials):
        testimonials[idx]['is_visible'] = not testimonials[idx].get('is_visible', True)
        _save_testimonials_list(testimonials)
        status = 'visible' if testimonials[idx]['is_visible'] else 'hidden'
        flash(f'Testimonial is now {status}.', 'success')
    return redirect(url_for('admin_testimonials'))


# ── ANNOUNCEMENT BANNER ────────────────────────────────────────────────────────

@app.route('/admin/announcement', methods=['GET', 'POST'])
def admin_announcement():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    from forms import AnnouncementForm
    form = AnnouncementForm()
    if form.validate_on_submit():
        SiteConfig.set('announcement_active',   form.is_active.data)
        SiteConfig.set('announcement_text',     form.text.data.strip())
        SiteConfig.set('announcement_link_url', form.link_url.data.strip() if form.link_url.data else '')
        SiteConfig.set('announcement_link_text', form.link_text.data.strip() or 'Learn More')
        SiteConfig.set('announcement_style',    form.style.data)
        status = 'activated and saved' if form.is_active.data == '1' else 'saved (inactive)'
        flash(f'Announcement banner {status}!', 'success')
        return redirect(url_for('admin_announcement'))
    if not form.is_submitted():
        form.is_active.data  = SiteConfig.get('announcement_active', '0')
        form.text.data       = SiteConfig.get('announcement_text', '')
        form.link_url.data   = SiteConfig.get('announcement_link_url', '')
        form.link_text.data  = SiteConfig.get('announcement_link_text', 'Learn More')
        form.style.data      = SiteConfig.get('announcement_style', 'info')
    return render_template('admin/announcement.html', form=form, title='Announcement Banner')


# ── ADMIN ACCOUNT SETTINGS ─────────────────────────────────────────────────────

@app.route('/admin/account', methods=['GET', 'POST'])
def admin_account():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    from forms import AdminAccountForm
    from werkzeug.security import check_password_hash, generate_password_hash
    form = AdminAccountForm()

    stored_username = SiteConfig.get('admin_username_override') or os.environ.get('ADMIN_USERNAME', 'admin')

    if form.validate_on_submit():
        # Verify current password against whichever credential store is active
        stored_hash = SiteConfig.get('admin_password_hash')
        if stored_hash:
            try:
                valid = check_password_hash(stored_hash, form.current_password.data)
            except Exception:
                valid = False
        else:
            valid = form.current_password.data == os.environ.get('ADMIN_PASSWORD', 'kshitiz2025')

        if not valid:
            flash('Current password is incorrect.', 'error')
            return render_template('admin/account_settings.html', form=form,
                                   title='Account Settings', current_username=stored_username)

        # Validate password confirmation
        if form.new_password.data and form.new_password.data != form.confirm_password.data:
            flash('New passwords do not match.', 'error')
            return render_template('admin/account_settings.html', form=form,
                                   title='Account Settings', current_username=stored_username)

        SiteConfig.set('admin_username_override', form.new_username.data.strip())
        if form.new_password.data:
            SiteConfig.set('admin_password_hash', generate_password_hash(form.new_password.data))
            flash('Username and password updated successfully! Use your new credentials next time you log in.', 'success')
        else:
            flash('Username updated. Password unchanged.', 'success')
        return redirect(url_for('admin_account'))

    if not form.is_submitted():
        form.new_username.data = stored_username

    return render_template('admin/account_settings.html', form=form,
                           title='Account Settings', current_username=stored_username)

    # GET
    faqs      = ChatbotFAQ.query.order_by(ChatbotFAQ.priority.desc(), ChatbotFAQ.id.desc()).all()
    inquiries = ChatbotInquiry.query.order_by(ChatbotInquiry.created_at.desc()).limit(200).all()
    unread    = ChatbotInquiry.query.filter_by(is_read=False).count()
    total_inq = ChatbotInquiry.query.count()

    settings = {
        'enabled':       SiteConfig.get('chatbot_enabled', 'true').lower() != 'false',
        'name':          SiteConfig.get('chatbot_name', 'Kshitiz Assistant'),
        'greeting':      SiteConfig.get('chatbot_greeting', ''),
        'fallback':      SiteConfig.get('chatbot_fallback', "I'm not sure about that. You can reach Kshitiz's team on WhatsApp or browse the website!"),
        'whatsapp':      SiteConfig.get('chatbot_whatsapp', ''),
        'quick_replies': '\n'.join(json.loads(SiteConfig.get('chatbot_quick_replies', '[]')) or []),
    }

    categories = ['general', 'courses', 'pricing', 'support', 'navigation', 'technical', 'other']

    return render_template('admin/chatbot.html',
                           faqs=faqs, inquiries=inquiries,
                           unread=unread, total_inq=total_inq,
                           settings=settings, categories=categories)
