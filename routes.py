from flask import render_template, request, jsonify, redirect, url_for, flash, session
from app import app
from models import DataManager, AdminUser
from forms import NewsletterForm, PollVoteForm, AdminLoginForm, ReelForm, OpinionForm, HeroContentForm, PaymentSettingsForm
from utils import save_uploaded_file, calculate_poll_percentages, get_youtube_embed_url
import razorpay
import os

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
    
    # Calculate poll percentages
    for opinion in content['opinions']:
        opinion['percentages'] = calculate_poll_percentages(opinion['votes'])
        opinion['total_votes'] = sum(opinion['votes'])
    
    # Get Razorpay settings from database
    from database import SiteContent
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
                         razorpay_key=razorpay_key)

@app.route('/reel/<int:reel_id>')
def reel_detail(reel_id):
    """Reel detail page"""
    content = DataManager.get_content()
    reel = None
    
    for r in content['reels']:
        if r['id'] == reel_id:
            reel = r
            break
    
    if not reel:
        flash('Reel not found!', 'error')
        return redirect(url_for('index'))
    
    # Process YouTube URL for embedding
    if reel.get('video_url'):
        reel['embed_url'] = get_youtube_embed_url(reel['video_url'])
    
    return render_template('reel_detail.html', reel=reel)

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

@app.route('/create_payment', methods=['POST'])
def create_payment():
    """Create Razorpay payment order"""
    try:
        # Get Razorpay settings from database
        from database import SiteContent
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
    
    from database import Subscriber
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
        from database import Reel, db
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
            extra_context=form.extra_context.data or ''
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
        from database import Opinion, db
        import json
        
        poll_options = [form.poll_option1.data, form.poll_option2.data]
        if form.poll_option3.data:
            poll_options.append(form.poll_option3.data)
        
        new_opinion = Opinion(
            title=form.title.data,
            position=form.position.data,
            description=form.description.data or '',
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
    
    from database import Reel, db
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
    
    return render_template('admin/reel_form.html', form=form, title='Edit Reel', reel=reel)

@app.route('/admin/reel/<int:reel_id>/delete', methods=['POST'])
def admin_delete_reel(reel_id):
    """Delete reel"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from database import Reel, db
    
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
    
    from database import Opinion, db
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
    
    from database import Opinion, db
    
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
    
    from database import Opinion
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
    
    from database import SiteContent, db
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
        # Handle banner image upload
        banner_url = current_hero.get('banner_url', '')
        if form.banner_image.data:
            uploaded_path = save_uploaded_file(form.banner_image.data, 'hero')
            if uploaded_path:
                banner_url = uploaded_path
        elif form.banner_url.data:
            banner_url = form.banner_url.data
        
        # Update hero content
        updated_hero = {
            "name": form.name.data,
            "tagline": form.tagline.data,
            "banner_url": banner_url
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
    
    return render_template('admin/hero_form.html', form=form, title='Hero Content', current_hero=current_hero)

@app.route('/admin/payment-settings', methods=['GET', 'POST'])
def admin_payment_settings():
    """Manage Razorpay payment settings"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    from database import SiteContent, db
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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
