"""
Security Scanner - Security vulnerability scanning
Detects SQL injection, unsafe deserialization, hardcoded secrets, etc.
"""
import ast
import re
from typing import List, Dict, Any, Optional, Set
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
    SENSITIVE_PATTERNS = [
        (r'(?i)(password|passwd|pwd)\s*=\s*[\'"][^\'"]+[\'"]', 'password'),
        (r'(?i)(api_key|apikey|api_secret)\s*=\s*[\'"][^\'"]+[\'"]', 'API key'),
        (r'(?i)(secret|secret_key)\s*=\s*[\'"][^\'"]+[\'"]', 'secret key'),
        (r'(?i)(token|auth_token|access_token)\s*=\s*[\'"][^\'"]+[\'"]', 'token'),
        (r'(?i)(private_key|privatekey)\s*=\s*[\'"][^\'"]+[\'"]', 'private key'),
        (r'(?i)(aws_access_key|aws_secret)\s*=\s*[\'"][^\'"]+[\'"]', 'AWS credential'),
        (r'(?i)(database_url|db_password)\s*=\s*[\'"][^\'"]+[\'"]', 'database credential'),
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
        
        for i, line in enumerate(source_lines, 1):
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
                        if any(indicator in value for indicator in placeholder_indicators):
                            continue
                        # Skip values that are too short (likely placeholders)
                        if len(value) < 4:
                            continue
                        # Skip values that look like variable names (no special chars, starts with letter)
                        if re.match(r'^[a-z_][a-z0-9_]*$', value_match.group(1)):
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
        os_functions = {'system', 'popen', 'spawn', 'call', 'run'}
        subprocess_functions = {'call', 'run', 'Popen', 'check_output'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_full_name = self._get_func_full_name(node.func)
                
                # os.system, os.popen
                if func_full_name.startswith('os.'):
                    # Ensure node.func is ast.Attribute type before accessing attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in os_functions:
                        # Check arguments
                        if node.args:
                            arg = node.args[0]
                            if not isinstance(arg, ast.Constant):
                                self.issues.append(CodeIssue(
                                    id=self._generate_issue_id("command_injection"),
                                    type="security",
                                    severity=SeverityLevel.ERROR,
                                    message=f"Using os.{node.func.attr}() may lead to command injection",
                                    lineno=node.lineno,
                                    suggestion="Use subprocess module with shell=False"
                                ))
                
                # subprocess with shell=True
                elif func_full_name.startswith('subprocess.'):
                    # Ensure node.func is ast.Attribute type before accessing attr
                    if isinstance(node.func, ast.Attribute) and node.func.attr in subprocess_functions:
                        for keyword in node.keywords:
                            if keyword.arg == 'shell':
                                if isinstance(keyword.value, ast.Constant) and keyword.value.value == True:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("shell_true"),
                                        type="security",
                                        severity=SeverityLevel.ERROR,
                                        message="subprocess with shell=True has command injection risk",
                                        lineno=node.lineno,
                                        suggestion="Use shell=False and pass argument list"
                                    ))
    
    def _check_path_traversal(self, tree: ast.AST):
        """Check for path traversal risks"""
        file_operations = {'open', 'read', 'write', 'mkdir', 'makedirs', 'remove', 'unlink'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
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
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value == False:
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
                                    (keyword.arg == 'enabled' and keyword.value.value == False) or
                                    (keyword.arg == 'disable' and keyword.value.value == True)
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