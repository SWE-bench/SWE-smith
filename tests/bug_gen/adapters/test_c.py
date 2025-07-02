import pytest

from swesmith.bug_gen.adapters.c import (
    get_entities_from_file_c,
)


@pytest.fixture
def entities(test_file_c):
    entities = []
    get_entities_from_file_c(entities, test_file_c)
    return entities


def test_get_entities_from_file_c_count(entities):
    assert len(entities) == 15


def test_get_entities_from_file_c_max(test_file_c):
    entities = []
    get_entities_from_file_c(entities, test_file_c, 3)
    assert len(entities) == 3


def test_get_entities_from_file_c_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_c([], "non-existent-file")


def test_get_entities_from_file_c_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.c"
    no_functions_file.write_text("// there are no functions here")
    entities = []
    get_entities_from_file_c(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_c_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "restore_signals",
        "isolate_child",
        "spawn",
        "print_usage",
        "print_license",
        "set_pdeathsig",
        "add_expect_status",
        "parse_args",
        "parse_env",
        "register_subreaper",
        "reaper_check",
        "configure_signals",
        "wait_and_forward_signal",
        "reap_zombies",
        "main",
    ]
    assert names == expected_names


def test_get_entities_from_file_c_line_ranges(entities):
    start_end = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (132, 149),
        (151, 179),
        (182, 225),
        (227, 271),
        (273, 281),
        (283, 295),
        (297, 313),
        (315, 400),
        (402, 419),
        (423, 437),
        (441, 460),
        (463, 506),
        (508, 546),
        (548, 611),
        (614, 688),
    ]
    assert start_end == expected_ranges


def test_get_entities_from_file_c_extensions(entities):
    assert all([e.ext == "c" for e in entities]), (
        "All entities should have the extension 'c'"
    )


def test_get_entities_from_file_c_file_paths(entities, test_file_c):
    assert all([e.file_path == test_file_c for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_c_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "int restore_signals(const signal_configuration_t* const sigconf_ptr)",
        "int isolate_child(void)",
        "int spawn(const signal_configuration_t* const sigconf_ptr, char* const argv[], int* const child_pid_ptr)",
        "void print_usage(char* const name, FILE* const file)",
        "void print_license(FILE* const file)",
        "int set_pdeathsig(char* const arg)",
        "int add_expect_status(char* arg)",
        "int parse_args(const int argc, char* const argv[], char* (**child_args_ptr_ptr)[], int* const parse_fail_exitcode_ptr)",
        "int parse_env(void)",
        "int register_subreaper (void)",
        "void reaper_check (void)",
        "int configure_signals(sigset_t* const parent_sigset_ptr, const signal_configuration_t* const sigconf_ptr)",
        "int wait_and_forward_signal(sigset_t const* const parent_sigset_ptr, pid_t const child_pid)",
        "int reap_zombies(const pid_t child_pid, int* const child_exitcode_ptr)",
        "int main(int argc, char *argv[])",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_c_multi_line_signature(tmp_path):
    multi_line_signature_file = tmp_path / "multi_line_sig.c"
    multi_line_signature_file.write_text(
        "void multi_line(\n\tint a1,\n\tint a2,\n\tint a3\n)\n{\n}"
    )
    entities = []
    get_entities_from_file_c(entities, multi_line_signature_file)
    assert len(entities) == 1
    assert entities[0].signature == "void multi_line(int a1, int a2, int a3)"


def test_get_entities_from_file_c_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "int restore_signals(const signal_configuration_t* const sigconf_ptr) {\n\t// TODO: Implement this function\n}",
        "int isolate_child(void) {\n\t// TODO: Implement this function\n}",
        "int spawn(const signal_configuration_t* const sigconf_ptr, char* const argv[], int* const child_pid_ptr) {\n\t// TODO: Implement this function\n}",
        "void print_usage(char* const name, FILE* const file) {\n\t// TODO: Implement this function\n}",
        "void print_license(FILE* const file) {\n\t// TODO: Implement this function\n}",
        "int set_pdeathsig(char* const arg) {\n\t// TODO: Implement this function\n}",
        "int add_expect_status(char* arg) {\n\t// TODO: Implement this function\n}",
        "int parse_args(const int argc, char* const argv[], char* (**child_args_ptr_ptr)[], int* const parse_fail_exitcode_ptr) {\n\t// TODO: Implement this function\n}",
        "int parse_env(void) {\n\t// TODO: Implement this function\n}",
        "int register_subreaper (void) {\n\t// TODO: Implement this function\n}",
        "void reaper_check (void) {\n\t// TODO: Implement this function\n}",
        "int configure_signals(sigset_t* const parent_sigset_ptr, const signal_configuration_t* const sigconf_ptr) {\n\t// TODO: Implement this function\n}",
        "int wait_and_forward_signal(sigset_t const* const parent_sigset_ptr, pid_t const child_pid) {\n\t// TODO: Implement this function\n}",
        "int reap_zombies(const pid_t child_pid, int* const child_exitcode_ptr) {\n\t// TODO: Implement this function\n}",
        "int main(int argc, char *argv[]) {\n\t// TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs
