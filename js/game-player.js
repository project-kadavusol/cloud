// Enhanced Game Player with better error handling
class EnhancedGamePlayer {
    constructor() {
        this.currentGame = null;
        this.gameFile = null;
        this.emulatorLoaded = false;
        this.init();
    }

    init() {
        this.loadGameFromURL();
        this.setupEventListeners();
        this.setupFullscreenHandling();
    }

    loadGameFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const gameName = urlParams.get('game');
        const gameFile = urlParams.get('file');

        if (gameName && gameFile) {
            document.getElementById('current-game').textContent = gameName.toUpperCase();
            this.currentGame = gameName;
            this.gameFile = gameFile;
            this.initializeEmulator();
        } else {
            this.showError('No game specified. Please select a game from the main page.');
        }
    }

    initializeEmulator() {
        const loadingMessage = document.getElementById('loading-message');
        loadingMessage.classList.add('show');

        // Configure EmulatorJS
        window.EJS_player = "#game";
        window.EJS_gameName = this.currentGame;
        window.EJS_biosUrl = "";
        window.EJS_gameUrl = this.gameFile;
        window.EJS_core = this.detectSystem(this.gameFile);
        window.EJS_pathtodata = "emulatorjs/data/";
        window.EJS_startOnLoaded = true;
        window.EJS_DEBUG_XX = false;
        window.EJS_disableDatabases = true;

        // Event listeners
        window.EJS_onGameStart = () => {
            console.log('✅ Game started successfully!');
            loadingMessage.classList.remove('show');
            this.emulatorLoaded = true;
            this.setupGameControls();
            this.initializeSaveSystem();
        };

        window.EJS_onGameError = (error) => {
            console.error('❌ Game error:', error);
            loadingMessage.textContent = 'Error loading game. Please check the ROM file.';
            loadingMessage.style.color = '#ff4444';
        };

        // Load EmulatorJS script
        this.loadEmulatorScript();
    }

    loadEmulatorScript() {
        const script = document.createElement('script');
        script.src = 'emulatorjs/data/loader.js';
        script.onload = () => {
            console.log('✅ EmulatorJS loaded successfully');
        };
        script.onerror = () => {
            console.error('❌ Failed to load EmulatorJS');
            this.showError('Failed to load emulator. Please check if EmulatorJS files are properly installed.');
        };
        document.body.appendChild(script);
    }

    detectSystem(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const systemMap = {
            'nes': 'nes', 'fds': 'nes', 'unif': 'nes',
            'smc': 'snes', 'sfc': 'snes', 'fig': 'snes',
            'gb': 'gb', 'gbc': 'gbc',
            'gba': 'gba',
            'gen': 'segaMD', 'md': 'segaMD',
            'sms': 'segaMS',
            'gg': 'segaGG',
            'pce': 'pce',
            'ngp': 'ngp', 'ngc': 'ngp'
        };
        return systemMap[ext] || 'nes';
    }

    setupEventListeners() {
        // Fullscreen
        document.getElementById('fullscreen-btn').addEventListener('click', () => {
            this.toggleFullscreen();
        });

        // Keyboard controls
        document.addEventListener('keydown', this.handleKeyboard.bind(this));
    }

    setupGameControls() {
        const gameContainer = document.getElementById('game');
        if (gameContainer) {
            gameContainer.setAttribute('tabindex', '0');
            gameContainer.style.outline = 'none';
            
            gameContainer.addEventListener('click', () => {
                gameContainer.focus();
                console.log('🎯 Game container focused');
            });

            setTimeout(() => {
                gameContainer.focus();
            }, 1000);
        }
    }

    handleKeyboard(e) {
        // Prevent default for game keys
        const gameKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 
                         'Enter', 'Shift', 'KeyZ', 'KeyX', 'KeyA', 'KeyS'];
        
        if (gameKeys.includes(e.key) || gameKeys.includes(e.code)) {
            e.preventDefault();
        }

        // Quick save/load shortcuts
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 's': e.preventDefault(); this.quickSave(); break;
                case 'l': e.preventDefault(); this.quickLoad(); break;
            }
        }
    }

    toggleFullscreen() {
        const wrapper = document.querySelector('.emulator-wrapper');
        
        if (!document.fullscreenElement) {
            if (wrapper.requestFullscreen) {
                wrapper.requestFullscreen();
            } else if (wrapper.webkitRequestFullscreen) {
                wrapper.webkitRequestFullscreen();
            }
        } else {
            document.exitFullscreen();
        }
    }

    setupFullscreenHandling() {
        document.addEventListener('fullscreenchange', () => {
            const wrapper = document.querySelector('.emulator-wrapper');
            if (document.fullscreenElement) {
                wrapper.classList.add('fullscreen');
            } else {
                wrapper.classList.remove('fullscreen');
            }
        });
    }

    initializeSaveSystem() {
        if (this.currentGame) {
            gameSaver.setGame(this.currentGame);
            console.log('💾 Save system ready for:', this.currentGame);
        }
    }

    async quickSave() {
        if (window.EJS && typeof EJS_getState === 'function') {
            try {
                const state = EJS_getState();
                await gameSaver.quickSave(state);
                this.showNotification('✅ Game saved!');
            } catch (error) {
                this.showNotification('❌ Save failed');
            }
        }
    }

    async quickLoad() {
        try {
            const state = await gameSaver.quickLoad();
            if (window.EJS && typeof EJS_setState === 'function') {
                EJS_setState(state);
                this.showNotification('✅ Game loaded!');
            }
        } catch (error) {
            this.showNotification('❌ No save found');
        }
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 10000;
            font-family: 'Roboto', sans-serif;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }

    showError(message) {
        const loadingMessage = document.getElementById('loading-message');
        loadingMessage.classList.add('show');
        loadingMessage.textContent = message;
        loadingMessage.style.color = '#ff4444';
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new EnhancedGamePlayer();
});