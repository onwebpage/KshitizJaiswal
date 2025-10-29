from flask import render_template, request, jsonify, redirect, url_for, flash, session, abort
from app import app, db
from models import DataManager, AdminUser, SiteContent, Reel, Opinion, Subscriber, SubscriptionTier, Course, Module, Lesson, UserCourseAccess
from forms import NewsletterForm, PollVoteForm, AdminLoginForm, ReelForm, OpinionForm, HeroContentForm, PaymentSettingsForm, SubscriptionTierForm, CourseForm, ModuleForm, LessonForm
from utils import save_uploaded_file, calculate_poll_percentages, get_youtube_embed_url
from clerk_auth import clerk_auth_required, get_clerk_user, get_clerk_user_id
import razorpay
import os
import json

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(
    os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummy_key'),
    os.environ.get('RAZORPAY_KEY_SECRET', 'dummy_secret')
))

@app.route('/')
def index():
    """Homepage"""
    content = DataManager.get_content()
    newsletter_form = NewsletterForm()
    poll_form = PollVoteForm()
    
    # Show only top 10 latest/featured reels on homepage
    featured_reels = Reel.query.filter_by(is_featured=True).order_by(Reel.created_at.desc()).limit(10).all()
    if not featured_reels:
        # If no featured reels, show latest 10
        featured_reels = Reel.query.order_by(Reel.created_at.desc()).limit(10).all()
    
    content['reels'] = [reel.to_dict() for reel in featured_reels]
    
    # Calculate poll percentages
    for opinion in content['opinions']:
        opinion['percentages'] = calculate_poll_percentages(opinion['votes'])
        opinion['total_votes'] = sum(opinion['votes'])
    
    # Get subscription tiers from database
    AdminUser.create_default_tiers()  # Create default tiers if none exist
    subscription_tiers = AdminUser.get_subscription_tiers()
    
    # Get Razorpay settings from database
    # already imported - SiteContent
    import json
    payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
    razorpay_key = 'rzp_test_dummy_key'
    if payment_content:
        payment_settings = json.loads(payment_content.content_data)
        razorpay_key = payment_settings.get('razorpay_key_id', 'rzp_test_dummy_key')
    
    return render_template('index.html', 
                         content=content, 
                         newsletter_form=newsletter_form,
                         poll_form=poll_form,
                         subscription_tiers=subscription_tiers,
                         razorpay_key=razorpay_key)

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
    
    # Increment view count
    reel.view_count += 1
    db.session.commit()
    
    # Get reel data
    reel_data = reel.to_dict()
    
    # Process YouTube URL for embedding
    if reel_data.get('video_url'):
        reel_data['embed_url'] = get_youtube_embed_url(reel_data['video_url'])
    
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
    """Newsletter subscription"""
    form = NewsletterForm()
    
    if form.validate_on_submit():
        try:
            DataManager.add_subscriber(
                form.name.data,
                form.email.data,
                form.place.data,
                form.age.data
            )
            flash('Successfully subscribed to newsletter!', 'success')
        except Exception as e:
            flash('Error subscribing to newsletter. Please try again.', 'error')
    else:
        flash('Please fill all fields correctly.', 'error')
    
    return redirect(url_for('index') + '#newsletter')

