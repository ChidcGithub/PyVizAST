/**
 * LLM Downloader Component
 * 
 * Quick access to download and setup LLM tools (Ollama, aria2)
 * 
 * @author Chidc
 * @link github.com/chidcGithub
 */
import React, { useState, useEffect } from 'react';
import { useToast } from './ToastContext';
import logger from '../utils/logger';

/**
 * Platform icons
 */
const PLATFORM_ICONS = {
  windows: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801" />
    </svg>
  ),
  darwin: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
    </svg>
  ),
  linux: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.504 0c-.155 0-.311.003-.466.007-.984.03-1.861.318-2.627.856-.766.539-1.364 1.229-1.798 2.073-.433.843-.654 1.762-.654 2.754 0 .781.126 1.517.377 2.205.252.688.605 1.292 1.06 1.812.454.52.992.93 1.613 1.23.621.298 1.286.447 1.995.447.71 0 1.374-.149 1.995-.448.62-.3 1.158-.71 1.613-1.23.454-.52.807-1.123 1.059-1.811.251-.688.377-1.424.377-2.205 0-.992-.221-1.911-.654-2.754-.434-.844-1.032-1.534-1.798-2.073-.766-.538-1.643-.826-2.627-.856-.155-.004-.311-.007-.466-.007zm-.004 1.5c.125 0 .25.002.374.006.745.023 1.4.24 1.964.65.563.41 1.003.947 1.32 1.61.316.664.474 1.393.474 2.188 0 .625-.1 1.217-.301 1.775-.201.558-.48 1.05-.838 1.475-.358.426-.78.761-1.268 1.005-.487.244-1.01.366-1.567.366-.557 0-1.08-.122-1.567-.366-.488-.244-.91-.579-1.268-1.005-.358-.426-.637-.917-.838-1.475-.201-.558-.301-1.15-.301-1.775 0-.795.158-1.524.474-2.188.317-.663.757-1.2 1.32-1.61.564-.41 1.219-.627 1.964-.65.124-.004.249-.006.374-.006zm-5.5 11.5c-.395.01-.764.087-1.108.232-.344.145-.65.35-.918.616-.268.266-.48.58-.634.942-.155.362-.232.753-.232 1.172 0 .42.077.81.232 1.172.154.362.366.676.634.942.268.266.574.47.918.616.344.145.713.222 1.108.232.395-.01.764-.087 1.108-.232.344-.145.65-.35.918-.616.268-.266.48-.58.634-.942.155-.362.232-.752.232-1.172 0-.42-.077-.81-.232-1.172-.154-.362-.366-.676-.634-.942-.268-.266-.574-.47-.918-.616-.344-.145-.713-.222-1.108-.232zm11 0c-.395.01-.764.087-1.108.232-.344.145-.65.35-.918.616-.268.266-.48.58-.634.942-.155.362-.232.753-.232 1.172 0 .42.077.81.232 1.172.154.362.366.676.634.942.268.266.574.47.918.616.344.145.713.222 1.108.232.395-.01.764-.087 1.108-.232.344-.145.65-.35.918-.616.268-.266.48-.58.634-.942.155-.362.232-.752.232-1.172 0-.42-.077-.81-.232-1.172-.154-.362-.366-.676-.634-.942-.268-.266-.574-.47-.918-.616-.344-.145-.713-.222-1.108-.232z" />
    </svg>
  ),
};

/**
 * LLM Downloader Component
 */
