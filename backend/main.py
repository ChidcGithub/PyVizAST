"""
PyVizAST - FastAPI Backend
基于AST的Python代码可视化与优化分析器
"""
import ast
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from .models.schemas import (
    CodeInput, AnalysisResult, ASTGraph,
    ComplexityMetrics, CodeIssue, SeverityLevel,
    PerformanceHotspot, OptimizationSuggestion,
    LearningModeResult, ChallengeResult
)
from .ast_parser import ASTParser, NodeMapper
from .analyzers import ComplexityAnalyzer, PerformanceAnalyzer, CodeSmellDetector, SecurityScanner
from .optimizers import SuggestionEngine, PatchGenerator
from .utils.logger import get_logger, log_exception, init_logging


# 自定义异常类
class AnalysisError(Exception):
    """分析过程中的错误"""
    pass


class CodeParsingError(AnalysisError):
    """代码解析错误"""
    pass


class CodeTooLargeError(AnalysisError):
    """代码过大错误"""
    pass


class ResourceNotFoundError(Exception):
    """资源未找到错误"""
    pass


# 初始化日志系统
logger = init_logging(level=logging.INFO)


# 创建FastAPI应用
app = FastAPI(
    title="PyVizAST API",
    description="Python AST可视化与静态分析API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
import os
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 从环境变量读取允许的来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """处理 Pydantic 验证错误"""
    log_exception(logger, exc, f"请求路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"输入验证失败: {exc}"}
    )


@app.exception_handler(CodeParsingError)
async def code_parsing_exception_handler(request: Request, exc: CodeParsingError):
    """处理代码解析错误"""
    logger.warning(f"代码解析错误: {exc} | 路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(CodeTooLargeError)
async def code_too_large_exception_handler(request: Request, exc: CodeTooLargeError):
    """处理代码过大错误"""
    logger.warning(f"代码过大: {exc} | 路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": str(exc)}
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    """处理资源未找到错误"""
    logger.warning(f"资源未找到: {exc} | 路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(AnalysisError)
async def analysis_exception_handler(request: Request, exc: AnalysisError):
    """处理分析过程中的错误"""
    log_exception(logger, exc, f"请求路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"分析过程中发生错误: {str(exc)}"}
    )


@app.exception_handler(OSError)
async def os_exception_handler(request: Request, exc: OSError):
    """处理操作系统错误（如文件操作）"""
    log_exception(logger, exc, f"请求路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误，请稍后重试"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    log_exception(logger, exc, f"请求路径: {request.url.path}")
    # 生产环境不返回详细错误信息
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误"}
    )


# 本地模型定义
class PatchApplyRequest(BaseModel):
    """补丁应用请求模型"""
    code: str
    patch: str


class AnalyzerFactory:
    """分析器工厂 - 每次请求创建新实例避免状态污染"""
    
    @staticmethod
    def create_complexity_analyzer() -> ComplexityAnalyzer:
        return ComplexityAnalyzer()
    
    @staticmethod
    def create_performance_analyzer() -> PerformanceAnalyzer:
        return PerformanceAnalyzer()
    
    @staticmethod
    def create_code_smell_detector() -> CodeSmellDetector:
        return CodeSmellDetector()
    
    @staticmethod
    def create_security_scanner() -> SecurityScanner:
        return SecurityScanner()
    
    @staticmethod
    def create_suggestion_engine() -> SuggestionEngine:
        return SuggestionEngine()
    
    @staticmethod
    def create_patch_generator() -> PatchGenerator:
        return PatchGenerator()
    
    @staticmethod
    def create_node_mapper(theme: str = "default") -> NodeMapper:
        return NodeMapper(theme=theme)


def get_parser(options: dict = None) -> ASTParser:
    """获取配置化的解析器实例"""
    options = options or {}
    max_nodes = options.get('max_nodes', 2000)
    simplified = options.get('simplified', False)
    
    return ASTParser(max_nodes=max_nodes, simplified=simplified)


@app.get("/")
async def root():
    """API根端点"""
    return {
        "name": "PyVizAST API",
        "version": "0.1.0",
        "description": "Python AST可视化与静态分析器",
        "status": "running",
        "endpoints": {
            "analyze": "/api/analyze",
            "ast": "/api/ast",
            "complexity": "/api/complexity",
            "performance": "/api/performance",
            "security": "/api/security",
            "suggestions": "/api/suggestions",
            "docs": "/docs"
        }
    }


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "PyVizAST API"}


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_code(input_data: CodeInput):
    """
    完整代码分析
    解析AST、分析复杂度、检测问题、生成优化建议
    """
    logger.info(f"开始分析代码, 文件名: {input_data.filename or '未指定'}")
    
    try:
        code = input_data.code
        filename = input_data.filename
        options = input_data.options or {}
        
        # 检测代码大小，自动启用简化模式
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500
        logger.debug(f"代码行数: {code_lines}, 简化模式: {auto_simplified}")
        
        # 解析AST - 使用渐进式策略处理大文件
        tree = None
        simplification_level = 0  # 0=正常, 1=简化, 2=激进简化
        
        while tree is None and simplification_level <= 2:
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                # 语法错误应该立即抛出，不需要重试
                raise CodeParsingError(f"语法错误: {str(e)}")
            except MemoryError:
                simplification_level += 1
                if simplification_level == 1:
                    # 第一次内存错误：尝试简化模式
                    logger.warning(f"代码过大 ({code_lines} 行)，尝试简化模式...")
                    auto_simplified = True
                    import gc
                    gc.collect()  # 强制垃圾回收
                elif simplification_level == 2:
                    # 第二次内存错误：尝试激进简化
                    logger.warning("简化模式仍不足，尝试激进简化...")
                    # 尝试只解析代码结构（去除函数体内容）
                    try:
                        # 只保留代码的结构框架
                        lines = code.splitlines()
                        if len(lines) > 2000:
                            # 对于超大文件，只分析前 2000 行
                            code = '\n'.join(lines[:2000])
                            code_lines = 2000
                            tree = ast.parse(code)
                            logger.info(f"已截取前 2000 行进行分析")
                            break
                    except SyntaxError as e:
                        # 截取后的代码可能有语法错误，直接抛出
                        raise CodeParsingError(f"语法错误: {str(e)}")
                    except MemoryError:
                        pass
                    import gc
                    gc.collect()
                else:
                    # 最终失败
                    raise CodeTooLargeError(
                        f"代码过大 ({code_lines} 行)，无法解析。"
                        f"建议：1) 将代码拆分为多个文件；"
                        f"2) 使用更强大的机器；"
                        f"3) 只分析部分代码。"
                    )
        
        parser = get_parser({'simplified': auto_simplified, **options})
        ast_graph = parser.parse(code)
        
        # 创建新的分析器实例
        theme = options.get('theme', 'default')
        node_mapper = AnalyzerFactory.create_node_mapper(theme)
        complexity_analyzer = AnalyzerFactory.create_complexity_analyzer()
        performance_analyzer = AnalyzerFactory.create_performance_analyzer()
        code_smell_detector = AnalyzerFactory.create_code_smell_detector()
        security_scanner = AnalyzerFactory.create_security_scanner()
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        
        # 应用主题
        ast_graph = node_mapper.apply_theme_to_graph(ast_graph)
        ast_graph = node_mapper.calculate_node_sizes(ast_graph)
        
        # 复杂度分析
        complexity = complexity_analyzer.analyze(code, tree)
        
        # 性能分析
        performance_hotspots = performance_analyzer.analyze(code, tree)
        
        # 代码异味检测
        code_smell_detector.analyze(code, tree)
        
        # 安全扫描
        security_scanner.scan(code, tree)
        
        # 合并所有问题
        all_issues = (
            complexity_analyzer.get_issues() +
            performance_analyzer.get_issues() +
            code_smell_detector.issues +
            security_scanner.issues
        )
        
        # 生成优化建议
        suggestions = suggestion_engine.generate_suggestions(code, tree, all_issues)
        
        # 生成统计摘要
        summary = {
            "total_issues": len(all_issues),
            "critical_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.CRITICAL),
            "error_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.ERROR),
            "warning_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.WARNING),
            "info_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.INFO),
            "performance_hotspots": len(performance_hotspots),
            "suggestions_count": len(suggestions),
            "security_summary": security_scanner.get_security_summary(),
            "node_statistics": node_mapper.get_statistics(ast_graph)
        }
        
        logger.info(f"分析完成, 发现 {len(all_issues)} 个问题")
        
        return AnalysisResult(
            filename=filename,
            total_lines=len(code.splitlines()),
            ast_graph=ast_graph,
            complexity=complexity,
            issues=all_issues,
            performance_hotspots=performance_hotspots,
            suggestions=suggestions,
            summary=summary
        )
    
    except (CodeParsingError, CodeTooLargeError):
        # 重新抛出已知异常，让全局处理器处理
        raise
    except RecursionError:
        logger.error("递归深度超限")
        raise AnalysisError("代码结构过于复杂，无法分析")
    except MemoryError:
        logger.error("内存不足")
        raise CodeTooLargeError("代码过大，内存不足")


@app.post("/api/ast")
async def get_ast(input_data: CodeInput):
    """
    获取AST图结构
    用于可视化
    """
    logger.debug(f"获取AST图结构")
    
    try:
        code = input_data.code
        options = input_data.options or {}
        
        # 自动简化大文件
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500 or options.get('simplified', False)
        
        # 解析AST
        try:
            parser = get_parser({'simplified': auto_simplified, **options})
            ast_graph = parser.parse(code)
        except SyntaxError as e:
            raise CodeParsingError(f"语法错误: {str(e)}")
        except MemoryError:
            raise CodeTooLargeError("代码过大，无法解析")
        
        # 应用主题和布局
        theme = options.get('theme', 'default')
        format_type = options.get('format', 'cytoscape')
        
        node_mapper = AnalyzerFactory.create_node_mapper(theme)
        ast_graph = node_mapper.apply_theme_to_graph(ast_graph)
        ast_graph = node_mapper.calculate_node_sizes(ast_graph)
        
        # 转换格式
        if format_type == 'cytoscape':
            return node_mapper.to_cytoscape_elements(ast_graph)
        elif format_type == 'd3':
            return node_mapper.to_d3_format(ast_graph)
        elif format_type == 'tree':
            return node_mapper.to_hierarchical_tree(ast_graph)
        else:
            return ast_graph
    
    except (CodeParsingError, CodeTooLargeError):
        raise


@app.post("/api/ast/filter")
async def filter_ast(input_data: CodeInput, node_types: Optional[str] = None, max_depth: Optional[int] = None):
    """
    过滤AST节点
    """
    logger.debug(f"过滤AST节点, 类型: {node_types}, 最大深度: {max_depth}")
    
    try:
        from .models.schemas import NodeType
        
        code = input_data.code
        options = input_data.options or {}
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        node_mapper = AnalyzerFactory.create_node_mapper()
        
        # 按类型过滤
        if node_types:
            try:
                types = [NodeType[t.strip().upper()] for t in node_types.split(',')]
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的节点类型: {e}"
                )
            ast_graph = node_mapper.filter_by_type(ast_graph, types)
        
        # 按深度过滤
        if max_depth:
            if max_depth < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="最大深度必须大于0"
                )
            ast_graph = node_mapper.filter_by_depth(ast_graph, max_depth)
        
        return node_mapper.to_cytoscape_elements(ast_graph)
    
    except HTTPException:
        raise
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/complexity", response_model=ComplexityMetrics)
async def get_complexity(input_data: CodeInput):
    """
    获取复杂度分析结果
    """
    logger.debug("获取复杂度分析")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        analyzer = AnalyzerFactory.create_complexity_analyzer()
        return analyzer.analyze(code, tree)
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/performance")
async def get_performance_issues(input_data: CodeInput):
    """
    获取性能热点分析
    """
    logger.debug("获取性能热点分析")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        analyzer = AnalyzerFactory.create_performance_analyzer()
        hotspots = analyzer.analyze(code, tree)
        issues = analyzer.get_issues()
        
        return {
            "hotspots": hotspots,
            "issues": issues
        }
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/security")
async def get_security_issues(input_data: CodeInput):
    """
    获取安全扫描结果
    """
    logger.debug("获取安全扫描结果")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        scanner = AnalyzerFactory.create_security_scanner()
        scanner.scan(code, tree)
        summary = scanner.get_security_summary()
        
        return {
            "issues": scanner.issues,
            "summary": summary
        }
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/suggestions")
async def get_suggestions(input_data: CodeInput):
    """
    获取优化建议
    """
    logger.debug("获取优化建议")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        
        # 创建新的分析器实例
        complexity_analyzer = AnalyzerFactory.create_complexity_analyzer()
        performance_analyzer = AnalyzerFactory.create_performance_analyzer()
        code_smell_detector = AnalyzerFactory.create_code_smell_detector()
        security_scanner = AnalyzerFactory.create_security_scanner()
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        
        # 运行完整分析获取问题
        complexity_analyzer.analyze(code, tree)
        performance_analyzer.analyze(code, tree)
        code_smell_detector.analyze(code, tree)
        security_scanner.scan(code, tree)
        
        all_issues = (
            complexity_analyzer.get_issues() +
            performance_analyzer.get_issues() +
            code_smell_detector.issues +
            security_scanner.issues
        )
        
        suggestions = suggestion_engine.generate_suggestions(code, tree, all_issues)
        by_category = suggestion_engine.get_suggestions_by_category()
        
        return {
            "suggestions": suggestions,
            "by_category": by_category,
            "high_priority": suggestion_engine.get_high_priority_suggestions()
        }
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/patches")
async def generate_patches(input_data: CodeInput):
    """
    生成自动修复补丁
    """
    logger.debug("生成自动修复补丁")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        
        # 创建新实例
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        patch_generator = AnalyzerFactory.create_patch_generator()
        
        # 获取建议
        suggestions = suggestion_engine.generate_suggestions(code, tree)
        patches = patch_generator.generate_all_patches(code, suggestions)
        
        return {
            "patches": patches,
            "total": len(patches)
        }
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


