/**
 * LLM Settings Component
 * 
 * Configure LLM integration settings for PyVizAST
 * 
 * @author Chidc
 * @link github.com/chidcGithub
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useToast } from './ToastContext';
import logger from '../utils/logger';
import {
  getLLMStatus,
  getLLMConfig,
  updateLLMConfig,
  getLLMModels,
  pullModel,
  deleteModel,
  getOllamaStatus,
  installOllama,
  startOllamaServer,
} from '../api';

/**
 * Recommended models for PyVizAST
 */
const RECOMMENDED_MODELS = [
  { name: 'codellama:7b', display: 'CodeLlama 7B', desc: 'Best for code analysis', ram: '8GB', size: '3.8GB' },
  { name: 'codellama:13b', display: 'CodeLlama 13B', desc: 'Better quality', ram: '16GB', size: '7.4GB' },
  { name: 'llama3.2:3b', display: 'Llama 3.2 3B', desc: 'Fast & efficient', ram: '6GB', size: '2.0GB' },
  { name: 'mistral:7b', display: 'Mistral 7B', desc: 'General purpose', ram: '8GB', size: '4.1GB' },
  { name: 'deepseek-coder:6.7b', display: 'DeepSeek Coder', desc: 'Python specialist', ram: '8GB', size: '3.8GB' },
  { name: 'qwen2.5-coder:7b', display: 'Qwen 2.5 Coder', desc: 'Multilingual', ram: '8GB', size: '4.7GB' },
];

/**
 * Format bytes to human readable
 */
const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

/**
 * LLM Settings Panel Component
 */
