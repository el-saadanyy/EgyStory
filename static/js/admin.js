/**
 * EgyStory Admin Dashboard — Non-reloading AJAX Engine
 * Provides smooth asynchronous actions, real-time UI updates, and notification toasts.
 */

(function () {
  'use strict';

  function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    if (cookie) return cookie.split('=')[1];
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function showAdminToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'messages-container';
      container.style.cssText = 'position: fixed; top: 80px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 12px; width: 360px; max-width: calc(100vw - 32px); pointer-events: none;';
      document.body.appendChild(container);
    }

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.style.cssText = 'pointer-events: auto; animation: slideInToast 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards; display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-radius: var(--radius-md, 10px); background: #25231E; border: 1px solid rgba(228, 192, 113, 0.35); color: #F5EDD5; box-shadow: 0 10px 25px rgba(0,0,0,0.5);';

    let iconSvg = '';
    if (type === 'success') {
      alert.style.borderColor = 'rgba(34, 197, 94, 0.4)';
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5" style="flex-shrink:0;"><polyline points="20 6 9 17 4 12"/></svg>';
    } else if (type === 'error' || type === 'danger') {
      alert.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2.5" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    } else if (type === 'warning') {
      alert.style.borderColor = 'rgba(234, 179, 8, 0.4)';
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#facc15" stroke-width="2.5" style="flex-shrink:0;"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    } else {
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    }

    alert.innerHTML = `
      ${iconSvg}
      <span style="flex:1;line-height:1.45;font-weight:600;font-size:13.5px;">${message}</span>
      <button class="alert-close" aria-label="Dismiss" style="background:none;border:none;color:#AFA793;cursor:pointer;padding:4px;display:flex;align-items:center;transition:color 0.2s;">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;

    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => dismissAlert(alert));
      closeBtn.addEventListener('mouseenter', () => { closeBtn.style.color = '#FFFFFF'; });
      closeBtn.addEventListener('mouseleave', () => { closeBtn.style.color = '#AFA793'; });
    }

    container.appendChild(alert);

    setTimeout(() => {
      dismissAlert(alert);
    }, 4500);
  }

  function dismissAlert(alert) {
    if (!alert || !alert.parentNode) return;
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-12px) scale(0.95)';
    alert.style.transition = 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)';
    setTimeout(() => {
      if (alert.parentNode) alert.remove();
    }, 250);
  }

  function removeTableRow(row, callback) {
    if (!row) return;
    row.style.transition = 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)';
    row.style.opacity = '0';
    row.style.transform = 'scale(0.97) translateY(-6px)';
    
    setTimeout(() => {
      const tbody = row.closest('tbody');
      const card = row.closest('.admin-card');
      row.remove();
      
      if (tbody && tbody.querySelectorAll('tr').length === 0) {
        if (card) {
          const wrap = card.querySelector('.table-wrap') || card.querySelector('.admin-users-table-wrapper');
          if (wrap) {
            wrap.innerHTML = '<div style="padding: 48px; text-align: center; color: #AFA793; font-size: 15px;">✨ All caught up! No remaining items.</div>';
          }
        }
      }
      if (typeof callback === 'function') callback();
    }, 350);
  }

  // Export functions to window
  window.showAdminToast = showAdminToast;
  window.removeTableRow = removeTableRow;
  window.getCsrfToken = getCsrfToken;

  // Universal DOM Initializer
  document.addEventListener('DOMContentLoaded', function () {
    // ── 1. Intercept Standard Async Forms (Toggle Featured, Critical, Deletions) ──
    document.addEventListener('submit', function (e) {
      const form = e.target;
      if (!form || !form.action) return;

      const isAsyncAction = (
        form.action.includes('toggle-featured') ||
        form.action.includes('toggle-critical') ||
        form.action.includes('toggle-status') ||
        form.action.includes('delete-user') ||
        form.action.includes('delete-tag') ||
        form.action.includes('delete-comment') ||
        form.action.includes('delete-completed') ||
        form.action.includes('/reports/') ||
        form.classList.contains('async-form')
      );

      if (isAsyncAction) {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const origBtnHtml = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.style.opacity = '0.6';
        }

        const formData = new FormData(form);
        formData.append('ajax', '1');

        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          }
        })
        .then(res => res.json())
        .then(data => {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
          }

          if (data.success) {
            showAdminToast(data.message || 'Action completed successfully.', 'success');

            const row = form.closest('tr');

            // Handle Toggle Featured
            if (data.is_featured !== undefined && row) {
              const priorityCell = row.children[3];
              if (submitBtn) {
                if (data.is_featured) {
                  submitBtn.className = 'btn btn-outline btn-sm';
                  submitBtn.style.color = '#E4C071';
                  submitBtn.style.borderColor = 'rgba(228, 192, 113, 0.4)';
                  submitBtn.title = 'Remove from Featured';
                  submitBtn.innerHTML = '★ Unfeature';
                } else {
                  submitBtn.className = 'btn btn-ghost btn-sm';
                  submitBtn.style.color = '#AFA793';
                  submitBtn.style.border = '1px solid rgba(255,255,255,0.15)';
                  submitBtn.title = 'Mark as Featured';
                  submitBtn.innerHTML = '☆ Feature';
                }
              }
              if (priorityCell) {
                const existingFeatured = priorityCell.querySelector('.badge-warning');
                if (data.is_featured && !existingFeatured) {
                  const badge = document.createElement('span');
                  badge.className = 'badge badge-warning';
                  badge.style.cssText = 'font-weight: 800; background: rgba(228, 192, 113, 0.2); color: #E4C071; border-color: rgba(228, 192, 113, 0.4);';
                  badge.textContent = '🌟 Featured';
                  priorityCell.firstElementChild.prepend(badge);
                } else if (!data.is_featured && existingFeatured) {
                  existingFeatured.remove();
                }
              }
            }

            // Handle Toggle Critical
            else if (data.is_manual_critical !== undefined && row) {
              const priorityCell = row.children[3];
              if (submitBtn) {
                if (data.is_manual_critical) {
                  submitBtn.className = 'btn btn-outline btn-sm';
                  submitBtn.style.color = '#AFA793';
                  submitBtn.style.borderColor = 'rgba(255,255,255,0.15)';
                  submitBtn.innerHTML = 'Remove Critical';
                } else {
                  submitBtn.className = 'btn btn-primary btn-sm';
                  submitBtn.style.background = 'linear-gradient(135deg, #a855f7, #9333ea)';
                  submitBtn.style.border = 'none';
                  submitBtn.style.boxShadow = '0 0 12px rgba(168, 85, 247, 0.4)';
                  submitBtn.innerHTML = '★ Mark Critical';
                }
              }
              if (priorityCell) {
                const priorityContainer = priorityCell.firstElementChild;
                if (priorityContainer) {
                  const badges = priorityContainer.querySelectorAll('.badge-rare, .badge-danger, .badge-gray');
                  badges.forEach(b => b.remove());
                  const newBadge = document.createElement('span');
                  if (data.is_manual_critical) {
                    newBadge.className = 'badge badge-rare';
                    newBadge.style.fontWeight = '800';
                    newBadge.textContent = '⚙️ Manual Critical';
                  } else if (data.is_auto_critical) {
                    newBadge.className = 'badge badge-danger';
                    newBadge.style.fontWeight = '800';
                    newBadge.textContent = '⚡ Auto Critical';
                  } else {
                    newBadge.className = 'badge badge-gray';
                    newBadge.textContent = 'Standard';
                  }
                  priorityContainer.appendChild(newBadge);
                }
              }
            }

            // Handle Toggle Admin Status
            else if (data.is_active !== undefined && row) {
              const statusCell = row.children[2] || row.querySelector('td:nth-child(3)');
              if (statusCell) {
                statusCell.innerHTML = data.is_active
                  ? '<span class="badge badge-success">✓ Active</span>'
                  : '<span class="badge badge-warning">Deactivated</span>';
              }
              if (submitBtn) {
                submitBtn.innerHTML = data.is_active ? 'Deactivate' : 'Activate';
                submitBtn.className = data.is_active ? 'btn btn-sm btn-ghost' : 'btn btn-sm btn-outline';
              }
            }

            // Handle Reports Action
            else if (data.report_id && row) {
              const statusCell = row.children[3] || row.querySelector('td:nth-child(4)');
              const actionCell = row.querySelector('.actions-col');
              if (statusCell) {
                if (data.status === 'Reviewed') {
                  statusCell.innerHTML = '<span class="badge badge-success">✓ Reviewed</span>';
                } else if (data.status === 'Dismissed') {
                  statusCell.innerHTML = '<span class="badge badge-gray">Dismissed</span>';
                } else if (data.status === 'Action Taken') {
                  statusCell.innerHTML = '<span class="badge badge-danger">⚡ Action Taken</span>';
                }
              }
              if (actionCell) {
                actionCell.innerHTML = '<span style="font-size: 13px; color: #AFA793;">Done</span>';
              }
            }

            // Handle Item Deletion (User, Tag, Comment, etc.)
            else if (data.user_id || data.tag_id || data.comment_id || data.admin_id) {
              removeTableRow(row);
            }
          } else {
            showAdminToast(data.message || 'Operation could not be completed.', 'error');
          }
        })
        .catch(err => {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.innerHTML = origBtnHtml;
          }
          showAdminToast('A network error occurred. Please try again.', 'error');
        });
      }
    });

    // ── 2. Intercept Approve Campaign Links ──
    document.addEventListener('click', function (e) {
      const approveLink = e.target.closest('a[href*="/campaign/"][href*="/approve"]');
      if (approveLink) {
        e.preventDefault();
        const row = approveLink.closest('tr');
        approveLink.style.pointerEvents = 'none';
        approveLink.style.opacity = '0.6';
        approveLink.textContent = 'Approving...';

        fetch(approveLink.href, {
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          }
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showAdminToast(data.message || 'Campaign approved and is now active!', 'success');
            removeTableRow(row);
          } else {
            approveLink.style.pointerEvents = 'auto';
            approveLink.style.opacity = '1';
            approveLink.textContent = '✓ Approve';
            showAdminToast(data.message || 'Could not approve campaign.', 'error');
          }
        })
        .catch(() => {
          approveLink.style.pointerEvents = 'auto';
          approveLink.style.opacity = '1';
          approveLink.textContent = '✓ Approve';
          showAdminToast('Failed to approve campaign.', 'error');
        });
      }
    });
  });
})();
