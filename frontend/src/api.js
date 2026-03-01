import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30秒超时

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
  const response = await api.post('/api/complexity', { code });
  return response.data;
};

/**
 * 获取性能问题
 */
export const getPerformanceIssues = async (code) => {
  const response = await api.post('/api/performance', { code });
  return response.data;
};

/**
 * 获取安全问题
 */
export const getSecurityIssues = async (code) => {
  const response = await api.post('/api/security', { code });
  return response.data;
};

/**
 * 获取优化建议
 */
export const getSuggestions = async (code) => {
  const response = await api.post('/api/suggestions', { code });
  return response.data;
};

/**
 * 生成补丁
 */
export const generatePatches = async (code) => {
  const response = await api.post('/api/patches', { code });
  return response.data;
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

export default api;
