/* WhatsApp link handler — wa.me universal deep links on mobile, WhatsApp Web on desktop */
(function () {
    'use strict';

    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
            || (navigator.maxTouchPoints && navigator.maxTouchPoints > 1);
    }

    function openWhatsApp(mobileUrl, desktopFallback) {
        if (!mobileUrl || mobileUrl === '#') return;

        if (isMobileDevice()) {
            // wa.me is the universal deep link: opens the WhatsApp app directly
            // on Android and iPhone. If WhatsApp is not installed the link
            // redirects to the App Store / Play Store automatically.
            window.location.href = mobileUrl;
        } else {
            // On desktop open WhatsApp Web in a new tab
            window.open(desktopFallback || mobileUrl, '_blank', 'noopener,noreferrer');
        }
    }

    function bindWhatsAppLinks() {
        document.querySelectorAll('[data-whatsapp-link]').forEach(function (el) {
            if (el.dataset.waBound) return;
            el.dataset.waBound = '1';

            var mobileUrl  = el.getAttribute('data-whatsapp-link');
            var desktopUrl = el.getAttribute('data-whatsapp-fallback') || mobileUrl;
            if (!mobileUrl || mobileUrl === '#') return;

            // Keep the href valid so right-click / long-press / copy-link work
            el.setAttribute('href', mobileUrl);

            el.addEventListener('click', function (e) {
                e.preventDefault();
                openWhatsApp(mobileUrl, desktopUrl);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', bindWhatsAppLinks);
    window.openWhatsApp       = openWhatsApp;
    window.bindWhatsAppLinks  = bindWhatsAppLinks;
})();
