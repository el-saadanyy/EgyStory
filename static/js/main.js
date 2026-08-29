/* ================================================================
   EgyStory - main.js
   Navigation toggle, messages auto-dismiss, user menu dropdown,
   smooth scroll, sticky navbar, hero slider
   ================================================================ */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Sticky Navbar
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const isHome = document.body.classList.contains('is-home');
    const placeholder = document.createElement('div');
    placeholder.style.display = 'none';
    placeholder.style.height = navbar.offsetHeight + 'px';
    
    if (!isHome) {
      navbar.parentNode.insertBefore(placeholder, navbar);
    }

    window.addEventListener('scroll', function () {
      if (window.scrollY > 0) {
        navbar.classList.add('navbar-fixed');
        if (!isHome) {
          placeholder.style.display = 'block';
        }
      } else {
        navbar.classList.remove('navbar-fixed');
        if (!isHome) {
          placeholder.style.display = 'none';
        }
      }
    });
  }

  // 2 & 3. Toast Notifications — auto-dismiss + manual close
  const TOAST_DURATION = 5000; // ms

  function dismissToast(toast) {
    if (toast.dataset.dismissed) return;
    toast.dataset.dismissed = '1';
    toast.classList.add('toast-hiding');
    // Remove after animation completes (matches toast-slide-out: 0.3s)
    setTimeout(function () { toast.remove(); }, 320);
  }

  document.querySelectorAll('.alert[data-auto-dismiss]').forEach(function (toast) {
    // Animate progress bar
    var progress = toast.querySelector('.alert-progress');
    if (progress) {
      progress.style.transition = 'transform ' + TOAST_DURATION + 'ms linear';
      progress.style.transform = 'scaleX(1)';
      // Force reflow so transition fires
      progress.getBoundingClientRect();
      progress.style.transform = 'scaleX(0)';
    }

    // Auto dismiss after duration
    var timer = setTimeout(function () { dismissToast(toast); }, TOAST_DURATION);

    // Manual close button
    var closeBtn = toast.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        clearTimeout(timer);
        dismissToast(toast);
      });
    }

    // Pause on hover
    toast.addEventListener('mouseenter', function () {
      if (progress) progress.style.animationPlayState = 'paused';
    });
    toast.addEventListener('mouseleave', function () {
      if (progress) progress.style.animationPlayState = 'running';
    });
  });

  // 4. Mobile navbar toggle
  const navToggle = document.getElementById('navbar-toggle');
  const mobileNav = document.getElementById('mobile-nav');
  if (navToggle && mobileNav) {
    navToggle.addEventListener('click', function () {
      mobileNav.classList.toggle('open');
      const isOpen = mobileNav.classList.contains('open');
      navToggle.setAttribute('aria-expanded', isOpen);
    });
  }

  // 5. User menu dropdown
  const menuTrigger = document.getElementById('user-menu-trigger');
  const menuDropdown = document.getElementById('user-menu-dropdown');
  if (menuTrigger && menuDropdown) {
    menuTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      menuDropdown.classList.toggle('open');
    });
    document.addEventListener('click', function () {
      menuDropdown.classList.remove('open');
    });
    menuDropdown.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  }

  // 6. Hero Slider
  const sliderItems = document.querySelectorAll('.hero-slider .slider-item');
  if (sliderItems.length > 1) {
    let currentSlide = 0;
    const sliderContainer = document.querySelector('.hero-slider');

    // Create slider controls container
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'slider-controls';

    // Prev Button
    const prevBtn = document.createElement('button');
    prevBtn.className = 'slider-arrow';
    prevBtn.setAttribute('aria-label', 'Previous campaign');
    prevBtn.innerHTML = '‹';

    // Next Button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'slider-arrow';
    nextBtn.setAttribute('aria-label', 'Next campaign');
    nextBtn.innerHTML = '›';

    // Dots wrapper
    const dotsContainer = document.createElement('div');
    dotsContainer.className = 'slider-dots';

    sliderItems.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.className = i === 0 ? 'slider-dot active' : 'slider-dot';
      dot.setAttribute('aria-label', 'Go to slide ' + (i + 1));

      dot.addEventListener('click', () => {
        goToSlide(i);
        resetInterval();
      });
      dotsContainer.appendChild(dot);
    });

    controlsContainer.appendChild(prevBtn);
    controlsContainer.appendChild(dotsContainer);
    controlsContainer.appendChild(nextBtn);

    // Replace old placeholder note or append controls directly after slider
    const textNote = sliderContainer.querySelector('div:last-child');
    if (textNote && textNote.innerText.includes('Showing 1 of')) {
      textNote.replaceWith(controlsContainer);
    } else {
      sliderContainer.after(controlsContainer);
    }

    const dots = dotsContainer.querySelectorAll('.slider-dot');

    function goToSlide(index) {
      if (currentSlide === index) return;

      const prevSlide = currentSlide;
      currentSlide = index;

      // Update dots active class
      dots[prevSlide].classList.remove('active');
      dots[currentSlide].classList.add('active');

      // Handle outgoing slide
      sliderItems[prevSlide].classList.remove('active');
      sliderItems[prevSlide].classList.add('outgoing');

      setTimeout(() => {
        sliderItems[prevSlide].classList.remove('outgoing');
      }, 600);

      // Handle incoming slide
      sliderItems[currentSlide].classList.remove('outgoing');
      sliderItems[currentSlide].classList.add('active');
    }

    function nextSlide() {
      goToSlide((currentSlide + 1) % sliderItems.length);
    }

    function prevSlide() {
      goToSlide((currentSlide - 1 + sliderItems.length) % sliderItems.length);
    }

    prevBtn.addEventListener('click', () => {
      prevSlide();
      resetInterval();
    });

    nextBtn.addEventListener('click', () => {
      nextSlide();
      resetInterval();
    });

    let slideInterval = setInterval(nextSlide, 5000);

    function resetInterval() {
      clearInterval(slideInterval);
      slideInterval = setInterval(nextSlide, 5000);
    }

    sliderContainer.addEventListener('mouseenter', () => clearInterval(slideInterval));
    sliderContainer.addEventListener('mouseleave', resetInterval);
  }

  // 7. Smooth scroll and active state for Navigation
  const aboutLinks = document.querySelectorAll('.nav-link-about');
  const homeLinks = document.querySelectorAll('.nav-link-home');
  const aboutSection = document.getElementById('about');

  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#' || (targetId === '#about' && !aboutSection)) return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        e.preventDefault();
        const headerOffset = navbar ? navbar.offsetHeight : 80;
        const elementPosition = targetElement.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.scrollY - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });
        
        if (mobileNav && mobileNav.classList.contains('open')) {
            navToggle.click();
        }
      }
    });
  });

  if (aboutSection) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          aboutLinks.forEach(link => link.classList.add('active'));
          homeLinks.forEach(link => link.classList.remove('active'));
        } else {
          aboutLinks.forEach(link => link.classList.remove('active'));
          if (window.scrollY < 100) {
              homeLinks.forEach(link => link.classList.add('active'));
          }
        }
      });
    }, {
      rootMargin: '-20% 0px -60% 0px'
    });
    
    observer.observe(aboutSection);
    
    window.addEventListener('scroll', () => {
        if (window.scrollY < 100 && (!aboutLinks[0] || !aboutLinks[0].classList.contains('active'))) {
            homeLinks.forEach(link => link.classList.add('active'));
        }
    });
  }

  // 8. Custom Campaign Reject Confirmation Modal
  const rejectModal = document.getElementById('reject-modal');
  if (rejectModal) {
    const modalForm = document.getElementById('reject-modal-form');
    const modalMsg = document.getElementById('reject-modal-message');
    const closeBtn = document.getElementById('reject-modal-close');
    const cancelBtn = document.getElementById('reject-modal-cancel');

    function openRejectModal(actionUrl, campaignTitle) {
      if (modalForm) modalForm.action = actionUrl;
      if (modalMsg) {
        if (campaignTitle) {
          modalMsg.textContent = 'Are you sure you want to reject "' + campaignTitle + '"? This action will mark the campaign as rejected/cancelled.';
        } else {
          modalMsg.textContent = 'Are you sure you want to reject this campaign? This action will mark the campaign as rejected/cancelled.';
        }
      }
      rejectModal.classList.add('is-open');
      rejectModal.setAttribute('aria-hidden', 'false');
    }

    function closeRejectModal() {
      rejectModal.classList.remove('is-open');
      rejectModal.setAttribute('aria-hidden', 'true');
    }

    document.querySelectorAll('.btn-reject-campaign').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        const actionUrl = this.dataset.actionUrl;
        const title = this.dataset.campaignTitle;
        openRejectModal(actionUrl, title);
      });
    });

    if (closeBtn) closeBtn.addEventListener('click', closeRejectModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeRejectModal);

    rejectModal.addEventListener('click', function (e) {
      if (e.target === rejectModal) closeRejectModal();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && rejectModal.classList.contains('is-open')) {
        closeRejectModal();
      }
    });
  }

  // 9. Project Detail Image Slider (Feature #10)
  const detailSlider = document.querySelector('.project-slider');
  if (detailSlider) {
    const slides = detailSlider.querySelectorAll('.slider-slide');
    const thumbnails = detailSlider.querySelectorAll('.slider-thumbnail-item');
    const prevBtn = detailSlider.querySelector('.slider-prev');
    const nextBtn = detailSlider.querySelector('.slider-next');
    const counterBadge = detailSlider.querySelector('.slider-counter-badge');
    let currentIndex = 0;

    function updateSlider(index) {
      if (slides.length === 0) return;
      currentIndex = (index + slides.length) % slides.length;

      slides.forEach((slide, idx) => {
        if (idx === currentIndex) {
          slide.classList.add('active');
        } else {
          slide.classList.remove('active');
        }
      });

      thumbnails.forEach((thumb, idx) => {
        if (idx === currentIndex) {
          thumb.classList.add('active');
          thumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
        } else {
          thumb.classList.remove('active');
        }
      });

      if (counterBadge) {
        counterBadge.textContent = (currentIndex + 1) + ' / ' + slides.length;
      }
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        updateSlider(currentIndex - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        updateSlider(currentIndex + 1);
      });
    }

    thumbnails.forEach((thumb, idx) => {
      thumb.addEventListener('click', function () {
        updateSlider(idx);
      });
    });

    document.addEventListener('keydown', function (e) {
      if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA')) return;
      if (e.key === 'ArrowLeft') {
        updateSlider(currentIndex - 1);
      } else if (e.key === 'ArrowRight') {
        updateSlider(currentIndex + 1);
      }
    });
  }

  // 10. Clickable Campaign Cards & Hero Slider Delegation
  document.addEventListener('click', function (e) {
    // A. Campaign Card Click Handling
    const card = e.target.closest('.campaign-card');
    if (card) {
      const interactiveEl = e.target.closest('a, button, input, select, textarea, label, form, .badge-action, [role="button"]');
      if (!interactiveEl) {
        const url = card.dataset.campaignUrl;
        if (url) {
          window.location.href = url;
          return;
        }
      }
    }

    // B. Hero Campaign Slider Item Click Handling
    const slide = e.target.closest('.hero-slider .slider-item.active');
    if (slide) {
      const interactiveEl = e.target.closest('a, button, input, select, textarea, label, form, .slider-arrow, .slider-dot, [role="button"]');
      if (!interactiveEl) {
        const url = slide.dataset.campaignUrl;
        if (url) {
          window.location.href = url;
          return;
        }
      }
    }
  });

  // Keyboard accessibility (Enter or Space key on campaign cards & hero slides)
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const activeEl = document.activeElement;
    if (!activeEl) return;

    if (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT') return;

    if (activeEl.classList.contains('campaign-card') || (activeEl.classList.contains('slider-item') && activeEl.classList.contains('active'))) {
      const interactiveEl = e.target.closest('a, button, input, select, textarea, label, form, .slider-arrow, .slider-dot, [role="button"]');
      if (interactiveEl && interactiveEl !== activeEl) return;

      const url = activeEl.dataset.campaignUrl;
      if (url) {
        e.preventDefault();
        window.location.href = url;
      }
    }
  });

  // 7. Campaign Report Modal Toggle Handler

  const reportOpenBtn = document.getElementById('btn-open-report-modal');
  const reportModal = document.getElementById('reportModal');
  const reportCloseBtn = document.getElementById('btn-close-report-modal');
  const reportCancelBtn = document.getElementById('btn-cancel-report-modal');

  if (reportModal) {
    function openReportModal() {
      reportModal.style.display = 'flex';
      reportModal.setAttribute('aria-hidden', 'false');
    }

    function closeReportModal() {
      reportModal.style.display = 'none';
      reportModal.setAttribute('aria-hidden', 'true');
    }

    if (reportOpenBtn) {
      reportOpenBtn.addEventListener('click', openReportModal);
    }
    if (reportCloseBtn) {
      reportCloseBtn.addEventListener('click', closeReportModal);
    }
    if (reportCancelBtn) {
      reportCancelBtn.addEventListener('click', closeReportModal);
    }

    reportModal.addEventListener('click', function (e) {
      if (e.target === reportModal) {
        closeReportModal();
      }
    });
  }

  // 8. Campaign Cancel Modal Toggle Handler (Feature #9)
  const cancelOpenBtn = document.getElementById('btn-open-cancel-modal');
  const cancelModal = document.getElementById('cancelCampaignModal');
  const cancelCloseBtn = document.getElementById('btn-close-cancel-modal');
  const cancelKeepBtn = document.getElementById('btn-cancel-modal-close');

  if (cancelModal) {
    function openCancelModal() {
      cancelModal.style.display = 'flex';
      cancelModal.setAttribute('aria-hidden', 'false');
    }

    function closeCancelModal() {
      cancelModal.style.display = 'none';
      cancelModal.setAttribute('aria-hidden', 'true');
    }

    if (cancelOpenBtn) {
      cancelOpenBtn.addEventListener('click', openCancelModal);
    }
    if (cancelCloseBtn) {
      cancelCloseBtn.addEventListener('click', closeCancelModal);
    }
    if (cancelKeepBtn) {
      cancelKeepBtn.addEventListener('click', closeCancelModal);
    }

    cancelModal.addEventListener('click', function (e) {
      if (e.target === cancelModal) {
        closeCancelModal();
      }
    });
  }

  // 11. Search Autocomplete / Suggestions
  const searchForms = document.querySelectorAll('form[action*="cases"]');
  searchForms.forEach(function (form) {
    const searchInput = form.querySelector('input[name="q"]');
    if (!searchInput) return;

    // Create autocomplete dropdown element
    const dropdown = document.createElement('div');
    dropdown.className = 'search-autocomplete-dropdown';
    dropdown.style.display = 'none';

    // Position relative wrapper
    let wrapper = searchInput.parentElement;
    if (wrapper) {
      if (getComputedStyle(wrapper).position === 'static') {
        wrapper.style.position = 'relative';
      }
      wrapper.appendChild(dropdown);
    }

    let debounceTimer = null;
    let selectedIndex = -1;
    let currentQuery = '';

    function hideDropdown() {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
      selectedIndex = -1;
    }

    function renderSuggestions(suggestions, query) {
      if (!suggestions || suggestions.length === 0) {
        hideDropdown();
        return;
      }

      dropdown.innerHTML = '';
      selectedIndex = -1;

      suggestions.forEach(function (item, index) {
        const row = document.createElement('a');
        row.href = item.url;
        row.className = 'autocomplete-item';
        row.dataset.index = index;

        const titleSpan = document.createElement('span');
        titleSpan.className = 'autocomplete-title';
        titleSpan.textContent = item.title;

        const badgeSpan = document.createElement('span');
        badgeSpan.className = 'autocomplete-badge';
        badgeSpan.textContent = item.match_type || 'Campaign';

        row.appendChild(titleSpan);
        row.appendChild(badgeSpan);

        row.addEventListener('click', function (e) {
          e.preventDefault();
          window.location.href = item.url;
        });

        dropdown.appendChild(row);
      });

      dropdown.style.display = 'block';
    }

    function fetchSuggestions(query) {
      if (!query || query.length < 2) {
        hideDropdown();
        return;
      }

      currentQuery = query;
      const url = '/cases/autocomplete/?q=' + encodeURIComponent(query);

      fetch(url)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (currentQuery === query) {
            renderSuggestions(data.suggestions, query);
          }
        })
        .catch(function () { hideDropdown(); });
    }

    searchInput.addEventListener('input', function () {
      const query = searchInput.value.trim();
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        fetchSuggestions(query);
      }, 250);
    });

    searchInput.addEventListener('keydown', function (e) {
      const items = dropdown.querySelectorAll('.autocomplete-item');
      if (dropdown.style.display === 'block' && items.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          selectedIndex = (selectedIndex + 1) % items.length;
          highlightItem(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          selectedIndex = (selectedIndex - 1 + items.length) % items.length;
          highlightItem(items);
        } else if (e.key === 'Escape') {
          hideDropdown();
        } else if (e.key === 'Enter') {
          if (selectedIndex >= 0 && items[selectedIndex]) {
            e.preventDefault();
            items[selectedIndex].click();
          }
        }
      }
    });

    function highlightItem(items) {
      items.forEach(function (el, idx) {
        if (idx === selectedIndex) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      });
    }

    document.addEventListener('click', function (e) {
      if (!form.contains(e.target)) {
        hideDropdown();
      }
    });

    searchInput.addEventListener('focus', function () {
      const query = searchInput.value.trim();
      if (query.length >= 2 && dropdown.children.length > 0) {
        dropdown.style.display = 'block';
      }
    });
  });

  // ── Global Custom Select Replacement ─────────────────────────
  function initCustomSelects() {
    document.querySelectorAll('select:not([multiple]):not(.no-custom-select)').forEach(function (select) {
      if (select.dataset.customSelectInitialized) return;
      select.dataset.customSelectInitialized = 'true';

      // Hide original select visually but keep it for form submission & accessibility
      select.style.position = 'absolute';
      select.style.opacity = '0';
      select.style.pointerEvents = 'none';
      select.style.height = '0';
      select.style.width = '0';
      select.style.margin = '0';
      select.style.padding = '0';
      select.style.border = 'none';
      select.tabIndex = -1;

      // Create wrapper
      const wrapper = document.createElement('div');
      wrapper.className = 'custom-select-container';
      if (select.className) {
        select.className.split(' ').forEach(function (c) {
          c = c.trim();
          if (c && c !== 'form-control' && c !== 'form-input') {
            wrapper.classList.add(c);
          }
        });
      }

      // Create Trigger
      const trigger = document.createElement('div');
      trigger.className = 'custom-select-trigger';
      trigger.tabIndex = 0;
      trigger.setAttribute('role', 'combobox');
      trigger.setAttribute('aria-expanded', 'false');

      const selectedOption = select.options[select.selectedIndex] || select.options[0];
      const triggerText = document.createElement('span');
      triggerText.className = 'custom-select-label';
      triggerText.textContent = selectedOption ? selectedOption.text : '';
      if (selectedOption && !selectedOption.value) {
        triggerText.classList.add('is-placeholder');
      }

      const arrow = document.createElement('span');
      arrow.className = 'custom-select-arrow';
      arrow.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E4C071" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`;

      trigger.appendChild(triggerText);
      trigger.appendChild(arrow);

      // Create Menu Dropdown List
      const menu = document.createElement('div');
      menu.className = 'custom-select-menu';
      menu.setAttribute('role', 'listbox');

      function populateOptions() {
        menu.innerHTML = '';
        Array.from(select.options).forEach(function (opt, idx) {
          const item = document.createElement('div');
          item.className = 'custom-select-item';
          item.textContent = opt.text;
          item.dataset.value = opt.value;
          item.dataset.index = idx;
          item.setAttribute('role', 'option');

          if (opt.disabled) {
            item.classList.add('is-disabled');
          }
          if (idx === select.selectedIndex) {
            item.classList.add('is-selected');
          }

          item.addEventListener('click', function (e) {
            e.stopPropagation();
            if (opt.disabled) return;
            select.selectedIndex = idx;
            triggerText.textContent = opt.text;
            if (!opt.value) {
              triggerText.classList.add('is-placeholder');
            } else {
              triggerText.classList.remove('is-placeholder');
            }
            menu.querySelectorAll('.custom-select-item').forEach(function (el) {
              el.classList.remove('is-selected');
            });
            item.classList.add('is-selected');
            wrapper.classList.remove('is-open');
            trigger.setAttribute('aria-expanded', 'false');

            // Dispatch change event to original select
            select.dispatchEvent(new Event('change', { bubbles: true }));
          });

          menu.appendChild(item);
        });
      }

      populateOptions();

      // Open / Close Toggle
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = wrapper.classList.contains('is-open');
        // Close all other open custom selects first
        document.querySelectorAll('.custom-select-container.is-open').forEach(function (w) {
          if (w !== wrapper) {
            w.classList.remove('is-open');
            const tr = w.querySelector('.custom-select-trigger');
            if (tr) tr.setAttribute('aria-expanded', 'false');
          }
        });

        if (isOpen) {
          wrapper.classList.remove('is-open');
          trigger.setAttribute('aria-expanded', 'false');
        } else {
          populateOptions();
          wrapper.classList.add('is-open');
          trigger.setAttribute('aria-expanded', 'true');
        }
      });

      // Keyboard support on trigger
      trigger.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
          e.preventDefault();
          if (!wrapper.classList.contains('is-open')) {
            wrapper.classList.add('is-open');
            trigger.setAttribute('aria-expanded', 'true');
          }
        } else if (e.key === 'Escape') {
          wrapper.classList.remove('is-open');
          trigger.setAttribute('aria-expanded', 'false');
        }
      });

      // Insert wrapper in DOM
      select.parentNode.insertBefore(wrapper, select);
      wrapper.appendChild(select);
      wrapper.appendChild(trigger);
      wrapper.appendChild(menu);

      // Listen to external change on original select
      select.addEventListener('change', function () {
        const curOpt = select.options[select.selectedIndex];
        if (curOpt) {
          triggerText.textContent = curOpt.text;
          if (!curOpt.value) {
            triggerText.classList.add('is-placeholder');
          } else {
            triggerText.classList.remove('is-placeholder');
          }
          menu.querySelectorAll('.custom-select-item').forEach(function (el, i) {
            if (i === select.selectedIndex) el.classList.add('is-selected');
            else el.classList.remove('is-selected');
          });
        }
      });
    });

    // Close on click outside
    document.addEventListener('click', function () {
      document.querySelectorAll('.custom-select-container.is-open').forEach(function (w) {
        w.classList.remove('is-open');
        const tr = w.querySelector('.custom-select-trigger');
        if (tr) tr.setAttribute('aria-expanded', 'false');
      });
    });
  }

  window.initCustomSelects = initCustomSelects;
  initCustomSelects();
});





