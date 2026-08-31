/* ================================================================
   EgyStory — auth.js
   Password visibility toggle, profile picture preview
   ================================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // ── Password visibility toggles ────────────────────────────
  document.querySelectorAll('.password-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.previousElementSibling;
      if (!input) return;
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      btn.innerHTML = isPassword
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    });
  });

  // ── Profile picture preview on register/edit ────────────────
  const avatarInput = document.getElementById('avatar-input');
  const avatarPreview = document.getElementById('avatar-preview');
  if (avatarInput && avatarPreview) {
    avatarInput.addEventListener('change', function () {
      const file = avatarInput.files[0];
      if (!file) return;

      // Client-side size check (5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('Image must be smaller than 5MB.');
        avatarInput.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = function (e) {
        avatarPreview.src = e.target.result;
      };
      reader.readAsDataURL(file);

      // Reset clear input if a new file is chosen and update button text
      const clearInput = document.getElementById('clear_avatar_input');
      if (clearInput) {
        clearInput.value = '0';
      }
      const changeBtn = document.getElementById('btn-change-avatar');
      if (changeBtn) {
        changeBtn.innerText = 'Change Photo';
      }
      const clearBtn = document.getElementById('btn-clear-avatar');
      if (clearBtn) {
        clearBtn.style.display = 'inline-block';
        clearBtn.disabled = false;
        clearBtn.style.opacity = '1';
        clearBtn.innerText = 'Clear Photo';
      }
    });

    // Click on Change Photo button triggers file chooser
    const changeBtn = document.getElementById('btn-change-avatar');
    if (changeBtn) {
      changeBtn.addEventListener('click', function () {
        avatarInput.click();
      });
    }

    // Click on Clear Photo button clears selection and resets preview
    const clearBtn = document.getElementById('btn-clear-avatar');
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        avatarInput.value = '';
        const defaultSrc = avatarPreview.getAttribute('data-default-src') || '/static/images/default-avatar.svg';
        avatarPreview.src = defaultSrc;
        const clearInput = document.getElementById('clear_avatar_input');
        if (clearInput) {
          clearInput.value = '1';
        }
        clearBtn.style.display = 'none';
      });
    }

    // Click on the upload area triggers the hidden file input
    const uploadArea = document.getElementById('avatar-upload-area');
    if (uploadArea) {
      uploadArea.addEventListener('click', function () {
        avatarInput.click();
      });
    }
  }

});
