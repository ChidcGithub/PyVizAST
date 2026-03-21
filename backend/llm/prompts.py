"""
LLM Prompt Templates - Optimized for Python AST Analysis

@author: Chidc
@link: github.com/chidcGithub
"""
from typing import List, Optional


# ============== System Prompts ==============

SYSTEM_PROMPT_EXPLANATION = """You are an expert Python programming educator specializing in AST (Abstract Syntax Tree) analysis.

Your role:
- Explain Python code constructs clearly and concisely
- Provide practical, runnable code examples
- Connect concepts to real-world programming scenarios
- Use simple language suitable for learners at all levels

Output format: Valid JSON only. No markdown, no code blocks, no explanation outside JSON."""

SYSTEM_PROMPT_CHALLENGE = """You are an expert Python code reviewer and educator creating educational challenges.

Your role:
- Create realistic code with intentional issues
- Design problems that teach common pitfalls
- Provide helpful hints without revealing answers
- Match difficulty appropriately

Output format: Valid JSON only. No markdown, no code blocks, no explanation outside JSON."""


# ============== Helper Functions ==============

def _escape_json_string(s: str) -> str:
    """Escape special characters for JSON strings"""
    if not s:
        return ""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def _truncate_code(code: str, max_length: int = 1500) -> str:
    """Truncate code while preserving readability"""
    if not code or len(code) <= max_length:
        return code
    return code[:max_length] + "\n# ... (truncated)"


# ============== Prompt Builders ==============

def get_node_explanation_prompt(
    node_type: str,
    node_name: Optional[str] = None,
    node_info: Optional[dict] = None,
    code_context: Optional[str] = None,
    full_code: Optional[str] = None
) -> str:
    """
    Generate prompt for AST node explanation.
    
    Optimized for:
    - Clear context about the node
    - Specific focus on the selected code
    - Practical examples
    """
    
    sections = []
    
    # Header
    sections.append("# Task: Explain Python AST Node\n")
    sections.append(f"Node Type: **{node_type}**\n")
    
    # Node identification
    if node_name:
        sections.append(f"Node Name: `{node_name}`\n")
    
    # Node details
    if node_info:
        details = []
        for key, value in node_info.items():
            if value is not None and value != '' and not (isinstance(value, (list, dict)) and len(value) == 0):
                details.append(f"- {key}: {value}")
        if details:
            sections.append("\n## Node Details\n" + "\n".join(details) + "\n")
    
    # Code context (most important)
    if code_context:
        sections.append(f"""
## Selected Code
This is the specific code being analyzed:
```python
{_truncate_code(code_context)}
```
""")
    
    # Full code context (secondary)
    if full_code and full_code != code_context:
        truncated_full = _truncate_code(full_code, 2000)
        sections.append(f"""
## Surrounding Code Context
```python
{truncated_full}
```
""")
    
    # Output format specification
    sections.append("""
## Required Output Format
Return ONLY valid JSON with this exact structure:
{
  "explanation": "Brief 1-2 sentence explanation of what this node does in the context of the code above",
  "python_doc": "Detailed documentation (2-3 paragraphs) about this Python construct, including syntax rules and behavior",
  "examples": [
    "# Example 1: Basic usage\\n...",
    "# Example 2: Common pattern\\n..."
  ],
  "related_concepts": ["concept1", "concept2", "concept3"]
}

Important:
- explanation should reference the specific code shown above
- examples should be practical and runnable
- related_concepts should include 3-5 relevant Python terms
- Return ONLY the JSON object, no other text
""")
    
    return "".join(sections)


