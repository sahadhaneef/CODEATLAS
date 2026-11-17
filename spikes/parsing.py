"""In-memory syntax span prototype. Input is bytes, never an executable project."""

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_typescript


def definitions(content: bytes, language: str):
    grammar = {
        "python": tree_sitter_python.language,
        "typescript": tree_sitter_typescript.language_typescript,
        "tsx": tree_sitter_typescript.language_tsx,
    }[language]
    tree = Parser(Language(grammar())).parse(content)
    spans = []

    def visit(node):
        if node.type in ("function_definition", "class_definition", "function_declaration"):
            name = node.child_by_field_name("name")
            if name:
                spans.append(
                    {
                        "name": content[name.start_byte : name.end_byte].decode("utf-8"),
                        "start_byte": node.start_byte,
                        "end_byte": node.end_byte,
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + (1 if node.end_point.column else 0),
                    }
                )
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return {
        "has_errors": tree.root_node.has_error,
        "definitions": spans,
        "capability": "syntax_only",
        "resolved_references": False,
    }
