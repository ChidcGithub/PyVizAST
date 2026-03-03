"""
Security Scanner - 安全性扫描
检测SQL注入、不安全反序列化、硬编码密钥等
"""
import ast
import re
from typing import List, Dict, Any, Optional, Set
from ..models.schemas import CodeIssue, SeverityLevel


class SecurityScanner:
    """安全漏洞扫描器"""
    
    # 危险函数列表
    DANGEROUS_FUNCTIONS = {
        'eval': {
            'severity': SeverityLevel.CRITICAL,
            'message': '使用eval()可能导致代码注入漏洞',
            'suggestion': '使用ast.literal_eval()或json.loads()替代'
        },
        'exec': {
            'severity': SeverityLevel.CRITICAL,
            'message': '使用exec()可能导致代码注入漏洞',
            'suggestion': '重构代码避免动态执行'
        },
        'compile': {
            'severity': SeverityLevel.WARNING,
            'message': '使用compile()可能存在安全风险',
            'suggestion': '确保源代码来源可信'
        },
        '__import__': {
            'severity': SeverityLevel.WARNING,
            'message': '动态导入模块可能导致安全问题',
            'suggestion': '使用importlib替代'
        },
    }
    
    # 敏感词模式（用于检测硬编码密钥）
    SENSITIVE_PATTERNS = [
        (r'(?i)(password|passwd|pwd)\s*=\s*[\'"][^\'"]+[\'"]', '密码'),
        (r'(?i)(api_key|apikey|api_secret)\s*=\s*[\'"][^\'"]+[\'"]', 'API密钥'),
        (r'(?i)(secret|secret_key)\s*=\s*[\'"][^\'"]+[\'"]', '密钥'),
        (r'(?i)(token|auth_token|access_token)\s*=\s*[\'"][^\'"]+[\'"]', '令牌'),
        (r'(?i)(private_key|privatekey)\s*=\s*[\'"][^\'"]+[\'"]', '私钥'),
        (r'(?i)(aws_access_key|aws_secret)\s*=\s*[\'"][^\'"]+[\'"]', 'AWS凭证'),
        (r'(?i)(database_url|db_password)\s*=\s*[\'"][^\'"]+[\'"]', '数据库凭证'),
    ]
    
    # SQL注入风险模式
    SQL_PATTERNS = [
        r'execute\s*\([^)]*%s',
        r'execute\s*\([^)]*format',
        r'execute\s*\([^)]*f[\'"]',
        r'execute\s*\([^)]*\+',
        r'cursor\.execute\s*\([^)]*\.',
    ]
    
    # 不安全的反序列化
    UNSAFE_DESERIALIZE = {
        'pickle.loads': 'pickle反序列化可能导致任意代码执行',
        'pickle.load': 'pickle反序列化可能导致任意代码执行',
        'yaml.unsafe_load': 'YAML不安全加载可能导致任意代码执行',
        'marshal.loads': 'marshal反序列化存在安全风险',
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.issue_counter = 0
    
    def _generate_issue_id(self, issue_type: str) -> str:
        self.issue_counter += 1
        return f"security_{issue_type}_{self.issue_counter}"
    
    def scan(self, code: str, tree: Optional[ast.AST] = None) -> List[CodeIssue]:
        """
        扫描代码安全漏洞
        
        Args:
            code: 源代码字符串
            tree: 可选的AST树
        
        Returns:
            安全问题列表
        """
        if tree is None:
            tree = ast.parse(code)
        
        self.issues = []
        self.issue_counter = 0
        
        source_lines = code.splitlines()
        
        # 执行各项安全检查
        self._check_dangerous_functions(tree)
        self._check_sql_injection(code, tree)
        self._check_hardcoded_secrets(code, source_lines)
        self._check_unsafe_deserialization(tree)
        self._check_command_injection(tree)
        self._check_path_traversal(tree)
        self._check_weak_crypto(tree)
        self._check_insecure_defaults(tree)
        
        return self.issues
    
    def _check_dangerous_functions(self, tree: ast.AST):
        """检查危险函数调用"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in self.DANGEROUS_FUNCTIONS:
                    danger_info = self.DANGEROUS_FUNCTIONS[func_name]
                    
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("dangerous_func"),
                        type="security",
                        severity=danger_info['severity'],
                        message=danger_info['message'],
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        documentation_url="https://owasp.org/www-community/attacks/Code_Injection"
                    ))
    
    def _check_sql_injection(self, code: str, tree: ast.AST):
        """检查SQL注入风险"""
        
        # 使用正则表达式快速扫描
        for i, line in enumerate(code.splitlines(), 1):
            for pattern in self.SQL_PATTERNS:
                if re.search(pattern, line):
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("sql_injection"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message="可能的SQL注入漏洞，请使用参数化查询",
                        lineno=i,
                        source_snippet=line.strip(),
                        documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                    ))
        
        # AST级别的检查
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('execute', 'executemany'):
                        # 检查参数是否是字符串拼接
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                                # 使用 % 格式化
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("sql_format"),
                                    type="security",
                                    severity=SeverityLevel.WARNING,
                                    message="SQL查询使用字符串格式化，可能存在注入风险",
                                    lineno=node.lineno,
                                    documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                                ))
                            elif isinstance(arg, ast.JoinedStr):
                                # f-string
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("sql_fstring"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message="SQL查询使用f-string格式化，存在SQL注入风险",
                                    lineno=node.lineno,
                                    documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                                ))
    
    def _check_hardcoded_secrets(self, code: str, source_lines: List[str]):
        """检查硬编码的敏感信息"""
        # 编译一个匹配注释行开头（包括缩进）的正则
        comment_pattern = re.compile(r'^\s*#')
        # 匹配多行字符串开头
        multiline_string_start = re.compile(r'^\s*(\'\'\'|""")')
        
        for i, line in enumerate(source_lines, 1):
            # 跳过注释行
            if comment_pattern.match(line):
                continue
            
            # 跳过多行字符串内的内容（简化处理）
            if multiline_string_start.search(line):
                continue
            
            for pattern, secret_type in self.SENSITIVE_PATTERNS:
                if re.search(pattern, line):
                    # 排除明显的占位符和示例值
                    stripped = line.strip().lower()
                    placeholder_indicators = [
                        'xxx', 'your_', 'example', 'placeholder', 'sample',
                        'changeme', 'todo', 'fixme', '<', '>', 'dummy',
                        'test_key', 'fake', 'mock'
                    ]
                    
                    # 如果行中包含占位符指示词，跳过
                    if any(indicator in stripped for indicator in placeholder_indicators):
                        continue
                    
                    # 检查值是否是明显的占位符
                    # 提取等号右边的值
                    value_match = re.search(r'=\s*["\']([^"\']+)["\']', line)
                    if value_match:
                        value = value_match.group(1).lower()
                        if any(indicator in value for indicator in placeholder_indicators):
                            continue
                        # 跳过太短的值（很可能是占位符）
                        if len(value) < 4:
                            continue
                    
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("hardcoded_secret"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message=f"检测到硬编码的{secret_type}",
                        lineno=i,
                        source_snippet=stripped[:50] + ('...' if len(stripped) > 50 else ''),
                        documentation_url="https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password"
                    ))
    
    def _check_unsafe_deserialization(self, tree: ast.AST):
        """检查不安全的反序列化"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 获取函数完整名称
                func_full_name = self._get_func_full_name(node.func)
                
                if func_full_name in self.UNSAFE_DESERIALIZE:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("unsafe_deserialize"),
                        type="security",
                        severity=SeverityLevel.CRITICAL,
                        message=self.UNSAFE_DESERIALIZE[func_full_name],
                        lineno=node.lineno,
                        documentation_url="https://owasp.org/www-community/attacks/Deserialization_of_untrusted_data"
                    ))
    
    def _get_func_full_name(self, node: ast.AST) -> str:
        """获取函数的完整名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_full_name(node.value)
            return f"{value_name}.{node.attr}"
        return ""
    
    def _check_command_injection(self, tree: ast.AST):
        """检查命令注入风险"""
        os_functions = {'system', 'popen', 'spawn', 'call', 'run'}
        subprocess_functions = {'call', 'run', 'Popen', 'check_output'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # os.system, os.popen
                if func_full_name.startswith('os.'):
                    # 确保 node.func 是 ast.Attribute 类型才能访问 attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in os_functions:
                        # 检查参数
                        if node.args:
                            arg = node.args[0]
                            if not isinstance(arg, ast.Constant):
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("command_injection"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message=f"使用os.{node.func.attr}()可能导致命令注入",
                                    lineno=node.lineno,
                                    suggestion="使用subprocess模块并设置shell=False"
                                ))
                
                # subprocess with shell=True
                elif func_full_name.startswith('subprocess.'):
                    # 确保 node.func 是 ast.Attribute 类型才能访问 attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in subprocess_functions:
                        for keyword in node.keywords:
                            if keyword.arg == 'shell':
                                if isinstance(keyword.value, ast.Constant) and keyword.value.value == True:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("shell_true"),
                                        type="security",
                                        severity=SeverityLevel.ERROR,
                                        message="subprocess使用shell=True存在命令注入风险",
                                        lineno=node.lineno,
                                        suggestion="使用shell=False并传递参数列表"
                                    ))
    
    def _check_path_traversal(self, tree: ast.AST):
        """检查路径遍历风险"""
        file_operations = {'open', 'read', 'write', 'mkdir', 'makedirs', 'remove', 'unlink'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in file_operations:
                    if node.args:
                        arg = node.args[0]
                        # 检查是否使用了用户输入
                        if isinstance(arg, ast.BinOp) or isinstance(arg, ast.JoinedStr):
                            self.issues.append(CodeIssue(
                                id=self._generate_issue_id("path_traversal"),
                                type="security",
                                severity=SeverityLevel.WARNING,
                                message="文件操作可能存在路径遍历风险",
                                lineno=node.lineno,
                                suggestion="验证和清理用户输入的路径"
                            ))
    
    def _check_weak_crypto(self, tree: ast.AST):
        """检查弱加密算法"""
        weak_algorithms = {'md5', 'sha1', 'des', 'rc4', 'blowfish'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # hashlib
                if func_full_name.startswith('hashlib.'):
                    algo_name = node.func.attr.lower()
                    if algo_name in weak_algorithms:
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("weak_crypto"),
                            type="security",
                            severity=SeverityLevel.WARNING,
                            message=f"使用弱哈希算法 {algo_name}，建议使用sha256或sha3",
                            lineno=node.lineno
                        ))
                
                # Crypto/PyCryptodome
                elif 'DES' in func_full_name or 'RC4' in func_full_name:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("weak_cipher"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message="使用弱加密算法，建议使用AES",
                        lineno=node.lineno
                    ))
    
    def _check_insecure_defaults(self, tree: ast.AST):
        """检查不安全的默认配置"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # SSL/TLS 验证
                if 'requests' in func_full_name or 'httpx' in func_full_name:
                    for keyword in node.keywords:
                        if keyword.arg == 'verify':
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value == False:
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("ssl_verify"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message="禁用SSL证书验证存在中间人攻击风险",
                                    lineno=node.lineno
                                ))
                
                # 禁用CSRF保护等
                if 'csrf' in func_full_name.lower():
                    for keyword in node.keywords:
                        if keyword.arg in ('enabled', 'disable'):
                            if isinstance(keyword.value, ast.Constant):
                                # 检查 enabled=False 或 disable=True 的情况
                                is_disabled = (
                                    (keyword.arg == 'enabled' and keyword.value.value == False) or
                                    (keyword.arg == 'disable' and keyword.value.value == True)
                                )
                                if is_disabled:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("csrf_disabled"),
                                        type="security",
                                        severity=SeverityLevel.WARNING,
                                        message="禁用CSRF保护可能导致安全漏洞",
                                        lineno=node.lineno
                                    ))
    
    def get_security_summary(self) -> Dict[str, int]:
        """获取安全扫描摘要"""
        summary = {
            'critical': 0,
            'error': 0,
            'warning': 0,
            'info': 0
        }
        
        for issue in self.issues:
            if issue.severity == SeverityLevel.CRITICAL:
                summary['critical'] += 1
            elif issue.severity == SeverityLevel.ERROR:
                summary['error'] += 1
            elif issue.severity == SeverityLevel.WARNING:
                summary['warning'] += 1
            else:
                summary['info'] += 1
        
        return summary
