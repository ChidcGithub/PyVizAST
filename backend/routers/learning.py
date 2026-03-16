"""
Learning mode API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter

from ..models.schemas import CodeInput, LearningModeResult
from ..exceptions import ResourceNotFoundError, CodeParsingError
from ..ast_parser import ASTParser
from ..llm import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learn", tags=["learning"])


def get_parser(options: dict = None) -> ASTParser:
    """Get configured parser instance"""
    options = options or {}
    max_nodes = options.get('max_nodes', 2000)
    simplified = options.get('simplified', False)
    return ASTParser(max_nodes=max_nodes, simplified=simplified)


def _generate_node_explanation(node) -> Dict[str, Any]:
    """Generate comprehensive node explanation for learning mode"""
    node_name = node.name or "unnamed"
    node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
    
    # Comprehensive explanations for all AST node types
    explanations = {
        # Structure nodes
        "module": {
            "explanation": "This is the module (file) root node, representing the entire Python file.",
            "doc": "A module is the top-level organizational unit in Python. Each Python file is a module that can contain "
                   "function definitions, class definitions, import statements, and executable code. Modules help organize "
                   "code and provide namespace isolation.",
            "examples": [
                "# my_module.py\nimport os\n\ndef helper():\n    pass",
                "# All code in a file belongs to the module"
            ],
            "related": ["import", "package", "__name__", "__file__"]
        },
        "function": {
            "explanation": f"This is a function definition node. Function name is '{node_name}', "
                          f"it contains {len(node.children)} child nodes.",
            "doc": "In Python, functions are code blocks defined using the def keyword. Functions encapsulate reusable logic, "
                   "can receive parameters (positional, keyword, *args, **kwargs), and return values. They support decorators, "
                   "type hints, and docstrings for documentation.",
            "examples": [
                "def greet(name: str) -> str:\n    \"\"\"Return a greeting message.\"\"\"\n    return f'Hello, {name}!'",
                "def calculate(*args, operation='sum'):\n    if operation == 'sum':\n        return sum(args)\n    return max(args)"
            ],
            "related": ["parameters", "return", "decorators", "lambda", "type hints", "docstring"]
        },
        "class": {
            "explanation": f"This is a class definition node. Class name is '{node_name}'.",
            "doc": "Classes are blueprints for creating objects. They encapsulate data (attributes) and behavior (methods). "
                   "Python supports single and multiple inheritance, property decorators, class methods, static methods, "
                   "and special (dunder) methods like __init__, __str__, __repr__.",
            "examples": [
                "class Person:\n    def __init__(self, name: str):\n        self.name = name\n    \n    def greet(self) -> str:\n        return f'Hello, I am {self.name}'",
                "class Student(Person):\n    def __init__(self, name, grade):\n        super().__init__(name)\n        self.grade = grade"
            ],
            "related": ["inheritance", "methods", "attributes", "property", "classmethod", "staticmethod", "__init__"]
        },
        
        # Control flow
        "if": {
            "explanation": "This is an if conditional node, used to execute different code based on conditions.",
            "doc": "If statements control program flow based on boolean conditions. Python supports if-elif-else chains, "
                   "and conditions can be any expression that evaluates to a truthy or falsy value. Avoid deeply nested "
                   "conditionals by using early returns or guard clauses.",
            "examples": [
                "if x > 0:\n    print('positive')\nelif x < 0:\n    print('negative')\nelse:\n    print('zero')",
                "# Guard clause pattern\nif not user:\n    return None\n# Process user..."
            ],
            "related": ["elif", "else", "boolean logic", "ternary operator", "guard clause"]
        },
        "for": {
            "explanation": "This is a for loop node, used to iterate over iterable objects.",
            "doc": "For loops iterate over any iterable object (list, tuple, dict, set, string, range, generator). "
                   "Use enumerate() for index-value pairs, zip() for parallel iteration, and dict.items() for key-value pairs. "
                   "Avoid modifying the iterable while looping.",
            "examples": [
                "for i, item in enumerate(items):\n    print(f'{i}: {item}')",
                "for name, score in students.items():\n    print(f'{name}: {score}')",
                "for x, y in zip(list1, list2):\n    result.append(x + y)"
            ],
            "related": ["while", "range()", "enumerate()", "zip()", "iterators", "list comprehension", "break", "continue"]
        },
        "while": {
            "explanation": "This is a while loop node, used to repeat code while a condition is true.",
            "doc": "While loops continue execution as long as the condition remains truthy. Be careful to ensure "
                   "the condition eventually becomes false to avoid infinite loops. Use break to exit early "
                   "and continue to skip to the next iteration.",
            "examples": [
                "count = 0\nwhile count < 10:\n    print(count)\n    count += 1",
                "while True:\n    response = get_input()\n    if response == 'quit':\n        break"
            ],
            "related": ["for", "break", "continue", "else clause", "infinite loop"]
        },
        "try": {
            "explanation": "This is a try-except node for exception handling.",
            "doc": "Try-except blocks handle exceptions gracefully. Always catch specific exceptions rather than bare 'except:'. "
                   "The 'finally' clause always executes regardless of exceptions. Use 'else' clause for code that should "
                   "run only if no exception occurred.",
            "examples": [
                "try:\n    result = risky_operation()\nexcept ValueError as e:\n    print(f'Invalid value: {e}')\nelse:\n    print(f'Success: {result}')\nfinally:\n    cleanup()",
                "# Context manager is preferred for resources\nwith open('file.txt') as f:\n    data = f.read()"
            ],
            "related": ["except", "finally", "raise", "else", "with", "context manager", "custom exceptions"]
        },
        "with": {
            "explanation": "This is a with statement node for context management.",
            "doc": "The 'with' statement provides context management for resources that need setup and cleanup. "
                   "It ensures proper resource release even if exceptions occur. Common uses include file handling, "
                   "database connections, locks, and custom context managers.",
            "examples": [
                "with open('file.txt', 'r') as f:\n    content = f.read()\n# File automatically closed here",
                "with threading.Lock():\n    shared_resource.modify()\n# Lock automatically released"
            ],
            "related": ["context manager", "__enter__", "__exit__", "contextlib", "try-finally"]
        },
        
        # Expressions
        "call": {
            "explanation": f"This is a function call node, calling '{node_name}' function.",
            "doc": "Function calls execute a function with provided arguments. Python supports positional arguments, "
                   "keyword arguments, unpacking with *args and **kwargs. Built-in functions like len(), print(), "
                   "range() are frequently used. Method calls on objects use dot notation.",
            "examples": [
                "result = calculate(1, 2, 3, operation='sum')",
                "print(*items, sep=', ')\nprocess(**config)"
            ],
            "related": ["arguments", "parameters", "return value", "built-in functions", "methods"]
        },
        "binary_op": {
            "explanation": "This is a binary operation node (e.g., +, -, *, /, ==, and, or).",
            "doc": "Binary operations combine two operands with an operator. Arithmetic operators (+, -, *, /, //, %, **) "
                   "perform math. Comparison operators (==, !=, <, >, <=, >=) return boolean values. "
                   "Logical operators (and, or) short-circuit evaluation.",
            "examples": [
                "result = a + b * c  # Multiplication first\nresult = (a + b) * c  # Addition first",
                "if x > 0 and y > 0:  # Short-circuit: y not evaluated if x <= 0\n    return 'both positive'"
            ],
            "related": ["operators", "precedence", "short-circuit", "comparison", "arithmetic"]
        },
        "compare": {
            "explanation": "This is a comparison operation node.",
            "doc": "Comparison operators compare values and return boolean results. Python supports chained comparisons "
                   "like 'a < b < c' which is equivalent to 'a < b and b < c' but more readable and efficient. "
                   "Use 'is' for identity comparison, '==' for equality.",
            "examples": [
                "if 0 < x < 100:  # Chained comparison\n    print('x is between 0 and 100')",
                "if x is None:  # Identity check\n    x = default_value"
            ],
            "related": ["boolean", "operators", "chaining", "identity", "equality"]
        },
        "lambda": {
            "explanation": "This is a lambda (anonymous function) node.",
            "doc": "Lambda expressions create small anonymous functions with a single expression. They are useful for "
                   "short callbacks, key functions in sorting, and simple transformations. For complex logic, "
                   "use regular def functions for readability.",
            "examples": [
                "square = lambda x: x ** 2\nsquares = list(map(lambda x: x**2, range(10)))",
                "students.sort(key=lambda s: s.grade)"
            ],
            "related": ["function", "def", "map", "filter", "sorted", "key function"]
        },
        
        # Data structures
        "list": {
            "explanation": "This is a list literal node.",
            "doc": "Lists are mutable ordered sequences that can contain heterogeneous elements. They support indexing, "
                   "slicing, and various methods like append(), extend(), insert(), remove(), pop(). "
                   "Use list comprehensions for concise list creation.",
            "examples": [
                "numbers = [1, 2, 3, 4, 5]\nfirst = numbers[0]\nslice = numbers[1:3]",
                "squares = [x**2 for x in range(10) if x % 2 == 0]  # List comprehension"
            ],
            "related": ["tuple", "list comprehension", "slicing", "append", "extend", "mutable"]
        },
        "dict": {
            "explanation": "This is a dictionary literal node.",
            "doc": "Dictionaries are mutable mappings of key-value pairs. Keys must be hashable (immutable). "
                   "Python 3.7+ preserves insertion order. Use dict.get() for safe access with defaults, "
                   "and dict comprehension for creating dictionaries from iterables.",
            "examples": [
                "person = {'name': 'Alice', 'age': 30}\nname = person.get('name', 'Unknown')",
                "squares = {x: x**2 for x in range(5)}  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}"
            ],
            "related": ["keys", "values", "items", "get", "update", "setdefault", "defaultdict"]
        },
        "set": {
            "explanation": "This is a set literal node.",
            "doc": "Sets are unordered collections of unique elements. They support mathematical set operations "
                   "like union (|), intersection (&), difference (-), and symmetric difference (^). "
                   "Use sets for membership testing and removing duplicates.",
            "examples": [
                "unique = set([1, 2, 2, 3, 3, 3])  # {1, 2, 3}\nif item in my_set:  # O(1) lookup",
                "common = set_a & set_b  # Intersection\nall_items = set_a | set_b  # Union"
            ],
            "related": ["frozenset", "union", "intersection", "difference", "membership"]
        },
        "tuple": {
            "explanation": "This is a tuple literal node.",
            "doc": "Tuples are immutable ordered sequences. They are commonly used for fixed collections of items, "
                   "function return values, and dictionary keys (since they're hashable). "
                   "Named tuples provide field names for better readability.",
            "examples": [
                "point = (3, 4)\nx, y = point  # Unpacking",
                "from collections import namedtuple\nPoint = namedtuple('Point', ['x', 'y'])\np = Point(3, 4)"
            ],
            "related": ["list", "unpacking", "namedtuple", "immutable", "hashable"]
        },
        
        # Variables
        "assign": {
            "explanation": "This is an assignment node, binding a value to a variable name.",
            "doc": "Assignment binds a value to a name. Python supports multiple assignment (a, b = 1, 2), "
                   "chained assignment (x = y = 0), and augmented assignment (x += 1). "
                   "Variables are references to objects, not containers.",
            "examples": [
                "x = 10\na, b = 1, 2  # Tuple unpacking\nx = y = z = 0  # Chained",
                "x += 1  # Augmented assignment\ndata['key'] = value  # Subscript assignment"
            ],
            "related": ["variables", "names", "binding", "augmented assignment", "unpacking"]
        },
        "name": {
            "explanation": f"This is a name (identifier) node: '{node_name}'.",
            "doc": "Names are identifiers that reference objects in Python's namespace. They can refer to variables, "
                   "functions, classes, modules, or any object. Name resolution follows LEGB rule: "
                   "Local, Enclosing, Global, Built-in scopes.",
            "examples": [
                "x = 10  # 'x' is a name\nimport math  # 'math' is a name\nprint(math.pi)",
                "def outer():\n    x = 1  # Local scope\n    def inner():\n        nonlocal x  # Enclosing scope"
            ],
            "related": ["scope", "namespace", "LEGB", "global", "nonlocal"]
        },
        
        # Others
        "import": {
            "explanation": "This is an import statement node.",
            "doc": "Import statements load modules and make their contents available. Use 'import module' for "
                   "full module access, 'from module import name' for specific items, and 'as' for aliases. "
                   "Avoid 'from module import *' as it pollutes the namespace.",
            "examples": [
                "import os\nfrom datetime import datetime, timedelta\nimport numpy as np",
                "from collections import defaultdict, Counter"
            ],
            "related": ["module", "package", "from", "as", "__import__", "importlib"]
        },
        "return": {
            "explanation": "This is a return statement node.",
            "doc": "Return statements exit a function and optionally return a value. Functions without explicit "
                   "return statements return None. Multiple values can be returned as a tuple. "
                   "Early returns can improve code clarity by handling edge cases first.",
            "examples": [
                "def add(a, b):\n    return a + b",
                "def find_item(items, target):\n    for i, item in enumerate(items):\n        if item == target:\n            return i  # Early return\n    return -1"
            ],
            "related": ["function", "None", "yield", "early return"]
        },
        "yield": {
            "explanation": "This is a yield statement node, used in generators.",
            "doc": "Yield statements turn a function into a generator. Generators produce values lazily, "
                   "one at a time, which is memory efficient for large sequences. Use 'yield from' to delegate "
                   "to another generator. Generator expressions offer a concise syntax.",
            "examples": [
                "def countdown(n):\n    while n > 0:\n        yield n\n        n -= 1",
                "# Generator expression\nsquares = (x**2 for x in range(1000000))  # Lazy evaluation"
            ],
            "related": ["generator", "iterator", "next", "yield from", "generator expression"]
        }
    }
    
    return explanations.get(node_type, {
        "explanation": f"This is an AST node of type {node_type}.",
        "doc": f"The {node_type} node type represents a specific construct in Python's abstract syntax tree. "
               f"Click on different nodes in the visualization to learn more about each type.",
        "examples": [],
        "related": ["AST", "parsing", "Python syntax"]
    })


@router.post("/node/{node_id}")
async def explain_node(node_id: str, input_data: CodeInput):
    """Explain AST node (learning mode) - supports LLM enhancement"""
    logger.debug(f"Explaining AST node: {node_id}")
    
    try:
        code = input_data.code
        options = input_data.options or {}
        use_llm = options.get('use_llm', False)
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        # Find node
        node = None
        for n in ast_graph.nodes:
            if n.id == node_id:
                node = n
                break
        
        if not node:
            raise ResourceNotFoundError(f"Node not found: {node_id}")
        
        node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
        node_name = node.name
        
        # Try LLM first if enabled and requested
        if use_llm:
            llm_service = get_llm_service()
            if llm_service.is_enabled and llm_service.status.value == "ready":
                try:
                    llm_explanation = await llm_service.generate_explanation(
                        node_type=node_type,
                        node_name=node_name,
                        code_context=code
                    )
                    return LearningModeResult(
                        node_id=node_id,
                        explanation=llm_explanation.explanation,
                        python_doc=llm_explanation.python_doc,
                        examples=llm_explanation.examples,
                        related_concepts=llm_explanation.related_concepts
                    )
                except Exception as e:
                    logger.warning(f"LLM explanation failed, falling back to static: {e}")
        
        # Fall back to static explanations
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
        raise CodeParsingError(f"Syntax error: {str(e)}")