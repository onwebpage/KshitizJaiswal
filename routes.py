from flask import render_template, request, jsonify, redirect, url_for, flash, session
from app import app
from models import DataManager, AdminUser
from forms import NewsletterForm, PollVoteForm, AdminLoginForm, ReelForm, OpinionForm
from utils import save_uploaded_file, calculate_poll_percentages
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
    
    return render_template('index.html', 
                         content=content, 
                         newsletter_form=newsletter_form,
                         poll_form=poll_form,
                         razorpay_key=os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummy_key'))

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
        amount = int(request.json.get('amount', 10)) * 100  # Convert to paise
        
        order_data = {
            'amount': amount,
            'currency': 'INR',
            'receipt': f'support_{amount//100}',
            'payment_capture': 1
        }
        
        order = razorpay_client.order.create(data=order_data)
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
    
    content = DataManager.get_content()
    subscribers = DataManager.load_json('data/subscribers.json')
    
    return render_template('admin/dashboard.html', 
                         content=content, 
                         subscribers=subscribers.get('subscribers', []))

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
        content = DataManager.get_content()
        
        # Generate new ID
        new_id = max([r['id'] for r in content['reels']], default=0) + 1
        
        # Handle thumbnail upload
        thumbnail_url = None
        if form.thumbnail.data:
            thumbnail_url = save_uploaded_file(form.thumbnail.data, 'reels')
        
        # Process sources
        sources = [s.strip() for s in form.sources.data.split('\n') if s.strip()]
        
        new_reel = {
            'id': new_id,
            'title': form.title.data,
            'thumbnail': thumbnail_url or '',
            'video_url': form.video_url.data or '',
            'behind_thought': form.behind_thought.data,
            'sources': sources,
            'extra_context': form.extra_context.data or ''
        }
        
        content['reels'].append(new_reel)
        DataManager.save_content(content)
        
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
        content = DataManager.get_content()
        
        # Generate new ID
        new_id = max([o['id'] for o in content['opinions']], default=0) + 1
        
        poll_options = [form.poll_option1.data, form.poll_option2.data]
        if form.poll_option3.data:
            poll_options.append(form.poll_option3.data)
        
        new_opinion = {
            'id': new_id,
            'title': form.title.data,
            'position': form.position.data,
            'description': form.description.data or '',
            'poll_question': form.poll_question.data,
            'poll_options': poll_options,
            'votes': [0] * len(poll_options)
        }
        
        content['opinions'].append(new_opinion)
        DataManager.save_content(content)
        
        flash('Opinion added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/opinion_form.html', form=form, title='Add New Opinion')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
