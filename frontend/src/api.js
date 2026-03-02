import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30秒超时
const MAX_RETRIES = 2; // 最大重试次数
const RETRY_DELAY = 1000; // 重试延迟（毫秒）

// 幂等方法列表（可以安全重试）
const IDEMPOTENT_METHODS = ['get', 'head', 'options', 'put', 'delete'];

// 判断是否应该重试的错误
const shouldRetry = (error, method) => {
  // 不重试的情况
  if (!error) return false;
  
  // 非幂等方法不重试（避免重复操作）
  if (method && !IDEMPOTENT_METHODS.includes(method.toLowerCase())) {
    return false;
  }
  
  // 4xx 错误不重试（客户端错误）
  if (error.response?.status >= 400 && error.response?.status < 500) {
    return false;
  }
  
  // 超时、网络错误、5xx 服务器错误可以重试
  return (
    error.code === 'ECONNABORTED' ||
    error.code === 'ERR_NETWORK' ||
    error.code === 'ECONNRESET' ||
    error.message?.includes('timeout') ||
    error.message?.includes('Network Error') ||
    (error.response?.status >= 500)
  );
};

// 延迟函数
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 带重试的请求包装器
const withRetry = async (requestFn, method = 'get', retries = MAX_RETRIES) => {
  try {
    return await requestFn();
  } catch (error) {
    // 如果不应该重试或已用完重试次数
    if (!shouldRetry(error, method) || retries <= 0) {
      throw error;
    }

    // 等待后重试
    await delay(RETRY_DELAY);
    return withRetry(requestFn, method, retries - 1);
  }
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token 等
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 辅助函数：从 detail 中提取可读的错误消息
const extractErrorMessage = (detail) => {
  if (!detail) return null;
  
  // 字符串直接返回
  if (typeof detail === 'string') return detail;
  
  // Pydantic 验证错误数组格式: [{type, loc, msg, ...}, ...]
  if (Array.isArray(detail)) {
    const messages = detail.map(err => {
      // 提取字段名和错误消息
      const field = err.loc?.join('.') || '';
      const msg = err.msg || err.message || JSON.stringify(err);
      return field ? `${field}: ${msg}` : msg;
    });
    return messages.join('; ');
  }
  
  // 对象格式
  if (typeof detail === 'object') {
    // 尝试提取常见字段
    if (detail.message) return detail.message;
    if (detail.msg) return detail.msg;
    if (detail.error) return detail.error;
    // 转换为 JSON 字符串
    try {
      return JSON.stringify(detail);
    } catch {
      return '未知错误';
    }
  }
  
  return String(detail);
};

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let errorMessage = '请求失败';
    
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      errorMessage = '请求超时，请检查网络连接或稍后重试';
    } else if (error.response) {
      // 服务器返回错误
      const status = error.response.status;
      const detail = error.response.data?.detail;
      const extractedMsg = extractErrorMessage(detail);
      
      switch (status) {
        case 400:
          errorMessage = extractedMsg || '请求参数错误';
          break;
        case 401:
          errorMessage = '未授权，请先登录';
          break;
        case 403:
          errorMessage = '拒绝访问';
          break;
        case 404:
          errorMessage = extractedMsg || '请求的资源不存在';
          break;
        case 422:
          // Pydantic 验证错误
          errorMessage = extractedMsg || '请求参数验证失败';
          break;
        case 500:
          errorMessage = extractedMsg || '服务器内部错误';
          break;
        default:
          errorMessage = extractedMsg || `请求失败 (${status})`;
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器，请检查服务器是否运行';
    }
    
    // 创建带有友好消息的错误对象
    const friendlyError = new Error(errorMessage);
    friendlyError.originalError = error;
    friendlyError.status = error.response?.status;
    
    return Promise.reject(friendlyError);
  }
);

/**
 * 分析Python代码
 * @param {string} code - Python代码
 * @param {Object} options - 分析选项
 * @param {AbortSignal} signal - 可选的取消信号
 */
export const analyzeCode = async (code, options = {}, signal = null) => {
  // POST 请求不重试，避免重复分析
  const response = await api.post('/api/analyze', {
    code,
    options,
  }, {
    signal,
  });
  return response.data;
};

/**
 * 获取AST图结构
 */
export const getAST = async (code, format = 'cytoscape', theme = 'default') => {
  // POST 请求不重试
  const response = await api.post('/api/ast', {
    code,
    options: { format, theme },
  });
  return response.data;
};

/**
 * 获取复杂度分析
 */
export const getComplexity = async (code) => {
  // POST 请求不重试
  const response = await api.post('/api/complexity', { code });
  return response.data;
};

/**
 * 获取性能问题
 */
export const getPerformanceIssues = async (code) => {
  // POST 请求不重试
  const response = await api.post('/api/performance', { code });
  return response.data;
};

/**
 * 获取安全问题
 */
export const getSecurityIssues = async (code) => {
  // POST 请求不重试
  const response = await api.post('/api/security', { code });
  return response.data;
};

/**
 * 获取优化建议
 */
export const getSuggestions = async (code) => {
  // POST 请求不重试
  const response = await api.post('/api/suggestions', { code });
  return response.data;
};

/**
 * 生成补丁
 */
export const generatePatches = async (code) => {
  // POST 请求不重试
  const response = await api.post('/api/patches', { code });
  return response.data;
};

/**
 * 获取节点解释（学习模式）
 */
export const explainNode = async (nodeId, code) => {
  // POST 请求不重试
  const response = await api.post(`/api/learn/node/${nodeId}`, { code });
  return response.data;
};

/**
 * 获取挑战列表
 */
export const getChallenges = async () => {
  // GET 请求可以安全重试
  return withRetry(async () => {
    const response = await api.get('/api/challenges');
    return response.data;
  }, 'get');
};

/**
 * 获取挑战详情
 */
export const getChallenge = async (challengeId) => {
  // GET 请求可以安全重试
  return withRetry(async () => {
    const response = await api.get(`/api/challenges/${challengeId}`);
    return response.data;
  }, 'get');
};

/**
 * 提交挑战答案
 */
export const submitChallenge = async (challengeId, foundIssues) => {
  // POST 请求不重试，避免重复提交
  const response = await api.post('/api/challenges/submit', {
    challenge_id: challengeId,
    found_issues: foundIssues,
  });
  return response.data;
};

/**
 * 检查服务器连接状态
 */
export const checkServerHealth = async () => {
  try {
    // GET 请求可以安全重试
    return withRetry(async () => {
      const response = await api.get('/api/health', { timeout: 5000 });
      return { connected: true, data: response.data };
    }, 'get');
  } catch (error) {
    return { 
      connected: false, 
      error: error.message,
      hint: '请确保后端服务器正在运行 (python run.py backend)'
    };
  }
};

/**
 * 获取API基础URL
 */
export const getApiBaseUrl = () => API_BASE_URL;

/**
 * 上传并分析项目（zip文件）
 * @param {File} file - zip文件对象
 * @param {boolean} quickMode - 快速模式（仅复杂度分析）
 * @param {AbortSignal} signal - 可选的取消信号
 */
export const analyzeProject = async (file, quickMode = false, signal = null) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(`/api/project/analyze?quick_mode=${quickMode}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 120000, // 项目分析可能需要更长时间，设置2分钟超时
    signal,
  });
  return response.data;
};

/**
 * 上传项目并获取文件列表（快速预览）
 * @param {File} file - zip文件对象
 */
export const uploadProject = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/project/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
  });
  return response.data;
};

export default api;
