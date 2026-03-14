"""
Security Scanner - Security vulnerability scanning
Detects SQL injection, unsafe deserialization, hardcoded secrets, etc.
"""
import ast
import os
import re
from typing import List, Dict, Optional
from ..models.schemas import CodeIssue, SeverityLevel


class SecurityScanner:
    """Security Vulnerability Scanner"""
    
    # List of dangerous functions
    DANGEROUS_FUNCTIONS = {
        'eval': {
            'severity': SeverityLevel.CRITICAL,
            'message': 'Using eval() may lead to code injection vulnerabilities',
            'suggestion': 'Use ast.literal_eval() or json.loads() instead'
        },
        'exec': {
            'severity': SeverityLevel.CRITICAL,
            'message': 'Using exec() may lead to code injection vulnerabilities',
            'suggestion': 'Refactor code to avoid dynamic execution'
        },
        'compile': {
            'severity': SeverityLevel.WARNING,
            'message': 'Using compile() may pose security risks',
            'suggestion': 'Ensure source code is from a trusted source'
        },
        '__import__': {
            'severity': SeverityLevel.WARNING,
            'message': 'Dynamic module import may cause security issues',
            'suggestion': 'Use importlib instead'
        },
    }
    
    # Sensitive word patterns (for detecting hardcoded secrets)
    # Updated to handle escaped quotes in string values
    SENSITIVE_PATTERNS = [
        # Password patterns
        (r'(?i)(password|passwd|pwd)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'password'),
        (r'(?i)(password|passwd|pwd)\s*=\s*[\'"][^\'"]{8,}[\'"]', 'password'),  # Longer passwords
        
        # API keys and secrets
        (r'(?i)(api_key|apikey|api_secret|api-key)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'API key'),
        (r'(?i)api[_-]?key[_-]?\w*\s*=\s*[\'"][a-zA-Z0-9_\-]{16,}[\'"]', 'API key'),  # API_KEY_XXX pattern
        (r'(?i)(secret|secret_key|secretkey)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'secret key'),
        (r'(?i)secret[_-]?key[_-]?\w*\s*=\s*[\'"][a-zA-Z0-9_\-]{16,}[\'"]', 'secret key'),
        
        # Token patterns
        (r'(?i)(token|auth_token|access_token|bearer|jwt)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'token'),
        (r'(?i)(token|auth_token|access_token)\s*=\s*[\'"][a-zA-Z0-9_\-\.]{20,}[\'"]', 'token'),
        (r'(?i)jwt[_-]?secret\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'JWT secret'),
        
        # Private keys
        (r'(?i)(private_key|privatekey|private-key)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'private key'),
        (r'(?i)(private_key|privatekey)\s*=\s*[\'"][\'"]-----BEGIN', 'private key'),  # PEM format
        
        # Cloud provider credentials
        (r'(?i)(aws_access_key|aws_secret|aws_key)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'AWS credential'),
        (r'(?i)(gcp_key|gcp_secret|google_api_key)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'GCP credential'),
        (r'(?i)(azure_key|azure_secret|azure_connection_string)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'Azure credential'),
        
        # Database credentials
        (r'(?i)(database_url|db_password|db_user|db_host)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'database credential'),
        (r'(?i)(mongodb_uri|mongo_url|postgres_url|mysql_url)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'database URL'),
        
        # OAuth and authentication
        (r'(?i)(oauth_token|oauth_secret|client_secret)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'OAuth credential'),
        (r'(?i)(client_id|client_secret)\s*=\s*[\'"][a-zA-Z0-9_\-]{16,}[\'"]', 'OAuth credential'),
        
        # Encryption keys
        (r'(?i)(encryption_key|encrypt_key|cipher_key)\s*=\s*[\'"](?:[^\'"\\]|\\.)*[\'"]', 'encryption key'),
        (r'(?i)(salt|iv)\s*=\s*[\'"][a-zA-Z0-9_\-]{8,}[\'"]', 'encryption salt/IV'),
    ]
    
    # SQL injection risk patterns
    SQL_PATTERNS = [
        r'execute\s*\([^)]*%s',
        r'execute\s*\([^)]*format',
        r'execute\s*\([^)]*f[\'"]',
        r'execute\s*\([^)]*\+',
        r'cursor\.execute\s*\([^)]*\.',
    ]
    
    # Unsafe deserialization
    UNSAFE_DESERIALIZE = {
        'pickle.loads': 'pickle deserialization may lead to arbitrary code execution',
        'pickle.load': 'pickle deserialization may lead to arbitrary code execution',
        'yaml.unsafe_load': 'YAML unsafe load may lead to arbitrary code execution',
        'marshal.loads': 'marshal deserialization has security risks',
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.issue_counter = 0
    
    def _generate_issue_id(self, issue_type: str) -> str:
        self.issue_counter += 1
        return f"security_{issue_type}_{self.issue_counter}"
    
    def scan(self, code: str, tree: Optional[ast.AST] = None) -> List[CodeIssue]:
        """
        Scan code for security vulnerabilities
        
        Args:
            code: Source code string
            tree: Optional AST tree
        
        Returns:
            List of security issues
        """
        if tree is None:
            tree = ast.parse(code)
        
        self.issues = []
        self.issue_counter = 0
        
        source_lines = code.splitlines()
        
        # Execute various security checks
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
        """Check for dangerous function calls"""
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
        """Check for SQL injection risks"""
        
        # Quick scan with regex
        for i, line in enumerate(code.splitlines(), 1):
            for pattern in self.SQL_PATTERNS:
                if re.search(pattern, line):
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("sql_injection"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message="Possible SQL injection vulnerability, please use parameterized queries",
                        lineno=i,
                        source_snippet=line.strip(),
                        documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                    ))
        
        # AST-level checks
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('execute', 'executemany'):
                        # Check if arguments are string concatenation
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                                # Using % formatting
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("sql_format"),
                                    type="security",
                                    severity=SeverityLevel.WARNING,
                                    message="SQL query uses string formatting, may have injection risk",
                                    lineno=node.lineno,
                                    documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                                ))
                            elif isinstance(arg, ast.JoinedStr):
                                # f-string
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("sql_fstring"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message="SQL query uses f-string formatting, has SQL injection risk",
                                    lineno=node.lineno,
                                    documentation_url="https://owasp.org/www-community/attacks/SQL_Injection"
                                ))
    
    def _check_hardcoded_secrets(self, code: str, source_lines: List[str]):
        """Check for hardcoded sensitive information"""
        # Compile a regex matching comment line start (including indentation)
        comment_pattern = re.compile(r'^\s*#')
        # Match multiline string start
        multiline_string_start = re.compile(r'^\s*(\'\'\'|""")')
        
        # Patterns that indicate dynamic value assignment (not hardcoded)
        dynamic_patterns = [
            r'os\.getenv\s*\(',  # os.getenv('VAR')
            r'os\.environ',       # os.environ['VAR']
            r'environ\.get\s*\(', # environ.get('VAR')
            r'getenv\s*\(',       # getenv('VAR')
            r'config\.',          # config.password
            r'settings\.',        # settings.secret_key
            r'self\.\w+\s*=\s*[^"\']',  # self.attr = value (not string literal)
            r'\.\w+\s*\(\s*\)',   # method call
            r'input\s*\(',        # input()
            r'args\.',            # args.password
            r'ArgumentParser',    # argparse
        ]
        dynamic_regex = re.compile('|'.join(dynamic_patterns))
        
        # Maximum line length to prevent regex backtracking attacks
        MAX_LINE_LENGTH = 2000
        
        for i, line in enumerate(source_lines, 1):
            # Skip very long lines to prevent regex performance issues
            if len(line) > MAX_LINE_LENGTH:
                continue
            
            # Skip comment lines
            if comment_pattern.match(line):
                continue
            
            # Skip content inside multiline strings (simplified handling)
            if multiline_string_start.search(line):
                continue
            
            # Skip lines with dynamic value sources
            if dynamic_regex.search(line):
                continue
            
            for pattern, secret_type in self.SENSITIVE_PATTERNS:
                if re.search(pattern, line):
                    # Exclude obvious placeholders and example values
                    stripped = line.strip().lower()
                    placeholder_indicators = [
                        'xxx', 'your_', 'example', 'placeholder', 'sample',
                        'changeme', 'todo', 'fixme', '<', '>', 'dummy',
                        'test_key', 'fake', 'mock', 'redacted', 'hidden',
                        '****', '####', 'none', 'null', 'empty'
                    ]
                    
                    # Skip if line contains placeholder indicators
                    if any(indicator in stripped for indicator in placeholder_indicators):
                        continue
                    
                    # Check if value is an obvious placeholder
                    # Extract the value on the right side of the equals sign
                    value_match = re.search(r'=\s*["\']([^"\']+)["\']', line)
                    if value_match:
                        value = value_match.group(1).lower()
                        original_value = value_match.group(1)
                        if any(indicator in value for indicator in placeholder_indicators):
                            continue
                        # Skip values that are too short and look like placeholders
                        # (very short values like "123", "abc", "key" are likely placeholders)
                        if len(value) < 3:
                            continue
                        # Skip if value is purely numeric and short (likely placeholder like "12345")
                        if value.isdigit() and len(value) <= 6:
                            continue
                        # Skip values that look like variable names (no special chars, starts with letter)
                        if re.match(r'^[a-z_][a-z0-9_]*$', original_value):
                            # Could be a variable name being passed, skip
                            continue
                    
                    # Check for f-string or variable interpolation
                    if 'f"' in line or "f'" in line or '{' in line:
                        continue
                    
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("hardcoded_secret"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message=f"Detected hardcoded {secret_type}",
                        lineno=i,
                        source_snippet=stripped[:50] + ('...' if len(stripped) > 50 else ''),
                        documentation_url="https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password"
                    ))
    
    def _check_unsafe_deserialization(self, tree: ast.AST):
        """Check for unsafe deserialization"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Get full function name
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
        """Get full name of a function"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_full_name(node.value)
            return f"{value_name}.{node.attr}"
        return ""
    
    def _check_command_injection(self, tree: ast.AST):
        """Check for command injection risks"""
        # Extended list of dangerous os functions
        os_functions = {'system', 'popen', 'spawn', 'spawnl', 'spawnle', 'spawnlp', 
                        'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe',
                        'call', 'run', 'startfile'}
        subprocess_functions = {'call', 'run', 'Popen', 'check_output', 'check_call', 'getoutput', 'getstatusoutput'}
        # Legacy/deprecated modules (Python 2 compatibility layer in Python 3)
        legacy_modules = {'commands', 'popen2', 'popen3', 'popen4'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # os.system, os.popen, os.spawn*, etc.
                if func_full_name.startswith('os.'):
                    # Ensure node.func is ast.Attribute type before accessing attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in os_functions:
                        # Check arguments - report for both dynamic and constant args with different severity
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant):
                                # Constant string - lower severity warning
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("command_func"),
                                    type="security",
                                    severity=SeverityLevel.INFO,
                                    message=f"Using os.{node.func.attr}() is discouraged, prefer subprocess module",
                                    lineno=node.lineno,
                                    suggestion="Use subprocess module with shell=False"
                                ))
                            else:
                                # Dynamic argument - higher severity
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("command_injection"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message=f"Using os.{node.func.attr}() with dynamic argument may lead to command injection",
                                    lineno=node.lineno,
                                    suggestion="Use subprocess module with shell=False and pass arguments as list"
                                ))
                
                # subprocess with shell=True
                elif func_full_name.startswith('subprocess.'):
                    # Ensure node.func is ast.Attribute type before accessing attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in subprocess_functions:
                        for keyword in node.keywords:
                            if keyword.arg == 'shell':
                                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("shell_true"),
                                        type="security",
                                        severity=SeverityLevel.ERROR,
                                        message="subprocess with shell=True has command injection risk",
                                        lineno=node.lineno,
                                        suggestion="Use shell=False and pass argument list"
                                    ))
                
                # Legacy modules like commands.getoutput
                elif func_full_name.startswith('commands.'):
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("legacy_command"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message="Legacy module 'commands' is insecure and removed in Python 3",
                        lineno=node.lineno,
                        suggestion="Use subprocess.run() with shell=False"
                    ))
                
                # popen2, popen3, popen4 modules
                elif any(func_full_name.startswith(f'{mod}.') for mod in legacy_modules):
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("popen_legacy"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message=f"Legacy module '{func_full_name.split('.')[0]}' is deprecated and insecure",
                        lineno=node.lineno,
                        suggestion="Use subprocess.Popen() instead"
                    ))
                
                # eval() and exec() with potentially user-controlled input
                elif isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
                    if node.args:
                        arg = node.args[0]
                        # Check if it's not a constant (i.e., potentially dynamic)
                        if not isinstance(arg, ast.Constant):
                            self.issues.append(CodeIssue(
                                id=self._generate_issue_id("code_injection"),
                                type="security",
                                severity=SeverityLevel.ERROR,
                                message=f"Using {node.func.id}() with dynamic input is a code injection risk",
                                lineno=node.lineno,
                                suggestion="Avoid eval/exec with user input; use ast.literal_eval() for safe evaluation"
                            ))
    
    def _check_path_traversal(self, tree: ast.AST):
        """Check for path traversal risks"""
        file_operations = {'open', 'read', 'write', 'mkdir', 'makedirs', 'remove', 'unlink'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # Direct file operations with user input
                if isinstance(node.func, ast.Name) and node.func.id in file_operations:
                    if node.args:
                        arg = node.args[0]
                        # Check if user input is used
                        if isinstance(arg, ast.BinOp) or isinstance(arg, ast.JoinedStr):
                            self.issues.append(CodeIssue(
                                id=self._generate_issue_id("path_traversal"),
                                type="security",
                                severity=SeverityLevel.WARNING,
                                message="File operation may have path traversal risk",
                                lineno=node.lineno,
                                suggestion="Validate and sanitize user-input paths"
                            ))
                
                # os.path.join with potential user input
                elif func_full_name == 'os.path.join':
                    # Check if any argument might be user-controlled
                    has_user_input = False
                    for arg in node.args:
                        # Check for Name nodes that might be user input
                        if isinstance(arg, ast.Name):
                            # Variables like 'filename', 'user_input', 'path' might be user-controlled
                            name_lower = arg.id.lower()
                            suspicious_names = ['filename', 'filepath', 'user', 'input', 'path', 
                                               'name', 'file', 'dir', 'directory']
                            if any(suspicious in name_lower for suspicious in suspicious_names):
                                has_user_input = True
                                break
                        elif isinstance(arg, ast.Subscript):
                            # Dict/list access like request.args['file']
                            has_user_input = True
                            break
                    
                    if has_user_input:
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("path_traversal_join"),
                            type="security",
                            severity=SeverityLevel.WARNING,
                            message="os.path.join with user input may still be vulnerable to path traversal",
                            lineno=node.lineno,
                            suggestion="Use os.path.realpath and validate the result is within expected directory"
                        ))
                
                # Path with f-string or format
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'format':
                        # Check if format is called on a path-like string
                        if isinstance(node.func.value, ast.Constant):
                            path_template = str(node.func.value.value)
                            path_indicators = ['/', '\\', '.txt', '.csv', '.json', '.xml', 
                                              '.log', '.dat', '.bin', '.db', '.sqlite',
                                              'path', 'file', 'dir', 'folder']
                            if any(indicator in path_template.lower() for indicator in path_indicators):
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("path_format_string"),
                                    type="security",
                                    severity=SeverityLevel.WARNING,
                                    message="Path constructed with format string may be vulnerable to path traversal",
                                    lineno=node.lineno,
                                    suggestion="Validate formatted path components and use os.path.realpath to resolve"
                                ))
                    elif node.func.attr == 'join':
                        # str.join() with path separators
                        if isinstance(node.func.value, ast.Constant):
                            separator = str(node.func.value.value)
                            if separator in ('/', '\\', os.sep):
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("path_join_separator"),
                                    type="security",
                                    severity=SeverityLevel.INFO,
                                    message="Using str.join with path separators, consider os.path.join for cross-platform compatibility",
                                    lineno=node.lineno,
                                    suggestion="Use os.path.join() for more reliable path construction"
                                ))
                
                # f-string path construction (JoinedStr)
                elif isinstance(node, ast.JoinedStr):
                    # Check if f-string contains path-like patterns
                    for value in node.values:
                        if isinstance(value, ast.Constant):
                            const_str = str(value.value)
                            path_indicators = ['/', '\\', '.txt', '.csv', '.json', '.xml',
                                              '.log', '.dat', 'path', 'file']
                            if any(indicator in const_str for indicator in path_indicators):
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("fstring_path"),
                                    type="security",
                                    severity=SeverityLevel.WARNING,
                                    message="f-string path construction may be vulnerable to path traversal",
                                    lineno=node.lineno,
                                    suggestion="Validate path components before constructing paths"
                                ))
                                break
    
    def _check_weak_crypto(self, tree: ast.AST):
        """Check for weak encryption algorithms"""
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
                            message=f"Using weak hash algorithm {algo_name}, recommend using sha256 or sha3",
                            lineno=node.lineno
                        ))
                
                # Crypto/PyCryptodome
                elif 'DES' in func_full_name or 'RC4' in func_full_name:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("weak_cipher"),
                        type="security",
                        severity=SeverityLevel.ERROR,
                        message="Using weak encryption algorithm, recommend using AES",
                        lineno=node.lineno
                    ))
    
    def _check_insecure_defaults(self, tree: ast.AST):
        """Check for insecure default configurations"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # SSL/TLS verification
                if 'requests' in func_full_name or 'httpx' in func_full_name:
                    for keyword in node.keywords:
                        if keyword.arg == 'verify':
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("ssl_verify"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message="Disabling SSL certificate verification has man-in-the-middle attack risk",
                                    lineno=node.lineno
                                ))
                
                # CSRF protection disabled, etc.
                if 'csrf' in func_full_name.lower():
                    for keyword in node.keywords:
                        if keyword.arg in ('enabled', 'disable'):
                            if isinstance(keyword.value, ast.Constant):
                                # Check for enabled=False or disable=True cases
                                is_disabled = (
                                    (keyword.arg == 'enabled' and keyword.value.value is False) or
                                    (keyword.arg == 'disable' and keyword.value.value is True)
                                )
                                if is_disabled:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("csrf_disabled"),
                                        type="security",
                                        severity=SeverityLevel.WARNING,
                                        message="Disabling CSRF protection may lead to security vulnerabilities",
                                        lineno=node.lineno
                                    ))
    
    def get_security_summary(self) -> Dict[str, int]:
        """Get security scan summary"""
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