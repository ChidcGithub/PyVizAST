import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30秒超时
const MAX_RETRIES = 2; // 最大重试次数
const RETRY_DELAY = 1000; // 重试延迟（毫秒）

// 判断是否应该重试的错误
const shouldRetry = (error) => {
  // 不重试的情况
  if (!error) return false;
  
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
const withRetry = async (requestFn, retries = MAX_RETRIES) => {
  try {
    return await requestFn();
  } catch (error) {
    // 如果不应该重试或已用完重试次数
    if (!shouldRetry(error) || retries <= 0) {
      throw error;
    }

    // 等待后重试
    await delay(RETRY_DELAY);
    return withRetry(requestFn, retries - 1);
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
      
      switch (status) {
        case 400:
          errorMessage = detail || '请求参数错误';
          break;
        case 401:
          errorMessage = '未授权，请先登录';
          break;
        case 403:
          errorMessage = '拒绝访问';
          break;
        case 404:
          errorMessage = detail || '请求的资源不存在';
          break;
        case 500:
          errorMessage = detail || '服务器内部错误';
          break;
        default:
          errorMessage = detail || `请求失败 (${status})`;
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
  return withRetry(async () => {
    const response = await api.post('/api/analyze', {
      code,
      options,
    }, {
      signal,
    });
    return response.data;
  });
};

/**
 * 获取AST图结构
 */
export const getAST = async (code, format = 'cytoscape', theme = 'default') => {
  return withRetry(async () => {
    const response = await api.post('/api/ast', {
      code,
      options: { format, theme },
    });
    return response.data;
  });
};

/**
 * 获取复杂度分析
 */
export const getComplexity = async (code) => {
  return withRetry(async () => {
    const response = await api.post('/api/complexity', { code });
    return response.data;
  });
};

/**
 * 获取性能问题
 */
export const getPerformanceIssues = async (code) => {
  return withRetry(async () => {
    const response = await api.post('/api/performance', { code });
    return response.data;
  });
};

/**
 * 获取安全问题
 */
export const getSecurityIssues = async (code) => {
  return withRetry(async () => {
    const response = await api.post('/api/security', { code });
    return response.data;
  });
};

/**
 * 获取优化建议
 */
export const getSuggestions = async (code) => {
  return withRetry(async () => {
    const response = await api.post('/api/suggestions', { code });
    return response.data;
  });
};

/**
 * 生成补丁
 */
export const generatePatches = async (code) => {
  return withRetry(async () => {
    const response = await api.post('/api/patches', { code });
    return response.data;
  });
};

/**
 * 获取节点解释（学习模式）
 */
export const explainNode = async (nodeId, code) => {
  const response = await api.post(`/api/learn/node/${nodeId}`, { code });
  return response.data;
};

/**
 * 获取挑战列表
 */
export const getChallenges = async () => {
  const response = await api.get('/api/challenges');
  return response.data;
};

/**
 * 获取挑战详情
 */
export const getChallenge = async (challengeId) => {
  const response = await api.get(`/api/challenges/${challengeId}`);
  return response.data;
};

/**
 * 提交挑战答案
 */
export const submitChallenge = async (challengeId, foundIssues) => {
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
    const response = await api.get('/api/health', { timeout: 5000 });
    return { connected: true, data: response.data };
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

export default api;
