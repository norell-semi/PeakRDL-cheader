from typing import Union, Optional, List

from systemrdl.node import AddressableNode, AddrmapNode, Node, MemNode, RegfileNode, RegNode, FieldNode
from .design_state import DesignState

def get_node_prefix(ds: DesignState, root_node: Union[AddrmapNode, MemNode, RegfileNode], node: AddressableNode) -> str:
    if ds.reuse_typedefs:
        prefix = node.get_global_type_name("__")
        if prefix is None:
            # Unable to determine a reusable type name. Fall back to hierarchical path
            # Add prefix to prevent collision when mixing namespace methods
            prefix = "xtern__" + node.get_rel_path(
                root_node.parent,
                hier_separator="__",
                array_suffix="x",
                empty_array_suffix="x"
            )
    else:
        prefix = node.get_rel_path(
            root_node.parent,
            hier_separator="__",
            array_suffix="x",
            empty_array_suffix="x"
        )
    return prefix


def get_struct_name(ds: DesignState, root_node: Union[AddrmapNode, MemNode, RegfileNode], node: AddressableNode) -> str:
    if node.is_array and node.array_stride > node.size: # type: ignore # is_array implies array_stride is not none
        # Stride is larger than size of actual element.
        # Struct will be padded up, and therefore needs a unique name
        pad_suffix = f"__stride{node.array_stride:x}"
    else:
        pad_suffix = ""

    return get_node_prefix(ds, root_node, node) + pad_suffix + "_t"


def get_friendly_name(ds: DesignState, root_node: Union[AddrmapNode, MemNode, RegfileNode], node: Node) -> str:
    """
    Returns a useful string that helps identify the typedef in
    a comment
    """
    if ds.reuse_typedefs:
        friendly_name = node.get_global_type_name("::")

        if friendly_name is None:
            # Unable to determine a reusable type name. Fall back to hierarchical path
            friendly_name = node.get_rel_path(root_node.parent)
    else:
        friendly_name = node.get_rel_path(root_node.parent)

    return node.component_type_name + " - " + friendly_name

def get_field_prefix(reg_prefix: str, field: FieldNode) -> str:
    """
    Anonymous fields are referred to by their register's name
    """
    if field.is_anonymous:
        return reg_prefix
    return reg_prefix + "__" + field.inst_name.upper()


def reg_has_bitfields(ds: DesignState, node: RegNode) -> bool:
    """
    Registers with an anonymous field are emitted as a plain word rather than
    a bitfield union
    """
    return ds.generate_bitfields and node.anonymous_field is None


def get_all_regs(node: Node) -> List[RegNode]:
    return [n for n in node.descendants() if isinstance(n, RegNode)]


def get_reg_addr_macro_name(root_node: Union[AddrmapNode, MemNode, RegfileNode], node: RegNode) -> str:
    """
    Address macros are per-instance, so they are always named hierarchically
    """
    path = node.get_rel_path(
        root_node.parent,
        hier_separator="__",
        array_suffix="",
        empty_array_suffix="",
    )
    return path.upper() + "_addr"


def get_reg_addr_macro(ds: DesignState, root_node: Union[AddrmapNode, MemNode, RegfileNode], node: RegNode) -> str:
    """
    Returns the #define for the register's absolute address.
    Each array dimension within the register's lineage (from root_node down)
    becomes an index argument of a function-like macro.
    """
    array_nodes = []
    current: Optional[Node] = node
    while current is not None:
        if isinstance(current, AddressableNode) and current.is_array:
            array_nodes.append(current)
        if current is root_node:
            break
        current = current.parent
    array_nodes.reverse()

    terms = [f"{node.raw_absolute_address + ds.inst_offset:#x}UL"]
    args: List[str] = []
    for array_node in array_nodes:
        assert array_node.array_dimensions is not None
        assert array_node.array_stride is not None
        dims = array_node.array_dimensions
        for i in range(len(dims)):
            stride = array_node.array_stride
            for dim in dims[i+1:]:
                stride *= dim
            arg = f"i{len(args)}"
            args.append(arg)
            terms.append(f"({arg}) * {stride:#x}UL")

    name = get_reg_addr_macro_name(root_node, node)
    if args:
        return f"#define {name}({', '.join(args)}) ({' + '.join(terms)})"
    return f"#define {name} {terms[0]}"


def roundup_pow2(x: int) -> int:
    return 1<<(x-1).bit_length()