@app.route('/vote', methods=['POST'])
def vote_poll():
    """Handle poll voting"""
    form = PollVoteForm()
    
    if form.validate_on_submit():
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
    """Create Razorpay payment order"""
    try:
        # Get Razorpay settings from database
        # already imported - SiteContent
        import json
        payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
        
        if payment_content:
            payment_settings = json.loads(payment_content.content_data)
            razorpay_key_id = payment_settings.get('razorpay_key_id')
            razorpay_key_secret = payment_settings.get('razorpay_key_secret')
            
            if razorpay_key_id and razorpay_key_secret:
                # Create dynamic Razorpay client with database settings
                dynamic_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
            else:
                dynamic_client = razorpay_client  # Fallback to default
        else:
            dynamic_client = razorpay_client  # Fallback to default
        
        amount = int(request.json.get('amount', 10)) * 100  # Convert to paise
        
        order_data = {
            'amount': amount,
            'currency': 'INR',
            'receipt': f'support_{amount//100}',
            'payment_capture': 1
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
        
        new_reel = Reel(
            title=form.title.data,
            thumbnail=thumbnail_url or '',
            video_url=form.video_url.data or '',
            behind_thought=form.behind_thought.data,
            sources=json.dumps(sources),
            extra_context=form.extra_context.data or '',
            category_tag=form.category_tag.data or '',
            topic_tag=form.topic_tag.data or '',
            is_featured=bool(int(form.is_featured.data)),
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
        
        reel.title = form.title.data
        reel.video_url = form.video_url.data or ''
        reel.behind_thought = form.behind_thought.data
        reel.sources = json.dumps(sources)
        reel.extra_context = form.extra_context.data or ''
        reel.category_tag = form.category_tag.data or ''
        reel.topic_tag = form.topic_tag.data or ''
        reel.is_featured = bool(int(form.is_featured.data))
        
        db.session.commit()
        
        flash('Reel updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Pre-populate form with existing data
    if request.method == 'GET':
        form.title.data = reel.title
        form.video_url.data = reel.video_url
        form.behind_thought.data = reel.behind_thought
        form.sources.data = '\n'.join(json.loads(reel.sources) if reel.sources else [])
        form.extra_context.data = reel.extra_context
        form.category_tag.data = reel.category_tag or ''
        form.topic_tag.data = reel.topic_tag or ''
        form.is_featured.data = '1' if reel.is_featured else '0'
    
    return render_template('admin/reel_form.html', form=form, title='Edit Reel', reel=reel)

@app.route('/admin/reel/<int:reel_id>/delete', methods=['POST'])
def admin_delete_reel(reel_id):
    """Delete reel"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # already imported - Reel, db
    
    reel = Reel.query.get_or_404(reel_id)
    db.session.delete(reel)
    db.session.commit()
    
    flash('Reel deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

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
        # Handle desktop image upload
        desktop_url = ''
        if form.desktop_image.data:
            uploaded_path = save_uploaded_file(form.desktop_image.data, 'hero')
            if uploaded_path:
                desktop_url = uploaded_path
        else:
            # Use whatever is in the form field (empty if cleared, URL if provided)
            desktop_url = form.desktop_url.data or ''
        
        # Handle mobile image upload
        mobile_url = ''
        if form.mobile_image.data:
            uploaded_path = save_uploaded_file(form.mobile_image.data, 'hero')
            if uploaded_path:
                mobile_url = uploaded_path
        else:
            # Use whatever is in the form field (empty if cleared, URL if provided)
            mobile_url = form.mobile_url.data or ''
        
        # Handle legacy banner image upload for backward compatibility
        banner_url = ''
        if form.banner_image.data:
            uploaded_path = save_uploaded_file(form.banner_image.data, 'hero')
            if uploaded_path:
                banner_url = uploaded_path
                # If no desktop/mobile specified, use banner for both
                if not desktop_url:
                    desktop_url = uploaded_path
                if not mobile_url:
                    mobile_url = uploaded_path
        else:
            # Use whatever is in the form field (empty if cleared, URL if provided)
            banner_url = form.banner_url.data or ''
            # If no desktop/mobile specified, use banner for both
            if not desktop_url and banner_url:
                desktop_url = banner_url
            if not mobile_url and banner_url:
                mobile_url = banner_url
        
        # Update hero content
        updated_hero = {
            "name": form.name.data,
            "tagline": form.tagline.data,
            "banner_url": banner_url,  # Keep for backward compatibility
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
    
    # Pre-populate form with current data
    if request.method == 'GET':
        form.name.data = current_hero.get('name', '')
        form.tagline.data = current_hero.get('tagline', '')
        form.banner_url.data = current_hero.get('banner_url', '')
        form.desktop_url.data = current_hero.get('desktop_url', '')
        form.mobile_url.data = current_hero.get('mobile_url', '')
    
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
        
        # Add new resource
        new_resource = {
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'link': form.link.data,
            'image': form.image.data or 'https://pixabay.com/get/g1607648249e3d2cc886480cc481c2224cb52f7fd6b06e51d63e7c2ee7d304d71973191ec7388dc286501651899d7fd130bc378c50e5ab80727d452f099c3f672_1280.jpg'
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
        # Update resource
        resources[resource_index] = {
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'link': form.link.data,
            'image': form.image.data or resource.get('image', '')
        }
        
        # Save to database
        resources_content.content_data = json.dumps(resources)
        db.session.commit()
        
        flash('Learning resource updated successfully!', 'success')
        return redirect(url_for('admin_resources'))
    
    # Populate form with current data
    form.title.data = resource.get('title', '')
    form.description.data = resource.get('description', '')
    form.price.data = resource.get('price', '')
    form.link.data = resource.get('link', '')
    form.image.data = resource.get('image', '')
    
    return render_template('admin/resource_form.html', form=form, title='Edit Learning Resource', resource=resource)

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
        
        # Add new show
        new_show = {
            'title': form.title.data,
            'description': form.description.data,
            'image': form.image.data or 'https://pixabay.com/get/g51d3a9b60f5b304d6d9a2109588df26fa955fdad29b549ed6f2d44cdb714ef5b54d4b04df2f46da1bd05dede83422e909ae5403a8c87771e7130a78714c2e5df_1280.jpg',
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
        # Update show
        shows[show_index] = {
            'title': form.title.data,
            'description': form.description.data,
            'image': form.image.data or show.get('image', ''),
            'coming_soon': bool(int(form.coming_soon.data)),
            'notify_link': form.notify_link.data
        }
        
        # Save to database
        shows_content.content_data = json.dumps(shows)
        db.session.commit()
        
        flash('Upcoming show updated successfully!', 'success')
        return redirect(url_for('admin_shows'))
    
    # Populate form with current data
    form.title.data = show.get('title', '')
    form.description.data = show.get('description', '')
    form.image.data = show.get('image', '')
    form.coming_soon.data = '1' if show.get('coming_soon', True) else '0'
    form.notify_link.data = show.get('notify_link', '')
    
    return render_template('admin/show_form.html', form=form, title='Edit Upcoming Show', show=show)

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
@app.route('/admin/courses')
def admin_courses():
    """Admin courses listing"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    courses = Course.query.order_by(Course.sort_order, Course.id).all()
    return render_template('admin/courses.html', courses=courses)

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
        course.price = form.price.data
        course.is_active = bool(int(form.is_active.data))
        course.sort_order = form.sort_order.data
        
        db.session.commit()
        flash(f'Course "{course.title}" updated successfully!', 'success')
        return redirect(url_for('admin_courses'))
    
    form.title.data = course.title
    form.description.data = course.description
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
    
    modules = Module.query.order_by(Module.course_id, Module.sort_order).all()
    return render_template('admin/modules.html', modules=modules)

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
    
    lessons = Lesson.query.join(Module).order_by(Module.course_id, Module.sort_order, Lesson.sort_order).all()
    return render_template('admin/lessons.html', lessons=lessons)

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
    
    # Get next URL and ensure it's absolute
    next_url = session.pop('next_url', None)
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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

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
    
    payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
    razorpay_key = 'rzp_test_dummy_key'
    if payment_content:
        payment_settings = json.loads(payment_content.content_data)
        razorpay_key = payment_settings.get('razorpay_key_id', 'rzp_test_dummy_key')
    
    return render_template('courses.html', courses=courses_data, razorpay_key=razorpay_key)

@app.route('/my-courses')
def my_courses():
    """My Courses page - shows courses the user has purchased"""
    clerk_user_id = get_clerk_user_id()
    
    if not clerk_user_id:
        flash('Please sign in to view your courses.', 'warning')
        return redirect(url_for('clerk_login', next=request.url))
    
    user_accesses = UserCourseAccess.get_user_courses(clerk_user_id)
    
    my_courses_data = []
    for access in user_accesses:
        course = Course.query.get(access.course_id)
        if course and course.is_active:
            course_dict = course.to_dict()
            course_dict['has_access'] = True
            course_dict['module_count'] = len(course.modules)
            course_dict['lesson_count'] = sum([len(module.lessons) for module in course.modules])
            course_dict['purchased_at'] = access.granted_at.strftime('%B %d, %Y') if access.granted_at else ''
            my_courses_data.append(course_dict)
    
    return render_template('my_courses.html', courses=my_courses_data)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Course detail page with modules and lessons"""
    course = Course.query.get_or_404(course_id)
    
    if not course.is_active:
        abort(404)
    
    clerk_user_id = get_clerk_user_id()
    has_access = UserCourseAccess.has_access(clerk_user_id, course_id) if clerk_user_id else False
    
    course_data = course.to_dict()
    course_data['has_access'] = has_access
    
    payment_content = SiteContent.query.filter_by(content_key='payment_settings').first()
    razorpay_key = 'rzp_test_dummy_key'
    if payment_content:
        payment_settings = json.loads(payment_content.content_data)
        razorpay_key = payment_settings.get('razorpay_key_id', 'rzp_test_dummy_key')
    
    return render_template('course_detail.html', course=course_data, razorpay_key=razorpay_key)

@app.route('/course/<int:course_id>/lesson/<int:lesson_id>')
def lesson_view(course_id, lesson_id):
    """Lesson viewing page with embedded video"""
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if not course.is_active:
        abort(404)
    
    clerk_user_id = get_clerk_user_id()
    
    if not clerk_user_id:
        flash('Please sign in to access this course.', 'warning')
        return redirect(url_for('clerk_login', next=request.url))
    
    has_access = UserCourseAccess.has_access(clerk_user_id, course_id)
    
    if not has_access:
        flash('You need to purchase this course to access lessons.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))
    
    lesson_data = lesson.to_dict()
    lesson_data['embed_url'] = get_youtube_embed_url(lesson.video_url) if lesson.video_url else None
    
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
    """Initiate course purchase"""
    course = Course.query.get_or_404(course_id)
    
    clerk_user_id = get_clerk_user_id()
    
    if not clerk_user_id:
        return jsonify({'success': False, 'message': 'Please sign in first'}), 401
    
    has_access = UserCourseAccess.has_access(clerk_user_id, course_id)
    if has_access:
        return jsonify({'success': False, 'message': 'You already have access to this course'}), 400
    
    try:
        amount = course.price * 100
        
        order = razorpay_client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': 1
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
    """Verify course payment and grant access"""
    data = request.get_json()
    
    payment_id = data.get('razorpay_payment_id')
    order_id = data.get('razorpay_order_id')
    signature = data.get('razorpay_signature')
    course_id = data.get('course_id')
    
    clerk_user_id = get_clerk_user_id()
    
    if not clerk_user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401
    
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
            amount_paid=course.price
        )
        db.session.add(access)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment verified! You now have access to the course.',
            'redirect_url': url_for('course_detail', course_id=course_id)
        })
    
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
