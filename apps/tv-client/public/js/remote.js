/**
 * 10-Foot Fire TV Spatial D-Pad & Remote Navigation Engine
 * Handles Arrow keys, OK (Enter), and Back (Escape/Backspace) across all 9 screens.
 */

class TvRemoteNavigator {
  constructor() {
    this.currentFocusElement = null;
    this.previousFocusElement = null;
    this.activeModal = null;
    this.initListeners();
  }

  initListeners() {
    // Physical Keyboard / Fire TV Remote Keydown Handler
    window.addEventListener('keydown', (e) => this.handleKeyDown(e));

    // Simulator Remote Button Click Handlers
    document.getElementById('rem-up')?.addEventListener('click', () => this.navigate('up'));
    document.getElementById('rem-down')?.addEventListener('click', () => this.navigate('down'));
    document.getElementById('rem-left')?.addEventListener('click', () => this.navigate('left'));
    document.getElementById('rem-right')?.addEventListener('click', () => this.navigate('right'));
    document.getElementById('rem-ok')?.addEventListener('click', () => this.activateCurrent());
    document.getElementById('rem-back')?.addEventListener('click', () => this.handleBack());

    // Toggle Remote Simulator Widget
    const toggleBtn = document.getElementById('btn-toggle-remote');
    const simulator = document.getElementById('remote-simulator');
    toggleBtn?.addEventListener('click', () => {
      simulator?.classList.toggle('minimized');
      toggleBtn.textContent = simulator?.classList.contains('minimized') ? '+' : '−';
    });
  }

  handleKeyDown(e) {
    // Fire TV KeyCodes: 19=Up, 20=Down, 21=Left, 22=Right, 23=DpadCenter(OK), 4=Back
    const key = e.key;
    const code = e.keyCode;

    if (
      document.activeElement?.tagName === 'SELECT' &&
      (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key) ||
        [19, 20, 21, 22].includes(code))
    ) {
      return;
    }

    // Ignore remote arrows if user is actively typing in a text input (allow left/right cursor unless at boundary)
    if (document.activeElement && document.activeElement.tagName === 'INPUT' && (key === 'ArrowLeft' || key === 'ArrowRight')) {
      return;
    }

    // Spacebar toggles playback / triggers AI drawer when on player screen
    if (key === ' ' || code === 32) {
      if (document.activeElement?.tagName !== 'INPUT' && window.TvApp?.currentScreen === 's-player') {
        e.preventDefault();
        window.TvApp?.handlePlayerSpaceAction();
        return;
      }
    }

