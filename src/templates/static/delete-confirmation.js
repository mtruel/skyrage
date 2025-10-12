/**
 * Shared delete confirmation logic for SkyRage
 * Provides a two-click confirmation pattern for delete actions with HTMX
 */

/**
 * State management for confirmation tracking
 */
const confirmationState = new Map();

/**
 * Initialize HTMX delete confirmation behavior
 * This should be called after HTMX is loaded
 */
function initDeleteConfirmations() {
    document.body.addEventListener('htmx:confirm', function(evt) {
        const target = evt.target;
        
        // Only handle delete operations with our confirmation class
        if (!target.classList.contains('confirm-delete-htmx')) {
            return;
        }
        
        // Prevent default HTMX confirm dialog
        evt.preventDefault();
        
        const buttonId = target.id || target.getAttribute('data-delete-id');
        const isConfirmed = confirmationState.get(buttonId);
        
        if (isConfirmed) {
            // Second click - allow the request to proceed
            confirmationState.delete(buttonId);
            evt.detail.issueRequest(true);
        } else {
            // First click - enter confirmation mode
            confirmationState.set(buttonId, true);
            
            const originalText = target.innerHTML;
            target.classList.add('confirm-delete');
            
            // Different text for different button types
            if (target.classList.contains('delete-btn')) {
                target.innerHTML = '🗑️';
            } else {
                target.innerHTML = 'Click again to confirm';
            }
            
            // Reset after 3 seconds
            setTimeout(() => {
                confirmationState.delete(buttonId);
                target.classList.remove('confirm-delete');
                target.innerHTML = originalText;
            }, 3000);
        }
    });
    
    // Handle player deletion errors (400 status when player has game history)
    document.body.addEventListener('htmx:responseError', function(evt) {
        const target = evt.target;
        
        // Check if this is a player deletion error
        if (target.id && target.id.startsWith('delete-player-')) {
            const username = target.id.replace('delete-player-', '');
            const errorDiv = document.getElementById(`error-${username}`);
            
            if (errorDiv && evt.detail.xhr.status === 400) {
                try {
                    const response = JSON.parse(evt.detail.xhr.responseText);
                    errorDiv.textContent = response.detail || 'Cannot delete player with game history.';
                    errorDiv.style.display = 'block';
                    
                    // Reset button state
                    target.classList.remove('confirm-delete');
                    target.innerHTML = '🗑️';
                    confirmationState.delete(target.id);
                } catch (e) {
                    console.error('Error parsing response:', e);
                }
            }
        }
    });
    
    // Handle dangling players deletion success
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.target;
        
        // Check if this is the dangling players delete button
        if (target.id === 'delete-dangling-btn' && evt.detail.successful) {
            try {
                const response = JSON.parse(evt.detail.xhr.responseText);
                
                if (response.deleted_count > 0) {
                    alert(`✅ Deleted ${response.deleted_count} dangling player(s):\n${response.deleted_usernames.join(', ')}\n\nTotal players: ${response.total_players}\nPlayers in games: ${response.protected_players}`);
                    window.location.reload();
                } else {
                    alert(`ℹ️ No dangling players found.\n\nTotal players: ${response.total_players}\nAll players are associated with games: ${response.protected_players}`);
                    target.disabled = false;
                    target.classList.remove('confirm-delete');
                    target.innerHTML = 'Delete Dangling Players';
                    confirmationState.delete(target.id);
                }
            } catch (e) {
                console.error('Error parsing response:', e);
            }
        }
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDeleteConfirmations);
} else {
    initDeleteConfirmations();
}
