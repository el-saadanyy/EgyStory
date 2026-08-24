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
});

