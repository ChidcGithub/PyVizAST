"""
AST Relationship Builder - Build code relationships from AST

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
from typing import Dict, List, Optional, Set

from ..models.schemas import ASTNode, ASTEdge, NodeType, VariableInfo, CodeRelationship

logger = logging.getLogger(__name__)


class RelationshipBuilder:
    """Build code relationships from parsed AST nodes"""
    
    def __init__(self):
        self._class_hierarchy: Dict[str, List[str]] = {}
        self._class_nodes: Dict[str, ASTNode] = {}
        self._function_nodes: Dict[str, ASTNode] = {}
        self._import_map: Dict[str, str] = {}
        self._scope_stack: List[str] = []
        self._variable_scopes: Dict[str, Set[str]] = {}
        self._global_vars: Set[str] = set()
        self._nonlocal_vars: Dict[str, Set[str]] = {}
    
    def reset(self):
        """Reset the builder state"""
        self._class_hierarchy = {}
        self._class_nodes = {}
        self._function_nodes = {}
        self._import_map = {}
        self._scope_stack = []
        self._variable_scopes = {}
        self._global_vars = set()
        self._nonlocal_vars = {}
    
    def track_node(self, node: ASTNode):
        """Track node for relationship building"""
        # Track class and function nodes for relationship building
        if node.type == NodeType.CLASS and node.name:
            self._class_nodes[node.name] = node
            self._class_hierarchy[node.name] = node.base_classes
        elif node.type == NodeType.FUNCTION and node.name:
            # Store with scope context
            scope_key = f"{self._scope_stack[-1]}.{node.name}" if self._scope_stack else node.name
            self._function_nodes[scope_key] = node
        
        # Track imports
        if node.type == NodeType.IMPORT and node.attributes.get('names'):
            for name, alias in node.attributes['names']:
                self._import_map[alias or name] = node.attributes.get('module', name) or name
    
    def push_scope(self, node_id: str):
        """Push scope onto stack"""
        self._scope_stack.append(node_id)
    
    def pop_scope(self):
        """Pop scope from stack"""
        if self._scope_stack:
            self._scope_stack.pop()
    
    def build_inheritance_relationships(self, nodes: Dict[str, ASTNode], 
                                        edges: List[ASTEdge],
                                        relationships: List[CodeRelationship]):
        """Build class inheritance relationships"""
        for class_name, base_names in self._class_hierarchy.items():
            class_node = self._class_nodes.get(class_name)
            if not class_node:
                continue
            
            for base_name in base_names:
                base_node = self._class_nodes.get(base_name)
                if base_node:
                    # Add edge for inheritance
                    edge_id = f"edge_{len(edges) + 1}"
                    edges.append(ASTEdge(
                        id=edge_id,
                        source=class_node.id,
                        target=base_node.id,
                        edge_type="inheritance",
                        label=f"extends {base_name}"
                    ))
                    
                    # Add relationship
                    relationships.append(CodeRelationship(
                        source_id=class_node.id,
                        target_id=base_node.id,
                        relationship_type="inheritance",
                        details=f"{class_name} extends {base_name}"
                    ))
                    
                    # Track derived classes
                    if base_name not in base_node.derived_classes:
                        base_node.derived_classes.append(class_name)
                    
                    # Track inherited methods
                    for method in base_node.methods:
                        if method not in class_node.inherited_methods:
                            class_node.inherited_methods.append(method)
                    
                    # Check for overridden methods
                    for method in class_node.methods:
                        if method in base_node.methods and method not in class_node.overridden_methods:
                            class_node.overridden_methods.append(method)
            
            # Calculate inheritance depth
            class_node.inheritance_depth = self._calculate_inheritance_depth(class_name)
    
    def _calculate_inheritance_depth(self, class_name: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate inheritance depth for a class"""
        if visited is None:
            visited = set()
        
        if class_name in visited:
            return 0
        visited.add(class_name)
        
        base_names = self._class_hierarchy.get(class_name, [])
        if not base_names:
            return 0
        
        max_depth = 0
        for base_name in base_names:
            if base_name in self._class_hierarchy:
                depth = self._calculate_inheritance_depth(base_name, visited)
                max_depth = max(max_depth, depth + 1)
            else:
                max_depth = max(max_depth, 1)
        
        return max_depth
    
    def build_call_relationships(self, nodes: Dict[str, ASTNode],
                                  edges: List[ASTEdge],
                                  relationships: List[CodeRelationship]):
        """Build function call relationships"""
        # Map function names to nodes (considering scope)
        function_map: Dict[str, ASTNode] = {}
        for node in nodes.values():
            if node.type == NodeType.FUNCTION and node.name:
                function_map[node.name] = node
        
        # Track call counts
        call_counts: Dict[str, int] = {}
        
        for node in nodes.values():
            if node.type == NodeType.CALL and node.name:
                # Check if calling a defined function
                if node.name in function_map:
                    target_node = function_map[node.name]
                    edge_id = f"edge_{len(edges) + 1}"
                    edges.append(ASTEdge(
                        id=edge_id,
                        source=node.id,
                        target=target_node.id,
                        edge_type="call",
                        label=node.name
                    ))
                    
                    # Track caller/callee relationships
                    if target_node.id not in node.calls_to:
                        node.calls_to.append(target_node.id)
                    if node.id not in target_node.called_by:
                        target_node.called_by.append(node.id)
                    
                    # Count calls
                    call_counts[node.name] = call_counts.get(node.name, 0) + 1
        
        # Update is_called_count for functions
        for func_name, count in call_counts.items():
            if func_name in function_map:
                function_map[func_name].is_called_count = count
    
    def build_import_relationships(self, nodes: Dict[str, ASTNode],
                                    edges: List[ASTEdge]):
        """Build import relationships"""
        import_nodes: Dict[str, ASTNode] = {}
        
        for node in nodes.values():
            if node.type == NodeType.IMPORT:
                if node.attributes.get('names'):
                    for name, alias in node.attributes['names']:
                        key = alias or name
                        if key:
                            import_nodes[key] = node
                            node.imported_symbols[key] = node.attributes.get('module', name) or name
                            if alias:
                                node.import_aliases[alias] = name
        
        # Check if name nodes use imports
        for node in nodes.values():
            if node.type == NodeType.NAME and node.name in import_nodes:
                import_node = import_nodes[node.name]
                edge_id = f"edge_{len(edges) + 1}"
                edges.append(ASTEdge(
                    id=edge_id,
                    source=node.id,
                    target=import_node.id,
                    edge_type="import-usage",
                    label=node.name
                ))
    
    def build_decorator_relationships(self, nodes: Dict[str, ASTNode],
                                       edges: List[ASTEdge]):
        """Build decorator relationships"""
        decorator_functions: Dict[str, ASTNode] = {}
        for node in nodes.values():
            if node.type == NodeType.FUNCTION and node.name:
                decorator_functions[node.name] = node
        
        for node in nodes.values():
            if node.decorators:
                for dec_name in node.decorators:
                    if dec_name in decorator_functions:
                        dec_node = decorator_functions[dec_name]
                        edge_id = f"edge_{len(edges) + 1}"
                        edges.append(ASTEdge(
                            id=edge_id,
                            source=node.id,
                            target=dec_node.id,
                            edge_type="decorator",
                            label=f"@{dec_name}"
                        ))
                        
                        # Track decorated_by
                        if dec_node.id not in node.decorated_by:
                            node.decorated_by.append(dec_node.id)
                        
                        # Track decorates
                        if node.id not in dec_node.decorates:
                            dec_node.decorates.append(node.id)
    
    def analyze_variable_scopes(self, nodes: Dict[str, ASTNode]):
        """Analyze variable definitions and usages across scopes"""
        # Find all variable definitions
        var_definitions: Dict[str, List[tuple]] = {}  # var_name -> [(node_id, lineno, scope)]
        
        for node in nodes.values():
            if node.type == NodeType.ASSIGN and node.name:
                scope = node.scope_name or "global"
                for var_name in node.name.split(" = "):
                    var_name = var_name.strip()
                    if var_name:
                        if var_name not in var_definitions:
                            var_definitions[var_name] = []
                        var_definitions[var_name].append((node.id, node.lineno or 0, scope))
                        
                        # Add to variables_defined
                        node.variables_defined.append(VariableInfo(
                            name=var_name,
                            lineno=node.lineno,
                            is_definition=True,
                            scope=scope
                        ))
        
        # Find variable usages
        for node in nodes.values():
            if node.type == NodeType.NAME and node.name:
                if node.name in var_definitions:
                    # Find the definition in the closest scope
                    definitions = var_definitions[node.name]
                    for def_node_id, def_lineno, def_scope in definitions:
                        # Add usage info
                        node.variables_used.append(VariableInfo(
                            name=node.name,
                            lineno=node.lineno,
                            is_usage=True,
                            scope=def_scope
                        ))
                        node.used_in.append(def_node_id)
    
    def post_process_nodes(self, nodes: Dict[str, ASTNode]):
        """Post-process nodes to calculate additional metrics"""
        def get_depth(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            node = nodes.get(node_id)
            if not node or not node.parent:
                return 0
            return 1 + get_depth(node.parent, visited)
        
        def count_descendants(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            node = nodes.get(node_id)
            if not node or not node.children:
                return 0
            count = len(node.children)
            for child_id in node.children:
                count += count_descendants(child_id, visited.copy())
            return count
        
        def get_scope_name(node_id: str) -> Optional[str]:
            node = nodes.get(node_id)
            if not node or not node.parent:
                return None
            
            parent = nodes.get(node.parent)
            if not parent:
                return None
            
            if parent.type in (NodeType.FUNCTION, NodeType.CLASS) and parent.name:
                return parent.name
            
            return get_scope_name(node.parent)
        
        def get_nested_scopes(node_id: str) -> List[str]:
            """Get IDs of nested functions/classes"""
            nested = []
            node = nodes.get(node_id)
            if not node:
                return nested
            
            def collect_nested(nid: str, depth: int):
                if depth > 5:
                    return
                n = nodes.get(nid)
                if not n:
                    return
                for child_id in n.children:
                    child = nodes.get(child_id)
                    if child and child.type in (NodeType.FUNCTION, NodeType.CLASS):
                        nested.append(child_id)
                    collect_nested(child_id, depth + 1)
            
            collect_nested(node_id, 0)
            return nested
        
        # Count function calls for each function
        call_counts = {}
        for node in nodes.values():
            if node.type == NodeType.CALL and node.name:
                call_counts[node.name] = call_counts.get(node.name, 0) + 1
        
        # Update each node
        for node_id, node in nodes.items():
            node.child_count = len(node.children)
            node.total_descendants = count_descendants(node_id, set())
            node.depth = get_depth(node_id, set())
            node.scope_name = get_scope_name(node_id)
            
            if node.type == NodeType.FUNCTION and node.name:
                node.is_called_count = call_counts.get(node.name, 0)
            
            if node.source_code:
                node.char_count = len(node.source_code)
            
            # Get nested scopes
            node.nested_scopes = get_nested_scopes(node_id)
