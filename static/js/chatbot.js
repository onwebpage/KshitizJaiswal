/* ═══════════════════════════════════════════════════════════
   Kshitiz Chatbot Widget — chatbot.js
   No external AI API — keyword matching + FAQ database
   ═══════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    // ── Config (injected by server via window.chatbotConfig) ──────────
    const CFG = window.chatbotConfig || {};
    const BOT_NAME    = CFG.name         || 'Kshitiz Assistant';
    const GREETING    = CFG.greeting     || 'Namaste! \uD83D\uDE4F I\'m Kshitiz\'s assistant. Ask me anything about courses, reels, or how to support Kshitiz!';
    const QUICK_INIT  = CFG.quickReplies && CFG.quickReplies.length
                        ? CFG.quickReplies
                        : ['\uD83D\uDCDA View Courses', '\uD83D\uDCB0 Course Pricing', '\uD83C\uDF9E Watch Reels', '\uD83D\uDCE9 Subscribe', '\uD83D\uDCAC Get Support'];

    // ── State ─────────────────────────────────────────────────────────
    var isOpen    = false;
    var greeted   = false;

    // ── DOM refs ──────────────────────────────────────────────────────
    var widget    = document.getElementById('chatbot-widget');
    var winEl     = document.getElementById('chatbot-window');
    var msgsEl    = document.getElementById('chatbot-messages');
    var typingEl  = document.getElementById('chatbot-typing');
    var qrEl      = document.getElementById('chatbot-quick-replies');
    var inputEl   = document.getElementById('chatbot-input');
    var notifEl   = document.getElementById('chatbot-notif');
    var closeBtn  = document.getElementById('chatbot-close-btn');
    var toggleBtn = document.getElementById('chatbot-toggle-btn');
    var sendBtn   = document.getElementById('chatbot-send-btn');

    if (!widget) return; // widget not in DOM (chatbot disabled)

    // ── Open / Close ──────────────────────────────────────────────────
    function open() {
        isOpen = true;
        winEl.style.display = 'flex';
        setTimeout(function () { winEl.classList.add('cb-open'); }, 10);
        if (notifEl) notifEl.style.display = 'none';
        inputEl.focus();
        if (!greeted) { greeted = true; sendGreeting(); }
        scrollBottom();
    }

    function close() {
        isOpen = false;
        winEl.classList.remove('cb-open');
        setTimeout(function () { winEl.style.display = 'none'; }, 320);
    }

    function toggle() { if (isOpen) close(); else open(); }

    // ── Messages ──────────────────────────────────────────────────────
    function addUserMsg(text) {
        var div = document.createElement('div');
        div.className = 'cb-msg cb-user';
        div.innerHTML = '<div class="cb-bubble">' + esc(text) + '</div>';
        msgsEl.appendChild(div);
        scrollBottom();
    }

    function addBotMsg(data) {
        hideTyping();
        var div = document.createElement('div');
        div.className = 'cb-msg cb-bot';

        var inner = '<div class="cb-avatar-icon"><i class="fas fa-user-tie"></i></div>';
        inner += '<div class="cb-bot-content">';
        inner += '<div class="cb-bubble">' + fmt(data.message || '') + '</div>';

        // Course cards
        if (data.courses && data.courses.length) {
            inner += '<div class="cb-courses">';
            data.courses.forEach(function (c) {
                var price = (c.price === 0 || c.price === '0') ? 'FREE' : '\u20B9' + c.price;
                inner += '<a href="/courses" class="cb-course-card">'
                       + '<span>' + esc(c.title) + '</span>'
                       + '<span class="cb-course-price">' + price + '</span>'
                       + '</a>';
            });
            inner += '</div>';
        }

        // WhatsApp button
        if (data.show_whatsapp && data.whatsapp_url) {
            inner += '<a href="' + esc(data.whatsapp_url) + '" target="_blank" rel="noopener" class="cb-wa-btn">'
                   + '<i class="fab fa-whatsapp"></i> Chat on WhatsApp</a>';
        }

        // Contact form
        if (data.show_contact_form) {
            inner += contactFormHtml();
        }

        inner += '</div>';
        div.innerHTML = inner;
        msgsEl.appendChild(div);

        // Attach contact form submit
        var fsubmit = div.querySelector('.cb-fsubmit');
        if (fsubmit) fsubmit.addEventListener('click', submitInquiry);

        // Set quick replies
        if (data.quick_replies && data.quick_replies.length) {
            setQR(data.quick_replies);
        }

        scrollBottom();
    }

    function contactFormHtml() {
        return '<div class="cb-contact-form" id="cb-cform">'
             + '<div class="cb-form-label">Share your details and we\'ll reach out:</div>'
             + '<input class="cb-finput" id="cf-name" type="text" placeholder="Your name" autocomplete="off">'
             + '<input class="cb-finput" id="cf-email" type="email" placeholder="Email address" autocomplete="off">'
             + '<input class="cb-finput" id="cf-phone" type="tel" placeholder="Phone number" autocomplete="off">'
             + '<button class="cb-fsubmit">Send Inquiry \u{1F4E8}</button>'
             + '</div>';
    }

    // ── Formatting ────────────────────────────────────────────────────
    function esc(s) {
        return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function fmt(s) {
        return esc(s)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    // ── Quick Replies ─────────────────────────────────────────────────
    function setQR(replies) {
        qrEl.innerHTML = '';
        replies.forEach(function (r) {
            var btn = document.createElement('button');
            btn.className = 'cb-qr';
            btn.textContent = r;
            btn.addEventListener('click', function () { send(r); });
            qrEl.appendChild(btn);
        });
    }

    // ── Typing ────────────────────────────────────────────────────────
    function showTyping() { typingEl.style.display = 'flex'; scrollBottom(); }
    function hideTyping() { typingEl.style.display = 'none'; }
    function scrollBottom() { msgsEl.scrollTop = msgsEl.scrollHeight; }

    // ── Greeting ──────────────────────────────────────────────────────
    function sendGreeting() {
        showTyping();
        setTimeout(function () {
            addBotMsg({ message: GREETING, quick_replies: QUICK_INIT });
        }, 750);
    }

    // ── Send Message ──────────────────────────────────────────────────
    function send(text) {
        text = (text || '').trim();
        if (!text) return;
        addUserMsg(text);
        setQR([]);
        showTyping();
        inputEl.value = '';

        fetch('/chatbot/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var delay = 500 + Math.random() * 500;
            setTimeout(function () { addBotMsg(data); }, delay);
        })
        .catch(function () {
            hideTyping();
            addBotMsg({
                message: 'Sorry, something went wrong. Please try again or reach us on WhatsApp!',
                quick_replies: ['\uD83D\uDCAC Get Support', '\uD83D\uDD04 Try Again']
            });
        });
    }

    function sendFromInput() { send(inputEl.value); }

    // ── Contact form submit ───────────────────────────────────────────
    function submitInquiry() {
        var name  = (document.getElementById('cf-name')  || {}).value || '';
        var email = (document.getElementById('cf-email') || {}).value || '';
        var phone = (document.getElementById('cf-phone') || {}).value || '';
        var form  = document.getElementById('cb-cform');
        if (form) form.remove();

        var summary = [name && ('Name: ' + name), email && ('Email: ' + email), phone && ('Phone: ' + phone)]
                      .filter(Boolean).join(' | ');
        if (summary) addUserMsg(summary);
        showTyping();

        fetch('/chatbot/inquiry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, email: email, phone: phone, message: 'Inquiry from chatbot' })
        }).catch(function () {});

        setTimeout(function () {
            addBotMsg({
                message: 'Thank you' + (name ? ', **' + name + '**' : '') + '! \uD83D\uDE4F We\'ve received your details and will reach out soon. You can also WhatsApp us directly for immediate help.',
                quick_replies: ['\uD83D\uDCDA View Courses', '\uD83D\uDCAC Get Support']
            });
        }, 800);
    }

    // ── Notification pulse ────────────────────────────────────────────
    setTimeout(function () {
        if (!isOpen && notifEl) notifEl.style.display = 'block';
    }, 3500);

    // ── Event listeners ───────────────────────────────────────────────
    toggleBtn.addEventListener('click', toggle);
    closeBtn.addEventListener('click', close);
    sendBtn.addEventListener('click', sendFromInput);
    inputEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendFromInput(); }
    });

    // ── Expose minimal API ────────────────────────────────────────────
    window.chatbot = { open: open, close: close, toggle: toggle };

})();
