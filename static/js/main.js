// Main JavaScript for Kshitiz Jaiswal Website
// Handles interactive features, animations, and user interactions

(function() {
    'use strict';

    // Global variables
    let disclaimerShown = false;
    let newsletterShown = false;
    let isExiting = false;

    // DOM Content Loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeWebsite();
    });

    // Initialize all website functionality
    function initializeWebsite() {
        initSmoothScrolling();
        initReelCarousel();
        initPollVoting();
        initNewsletterForm();
        initScrollAnimations();
        initDisclaimerPopup();
        initNewsletterPopup();
        initShareButtons();
        initNavbarEffects();
        initFormValidations();
        initPaymentSystem();
    }

    // Smooth scrolling for anchor links
    function initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    const navbarHeight = 76; // Account for fixed navbar
                    const targetPosition = target.offsetTop - navbarHeight;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    // Initialize reel carousel — JS-driven infinite loop with drag, swipe,
    // momentum, and auto-resume after user interaction.
    function initReelCarousel() {
        var carousel = document.getElementById('reelCarousel');
        if (!carousel) return;

        // Kill any residual CSS animation so JS owns the transform entirely
        carousel.style.animation = 'none';

        var SPEED        = 0.15;   // px per ms — auto-scroll pace
        var RESUME_DELAY = 3000;   // ms of inactivity before auto-scroll resumes
        var FRICTION     = 0.92;   // momentum decay per frame (lower = stops faster)
        var MIN_VELOCITY = 0.05;   // px/ms below which momentum is ignored

        var autoScrollPaused = false; // true while user is hovering (desktop)
        var dragging         = false;
        var touchLocked      = null;  // null | 'h' | 'v' — detected axis after touchstart
        var dragStartClient  = 0;
        var dragStartY       = 0;
        var dragStartX       = 0;
        var currentX         = 0;
        var lastTime         = null;
        var velocity         = 0;    // px/ms — momentum after drag release
        var lastDragX        = 0;
        var lastDragTime     = 0;
        var resumeTimer      = null;
        var oneSetWidth      = 0;

        // ── Clone real cards once for the seamless loop ────────────────────
        requestAnimationFrame(function() {
            var originals = Array.prototype.slice.call(carousel.children);
            if (!originals.length) return;

            oneSetWidth = carousel.scrollWidth;

            originals.forEach(function(card) {
                var clone = card.cloneNode(true);
                clone.setAttribute('aria-hidden', 'true');
                clone.setAttribute('tabindex', '-1');
                clone.querySelectorAll('a, button').forEach(function(el) {
                    el.setAttribute('tabindex', '-1');
                });
                carousel.appendChild(clone);
            });

            currentX = -oneSetWidth;
            applyTransform();
            requestAnimationFrame(tick);
        });

        function applyTransform() {
            carousel.style.transform = 'translateX(' + currentX + 'px)';
        }

        function wrapX(x) {
            if (x >= 0)           x -= oneSetWidth;
            if (x < -oneSetWidth) x += oneSetWidth;
            return x;
        }

        function scheduleResume() {
            clearTimeout(resumeTimer);
            resumeTimer = setTimeout(function() {
                if (!dragging) {
                    velocity  = 0;
                    lastTime  = null;
                }
            }, RESUME_DELAY);
        }

        function tick(timestamp) {
            if (!lastTime) lastTime = timestamp;
            var dt = Math.min(timestamp - lastTime, 50);
            lastTime = timestamp;

            if (!dragging && oneSetWidth > 0) {
                if (Math.abs(velocity) > MIN_VELOCITY) {
                    // Momentum phase — user just released a drag
                    currentX  = wrapX(currentX + velocity * dt);
                    velocity *= Math.pow(FRICTION, dt / 16); // frame-rate-independent decay
                    applyTransform();
                } else if (!autoScrollPaused) {
                    // Normal auto-scroll
                    currentX = wrapX(currentX + SPEED * dt);
                    applyTransform();
                }
            }

            requestAnimationFrame(tick);
        }

        // ── Hover pause (desktop only) ─────────────────────────────────────
        carousel.addEventListener('mouseenter', function() {
            if (!dragging) autoScrollPaused = true;
        });
        carousel.addEventListener('mouseleave', function() {
            autoScrollPaused = false;
            lastTime = null;
        });

        // ── Mouse drag ─────────────────────────────────────────────────────
        carousel.addEventListener('mousedown', function(e) {
            dragging        = true;
            autoScrollPaused = false;
            dragStartClient = e.clientX;
            dragStartX      = currentX;
            lastDragX       = e.clientX;
            lastDragTime    = performance.now();
            velocity        = 0;
            carousel.style.cursor = 'grabbing';
            clearTimeout(resumeTimer);
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            var now  = performance.now();
            var dx   = e.clientX - lastDragX;
            var dt   = now - lastDragTime || 1;
            velocity    = dx / dt;          // track live velocity
            lastDragX   = e.clientX;
            lastDragTime = now;

            currentX = wrapX(dragStartX + (e.clientX - dragStartClient));
            applyTransform();
        });

        document.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            carousel.style.cursor = '';
            // velocity is already set — momentum will carry it forward
            scheduleResume();
            lastTime = null;
        });

        // ── Touch swipe (mobile) ───────────────────────────────────────────
        carousel.addEventListener('touchstart', function(e) {
            dragging        = true;
            touchLocked     = null;
            dragStartClient = e.touches[0].clientX;
            dragStartY      = e.touches[0].clientY;
            dragStartX      = currentX;
            lastDragX       = e.touches[0].clientX;
            lastDragTime    = performance.now();
            velocity        = 0;
            clearTimeout(resumeTimer);
        }, { passive: true });

        carousel.addEventListener('touchmove', function(e) {
            if (!dragging) return;
            var tx = e.touches[0].clientX;
            var ty = e.touches[0].clientY;

            // Detect scroll axis on the first meaningful move
            if (touchLocked === null) {
                var absH = Math.abs(tx - dragStartClient);
                var absV = Math.abs(ty - dragStartY);
                if (absH < 3 && absV < 3) return; // too small to decide yet
                touchLocked = absH >= absV ? 'h' : 'v';
            }

            // Vertical scroll — let the browser handle it
            if (touchLocked === 'v') return;

            // Horizontal swipe — take control
            e.preventDefault();

            var now  = performance.now();
            var dx   = tx - lastDragX;
            var dt   = now - lastDragTime || 1;
            velocity    = dx / dt;
            lastDragX   = tx;
            lastDragTime = now;

            currentX = wrapX(dragStartX + (tx - dragStartClient));
            applyTransform();
        }, { passive: false }); // passive:false so we can preventDefault on horizontal

        carousel.addEventListener('touchend', function() {
            dragging    = false;
            touchLocked = null;
            scheduleResume();
            lastTime = null;
        }, { passive: true });

        // ── Tab visibility ─────────────────────────────────────────────────
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                autoScrollPaused = true;
            } else {
                autoScrollPaused = false;
                lastTime = null;
            }
        });
    }

    // Initialize poll voting functionality
    function initPollVoting() {
        const pollOptions = document.querySelectorAll('.poll-option');
        
        pollOptions.forEach(option => {
            option.addEventListener('click', function() {
                const opinionId = parseInt(this.dataset.opinionId);
                const optionIndex = parseInt(this.dataset.optionIndex);
                
                if (isNaN(opinionId) || isNaN(optionIndex)) {
                    showNotification('Invalid poll option', 'error');
                    return;
                }

                // Check if already voted (simple client-side check)
                const pollSection = this.closest('.poll-section');
                if (pollSection.classList.contains('voted')) {
                    showNotification('You have already voted on this poll', 'warning');
                    return;
                }

                // Disable all options in this poll
                const allOptions = pollSection.querySelectorAll('.poll-option');
                allOptions.forEach(opt => opt.style.pointerEvents = 'none');
                
                // Add loading state
                this.classList.add('loading');
                
                // Submit vote
                submitPollVote(opinionId, optionIndex, pollSection);
            });
        });
    }

    // Submit poll vote via form submission (not AJAX per guidelines)
    function submitPollVote(opinionId, optionIndex, pollSection) {
        const form = document.getElementById('pollForm');
        if (!form) {
            showNotification('Poll form not found', 'error');
            return;
        }

        // Set form values
        const opinionIdField = form.querySelector('[name="opinion_id"]');
        const optionIndexField = form.querySelector('[name="option_index"]');
        
        if (opinionIdField) opinionIdField.value = opinionId;
        if (optionIndexField) optionIndexField.value = optionIndex;

        // Create and submit form via AJAX (exception for specialized rendering)
        const formData = new FormData(form);
        
        fetch('/vote', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message, 'success');
                pollSection.classList.add('voted');
                
                // Refresh the page to show updated results
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(data.message || 'Error voting', 'error');
                // Re-enable options
                const allOptions = pollSection.querySelectorAll('.poll-option');
                allOptions.forEach(opt => opt.style.pointerEvents = 'auto');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Network error. Please try again.', 'error');
            // Re-enable options
            const allOptions = pollSection.querySelectorAll('.poll-option');
            allOptions.forEach(opt => opt.style.pointerEvents = 'auto');
        })
        .finally(() => {
            // Remove loading state
            const loadingOption = pollSection.querySelector('.poll-option.loading');
            if (loadingOption) {
                loadingOption.classList.remove('loading');
            }
        });
    }

    // Initialize newsletter form
    function initNewsletterForm() {
        const form = document.querySelector('.newsletter-form');
        if (!form) return;

        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Add loading state
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Subscribing...';
            submitBtn.disabled = true;
            
            // Form will submit normally, this just provides user feedback
            setTimeout(() => {
                if (submitBtn) {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            }, 3000);
        });
    }

    // Initialize scroll animations — only on explicit card/block elements, never on <section> tags
    function initScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -60px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target); // stop observing once visible
                }
            });
        }, observerOptions);

        // Only fade-in elements that already have the class — never add it to <section> or hero
        const explicitFadeEls = document.querySelectorAll('.fade-in-section');
        explicitFadeEls.forEach(el => observer.observe(el));

        // Slide animations
        document.querySelectorAll('.slide-in-left, .slide-in-right').forEach(el => observer.observe(el));

        // Scale animations — only explicit .scale-in elements, not broad selectors
        document.querySelectorAll('.scale-in').forEach(el => observer.observe(el));
    }

    // Initialize disclaimer popup
    function initDisclaimerPopup() {
        // Don't show on admin pages
        if (window.location.pathname.startsWith('/admin')) return;

        // Already accepted
        try {
            if (localStorage.getItem('disclaimerAccepted') === 'true') {
                disclaimerShown = true;
                return;
            }
        } catch(e) {}

        if (disclaimerShown) return;

        // Show custom popup after 7 seconds
        setTimeout(function() {
            if (disclaimerShown) return;
            disclaimerShown = true;
            if (typeof _showDisclaimerPopup === 'function') {
                _showDisclaimerPopup();
            }
            if (window.dataLayer) {
                window.dataLayer.push({ 'event': 'disclaimer_shown' });
            }
        }, 7000);
    }

    // Initialize newsletter popup
    function initNewsletterPopup() {
        // Don't show newsletter popup on admin pages
        if (window.location.pathname.startsWith('/admin')) return;

        // Session-only: don't show again if already dismissed or subscribed this session
        try {
            if (sessionStorage.getItem('nlDismissed') === '1' ||
                sessionStorage.getItem('nlSubscribed') === '1') {
                newsletterShown = true;
                return;
            }
        } catch(e) {}

        // Also respect permanent subscription flag
        try {
            if (localStorage.getItem('newsletterSubscribed') === 'true') {
                newsletterShown = true;
                return;
            }
        } catch(e) {}

        if (newsletterShown) return;

        // Show after 45 seconds
        setTimeout(function() {
            if (newsletterShown) return;
            newsletterShown = true;
            if (typeof _showNewsletterPopup === 'function') {
                _showNewsletterPopup();
            }
            if (window.dataLayer) window.dataLayer.push({ 'event': 'newsletter_popup_shown' });
            if (window.clarity) window.clarity('event', 'newsletter_popup_shown');
            if (window.fbq) window.fbq('trackCustom', 'NewsletterPopupShown');
        }, 45000);

        // AJAX form submission
        const newsletterForm = document.getElementById('newsletterPopupForm');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', async function(e) {
                e.preventDefault();

                const name = document.getElementById('popupName')?.value?.trim();
                const email = document.getElementById('popupEmail')?.value?.trim();
                const phone = document.getElementById('popupPhone')?.value?.trim() || '';
                const place = document.getElementById('popupPlace')?.value?.trim();
                const age = document.getElementById('popupAge')?.value?.trim();
                const errDiv = document.getElementById('newsletterPopupError');
                const submitBtn = document.getElementById('newsletterPopupSubmit');

                if (!name || !email || !place || !age) {
                    if (errDiv) { errDiv.textContent = 'Please fill in all fields.'; errDiv.style.display = 'block'; }
                    return;
                }

                if (phone && !/^[0-9+\-\s()]{7,20}$/.test(phone)) {
                    if (errDiv) { errDiv.textContent = 'Please enter a valid phone number.'; errDiv.style.display = 'block'; }
                    return;
                }

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i>Subscribing…';
                if (errDiv) errDiv.style.display = 'none';

                const formData = new FormData();
                formData.append('name', name);
                formData.append('email', email);
                formData.append('phone', phone);
                formData.append('place', place);
                formData.append('age', age);

                const csrfToken = document.querySelector('[name=csrf_token]')?.value ||
                                  document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('csrf_token='))?.split('=')[1] || '';
                if (csrfToken) formData.append('csrf_token', csrfToken);

                try {
                    const resp = await fetch('/newsletter', {
                        method: 'POST',
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                        body: formData
                    });
                    const data = await resp.json();

                    if (data.success) {
                        try { localStorage.setItem('newsletterSubscribed', 'true'); } catch(e) {}
                        try { sessionStorage.setItem('nlSubscribed', '1'); } catch(e) {}
                        newsletterForm.style.display = 'none';
                        const successEl = document.getElementById('newsletterPopupSuccess');
                        if (successEl) successEl.style.display = 'block';
                        // Auto-close after 3s
                        setTimeout(function() { dismissNewsletterPopup(); }, 3000);
                        if (window.dataLayer) window.dataLayer.push({ 'event': 'newsletter_subscribed', 'subscription_source': 'popup' });
                        if (window.clarity) window.clarity('event', 'newsletter_subscribed');
                        if (window.fbq) window.fbq('track', 'Lead');
                    } else {
                        if (errDiv) { errDiv.textContent = data.message || 'Something went wrong. Please try again.'; errDiv.style.display = 'block'; }
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right:6px;"></i>Subscribe Free';
                    }
                } catch (err) {
                    if (errDiv) { errDiv.textContent = 'Connection error. Please try again.'; errDiv.style.display = 'block'; }
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right:6px;"></i>Subscribe Free';
                }
            });
        }
    }


    // Initialize share buttons
    function initShareButtons() {
        const shareButtons = document.querySelectorAll('.share-btn');
        
        shareButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const url = encodeURIComponent(window.location.href);
                const title = encodeURIComponent(document.title);
                let shareUrl = '';
                
                if (this.classList.contains('twitter')) {
                    shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
                } else if (this.classList.contains('facebook')) {
                    shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
                } else if (this.classList.contains('linkedin')) {
                    shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${url}`;
                } else if (this.classList.contains('whatsapp')) {
                    shareUrl = `https://api.whatsapp.com/send?text=${title}%20${url}`;
                }
                
                if (shareUrl) {
                    if (this.classList.contains('whatsapp') && window.openWhatsApp) {
                        window.openWhatsApp(shareUrl);
                    } else {
                        window.open(shareUrl, '_blank', 'width=600,height=400');
                    }
                }
            });
        });
    }

    // Initialize navbar effects
    function initNavbarEffects() {
        const navbar = document.querySelector('.custom-navbar');
        if (!navbar) return;
        
        window.addEventListener('scroll', throttle(function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }, 100));
    }

    // Initialize form validations
    function initFormValidations() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');
            
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    validateField(this);
                });
                
                input.addEventListener('input', function() {
                    // Clear error state on input
                    this.classList.remove('is-invalid');
                    const feedback = this.parentNode.querySelector('.invalid-feedback');
                    if (feedback) {
                        feedback.remove();
                    }
                });
            });
        });
    }

    // Validate individual form field
    function validateField(field) {
        const value = field.value.trim();
        const type = field.type;
        const required = field.hasAttribute('required');
        let isValid = true;
        let message = '';

        // Required validation
        if (required && !value) {
            isValid = false;
            message = 'This field is required';
        }

        // Email validation
        if (type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                message = 'Please enter a valid email address';
            }
        }

        // Age validation
        if (field.name === 'age' && value) {
            const age = parseInt(value);
            if (age < 13 || age > 120) {
                isValid = false;
                message = 'Age must be between 13 and 120';
            }
        }

        // Update field state
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            showFieldError(field, message);
        }

        return isValid;
    }

    // Show field error message
    function showFieldError(field, message) {
        // Remove existing error message
        const existingFeedback = field.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        // Add new error message
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentNode.appendChild(feedback);
    }


    // Show notification
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show notification-toast`;
        notification.style.cssText = `
            position: fixed;
            top: 90px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Visibility change for carousel is handled inside initReelCarousel

    // Handle window resize
    window.addEventListener('resize', debounce(function() {
        // Recalculate any dynamic elements if needed
        console.log('Window resized');
    }, 250));

    // Handle page unload
    window.addEventListener('beforeunload', function() {
        // Clean up if necessary
        isExiting = true;
    });

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        // ESC key closes modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) modalInstance.hide();
            });
        }
    });

    // Initialize payment system — only provide a fallback if no page-level handler is defined
    function initPaymentSystem() {
        // Only set window.initiatePayment if the page hasn't already defined one
        if (typeof window.initiatePayment === 'undefined') {
            window.initiatePayment = function(amount) {
                if (!window.razorpayKey) {
                    showNotification('Payment system is not configured yet. Please contact the administrator.', 'error');
                    return;
                }
                showNotification('Preparing payment...', 'info');
                fetch('/create_payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount: amount })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        openRazorpayCheckout(data, amount);
                    } else {
                        showNotification(data.message || 'Failed to create payment order', 'error');
                    }
                })
                .catch(() => {
                    showNotification('Payment initialization failed. Please try again.', 'error');
                });
            };
        }
    }

    // Open Razorpay checkout (fallback helper)
    function openRazorpayCheckout(orderData, amount) {
        const options = {
            key: window.razorpayKey,
            amount: orderData.amount,
            currency: orderData.currency,
            name: 'Kshitiz Jaiswal',
            description: `Support - ₹${amount}`,
            order_id: orderData.order_id,
            handler: function(response) {
                fetch('/support/payment/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_signature: response.razorpay_signature
                    })
                })
                .then(res => res.json())
                .then(data => {
                    showNotification(data.success ? 'Payment successful! Thank you for your support! ❤️' : 'Payment received but verification failed. Please contact support.', data.success ? 'success' : 'warning');
                })
                .catch(() => {
                    showNotification('Payment received! Thank you for your support!', 'success');
                });
            },
            prefill: { name: '', email: '', contact: '' },
            theme: { color: '#CC0000' },
            modal: { ondismiss: function() { showNotification('Payment cancelled', 'info'); } }
        };
        try {
            const rzp = new Razorpay(options);
            rzp.open();
        } catch (error) {
            console.error('Razorpay initialization error:', error);
            showNotification('Payment system error. Please try again later.', 'error');
        }
    }

    // Console log for debugging
    console.log('Kshitiz Jaiswal Website - Main JS Loaded Successfully');
    
})();