function LLMDownloader({ isOpen, theme, onClose }) {
  const [platform, setPlatform] = useState('windows');
  const [ollamaInfo, setOllamaInfo] = useState(null);
  const [aria2Status, setAria2Status] = useState(null);
  const [aria2Instructions, setAria2Instructions] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    if (isOpen) {
      // Detect platform
      const ua = navigator.userAgent.toLowerCase();
      if (ua.includes('win')) setPlatform('windows');
      else if (ua.includes('mac')) setPlatform('darwin');
      else if (ua.includes('linux')) setPlatform('linux');

      // Fetch info
      fetchInfo();
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const fetchInfo = async () => {
    setLoading(true);
    try {
      const [ollamaRes, aria2Res, aria2InstRes] = await Promise.all([
        fetch('/api/llm/downloads/ollama'),
        fetch('/api/llm/downloads/aria2/status'),
        fetch('/api/llm/downloads/aria2/install'),
      ]);

      setOllamaInfo(await ollamaRes.json());
      setAria2Status(await aria2Res.json());
      setAria2Instructions(await aria2InstRes.json());
    } catch (err) {
      logger.error('Failed to fetch download info', { error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  // Handle overlay click to close
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  const isDark = theme === 'dark';

  return (
    <div className={`llm-overlay ${isDark ? '' : 'light'}`} onClick={handleOverlayClick}>
      <div className={`llm-modal llm-modal-compact ${isDark ? '' : 'light'}`}>
        <div className="llm-modal-header">
          <div className="llm-modal-header-left">
            <div className="llm-modal-icon">DL</div>
            <div className="llm-modal-title-group">
              <h2>Quick Setup</h2>
              <span className="llm-modal-subtitle">Get started with LLM features</span>
            </div>
          </div>
          <button className="llm-modal-close" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="llm-modal-content">
          {/* Platform indicator */}
          <div className="llm-platform-badge">
            {PLATFORM_ICONS[platform] || PLATFORM_ICONS.linux}
            <span>Detected: {platform.charAt(0).toUpperCase() + platform.slice(1)}</span>
          </div>

          {loading ? (
            <div className="llm-loading">
              <div className="llm-spinner"></div>
              <p>Loading...</p>
            </div>
          ) : (
            <>
              {/* Step 1: Ollama */}
              <div className="llm-setup-step">
                <div className="llm-step-number">1</div>
                <div className="llm-step-content">
                  <h3>Install Ollama</h3>
                  <p>Ollama runs LLMs locally on your machine</p>
                  
                  {ollamaInfo && (
                    <div className="llm-download-info">
                      <a
                        href={ollamaInfo.install_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="llm-download-btn"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        Download Ollama
                      </a>
                      
                      <div className="llm-instructions">
                        <h4>After installation:</h4>
                        <ol>
                          {ollamaInfo.instructions.map((inst, i) => (
                            <li key={i}>{inst}</li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 2: aria2 (Optional) */}
              <div className="llm-setup-step">
                <div className="llm-step-number">2</div>
                <div className="llm-step-content">
                  <h3>Install aria2 <span className="llm-optional">(Optional)</span></h3>
                  <p>Faster downloads with parallel connections</p>
                  
                  <div className="llm-aria2-status">
                    <span className={`llm-status-indicator ${aria2Status?.available ? 'available' : 'unavailable'}`}>
                      {aria2Status?.available ? 'Installed' : 'Not Installed'}
                    </span>
                    {aria2Status?.version && <span className="llm-version">{aria2Status.version}</span>}
                  </div>

                  {aria2Instructions && (
                    <div className="llm-install-commands">
                      <h4>Install via {aria2Instructions.instructions.method}:</h4>
                      <div className="llm-code-block">
                        {aria2Instructions.instructions.commands.map((cmd, i) => (
                          <div key={i} className="llm-code-line">
                            <code>{cmd}</code>
                            <button className="llm-copy-btn" onClick={() => copyToClipboard(cmd)}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                              </svg>
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 3: Download Model */}
              <div className="llm-setup-step">
                <div className="llm-step-number">3</div>
                <div className="llm-step-content">
                  <h3>Download a Model</h3>
                  <p>Pull a code-focused model for best results</p>
                  
                  <div className="llm-quick-commands">
                    <div className="llm-code-block">
                      <div className="llm-code-line">
                        <code>ollama pull codellama:7b</code>
                        <button className="llm-copy-btn" onClick={() => copyToClipboard('ollama pull codellama:7b')}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <p className="llm-command-note">Or use the LLM Settings panel to download models directly</p>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Tips */}
          <div className="llm-tips">
            <h4>Tips</h4>
            <ul>
              <li>Start with CodeLlama 7B - good balance of speed and quality</li>
              <li>8GB RAM minimum recommended for 7B models</li>
              <li>Models are stored locally and run offline</li>
              <li>Your data stays private - nothing is sent to external servers</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LLMDownloader;