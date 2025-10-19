# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Atlas CLI - Command-line interface for the semantic space

Interact with the 5D semantic space through the command line.
"""

import argparse
import json
import numpy as np

from atlas.space import SemanticSpace
from atlas.dimensions import DimensionMapper
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder


def print_separator(char="=", length=70):
    """Print a separator line"""
    print(char * length)


def print_section(title: str):
    """Print a section header"""
    print_separator()
    print(f"  {title}")
    print_separator()


def cmd_encode(args):
    """Encode text to 5D vector"""
    space = SemanticSpace()
    vector = space.encode(args.text)

    print_section("ENCODING RESULT")
    print(f'\nInput text: "{args.text}"')
    print(f"\n5D Vector: {vector}")

    if args.explain:
        print("\nDimensional Interpretation:")
        mapper = DimensionMapper()
        print(mapper.explain_vector(vector))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(
                {"text": args.text, "vector": vector.tolist()}, f, indent=2, ensure_ascii=False
            )
        print(f"\nSaved to: {args.output}")


def cmd_decode(args):
    """Decode 5D vector to text"""
    space = SemanticSpace()

    # Parse vector
    if args.vector:
        vector = np.array([float(x) for x in args.vector])
    elif args.input:
        with open(args.input, "r") as f:
            data = json.load(f)
            vector = np.array(data["vector"])
    else:
        print("Error: Must provide either --vector or --input")
        return

    result = space.decode(vector, with_reasoning=args.reasoning)

    print_section("DECODING RESULT")
    print(f"\n5D Vector: {vector}")

    if args.reasoning:
        print("\nReasoning Process:")
        print(result["reasoning"])
        print(f"\nDecoded Text: \"{result['text']}\"")
    else:
        print(f'\nDecoded Text: "{result}"')


def cmd_transform(args):
    """Transform text through the semantic space"""
    space = SemanticSpace()
    result = space.transform(args.text, show_reasoning=args.reasoning)

    print_section("TRANSFORMATION")
    print(f"\nOriginal: \"{result['original_text']}\"")
    print(f"\nVector: {result['vector']}")

    if args.reasoning:
        print("\nDecoding Reasoning:")
        print(result["decoded"]["reasoning"])
        print(f"\nReconstructed: \"{result['decoded']['text']}\"")
    else:
        print(f"\nReconstructed: \"{result['decoded']}\"")


def cmd_manipulate(args):
    """Manipulate a specific dimension"""
    space = SemanticSpace()
    result = space.manipulate_dimension(args.text, args.dimension, args.value)

    print_section("DIMENSION MANIPULATION")

    print("\n=== ORIGINAL ===")
    print(f"Text: \"{result['original']['text']}\"")
    print(f"Vector: {result['original']['vector']}")
    if args.reasoning:
        print("\nReasoning:")
        print(result["original"]["decoded"]["reasoning"])
    print(f"Decoded: \"{result['original']['decoded']['text']}\"")

    print("\n=== MODIFIED ===")
    print(f"Changed: {result['modified']['dimension_changed']}")
    print(f"New value: {result['modified']['new_value']}")
    print(f"Vector: {result['modified']['vector']}")
    if args.reasoning:
        print("\nReasoning:")
        print(result["modified"]["decoded"]["reasoning"])
    print(f"Decoded: \"{result['modified']['decoded']['text']}\"")


def cmd_interpolate(args):
    """Interpolate between two texts"""
    space = SemanticSpace()
    results = space.interpolate(args.text1, args.text2, args.steps)

    print_section("SEMANTIC INTERPOLATION")
    print(f'\nFrom: "{args.text1}"')
    print(f'To: "{args.text2}"')
    print(f"Steps: {args.steps}\n")

    for result in results:
        print(f"\nStep {result['step']} (α={result['alpha']:.2f}):")
        print(f"  Vector: {[f'{v:.2f}' for v in result['vector']]}")
        print(f"  Text: \"{result['decoded']['text']}\"")


def cmd_explore(args):
    """Explore how a dimension affects meaning"""
    space = SemanticSpace()

    # Generate range if not provided
    if args.range:
        values = [float(x) for x in args.range]
    else:
        values = list(np.linspace(-1, 1, args.steps))

    results = space.explore_dimension(args.text, args.dimension, values)

    print_section("DIMENSION EXPLORATION")
    print(f'\nBase text: "{args.text}"')
    print(f"Exploring: {results[0]['dimension']}\n")

    for result in results:
        print(f"\nValue: {result['value']:.2f}")
        print(f"  Text: \"{result['decoded']['text']}\"")


def cmd_info(args):
    """Show information about dimensions"""
    space = SemanticSpace()
    info = space.get_dimension_info()

    print_section("ATLAS SEMANTIC DIMENSIONS")
    print("\nThe 5 axes of meaning - regulators of semantic state:\n")

    for dim_key, dim_info in info.items():
        print(f"{dim_key.upper()}: {dim_info['name']}")
        print(f"  Poles: {dim_info['poles'][0]} ↔ {dim_info['poles'][1]}")
        print(f"  Role: {dim_info['description']}")
        print()


def cmd_encode_h(args):
    """Encode text to hierarchical tree"""
    encoder = HierarchicalEncoder()
    tree = encoder.encode_hierarchical(
        args.text, max_depth=args.max_depth, expand_threshold=args.expand_threshold
    )

    print_section("HIERARCHICAL ENCODING")
    print(f'\nInput text: "{args.text}"')
    print(f"Max depth: {args.max_depth}")
    print(f"Expand threshold: {args.expand_threshold}\n")

    # Print tree structure
    print("Hierarchical Tree:")
    _print_tree(tree, indent=0)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(tree.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {args.output}")


def _print_tree(node, indent=0):
    """Helper to print tree structure"""
    prefix = "  " * indent
    label = node.label or "unlabeled"
    key = node.key or "root"
    weight = node.weight or 1.0

    print(f"{prefix}[{key}] {label} (w={weight:.2f})")
    print(f"{prefix}  value: {[f'{v:.2f}' for v in node.value]}")

    if node.children:
        for child in node.children:
            _print_tree(child, indent + 1)


def cmd_decode_h(args):
    """Decode hierarchical tree to text"""
    decoder = HierarchicalDecoder()

    # Load tree from file
    with open(args.input, "r") as f:
        from atlas.hierarchical import TreeNode

        tree_data = json.load(f)
        tree = TreeNode(**tree_data)

    result = decoder.decode_hierarchical(tree, top_k=args.top_k, with_reasoning=args.reasoning)

    print_section("HIERARCHICAL DECODING")

    if args.reasoning:
        print("\nPath Reasoning:")
        for r in result["reasoning"]:
            print(f"  {r.path}: {r.label} (weight={r.weight:.2f})")
            if r.evidence:
                print(f"    Evidence: {', '.join(r.evidence)}")
        print()

    print(f"Decoded Text: \"{result['text']}\"")


def cmd_manipulate_h(args):
    """Manipulate hierarchical tree by path"""
    encoder = HierarchicalEncoder()
    decoder = HierarchicalDecoder()

    # Encode original
    original_tree = encoder.encode_hierarchical(args.text, max_depth=2)
    original_decoded = decoder.decode_hierarchical(original_tree, top_k=3)

    print_section("HIERARCHICAL MANIPULATION")

    print("\n=== ORIGINAL ===")
    print(f'Text: "{args.text}"')
    print(f"Decoded: \"{original_decoded['text']}\"")
    if args.reasoning:
        print("Path reasoning:")
        for r in original_decoded.get("reasoning", []):
            print(f"  {r.path}: {r.label} (w={r.weight:.2f})")

    # Parse edits
    edits = []
    for edit_str in args.edit:
        # Format: "path=v1,v2,v3,v4,v5"
        parts = edit_str.split("=")
        if len(parts) != 2:
            print(f"Error: Invalid edit format '{edit_str}'. Use 'path=v1,v2,v3,v4,v5'")
            return
        path = parts[0]
        values = [float(x) for x in parts[1].split(",")]
        if len(values) != 5:
            print(f"Error: Edit values must have 5 components, got {len(values)}")
            return
        edits.append((path, values))

    # Apply edits
    modified_tree = original_tree
    for path, values in edits:
        modified_tree = decoder.manipulate_path(modified_tree, path, values)

    # Decode modified
    modified_decoded = decoder.decode_hierarchical(modified_tree, top_k=3)

    print("\n=== MODIFIED ===")
    print(f"Edits applied: {len(edits)}")
    for path, values in edits:
        print(f"  {path} = {[f'{v:.2f}' for v in values]}")
    print(f"\nDecoded: \"{modified_decoded['text']}\"")
    if args.reasoning:
        print("Path reasoning:")
        for r in modified_decoded.get("reasoning", []):
            print(f"  {r.path}: {r.label} (w={r.weight:.2f})")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Atlas - Semantic Space Control Panel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Flat operations
  atlas encode "Собака бежит"
  atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning
  atlas transform "Любовь" --reasoning
  atlas manipulate "Собака" --dimension 1 --value -0.8
  atlas interpolate "Любовь" "Ненависть" --steps 5
  atlas explore "Жизнь" --dimension 2 --steps 5

  # Hierarchical operations (NEW)
  atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2
  atlas decode-h --input tree.json --top-k 3 --reasoning
  atlas manipulate-h "Собака" --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 --reasoning

  # Info
  atlas info
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Encode command
    parser_encode = subparsers.add_parser("encode", help="Encode text to 5D vector")
    parser_encode.add_argument("text", help="Text to encode")
    parser_encode.add_argument("--explain", action="store_true", help="Explain dimension values")
    parser_encode.add_argument("--output", "-o", help="Save result to JSON file")

    # Decode command
    parser_decode = subparsers.add_parser("decode", help="Decode 5D vector to text")
    parser_decode.add_argument("--vector", nargs=5, type=float, help="5D vector values")
    parser_decode.add_argument("--input", "-i", help="Load vector from JSON file")
    parser_decode.add_argument("--reasoning", action="store_true", help="Show reasoning process")

    # Transform command
    parser_transform = subparsers.add_parser(
        "transform", help="Transform text through semantic space"
    )
    parser_transform.add_argument("text", help="Text to transform")
    parser_transform.add_argument("--reasoning", action="store_true", help="Show reasoning")

    # Manipulate command
    parser_manipulate = subparsers.add_parser("manipulate", help="Manipulate a dimension")
    parser_manipulate.add_argument("text", help="Input text")
    parser_manipulate.add_argument(
        "--dimension",
        "-d",
        type=int,
        required=True,
        choices=[0, 1, 2, 3, 4],
        help="Dimension to change (0-4)",
    )
    parser_manipulate.add_argument(
        "--value", "-v", type=float, required=True, help="New value (-1 to 1)"
    )
    parser_manipulate.add_argument("--reasoning", action="store_true", help="Show reasoning")

    # Interpolate command
    parser_interpolate = subparsers.add_parser("interpolate", help="Interpolate between texts")
    parser_interpolate.add_argument("text1", help="First text")
    parser_interpolate.add_argument("text2", help="Second text")
    parser_interpolate.add_argument("--steps", type=int, default=5, help="Number of steps")

    # Explore command
    parser_explore = subparsers.add_parser("explore", help="Explore dimension effects")
    parser_explore.add_argument("text", help="Base text")
    parser_explore.add_argument(
        "--dimension",
        "-d",
        type=int,
        required=True,
        choices=[0, 1, 2, 3, 4],
        help="Dimension to explore (0-4)",
    )
    parser_explore.add_argument("--range", nargs="+", type=float, help="Values to try")
    parser_explore.add_argument("--steps", type=int, default=5, help="Number of steps if no range")

    # Hierarchical encode command (NEW)
    parser_encode_h = subparsers.add_parser("encode-h", help="Encode text to hierarchical tree")
    parser_encode_h.add_argument("text", help="Text to encode")
    parser_encode_h.add_argument(
        "--max-depth",
        type=int,
        default=1,
        choices=[0, 1, 2, 3, 4, 5],
        help="Maximum tree depth (default: 1)",
    )
    parser_encode_h.add_argument(
        "--expand-threshold",
        type=float,
        default=0.2,
        help="Threshold for lazy expansion (default: 0.2)",
    )
    parser_encode_h.add_argument("--output", "-o", help="Save tree to JSON file")

    # Hierarchical decode command (NEW)
    parser_decode_h = subparsers.add_parser("decode-h", help="Decode hierarchical tree to text")
    parser_decode_h.add_argument("--input", "-i", required=True, help="Load tree from JSON file")
    parser_decode_h.add_argument(
        "--top-k", type=int, default=3, help="Number of top paths (default: 3)"
    )
    parser_decode_h.add_argument("--reasoning", action="store_true", help="Show path reasoning")

    # Hierarchical manipulate command (NEW)
    parser_manipulate_h = subparsers.add_parser("manipulate-h", help="Manipulate tree by path")
    parser_manipulate_h.add_argument("text", help="Input text")
    parser_manipulate_h.add_argument(
        "--edit",
        action="append",
        required=True,
        help="Path edit: path=v1,v2,v3,v4,v5 (can be repeated)",
    )
    parser_manipulate_h.add_argument("--reasoning", action="store_true", help="Show path reasoning")

    # Info command
    parser_info = subparsers.add_parser("info", help="Show dimension information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route to appropriate command
    commands = {
        "encode": cmd_encode,
        "decode": cmd_decode,
        "transform": cmd_transform,
        "manipulate": cmd_manipulate,
        "interpolate": cmd_interpolate,
        "explore": cmd_explore,
        "encode-h": cmd_encode_h,
        "decode-h": cmd_decode_h,
        "manipulate-h": cmd_manipulate_h,
        "info": cmd_info,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