@app.post("/api/apply-patch")
async def apply_patch(request: PatchApplyRequest):
    """
    应用补丁到代码
    """
    logger.debug("应用补丁到代码")
    
    try:
        patch_generator = AnalyzerFactory.create_patch_generator()
        result = patch_generator.apply_patch(request.code, request.patch)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="补丁应用失败，格式不正确或与代码不匹配"
            )
        return {"fixed_code": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"补丁格式错误: {str(e)}"
        )


# 交互式学习模式端点
@app.post("/api/learn/node/{node_id}")
async def explain_node(node_id: str, input_data: CodeInput):
    """
    解释AST节点（学习模式）
    """
    logger.debug(f"解释AST节点: {node_id}")
    
    try:
        code = input_data.code
        options = input_data.options or {}
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        # 查找节点
        node = None
        for n in ast_graph.nodes:
            if n.id == node_id:
                node = n
                break
        
        if not node:
            raise ResourceNotFoundError(f"节点未找到: {node_id}")
        
        # 生成解释
        explanation = _generate_node_explanation(node)
        
        return LearningModeResult(
            node_id=node_id,
            explanation=explanation['explanation'],
            python_doc=explanation.get('doc'),
            examples=explanation.get('examples', []),
            related_concepts=explanation.get('related', [])
        )
    
    except (ResourceNotFoundError, CodeParsingError):
        raise
    except SyntaxError as e:
        raise CodeParsingError(f"语法错误: {str(e)}")