    if (key === 'ArrowUp' || code === 19) {
      e.preventDefault();
      this.navigate('up');
    } else if (key === 'ArrowDown' || code === 20) {
      e.preventDefault();
      this.navigate('down');
    } else if (key === 'ArrowLeft' || code === 21) {
      e.preventDefault();
      this.navigate('left');
    } else if (key === 'ArrowRight' || code === 22) {
      e.preventDefault();
      this.navigate('right');
    } else if (key === 'Enter' || code === 23) {
      // Don't prevent default on input return so form submit works if attached
      this.activateCurrent();
    } else if (key === 'Escape' || key === 'Backspace' || code === 4) {
      // Back navigation
      if (document.activeElement && document.activeElement.tagName === 'INPUT' && key === 'Backspace') {
        return; // Allow deleting characters inside inputs
      }
      e.preventDefault();
      this.handleBack();
    }
  }

  /**
   * Get all currently visible, focusable elements within the active screen/modal
   */
  getFocusableElements() {
    let container = document;
    
    // If a modal is open, trap focus strictly inside it
    if (this.activeModal && !this.activeModal.classList.contains('hidden')) {
      container = this.activeModal;
    } else {
      // If player AI drawer is open, trap focus inside the drawer
      const drawer = document.getElementById('player-ai-drawer');
      if (drawer && drawer.classList.contains('open')) {
        return Array.from(drawer.querySelectorAll('.tv-focusable')).filter(el => this.isVisible(el));
      }

      const activeScreen = document.querySelector('.tv-screen.active');
      if (activeScreen) {
        // Include header navigation buttons and active screen items
        const headerElements = Array.from(document.querySelectorAll('.tv-header .tv-focusable'));
        const screenElements = Array.from(activeScreen.querySelectorAll('.tv-focusable'));
        return [...headerElements, ...screenElements].filter(el => this.isVisible(el));
      }
    }

    const elements = Array.from(container.querySelectorAll('.tv-focusable'));
    return elements.filter(el => this.isVisible(el));
  }

  isVisible(el) {
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) && 
           window.getComputedStyle(el).visibility !== 'hidden' &&
           !el.closest('.hidden');
  }

  /**
   * Spatial Directional Navigation (calculates nearest candidate along direction vector)
   */
  navigate(direction) {
    const focusables = this.getFocusableElements();
    if (!focusables.length) return;

    const current = document.activeElement && focusables.includes(document.activeElement)
      ? document.activeElement
      : focusables[0];

    const currentRect = current.getBoundingClientRect();
    const currentCenter = {
      x: currentRect.left + currentRect.width / 2,
      y: currentRect.top + currentRect.height / 2,
    };

    let bestCandidate = null;
    let minDistance = Infinity;

    for (const candidate of focusables) {
      if (candidate === current) continue;

      const candRect = candidate.getBoundingClientRect();
      const candCenter = {
        x: candRect.left + candRect.width / 2,
        y: candRect.top + candRect.height / 2,
      };

      const dx = candCenter.x - currentCenter.x;
      const dy = candCenter.y - currentCenter.y;

      let isCandidateInDirection = false;
      let primaryDist = 0;
      let secondaryDist = 0;

      switch (direction) {
        case 'up':
          isCandidateInDirection = dy < -10;
          primaryDist = -dy;
          secondaryDist = Math.abs(dx);
          break;
        case 'down':
          isCandidateInDirection = dy > 10;
          primaryDist = dy;
          secondaryDist = Math.abs(dx);
          break;
        case 'left':
          isCandidateInDirection = dx < -10;
          primaryDist = -dx;
          secondaryDist = Math.abs(dy);
          break;
        case 'right':
          isCandidateInDirection = dx > 10;
          primaryDist = dx;
          secondaryDist = Math.abs(dy);
          break;
      }

      if (isCandidateInDirection) {
        // Weighted Manhattan distance prioritizing primary axis
        const score = primaryDist + secondaryDist * 1.5;
        if (score < minDistance) {
          minDistance = score;
          bestCandidate = candidate;
        }
      }
    }

    if (bestCandidate) {
      this.setFocus(bestCandidate);
    }
  }

  setFocus(element) {
    if (!element) return;
    this.currentFocusElement = element;
    element.focus();
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
  }

  activateCurrent() {
    const active = document.activeElement;
    if (active && typeof active.click === 'function') {
      active.click();
    }
  }

  handleBack() {
    // 0. If player in-screen AI drawer is open, close it and resume playback
    const drawer = document.getElementById('player-ai-drawer');
    if (drawer && drawer.classList.contains('open')) {
      window.TvApp?.closePlayerAiDrawer(true);
      return;
    }

    // 1. If modal is open, close it safely
    if (this.activeModal && !this.activeModal.classList.contains('hidden')) {
      window.TvApp?.closeModal();
      return;
    }

    // 2. Otherwise route back through app state
    window.TvApp?.navigateBack();
  }

  trapModalFocus(modalElement, defaultFocusId = null) {
    this.previousFocusElement = document.activeElement;
    this.activeModal = modalElement;
    modalElement.classList.remove('hidden');

    const focusables = Array.from(modalElement.querySelectorAll('.tv-focusable'));
    let defaultEl = null;

    if (defaultFocusId) {
      defaultEl = modalElement.querySelector(`#${defaultFocusId}`);
    }
    if (!defaultEl && focusables.length) {
      defaultEl = focusables[0];
    }

    if (defaultEl) {
      setTimeout(() => this.setFocus(defaultEl), 50);
    }
  }

  releaseModalFocus() {
    if (this.activeModal) {
      this.activeModal.classList.add('hidden');
      this.activeModal = null;
    }
    if (this.previousFocusElement && this.isVisible(this.previousFocusElement)) {
      this.setFocus(this.previousFocusElement);
    } else {
      this.focusFirstOnScreen();
    }
  }

  focusFirstOnScreen() {
    setTimeout(() => {
      const focusables = this.getFocusableElements();
      if (focusables.length > 0) {
        // Focus first primary screen element or nav button
        this.setFocus(focusables[0]);
      }
    }, 50);
  }
}

// Global Navigator instance
window.TvNavigator = new TvRemoteNavigator();
