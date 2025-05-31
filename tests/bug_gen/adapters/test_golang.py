from swesmith.bug_gen.adapters.golang import (
    go_get_entities_from_file,
)


def test_go_get_entities_from_file(go_test_file):
    entities = []
    go_get_entities_from_file(entities, go_test_file)
    assert len(entities) == 12