# 挑战数据加载器
def load_challenges() -> List[Dict[str, Any]]:
    """从 JSON 文件加载挑战数据"""
    challenges_path = Path(__file__).parent / "data" / "challenges.json"
    try:
        with open(challenges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("challenges", [])
    except FileNotFoundError:
        logger.warning(f"挑战数据文件未找到: {challenges_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"挑战数据 JSON 解析错误: {e}")
        return []


def get_challenges_cache() -> List[Dict[str, Any]]:
    """获取挑战数据（带缓存）"""
    if not hasattr(get_challenges_cache, '_cache'):
        get_challenges_cache._cache = load_challenges()
    return get_challenges_cache._cache


@app.get("/api/challenges")
async def get_challenges():
    """获取挑战列表"""
    logger.debug("获取挑战列表")
    challenges = get_challenges_cache()
    return [
        {
            "id": c["id"], 
            "title": c["title"], 
            "difficulty": c["difficulty"],
            "estimated_time_minutes": c.get("estimated_time_minutes")
        } 
        for c in challenges
    ]


@app.get("/api/challenges/{challenge_id}")
async def get_challenge(challenge_id: str):
    """获取挑战详情"""
    logger.debug(f"获取挑战详情: {challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == challenge_id:
            return {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "code": challenge["code"],
                "difficulty": challenge["difficulty"],
                "hints": challenge.get("hints", [])
            }
    raise ResourceNotFoundError(f"挑战未找到: {challenge_id}")


class ChallengeSubmission(BaseModel):
    challenge_id: str
    found_issues: List[str]


@app.post("/api/challenges/submit")
async def submit_challenge(submission: ChallengeSubmission):
    """提交挑战答案"""
    logger.debug(f"提交挑战答案: {submission.challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == submission.challenge_id:
            expected = set(challenge["issues"])
            found = set(submission.found_issues)
            
            correct = found & expected
            missed = expected - found
            wrong = found - expected
            
            score = len(correct) * 10 - len(wrong) * 5
            max_score = len(expected) * 10
            
            return ChallengeResult(
                challenge_id=submission.challenge_id,
                score=max(0, score),
                max_score=max_score,
                found_issues=list(correct),
                missed_issues=list(missed),
                feedback=_generate_challenge_feedback(correct, missed, wrong)
            )
    
    raise ResourceNotFoundError(f"挑战未找到: {submission.challenge_id}")


def _generate_node_explanation(node) -> Dict[str, Any]:
    """生成节点解释"""
    node_name = node.name or "未命名"
    
    explanations = {
        "function": {
            "explanation": f"这是一个函数定义节点。函数名是 '{node_name}'，"
                          f"它包含{len(node.children)}个子节点。",
            "doc": "在Python中，函数是使用def关键字定义的代码块，"
                   "可以接收参数并返回值。函数有助于代码复用和模块化。",
            "examples": [
                "def greet(name):\n    return f'Hello, {name}!'",
                "def add(a, b=0):\n    return a + b"
            ],
            "related": ["parameters", "return statement", "decorators"]
        },
        "class": {
            "explanation": f"这是一个类定义节点。类名是 '{node_name}'。",
            "doc": "类是对象的蓝图，包含属性和方法。"
                   "Python支持面向对象编程，包括继承、封装和多态。",
            "examples": [
                "class Dog:\n    def __init__(self, name):\n        self.name = name",
                "class Cat(Animal):\n    def speak(self):\n        print('Meow')"
            ],
            "related": ["inheritance", "methods", "attributes", "__init__"]
        },
        "for": {
            "explanation": "这是一个for循环节点，用于遍历可迭代对象。",
            "doc": "for循环是Python中最常用的迭代结构，"
                   "可以遍历列表、元组、字典、字符串等可迭代对象。",
            "examples": [
                "for i in range(10):\n    print(i)",
                "for item in my_list:\n    process(item)"
            ],
            "related": ["while loop", "range()", "iterators", "enumerate()"]
        },
        "if": {
            "explanation": "这是一个if条件判断节点，用于根据条件执行不同的代码。",
            "doc": "if语句根据条件表达式的真假来决定执行哪个分支。"
                   "可以配合elif和else使用。",
            "examples": [
                "if x > 0:\n    print('positive')\nelse:\n    print('non-positive')",
                "if x > 10 and y > 10:\n    return 'large'"
            ],
            "related": ["elif", "else", "conditional expressions", "boolean logic"]
        },
        "call": {
            "explanation": f"这是一个函数调用节点，调用 '{node_name}' 函数。",
            "doc": "函数调用会执行函数定义中的代码，并可以传递参数和接收返回值。",
            "examples": [
                "result = len(my_list)",
                "greeting = greet('World')"
            ],
            "related": ["arguments", "parameters", "return value", "built-in functions"]
        },
        "assign": {
            "explanation": "这是一个赋值节点，将值绑定到变量名。",
            "doc": "赋值操作将右侧的值绑定到左侧的变量名。"
                   "Python支持多重赋值和解包赋值。",
            "examples": [
                "x = 10",
                "a, b = 1, 2",
                "x = y = z = 0"
            ],
            "related": ["variables", "names", "binding", "augmented assignment"]
        }
    }
    
    return explanations.get(node.type.value, {
        "explanation": f"这是一个{node.type.value}类型的AST节点。",
        "doc": None,
        "examples": [],
        "related": []
    })


def _generate_challenge_feedback(correct, missed, wrong):
    """生成挑战反馈"""
    feedback = []
    
    if correct:
        feedback.append(f"太棒了！你正确识别了: {', '.join(correct)}")
    
    if missed:
        feedback.append(f"你遗漏了: {', '.join(missed)}")
    
    if wrong:
        feedback.append(f"错误识别: {', '.join(wrong)}")
    
    return " ".join(feedback) if feedback else "继续努力！"


# 前端日志接收端点
from pydantic import BaseModel
from typing import List as TypingList
from datetime import datetime


class FrontendLogEntry(BaseModel):
    """前端日志条目模型"""
    timestamp: str
    level: str
    message: str
    userAgent: Optional[str] = None
    url: Optional[str] = None
    reason: Optional[str] = None
    stack: Optional[str] = None
    componentStack: Optional[str] = None
    filename: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None


class FrontendLogsRequest(BaseModel):
    """前端日志请求模型"""
    logs: TypingList[FrontendLogEntry]


# 确保日志目录存在
LOGS_DIR = Path(__file__).parent.parent / "logs"


def ensure_logs_dir():
    """确保日志目录存在"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/logs/frontend")
async def receive_frontend_logs(request: FrontendLogsRequest):
    """
    接收前端日志并保存到文件
    """
    ensure_logs_dir()
    
    # 生成日志文件名（按日期）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"frontend-{today}.log"
    
    # 追加写入日志
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            for log_entry in request.logs:
                # 格式化日志条目
                log_line = (
                    f"[{log_entry.timestamp}] "
                    f"[{log_entry.level.upper()}] "
                    f"{log_entry.message}"
                )
                
                # 添加额外信息
                extras = []
                if log_entry.url:
                    extras.append(f"url={log_entry.url}")
                if log_entry.filename:
                    extras.append(f"file={log_entry.filename}:{log_entry.lineno}:{log_entry.colno}")
                if log_entry.stack:
                    extras.append(f"stack={log_entry.stack[:500]}")  # 限制栈长度
                if log_entry.componentStack:
                    extras.append(f"componentStack={log_entry.componentStack[:500]}")
                
                if extras:
                    log_line += f" | {' | '.join(extras)}"
                
                f.write(log_line + "\n")
        
        logger.debug(f"保存了 {len(request.logs)} 条前端日志")
        return {"status": "ok", "count": len(request.logs)}
    
    except Exception as e:
        logger.error(f"保存前端日志失败: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
