from swesmith.bug_gen.adapters.golang import (
    go_get_entities_from_file,
)
from swesmith.bug_gen.adapters.python import (
    py_get_entities_from_file,
)

get_entities_from_file = {
    "go": go_get_entities_from_file,
    "py": py_get_entities_from_file,
}