function LLMSettings({ isOpen, theme, onClose }) {
  const [config, setConfig] = useState({
    enabled: false,
    model: 'codellama:7b',
    base_url: 'http://localhost:11434',
    timeout: 60,
    temperature: 0.7,
    max_tokens: 2048,
    use_for_explanations: true,
    use_for_challenges: true,
    use_for_hints: true,
  });
  
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [installProgress, setInstallProgress] = useState(null);
  const [starting, setStarting] = useState(false);
  const [pulling, setPulling] = useState(null);
  const [pullProgress, setPullProgress] = useState(null);
  const toast = useToast();
  
  // Track if we've already auto-selected a model to prevent repeated updates
  const autoSelectDoneRef = useRef(false);

  // Define handleConfigChange first - used by other callbacks and effects
  const handleConfigChange = useCallback((key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  }, []);

  const fetchOllamaStatus = async () => {
    try {
      const data = await getOllamaStatus();
      setOllamaStatus(data);
    } catch (err) {
      logger.error('Failed to fetch Ollama status', { error: err.message });
      setOllamaStatus({ installed: false, running: false, can_auto_install: true });
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await getLLMStatus();
      setStatus(data);
    } catch (err) {
      logger.error('Failed to fetch LLM status', { error: err.message });
    }
  };

  const fetchConfig = async () => {
    try {
      const data = await getLLMConfig();
      setConfig(prev => ({ ...prev, ...data }));
    } catch (err) {
      logger.error('Failed to fetch LLM config', { error: err.message });
    }
  };

  const fetchModels = async () => {
    try {
      const data = await getLLMModels();
      setModels(data || []);
    } catch (err) {
      logger.error('Failed to fetch models', { error: err.message });
    }
  };

  // Fetch all status on open
  const fetchAll = useCallback(async () => {
    await Promise.all([
      fetchOllamaStatus(),
      fetchStatus(),
      fetchConfig(),
      fetchModels(),
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      fetchAll();
    }
  }, [isOpen, fetchAll]);

  // Auto-select first available model when models are loaded and no model is selected
  // Use ref to prevent repeated auto-selects which could cause render loops
  useEffect(() => {
    // Skip if already done or no models available
    if (autoSelectDoneRef.current || models.length === 0) return;
    
    // Check if we need to auto-select
    const needsSelection = !config.model || !models.some(m => m.name === config.model);
    
    if (needsSelection) {
      // Mark as done before updating to prevent loops
      autoSelectDoneRef.current = true;
      handleConfigChange('model', models[0].name);
    }
  }, [models, config.model, handleConfigChange]);
  
  // Reset auto-select flag when modal reopens
  useEffect(() => {
    if (isOpen) {
      autoSelectDoneRef.current = false;
    }
  }, [isOpen]);

  // Auto-select best model for code analysis
  // eslint-disable-next-line no-unused-vars
  const autoSelectBestModel = useCallback(() => {
    if (models.length === 0) {
      toast.info('No models installed. Please download a model first.');
      return;
    }

    // Priority order for code analysis
    const preferredModels = [
      'codellama:7b', 'codellama:13b', 'codellama',
      'deepseek-coder:6.7b', 'deepseek-coder',
      'qwen2.5-coder:7b', 'qwen2.5-coder',
      'mistral:7b', 'mistral',
      'llama3.2:3b', 'llama3.2', 'llama3',
    ];

    for (const preferred of preferredModels) {
      const found = models.find(m => m.name === preferred || m.name.startsWith(preferred.split(':')[0]));
      if (found) {
        handleConfigChange('model', found.name);
        toast.success(`Auto-selected: ${found.name}`);
        return;
      }
    }

    // Fallback to first available
    handleConfigChange('model', models[0].name);
    toast.success(`Auto-selected: ${models[0].name}`);
  }, [models, handleConfigChange, toast]);

  const handleSaveConfig = async () => {
    // Validate required fields
    if (config.enabled && !config.model) {
      toast.error('Please select a model before enabling LLM features');
      return;
    }
    
    if (config.enabled && !config.base_url) {
      toast.error('Please enter Ollama URL');
      return;
    }
    
    // Validate numeric fields
    if (config.temperature < 0 || config.temperature > 2) {
      toast.error('Temperature must be between 0 and 2');
      return;
    }
    
    if (config.max_tokens < 256 || config.max_tokens > 8192) {
      toast.error('Max tokens must be between 256 and 8192');
      return;
    }
    
    setLoading(true);
    try {
      const data = await updateLLMConfig(config);
      
      if (data.status === 'ok') {
        toast.success('LLM settings saved');
        setStatus(data.llm_status);
      } else {
        toast.error('Failed to save settings');
      }
    } catch (err) {
      toast.error('Failed to save settings');
      logger.error('Failed to save LLM config', { error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleInstallOllama = async () => {
    if (!ollamaStatus?.can_auto_install) {
      toast.error('Auto-install not supported on this platform');
      return;
    }

    setInstalling(true);
    setInstallProgress({ status: 'starting', progress: 0 });

    await installOllama(
      (progress) => {
        setInstallProgress({
          status: progress.status,
          progress: progress.progress || 0,
          error: progress.error,
        });

        if (progress.status === 'completed') {
          toast.success('Ollama installed successfully!');
          fetchOllamaStatus();
          setInstalling(false);
        }
      },
      (error) => {
        toast.error(`Installation failed: ${error}`);
        setInstalling(false);
      },
      () => {
        setInstalling(false);
      }
    );
  };

  const handleStartOllama = async () => {
    setStarting(true);
    try {
      const data = await startOllamaServer();

      if (data.status === 'started' || data.status === 'already_running') {
        toast.success('Ollama server started');
        await fetchAll();
      } else {
        toast.error('Failed to start Ollama server');
      }
    } catch (err) {
      toast.error('Failed to start Ollama server');
      logger.error('Ollama start failed', { error: err.message });
    } finally {
      setStarting(false);
    }
  };

  const handlePullModel = async (modelName) => {
    setPulling(modelName);
    setPullProgress({ status: 'starting', progress: 0 });

    await pullModel(
      modelName,
      (progress) => {
        // Safely calculate progress with NaN protection
        let progressPercent = 0;
        if (progress.completed != null && progress.total != null && progress.total > 0) {
          progressPercent = Math.round((progress.completed / progress.total) * 100);
          // Ensure it's a valid number
          if (isNaN(progressPercent) || !isFinite(progressPercent)) {
            progressPercent = 0;
          }
        }
        
        setPullProgress({
          status: progress.status || 'downloading',
          progress: progressPercent,
          digest: progress.digest,
          completed: progress.completed || 0,
          total: progress.total || 0,
        });
      },
      (error) => {
        toast.error(`Failed to pull model: ${error}`);
        setPulling(null);
        setPullProgress(null);
      },
      () => {
        toast.success(`Model ${modelName} downloaded successfully`);
        fetchModels();
        fetchStatus();
        setPulling(null);
        setPullProgress(null);
      }
    );
  };

  const handleDeleteModel = async (modelName) => {
    if (!window.confirm(`Delete model ${modelName}?`)) return;

    try {
      await deleteModel(modelName);
      toast.success(`Model ${modelName} deleted`);
      fetchModels();
      fetchStatus();
    } catch (err) {
      toast.error('Failed to delete model');
      logger.error('Model delete failed', { model: modelName, error: err.message });
    }
  };

  const isModelPulled = (modelName) => {
    const modelNameLower = modelName.toLowerCase();
    return models.some(m => {
      const installedName = m.name.toLowerCase();
      // Exact match (e.g., "codellama:7b" === "codellama:7b")
      if (installedName === modelNameLower) return true;
      // Check if installed model matches the recommended model with version
      // e.g., recommended "codellama:7b" should match installed "codeLlama:7b"
      // but NOT match "codellama:13b"
      const installedParts = installedName.split(':');
      const recommendedParts = modelNameLower.split(':');
      // If both have version tags, they must match exactly
      if (installedParts.length > 1 && recommendedParts.length > 1) {
        return installedParts[0] === recommendedParts[0] && installedParts[1] === recommendedParts[1];
      }
      // If only base name provided, match any version
      if (recommendedParts.length === 1) {
        return installedParts[0] === modelNameLower;
      }
      return false;
    });
  };

  // Handle overlay click to close
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

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

  if (!isOpen) return null;

  const isDark = theme === 'dark';
  const ollamaInstalled = ollamaStatus?.installed;
  const ollamaRunning = ollamaStatus?.running;

  return (
    <div className={`llm-overlay ${isDark ? '' : 'light'}`} onClick={handleOverlayClick}>
      <div className={`llm-modal ${isDark ? '' : 'light'}`}>
        <div className="llm-modal-header">
          <div className="llm-modal-header-left">
            <div className="llm-modal-icon">AI</div>
            <div className="llm-modal-title-group">
              <h2>LLM Settings</h2>
              <span className="llm-modal-subtitle">Configure local AI features</span>
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
          {/* Ollama Status Section */}
          <div className="llm-section">
            <h3>Ollama Status</h3>
            
            {!ollamaStatus ? (
              <div className="llm-loading">Checking Ollama status...</div>
            ) : (
              <div className={`llm-ollama-status ${ollamaRunning ? 'running' : ollamaInstalled ? 'installed' : 'not-installed'}`}>
                <div className="llm-ollama-status-icon">
                  {ollamaRunning ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  )}
                </div>
                <div className="llm-ollama-status-info">
                  <span className="llm-ollama-status-label">
                    {ollamaRunning ? 'Running' : ollamaInstalled ? 'Installed (Not Running)' : 'Not Installed'}
                  </span>
                  {ollamaStatus?.version && (
                    <span className="llm-ollama-version">v{ollamaStatus.version}</span>
                  )}
                </div>
                <div className="llm-ollama-actions">
                  {!ollamaInstalled && ollamaStatus?.can_auto_install && (
                    <button
                      className="llm-install-btn"
                      onClick={handleInstallOllama}
                      disabled={installing}
                    >
                      {installing ? 'Installing...' : 'Auto Install'}
                    </button>
                  )}
                  {!ollamaInstalled && !ollamaStatus?.can_auto_install && (
                    <a 
                      href="https://ollama.ai/download" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="llm-download-link"
                    >
                      Download Ollama
                    </a>
                  )}
                  {ollamaInstalled && !ollamaRunning && (
                    <button
                      className="llm-start-btn"
                      onClick={handleStartOllama}
                      disabled={starting}
                    >
                      {starting ? 'Starting...' : 'Start Server'}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Install Progress */}
            {installing && installProgress && (
              <div className="llm-install-progress">
                <div className="llm-progress-header">
                  <span>Installing Ollama...</span>
                  <span>{installProgress.progress.toFixed(0)}%</span>
                </div>
                <div className="llm-progress-bar">
                  <div className="llm-progress-fill" style={{ width: `${installProgress.progress}%` }} />
                </div>
                <span className="llm-progress-status">{installProgress.status}</span>
                {installProgress.error && (
                  <span className="llm-progress-error">{installProgress.error}</span>
                )}
              </div>
            )}
          </div>

          {/* Status Banner (only when LLM is enabled) */}
          {config.enabled && (
            <div className={`llm-status-banner ${status?.status || 'unavailable'}`}>
              <div className="llm-status-icon">
                {status?.status === 'ready' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                )}
              </div>
              <div className="llm-status-text">
                <span className="llm-status-label">{status?.status === 'ready' ? 'LLM Ready' : 'LLM Unavailable'}</span>
                <span className="llm-status-message">{status?.message || 'Checking status...'}</span>
              </div>
            </div>
          )}

          {/* Enable Toggle */}
          <div className="llm-section">
            <div className="llm-setting-row">
              <div className="llm-setting-info">
                <span className="llm-setting-label">Enable LLM Features</span>
                <span className="llm-setting-desc">Use local LLM for enhanced explanations and challenge generation</span>
              </div>
              <label className="llm-toggle">
                <input
                  type="checkbox"
                  checked={config.enabled}
                  onChange={(e) => handleConfigChange('enabled', e.target.checked)}
                  disabled={!ollamaRunning}
                />
                <span className="llm-toggle-slider"></span>
              </label>
            </div>
          </div>

          {config.enabled && ollamaRunning && (
            <>
              {/* Connection Settings */}
              <div className="llm-section">
                <h3>Connection</h3>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Ollama URL</span>
                  </div>
                  <input
                    type="text"
                    className="llm-input"
                    value={config.base_url}
                    onChange={(e) => handleConfigChange('base_url', e.target.value)}
                    placeholder="http://localhost:11434"
                  />
                </div>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Model</span>
                    <span className="llm-setting-desc">
                      {models.length > 0 ? `${models.length} model(s) installed` : 'No models installed'}
                    </span>
                  </div>
                  <div className="llm-model-select-wrapper">
                    <select
                      className="llm-select"
                      value={config.model}
                      onChange={(e) => handleConfigChange('model', e.target.value)}
                    >
                      {models.length > 0 ? (
                        models.map(m => (
                          <option key={m.name} value={m.name}>{m.name}</option>
                        ))
                      ) : (
                        RECOMMENDED_MODELS.map(m => (
                          <option key={m.name} value={m.name}>{m.display}</option>
                        ))
                      )}
                    </select>
                    {models.length > 0 && (
                      <button
                        className="llm-load-btn"
                        onClick={async () => {
                          setLoading(true);
                          try {
                            // Build the config to save
                            const newConfig = {
                              ...config,
                              enabled: true,
                              model: config.model || models[0].name,
                            };
                            
                            logger.debug('Loading LLM config', { newConfig });
                            const data = await updateLLMConfig(newConfig);
                            logger.debug('LLM config response', { data });
                            
                            if (data.status === 'ok') {
                              setConfig(newConfig);
                              
                              // Check actual status from response
                              const actualStatus = data.llm_status?.status;
                              const isReady = actualStatus === 'ready';
                              
                              logger.debug('LLM status check', { 
                                actualStatus, 
                                isReady,
                                llm_status: data.llm_status 
                              });
                              
                              setStatus({ ...status, ...data.llm_status, status: actualStatus || 'unavailable' });
                              
                              // Dispatch custom event to notify other components
                              window.dispatchEvent(new CustomEvent('llmConfigChanged', {
                                detail: { config: newConfig, status: data.llm_status }
                              }));
                              
                              if (isReady) {
                                toast.success(`LLM loaded: ${data.llm_status?.matched_model || newConfig.model}`);
                              } else {
                                toast.warning(data.llm_status?.message || 'Model not available');
                              }
                            } else {
                              toast.error('Failed to load LLM');
                            }
                          } catch (err) {
                            toast.error('Failed to load LLM');
                            logger.error('Failed to load LLM', { error: err.message });
                          } finally {
                            setLoading(false);
                          }
                        }}
                        title="Load model and enable LLM features"
                        disabled={loading}
                      >
                        {loading ? 'Loading...' : 'Load'}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Generation Settings */}
              <div className="llm-section">
                <h3>Generation</h3>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Temperature</span>
                    <span className="llm-setting-desc">Higher = more creative, Lower = more focused</span>
                  </div>
                  <div className="llm-range-wrapper">
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={config.temperature}
                      onChange={(e) => handleConfigChange('temperature', parseFloat(e.target.value))}
                    />
                    <span className="llm-range-value">{config.temperature}</span>
                  </div>
                </div>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Max Tokens</span>
                    <span className="llm-setting-desc">Maximum response length</span>
                  </div>
                  <input
                    type="number"
                    className="llm-input small"
                    value={config.max_tokens}
                    onChange={(e) => handleConfigChange('max_tokens', parseInt(e.target.value))}
                    min={256}
                    max={8192}
                  />
                </div>
              </div>

              {/* Feature Toggles */}
              <div className="llm-section">
                <h3>Features</h3>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Use for Explanations</span>
                    <span className="llm-setting-desc">Generate AST node explanations with LLM</span>
                  </div>
                  <label className="llm-toggle">
                    <input
                      type="checkbox"
                      checked={config.use_for_explanations}
                      onChange={(e) => handleConfigChange('use_for_explanations', e.target.checked)}
                    />
                    <span className="llm-toggle-slider"></span>
                  </label>
                </div>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Use for Challenges</span>
                    <span className="llm-setting-desc">Generate challenges with LLM</span>
                  </div>
                  <label className="llm-toggle">
                    <input
                      type="checkbox"
                      checked={config.use_for_challenges}
                      onChange={(e) => handleConfigChange('use_for_challenges', e.target.checked)}
                    />
                    <span className="llm-toggle-slider"></span>
                  </label>
                </div>
                <div className="llm-setting-row">
                  <div className="llm-setting-info">
                    <span className="llm-setting-label">Use for Hints</span>
                    <span className="llm-setting-desc">Generate contextual hints with LLM</span>
                  </div>
                  <label className="llm-toggle">
                    <input
                      type="checkbox"
                      checked={config.use_for_hints}
                      onChange={(e) => handleConfigChange('use_for_hints', e.target.checked)}
                    />
                    <span className="llm-toggle-slider"></span>
                  </label>
                </div>
              </div>

              {/* Model Management */}
              <div className="llm-section">
                <h3>Models</h3>
                
                {/* Pull Progress */}
                {pulling && pullProgress && (
                  <div className="llm-pull-progress">
                    <div className="llm-pull-progress-header">
                      <span>Pulling {pulling}</span>
                      <span>{pullProgress.progress}%</span>
                    </div>
                    <div className="llm-pull-progress-bar">
                      <div className="llm-pull-progress-fill" style={{ width: `${pullProgress.progress}%` }} />
                    </div>
                    <div className="llm-pull-progress-details">
                      <span className="llm-pull-status">{pullProgress.status}</span>
                      {pullProgress.completed && pullProgress.total && (
                        <span className="llm-pull-size">
                          {formatBytes(pullProgress.completed)} / {formatBytes(pullProgress.total)}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Recommended Models */}
                <div className="llm-recommended-models">
                  <h4>Recommended Models</h4>
                  <div className="llm-model-grid">
                    {RECOMMENDED_MODELS.map(model => (
                      <div key={model.name} className={`llm-model-card ${isModelPulled(model.name) ? 'pulled' : ''}`}>
                        <div className="llm-model-info">
                          <span className="llm-model-name">{model.display}</span>
                          <span className="llm-model-desc">{model.desc}</span>
                          <div className="llm-model-meta">
                            <span>RAM: {model.ram}</span>
                            <span>Size: {model.size}</span>
                          </div>
                        </div>
                        <div className="llm-model-actions">
                          {isModelPulled(model.name) ? (
                            (() => {
                              // Find the actual installed model that matches this recommended model
                              const installedModel = models.find(m => 
                                m.name.toLowerCase() === model.name.toLowerCase() || 
                                m.name.toLowerCase().startsWith(model.name.split(':')[0].toLowerCase())
                              );
                              // Check if this specific installed model is currently in use
                              const isInUse = installedModel && 
                                (config.model?.toLowerCase() === installedModel.name.toLowerCase());
                              
                              return isInUse ? (
                                <span className="llm-model-status active">
                                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="20 6 9 17 4 12" />
                                  </svg>
                                  In Use
                                </span>
                              ) : (
                                <button
                                  className="llm-model-use-btn"
                                  onClick={() => handleConfigChange('model', installedModel?.name || model.name)}
                                >
                                  Use
                                </button>
                              );
                            })()
                          ) : (
                            <button
                              className="llm-model-pull-btn"
                              onClick={() => handlePullModel(model.name)}
                              disabled={pulling !== null}
                            >
                              {pulling === model.name ? 'Downloading...' : 'Download'}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Installed Models */}
                {models.length > 0 && (
                  <div className="llm-installed-models">
                    <h4>Installed Models ({models.length})</h4>
                    <div className="llm-model-list">
                      {models.map(model => (
                        <div key={model.name} className="llm-installed-model">
                          <span className="llm-model-name">{model.name}</span>
                          <span className="llm-model-size">{formatBytes(model.size)}</span>
                          <button
                            className="llm-model-delete-btn"
                            onClick={() => handleDeleteModel(model.name)}
                          >
                            Delete
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Save Button */}
          <div className="llm-section llm-actions">
            <button
              className="llm-save-btn"
              onClick={handleSaveConfig}
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
          </div>

          {/* Help */}
          <div className="llm-help">
            <h4>Need Help?</h4>
            <ol>
              <li>Click "Auto Install" to install Ollama automatically</li>
              <li>Or install manually from <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer">ollama.ai</a></li>
              <li>Click "Start Server" to start Ollama</li>
              <li>Download a model from the list above</li>
              <li>Enable LLM features and save settings</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LLMSettings;