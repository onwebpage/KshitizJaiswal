/* Mobile-friendly WhatsApp link handler — same-window on phones, new tab on desktop */
(function () {
    'use strict';

    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
            || (window.matchMedia && window.matchMedia('(max-width: 768px)').matches);
    }

    function openWhatsApp(url, webFallback) {
        if (!url || url === '#') return;
        if (isMobileDevice()) {
            window.location.assign(url);
            return;
        }
        window.open(webFallback || url, '_blank', 'noopener,noreferrer');
    }

    function bindWhatsAppLinks() {
        document.querySelectorAll('[data-whatsapp-link]').forEach(function (el) {
            if (el.dataset.waBound) return;
            el.dataset.waBound = '1';

            var url = el.getAttribute('data-whatsapp-link');
            var fallback = el.getAttribute('data-whatsapp-fallback') || url;
            if (!url || url === '#') return;

            el.addEventListener('click', function (e) {
                e.preventDefault();
                openWhatsApp(url, fallback);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', bindWhatsAppLinks);
    window.openWhatsApp = openWhatsApp;
    window.bindWhatsAppLinks = bindWhatsAppLinks;
})();
