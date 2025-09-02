from flask import render_template, request, jsonify, redirect, url_for, flash, session, abort
from app import app, db
from models import DataManager, AdminUser, SiteContent, Reel, Opinion, Subscriber, SubscriptionTier
from forms import NewsletterForm, PollVoteForm, AdminLoginForm, ReelForm, OpinionForm, HeroContentForm, PaymentSettingsForm, SubscriptionTierForm
from utils import save_uploaded_file, calculate_poll_percentages, get_youtube_embed_url
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
        # already imported - Opinion, db
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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
