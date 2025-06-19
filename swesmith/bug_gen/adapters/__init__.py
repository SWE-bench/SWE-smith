from swesmith.bug_gen.adapters.golang import (
    get_entities_from_file_go,
)
from swesmith.bug_gen.adapters.java import (
    get_entities_from_file_java,
)
from swesmith.bug_gen.adapters.python import (
    get_entities_from_file_py,
)
from swesmith.bug_gen.adapters.ruby import (
    get_entities_from_file_rb,
)

get_entities_from_file = {
    "go": get_entities_from_file_go,
    "java": get_entities_from_file_java,
    "py": get_entities_from_file_py,
    "rb": get_entities_from_file_rb,
}
