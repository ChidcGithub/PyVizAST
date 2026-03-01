"""
PyVizAST - FastAPI Backend
基于AST的Python代码可视化与优化分析器
"""
import ast
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models.schemas import (
    CodeInput, AnalysisResult, ASTGraph,
    ComplexityMetrics, CodeIssue, SeverityLevel,
    PerformanceHotspot, OptimizationSuggestion,
    LearningModeResult, ChallengeResult
)
from .ast_parser import ASTParser, NodeMapper
from .analyzers import ComplexityAnalyzer, PerformanceAnalyzer, CodeSmellDetector, SecurityScanner
from .optimizers import SuggestionEngine, PatchGenerator


# 创建FastAPI应用
app = FastAPI(
    title="PyVizAST API",
    description="Python AST可视化与静态分析API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 初始化分析器
node_mapper = NodeMapper()
complexity_analyzer = ComplexityAnalyzer()
performance_analyzer = PerformanceAnalyzer()
code_smell_detector = CodeSmellDetector()
security_scanner = SecurityScanner()
suggestion_engine = SuggestionEngine()
patch_generator = PatchGenerator()


def get_parser(options: dict = None) -> ASTParser:
    """获取配置化的解析器实例"""
    options = options or {}
    max_nodes = options.get('max_nodes', 2000)
    simplified = options.get('simplified', False)
    
    # Auto-enable simplified mode for large code
    return ASTParser(max_nodes=max_nodes, simplified=simplified)


@app.get("/")
async def root():
    """API根端点"""
    return {
        "name": "PyVizAST API",
        "version": "0.1.0",
        "description": "Python AST可视化与静态分析器",
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


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_code(input_data: CodeInput):
    """
    完整代码分析
    解析AST、分析复杂度、检测问题、生成优化建议
    """
    try:
        code = input_data.code
        filename = input_data.filename
        options = input_data.options or {}
        
        # 检测代码大小，自动启用简化模式
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500
        
        # 解析AST
        tree = ast.parse(code)
        parser = get_parser({'simplified': auto_simplified, **options})
        ast_graph = parser.parse(code)
        
        # 应用主题
        theme = options.get('theme', 'default')
        node_mapper.set_theme(theme)
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
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析错误: {str(e)}")


@app.post("/api/ast")
async def get_ast(input_data: CodeInput):
    """
    获取AST图结构
    用于可视化
    """
    try:
        code = input_data.code
        options = input_data.options or {}
        
        # 自动简化大文件
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500 or options.get('simplified', False)
        
        # 解析AST
        parser = get_parser({'simplified': auto_simplified, **options})
        ast_graph = parser.parse(code)
        
        # 应用主题和布局
        theme = options.get('theme', 'default')
        format_type = options.get('format', 'cytoscape')
        
        node_mapper.set_theme(theme)
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
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/ast/filter")
async def filter_ast(input_data: CodeInput, node_types: Optional[str] = None, max_depth: Optional[int] = None):
    """
    过滤AST节点
    """
    try:
        from .models.schemas import NodeType
        
        code = input_data.code
        options = input_data.options or {}
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        # 按类型过滤
        if node_types:
            types = [NodeType[t.strip().upper()] for t in node_types.split(',')]
            ast_graph = node_mapper.filter_by_type(ast_graph, types)
        
        # 按深度过滤
        if max_depth:
            ast_graph = node_mapper.filter_by_depth(ast_graph, max_depth)
        
        return node_mapper.to_cytoscape_elements(ast_graph)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/complexity", response_model=ComplexityMetrics)
async def get_complexity(input_data: CodeInput):
    """
    获取复杂度分析结果
    """
    try:
        code = input_data.code
        tree = ast.parse(code)
        return complexity_analyzer.analyze(code, tree)
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/performance")
async def get_performance_issues(input_data: CodeInput):
    """
    获取性能热点分析
    """
    try:
        code = input_data.code
        tree = ast.parse(code)
        hotspots = performance_analyzer.analyze(code, tree)
        issues = performance_analyzer.get_issues()
        
        return {
            "hotspots": hotspots,
            "issues": issues
        }
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/security")
async def get_security_issues(input_data: CodeInput):
    """
    获取安全扫描结果
    """
    try:
        code = input_data.code
        tree = ast.parse(code)
        issues = security_scanner.scan(code, tree)
        summary = security_scanner.get_security_summary()
        
        return {
            "issues": issues,
            "summary": summary
        }
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/suggestions")
async def get_suggestions(input_data: CodeInput):
    """
    获取优化建议
    """
    try:
        code = input_data.code
        tree = ast.parse(code)
        
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
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/patches")
async def generate_patches(input_data: CodeInput):
    """
    生成自动修复补丁
    """
    try:
        code = input_data.code
        tree = ast.parse(code)
        
        # 获取建议
        suggestions = suggestion_engine.generate_suggestions(code, tree)
        patches = patch_generator.generate_all_patches(code, suggestions)
        
        return {
            "patches": patches,
            "total": len(patches)
        }
    
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"语法错误: {str(e)}")


@app.post("/api/apply-patch")
async def apply_patch(code: str, patch: str):
    """
    应用补丁到代码
    """
    try:
        result = patch_generator.apply_patch(code, patch)
        if result is None:
            raise HTTPException(status_code=400, detail="补丁应用失败")
        return {"fixed_code": result}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 交互式学习模式端点
@app.post("/api/learn/node/{node_id}")
async def explain_node(node_id: str, input_data: CodeInput):
    """
    解释AST节点（学习模式）
    """
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
            raise HTTPException(status_code=404, detail="节点未找到")
        
        # 生成解释
        explanation = _generate_node_explanation(node)
        
        return LearningModeResult(
            node_id=node_id,
            explanation=explanation['explanation'],
            python_doc=explanation.get('doc'),
            examples=explanation.get('examples', []),
            related_concepts=explanation.get('related', [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 挑战模式数据
CHALLENGES = [
    {
        "id": "challenge_1",
        "title": "优化嵌套循环",
        "description": "找出代码中的性能问题并修复",
        "code": """
def find_duplicates(arr):
    duplicates = []
    for i in range(len(arr)):
        for j in range(len(arr)):
            if i != j and arr[i] == arr[j]:
                if arr[i] not in duplicates:
                    duplicates.append(arr[i])
    return duplicates
""",
        "issues": ["nested_loop", "list_membership"],
        "difficulty": "easy"
    },
    {
        "id": "challenge_2",
        "title": "修复安全问题",
        "description": "找出代码中的安全漏洞",
        "code": """
def execute_user_input(user_input):
    result = eval(user_input)
    return result

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
""",
        "issues": ["eval_usage", "sql_injection"],
        "difficulty": "medium"
    },
    {
        "id": "challenge_3",
        "title": "降低复杂度",
        "description": "重构高复杂度代码",
        "code": """
def process_data(data, flag1, flag2, flag3, flag4):
    result = []
    if flag1:
        if flag2:
            if flag3:
                if flag4:
                    for item in data:
                        if item > 0:
                            if item < 100:
                                result.append(item * 2)
                        else:
                            if item > -100:
                                result.append(item * -1)
    return result
""",
        "issues": ["deep_nesting", "high_complexity"],
        "difficulty": "hard"
    }
]


@app.get("/api/challenges")
async def get_challenges():
    """获取挑战列表"""
    return [{"id": c["id"], "title": c["title"], "difficulty": c["difficulty"]} 
            for c in CHALLENGES]


@app.get("/api/challenges/{challenge_id}")
async def get_challenge(challenge_id: str):
    """获取挑战详情"""
    for challenge in CHALLENGES:
        if challenge["id"] == challenge_id:
            return {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "code": challenge["code"],
                "difficulty": challenge["difficulty"]
            }
    raise HTTPException(status_code=404, detail="挑战未找到")


class ChallengeSubmission(BaseModel):
    challenge_id: str
    found_issues: List[str]


@app.post("/api/challenges/submit")
async def submit_challenge(submission: ChallengeSubmission):
    """提交挑战答案"""
    for challenge in CHALLENGES:
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
    
    raise HTTPException(status_code=404, detail="挑战未找到")


def _generate_node_explanation(node) -> Dict[str, Any]:
    """生成节点解释"""
    explanations = {
        "function": {
            "explanation": f"这是一个函数定义节点。函数名是 '{node.name}'，"
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
            "explanation": f"这是一个类定义节点。类名是 '{node.name}'。",
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
            "explanation": f"这是一个函数调用节点，调用 '{node.name or 'unknown'}' 函数。",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