def get_challenge_generation_prompt(
    category: str,
    difficulty: str = "medium",
    topic: Optional[str] = None,
    focus_issues: Optional[List[str]] = None
) -> str:
    """
    Generate prompt for creating code challenges.
    
    Optimized for:
    - Clear difficulty guidelines
    - Specific issue types
    - Realistic code scenarios
    """
    
    difficulty_specs = {
        "easy": {
            "issues": "1-2 issues",
            "complexity": "Simple code patterns, obvious issues",
            "time": "3-5 minutes",
            "points": "50-100"
        },
        "medium": {
            "issues": "2-3 issues",
            "complexity": "Moderate patterns, requires understanding",
            "time": "5-10 minutes",
            "points": "100-200"
        },
        "hard": {
            "issues": "3-4 issues",
            "complexity": "Complex/subtle issues, expert knowledge needed",
            "time": "10-15 minutes",
            "points": "200-350"
        }
    }
    
    spec = difficulty_specs.get(difficulty, difficulty_specs["medium"])
    
    sections = []
    
    sections.append(f"""# Task: Create Python Code Challenge

## Requirements
- Category: {category}
- Difficulty: **{difficulty}**
- Issues to include: {spec['issues']}
- Code complexity: {spec['complexity']}
- Estimated time: {spec['time']}
- Points: {spec['points']}
""")
    
    if topic:
        sections.append(f"- Topic/Focus: {topic}\n")
    
    if focus_issues:
        sections.append(f"- Must include these issue types: {', '.join(focus_issues)}\n")
    
    # Available issue types reference
    sections.append("""
## Available Issue IDs
Performance: nested_loop, list_membership, string_concat_in_loop, inefficient_recursion, no_memoization, memory_inefficient, no_generator
Security: eval_usage, sql_injection, bare_except, resource_leak, broad_exception, race_condition, thread_unsafe
Complexity: deep_nesting, high_complexity, long_parameter_list
Code Smell: unused_variable, empty_list_iteration, dead_code, magic_string, boilerplate_code
Best Practice: missing_type_hints, no_enum, hardcoded_dependency, tight_coupling
""")
    
    sections.append("""
## Required Output Format
Return ONLY valid JSON with this exact structure:
{
  "title": "Challenge Title",
  "description": "What the learner should do (1-2 sentences)",
  "category": "performance|security|complexity|code_smell|best_practice",
  "code": "def example():\\n    # Code with intentional issues\\n    pass",
  "issues": ["issue_id_1", "issue_id_2"],
  "difficulty": "easy|medium|hard",
  "learning_objectives": ["objective 1", "objective 2"],
  "hints": ["Hint 1 (helpful but not revealing)", "Hint 2"],
  "solution_hint": "Brief guidance without full solution",
  "estimated_time_minutes": 5,
  "points": 100
}

Important:
- Code must be valid Python with proper indentation
- Issues must be from the available issue IDs list
- Hints should guide without revealing the answer
- Return ONLY the JSON object, no other text
""")
    
    return "".join(sections)


def get_challenge_hint_prompt(
    code: str,
    issues: List[str],
    user_progress: str = ""
) -> str:
    """
    Generate prompt for contextual hints.
    
    Optimized for:
    - Brief, helpful hints
    - Progress-aware suggestions
    """
    
    sections = []
    
    sections.append(f"""# Task: Generate Contextual Hint

## Challenge Code
```python
{_truncate_code(code, 1000)}
```

## Issues to Find
{', '.join(issues) if issues else 'Not specified'}

## User's Progress
{user_progress if user_progress else 'Just started'}
""")
    
    sections.append("""
## Required Output Format
Return ONLY valid JSON:
{
  "hint": "One specific hint (under 2 sentences) that helps progress without revealing the answer"
}

Important:
- Hint must be helpful but not give away the solution
- Consider what the user has already found
- Return ONLY the JSON object
""")
    
    return "".join(sections)


def get_code_improvement_prompt(
    code: str,
    issues: List[str]
) -> str:
    """
    Generate prompt for code improvement suggestions.
    
    Optimized for:
    - Clear before/after comparison
    - Specific fix explanations
    """
    
    sections = []
    
    sections.append(f"""# Task: Suggest Code Improvements

## Original Code
```python
{_truncate_code(code, 2000)}
```

## Identified Issues
{chr(10).join(f'- {issue}' for issue in issues) if issues else 'No specific issues provided'}
""")
    
    sections.append("""
## Required Output Format
Return ONLY valid JSON:
{
  "improved_code": "The improved Python code with all fixes applied",
  "changes": [
    {
      "issue": "issue_id",
      "fix": "Description of what was changed and why"
    }
  ],
  "explanation": "Brief summary of overall improvements (1-2 sentences)"
}

Important:
- improved_code must be complete, runnable Python
- Each change should explain both what and why
- Return ONLY the JSON object
""")
    
    return "".join(sections)


def get_learning_summary_prompt(
    completed_challenges: List[dict],
    identified_issues: List[str],
    missed_issues: List[str]
) -> str:
    """
    Generate prompt for personalized learning summary.
    
    Optimized for:
    - Actionable feedback
    - Clear next steps
    """
    
    total = len(identified_issues) + len(missed_issues)
    accuracy = (len(identified_issues) / total * 100) if total > 0 else 0
    
    sections = []
    
    sections.append(f"""# Task: Generate Learning Summary

## Performance
- Challenges completed: {len(completed_challenges)}
- Issues found: {len(identified_issues)}
- Issues missed: {len(missed_issues)}
- Accuracy: {accuracy:.0f}%

## Issues Correctly Identified
{', '.join(identified_issues) if identified_issues else 'None'}

## Issues Missed
{', '.join(missed_issues) if missed_issues else 'None'}
""")
    
    sections.append("""
## Required Output Format
Return ONLY valid JSON:
{
  "summary": "Personalized assessment (3-4 sentences covering strengths, areas for improvement, and recommended next steps)"
}

Important:
- Be encouraging while honest
- Suggest specific topics to study
- Return ONLY the JSON object
""")
    
    return "".join(sections)