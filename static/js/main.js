// Main JavaScript for Kshitiz Jaiswal Website
// Handles interactive features, animations, and user interactions

(function() {
    'use strict';

    // Global variables
    let disclaimerShown = false;
    let exitIntentShown = false;
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
        initExitIntentPopup();
        initShareButtons();
        initNavbarEffects();
        initFormValidations();
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
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, observerOptions);

        // Observe elements for animation
        const animatedElements = document.querySelectorAll('.reel-item, .resource-card, .opinion-card, .show-card, .contact-card');
        animatedElements.forEach(el => {
            el.classList.add('fade-in');
            observer.observe(el);
        });
    }

    // Initialize disclaimer popup
    function initDisclaimerPopup() {
        if (disclaimerShown) return;
        
        setTimeout(() => {
            const disclaimerModal = new bootstrap.Modal(document.getElementById('disclaimerModal'));
            disclaimerModal.show();
            disclaimerShown = true;
            
            // Store in localStorage to avoid showing again in same session
            localStorage.setItem('disclaimerShown', 'true');
        }, 7000);

        // Check if already shown in this session
        if (localStorage.getItem('disclaimerShown')) {
            disclaimerShown = true;
        }
    }

    // Initialize exit intent popup
    function initExitIntentPopup() {
        let mouseY = 0;
        
        document.addEventListener('mousemove', function(e) {
            mouseY = e.clientY;
        });

        document.addEventListener('mouseleave', function(e) {
            if (mouseY < 100 && !exitIntentShown && !disclaimerShown) {
                const exitModal = new bootstrap.Modal(document.getElementById('exitSupportModal'));
                exitModal.show();
                exitIntentShown = true;
            }
        });

        // Also trigger on scroll up near top
        let lastScrollY = window.scrollY;
        window.addEventListener('scroll', function() {
            if (window.scrollY < 100 && window.scrollY < lastScrollY && !exitIntentShown) {
                // User scrolled up near top - potential exit intent
                if (Math.random() < 0.3) { // 30% chance to avoid being annoying
                    const exitModal = new bootstrap.Modal(document.getElementById('exitSupportModal'));
                    exitModal.show();
                    exitIntentShown = true;
                }
            }
            lastScrollY = window.scrollY;
        });
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
        
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.style.background = 'rgba(15, 23, 42, 0.98)';
                navbar.style.backdropFilter = 'blur(15px)';
            } else {
                navbar.style.background = 'rgba(15, 23, 42, 0.95)';
                navbar.style.backdropFilter = 'blur(10px)';
            }
        });
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

    // Razorpay payment initialization
    window.initiatePayment = function(amount) {
        const loadingBtn = event.target;
        const originalText = loadingBtn.innerHTML;
        
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        loadingBtn.disabled = true;

        // Create payment order (exception for specialized payment processing)
        fetch('/create_payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amount: amount })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const options = {
                    key: window.razorpayKey,
                    amount: data.amount,
                    currency: data.currency,
                    order_id: data.order_id,
                    name: 'Kshitiz Jaiswal',
                    description: `Weekly Support - ₹${amount}`,
                    image: '/static/images/logo.png', // Add logo if available
                    handler: function(response) {
                        showNotification('Payment successful! Thank you for your support.', 'success');
                        
                        // Close modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('exitSupportModal'));
                        if (modal) modal.hide();
                        
                        // Redirect to thank you page or reload
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    },
                    prefill: {
                        name: '',
                        email: '',
                        contact: ''
                    },
                    theme: {
                        color: '#6366f1'
                    },
                    modal: {
                        ondismiss: function() {
                            loadingBtn.innerHTML = originalText;
                            loadingBtn.disabled = false;
                        }
                    }
                };

                const razorpay = new Razorpay(options);
                razorpay.open();
            } else {
                showNotification(data.message || 'Payment initialization failed', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Network error. Please try again.', 'error');
        })
        .finally(() => {
            loadingBtn.innerHTML = originalText;
            loadingBtn.disabled = false;
        });
    };

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

    // Console log for debugging
    console.log('Kshitiz Jaiswal Website - Main JS Loaded Successfully');
    
})();
