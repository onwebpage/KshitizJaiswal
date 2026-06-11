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

    // Initialize reel carousel auto-scroll
    function initReelCarousel() {
        const carousel = document.getElementById('reelCarousel');
        if (!carousel) return;

        // Pause animation on hover
        carousel.addEventListener('mouseenter', function() {
            this.style.animationPlayState = 'paused';
        });

        carousel.addEventListener('mouseleave', function() {
            this.style.animationPlayState = 'running';
        });

        // Handle reel clicks with loading state
        const reelLinks = document.querySelectorAll('.reel-link');
        reelLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const overlay = this.querySelector('.reel-overlay');
                if (overlay) {
                    overlay.innerHTML = '<i class="fas fa-spinner fa-spin"></i><h6>Loading...</h6>';
                }
            });
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

    // Initialize scroll animations
    function initScrollAnimations() {
        const observerOptions = {
            threshold: 0.15,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                }
            });
        }, observerOptions);

        // Observe elements for fade-in animation
        const fadeElements = document.querySelectorAll('.fade-in-section, section, .hero-section');
        fadeElements.forEach(el => {
            if (!el.classList.contains('fade-in-section')) {
                el.classList.add('fade-in-section');
            }
            observer.observe(el);
        });

        // Observe elements for slide animations
        const slideLeftElements = document.querySelectorAll('.slide-in-left');
        slideLeftElements.forEach(el => observer.observe(el));

        const slideRightElements = document.querySelectorAll('.slide-in-right');
        slideRightElements.forEach(el => observer.observe(el));

        // Observe elements for scale animation
        const scaleElements = document.querySelectorAll('.scale-in, .reel-item, .resource-card, .opinion-card, .show-card, .contact-card');
        scaleElements.forEach(el => {
            if (!el.classList.contains('scale-in')) {
                el.classList.add('scale-in');
            }
            observer.observe(el);
        });
    }

    // Initialize disclaimer popup
    function initDisclaimerPopup() {
        // Don't show disclaimer popup on admin pages
        if (window.location.pathname.startsWith('/admin')) {
            return;
        }
        
        // Check if already shown and accepted
        if (localStorage.getItem('disclaimerAccepted') === 'true') {
            disclaimerShown = true;
            return;
        }
        
        if (disclaimerShown) return;
        
        setTimeout(() => {
            const disclaimerModal = new bootstrap.Modal(document.getElementById('disclaimerModal'));
            disclaimerModal.show();
            disclaimerShown = true;
            
            // Track disclaimer view with GTM
            if (window.dataLayer) {
                window.dataLayer.push({
                    'event': 'disclaimer_shown'
                });
            }
        }, 7000);

        // Add event listener for when user accepts disclaimer
        const disclaimerModal = document.getElementById('disclaimerModal');
        const acceptButton = disclaimerModal.querySelector('[data-bs-dismiss="modal"]');
        
        if (acceptButton) {
            acceptButton.addEventListener('click', function() {
                localStorage.setItem('disclaimerAccepted', 'true');
                disclaimerShown = true;
                
                // Track disclaimer acceptance with GTM
                if (window.dataLayer) {
                    window.dataLayer.push({
                        'event': 'disclaimer_accepted'
                    });
                }
            });
        }
    }

    // Initialize newsletter popup
    function initNewsletterPopup() {
        // Don't show newsletter popup on admin pages
        if (window.location.pathname.startsWith('/admin')) {
            return;
        }
        
        // Check if already subscribed or dismissed
        if (localStorage.getItem('newsletterSubscribed') === 'true' || 
            localStorage.getItem('newsletterDismissed') === 'true') {
            newsletterShown = true;
            return;
        }
        
        if (newsletterShown) return;
        
        setTimeout(() => {
            const newsletterModal = new bootstrap.Modal(document.getElementById('newsletterModal'));
            newsletterModal.show();
            newsletterShown = true;
            
            // Track newsletter popup view with GTM
            if (window.dataLayer) {
                window.dataLayer.push({
                    'event': 'newsletter_popup_shown'
                });
            }
            
            // Track with Microsoft Clarity
            if (window.clarity) {
                window.clarity('event', 'newsletter_popup_shown');
            }
            
            // Track with Meta Pixel
            if (window.fbq) {
                window.fbq('trackCustom', 'NewsletterPopupShown');
            }
        }, 40000);

        // Add event listener for when modal is dismissed
        const newsletterModalEl = document.getElementById('newsletterModal');
        if (newsletterModalEl) {
            newsletterModalEl.addEventListener('hidden.bs.modal', function () {
                if (!localStorage.getItem('newsletterSubscribed')) {
                    localStorage.setItem('newsletterDismissed', 'true');
                    
                    // Track dismissal with GTM
                    if (window.dataLayer) {
                        window.dataLayer.push({
                            'event': 'newsletter_popup_dismissed'
                        });
                    }
                }
            });
        }

        // Add event listener for successful subscription
        const newsletterForm = document.getElementById('newsletterPopupForm');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', function() {
                localStorage.setItem('newsletterSubscribed', 'true');
                
                // Track subscription with GTM
                if (window.dataLayer) {
                    window.dataLayer.push({
                        'event': 'newsletter_subscribed',
                        'subscription_source': 'popup'
                    });
                }
                
                // Track with Microsoft Clarity
                if (window.clarity) {
                    window.clarity('event', 'newsletter_subscribed');
                }
                
                // Track with Meta Pixel
                if (window.fbq) {
                    window.fbq('track', 'Lead');
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
                    shareUrl = `https://wa.me/?text=${title}%20${url}`;
                }
                
                if (shareUrl) {
                    window.open(shareUrl, '_blank', 'width=600,height=400');
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

    // Handle visibility change (tab switching)
    document.addEventListener('visibilitychange', function() {
        const carousel = document.getElementById('reelCarousel');
        if (carousel) {
            if (document.hidden) {
                carousel.style.animationPlayState = 'paused';
            } else {
                carousel.style.animationPlayState = 'running';
            }
        }
    });

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

    // Initialize payment system
    function initPaymentSystem() {
        // Make initiatePayment available globally
        window.initiatePayment = function(amount) {
            if (!window.razorpayKey || window.razorpayKey === 'rzp_test_dummy_key') {
                showNotification('Payment system is not configured. Please contact the administrator.', 'error');
                return;
            }

            // Show loading
            showNotification('Preparing payment...', 'info');

            // Create payment order
            fetch('/create_payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: amount
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    openRazorpayCheckout(data, amount);
                } else {
                    showNotification(data.message || 'Failed to create payment order', 'error');
                }
            })
            .catch(error => {
                console.error('Payment error:', error);
                showNotification('Payment initialization failed. Please try again.', 'error');
            });
        };
    }

    // Open Razorpay checkout
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
                    if (data.success) {
                        showNotification('Payment successful! Thank you for your support! ❤️', 'success');
                    } else {
                        showNotification('Payment received but verification failed. Please contact support.', 'warning');
                    }
                })
                .catch(() => {
                    showNotification('Payment received! Thank you for your support!', 'success');
                });
            },
            prefill: {
                name: '',
                email: '',
                contact: ''
            },
            notes: {
                address: 'Support for Kshitiz Jaiswal'
            },
            theme: {
                color: '#6366f1'
            },
            modal: {
                ondismiss: function() {
                    showNotification('Payment cancelled', 'info');
                }
            }
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
