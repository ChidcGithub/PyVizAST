"""
LLM Prompt Templates

@author: Chidc
@link: github.com/chidcGithub
"""
from typing import List, Optional


# System prompts
SYSTEM_PROMPT_EXPLANATION = """You are an expert Python programming educator. Your task is to explain Python AST (Abstract Syntax Tree) nodes in a clear, educational manner.

Guidelines:
- Provide concise but comprehensive explanations
- Include practical code examples
- Mention best practices and common pitfalls
- Use simple language suitable for learners
- Focus on Python-specific behavior"""

SYSTEM_PROMPT_CHALLENGE = """You are an expert Python programming instructor who creates educational code challenges.

Guidelines:
- Create realistic code examples with intentional issues
- Issues should be educational and common in real-world code
- Provide helpful hints without giving away the answer
- Include clear learning objectives
- Match difficulty to the specified level"""


def get_node_explanation_prompt(
    node_type: str,
    node_name: Optional[str],
    node_info: dict,
    code_context: Optional[str] = None
) -> str:
    """Generate prompt for node explanation"""
    
    prompt = f"""Explain the Python AST node type: {node_type.upper()}

"""
    
    if node_name:
        prompt += f"Node name/identifier: {node_name}\n\n"
    
    if node_info:
        prompt += f"Node details:\n"
        for key, value in node_info.items():
            prompt += f"- {key}: {value}\n"
        prompt += "\n"
    
    if code_context:
        prompt += f"""Code context:
```python
{code_context}
```

"""
    
    prompt += """Please provide a structured explanation with:
1. A brief explanation of what this node represents (1-2 sentences)
2. Detailed documentation about how it works in Python (2-3 paragraphs)
3. 2-3 practical code examples showing correct usage
4. A list of 3-6 related concepts/keywords

Format your response as JSON:
{
  "explanation": "Brief explanation here",
  "python_doc": "Detailed documentation here",
  "examples": ["example 1", "example 2"],
  "related_concepts": ["concept1", "concept2"]
}"""
    
    return prompt


def get_challenge_generation_prompt(
    category: str,
    difficulty: str,
    topic: Optional[str] = None,
    focus_issues: Optional[List[str]] = None
) -> str:
    """Generate prompt for challenge creation"""
    
    difficulty_descriptions = {
        "easy": "Simple issues that beginners can identify. 1-2 issues in the code.",
        "medium": "Moderate complexity issues. 2-3 issues requiring good understanding.",
        "hard": "Complex or subtle issues. 3-4 issues requiring expert knowledge."
    }
    
    prompt = f"""Create a Python code challenge for finding issues in code.

Category: {category}
Difficulty: {difficulty} - {difficulty_descriptions.get(difficulty, "")}
"""
    
    if topic:
        prompt += f"\nTopic/Focus: {topic}\n"
    
    if focus_issues:
        prompt += f"\nShould include these types of issues: {', '.join(focus_issues)}\n"
    
    prompt += """

Create a realistic Python function or class with intentional issues that learners should identify.

Format your response as JSON:
{
  "title": "Challenge title",
  "description": "What the learner should do (1-2 sentences)",
  "category": "performance/security/complexity/code_smell/best_practice",
  "code": "The Python code with issues (use proper indentation)",
  "issues": ["issue_id_1", "issue_id_2"],
  "difficulty": "easy/medium/hard",
  "learning_objectives": ["objective 1", "objective 2"],
  "hints": ["hint 1 (don't give away answer)", "hint 2"],
  "solution_hint": "Brief hint about how to fix without full solution",
  "estimated_time_minutes": 5-15,
  "points": 100-350
}

Available issue IDs:
- nested_loop, list_membership, eval_usage, sql_injection
- deep_nesting, high_complexity, long_parameter_list
- unused_variable, empty_list_iteration, dead_code
- string_concat_in_loop, list_membership_check
- bare_except, resource_leak, broadException
- inefficient_recursion, no_memoization
- missing_type_hints, magic_string, no_enum
- memory_inefficient, no_generator
- race_condition, thread_unsafe, singleton_race
- hardcoded_dependency, datetime_coupling, tight_coupling
- boilerplate_code, missing_dataclass, manual_methods"""
    
    return prompt


def get_challenge_hint_prompt(
    code: str,
    issues: List[str],
    user_progress: str
) -> str:
    """Generate prompt for contextual hints"""
    
    return f"""A learner is working on a code challenge. Provide a helpful hint.

Code:
```python
{code}
```

Issues to find: {', '.join(issues)}
User's current progress: {user_progress}

Provide ONE specific hint that helps them progress without giving away the answer.
Keep it under 2 sentences.

Format: {{"hint": "Your hint here"}}"""


def get_code_improvement_prompt(
    code: str,
    issues: List[str]
) -> str:
    """Generate prompt for code improvement suggestions"""
    
    return f"""Analyze the following Python code and suggest improvements.

Code:
```python
{code}
```

Issues identified: {', '.join(issues)}

Provide improved code with explanations of changes.

Format your response as JSON:
{{
  "improved_code": "The improved Python code",
  "changes": [
    {{"issue": "issue_id", "fix": "description of the fix"}}
  ],
  "explanation": "Overall explanation of improvements"
}}"""


def get_learning_summary_prompt(
    completed_challenges: List[dict],
    identified_issues: List[str],
    missed_issues: List[str]
) -> str:
    """Generate prompt for personalized learning summary"""
    
    return f"""Generate a personalized learning summary for a Python programmer.

Completed challenges: {len(completed_challenges)}
Issues correctly identified: {', '.join(identified_issues) if identified_issues else 'None'}
Issues missed: {', '.join(missed_issues) if missed_issues else 'None'}

Provide:
1. A brief assessment of their strengths
2. Areas that need improvement
3. Recommended next steps

Keep it concise (3-4 sentences total).

Format: {{"summary": "Your summary here"}}"""
