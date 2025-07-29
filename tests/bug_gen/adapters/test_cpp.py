import pytest

from swesmith.bug_gen.adapters.cpp import (
    get_entities_from_file_cpp,
)


@pytest.fixture
def entities(test_file_cpp):
    entities = []
    get_entities_from_file_cpp(entities, test_file_cpp)
    return entities


def test_get_entities_from_file_cpp_max(test_file_cpp):
    entities = []
    get_entities_from_file_cpp(entities, test_file_cpp, 3)
    assert len(entities) == 3


def test_get_entities_from_file_cpp_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_cpp([], "non-existent-file")


def test_get_entities_from_file_cpp_count(entities):
    assert len(entities) == 13


def test_get_entities_from_file_cpp_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "parseCookies",
        "parseHeader",
        "split",
        "readUserFunction",
        "headerUserFunction",
        "writeFunction",
        "writeFileFunction",
        "writeUserFunction",
        "debugUserFunction",
        "urlEncode",
        "urlDecode",
        "isTrue",
        "sTimestampToT",
    ]
    assert names == expected_names


def test_get_entities_from_file_cpp_line_ranges(entities):
    actual_ranges = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (51, 71),
        (73, 114),
        (116, 126),
        (128, 131),
        (133, 136),
        (138, 142),
        (144, 148),
        (150, 153),
        (155, 158),
        (170, 173),
        (185, 188),
        (190, 194),
        (196, 213),
    ]
    assert actual_ranges == expected_ranges


def test_get_entities_from_file_cpp_extensions(entities):
    assert all([e.ext == "cpp" for e in entities]), (
        "All entities should have the extension 'cpp'"
    )


def test_get_entities_from_file_cpp_file_paths(entities, test_file_cpp):
    assert all([e.file_path == test_file_cpp for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_cpp_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "Cookies parseCookies(curl_slist* raw_cookies)",
        "Header parseHeader(const std::string& headers, std::string* status_line, std::string* reason)",
        "std::vector<std::string> split(const std::string& to_split, char delimiter)",
        "size_t readUserFunction(char* ptr, size_t size, size_t nitems, const ReadCallback* read)",
        "size_t headerUserFunction(char* ptr, size_t size, size_t nmemb, const HeaderCallback* header)",
        "size_t writeFunction(char* ptr, size_t size, size_t nmemb, std::string* data)",
        "size_t writeFileFunction(char* ptr, size_t size, size_t nmemb, std::ofstream* file)",
        "size_t writeUserFunction(char* ptr, size_t size, size_t nmemb, const WriteCallback* write)",
        "int debugUserFunction(CURL* /*handle*/, curl_infotype type, char* data, size_t size, const DebugCallback* debug)",
        "util::SecureString urlEncode(std::string_view s)",
        "util::SecureString urlDecode(std::string_view s)",
        "bool isTrue(const std::string& s)",
        "time_t sTimestampToT(const std::string& st)",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_cpp_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "Cookies parseCookies(curl_slist* raw_cookies) {\n\t// TODO: Implement this function\n}",
        "Header parseHeader(const std::string& headers, std::string* status_line, std::string* reason) {\n\t// TODO: Implement this function\n}",
        "std::vector<std::string> split(const std::string& to_split, char delimiter) {\n\t// TODO: Implement this function\n}",
        "size_t readUserFunction(char* ptr, size_t size, size_t nitems, const ReadCallback* read) {\n\t// TODO: Implement this function\n}",
        "size_t headerUserFunction(char* ptr, size_t size, size_t nmemb, const HeaderCallback* header) {\n\t// TODO: Implement this function\n}",
        "size_t writeFunction(char* ptr, size_t size, size_t nmemb, std::string* data) {\n\t// TODO: Implement this function\n}",
        "size_t writeFileFunction(char* ptr, size_t size, size_t nmemb, std::ofstream* file) {\n\t// TODO: Implement this function\n}",
        "size_t writeUserFunction(char* ptr, size_t size, size_t nmemb, const WriteCallback* write) {\n\t// TODO: Implement this function\n}",
        "int debugUserFunction(CURL* /*handle*/, curl_infotype type, char* data, size_t size, const DebugCallback* debug) {\n\t// TODO: Implement this function\n}",
        "util::SecureString urlEncode(std::string_view s) {\n\t// TODO: Implement this function\n}",
        "util::SecureString urlDecode(std::string_view s) {\n\t// TODO: Implement this function\n}",
        "bool isTrue(const std::string& s) {\n\t// TODO: Implement this function\n}",
        "time_t sTimestampToT(const std::string& st) {\n\t// TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs


def test_get_entities_from_file_cpp_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.cpp"
    no_functions_file.write_text("// there are no functions here")
    entities = []
    get_entities_from_file_cpp(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_cpp_constructor(tmp_path):
    constructor_file = tmp_path / "constructor.cpp"
    constructor_file.write_text("class SomeClass {\npublic:\n  SomeClass() {}\n};\n")
    entities = []
    get_entities_from_file_cpp(entities, constructor_file)
    assert len(entities) == 1
    assert entities[0].name == "SomeClass"
    assert entities[0].signature == "SomeClass()"
    assert entities[0].stub == "SomeClass() {\n\t// TODO: Implement this function\n}"


def test_get_entities_from_file_cpp_destructor(tmp_path):
    destructor_file = tmp_path / "destructor.cpp"
    destructor_file.write_text("""
        class SomeClass {
        public:
          SomeClass() {}
          ~SomeClass() {}
        };
    """)
    entities = []
    get_entities_from_file_cpp(entities, destructor_file)
    assert len(entities) == 2
    assert entities[0].name == "SomeClass"
    assert entities[0].signature == "SomeClass()"
    assert entities[0].stub == "SomeClass() {\n\t// TODO: Implement this function\n}"
    assert entities[1].name == "SomeClass Destructor"
    assert entities[1].signature == "~SomeClass()"
    assert entities[1].stub == "~SomeClass() {\n\t// TODO: Implement this function\n}"


def test_get_entities_from_file_cpp_suffix_return(tmp_path):
    suffix_file = tmp_path / "suffix_return.cpp"
    suffix_file.write_text(
        "parseCookies(curl_slist *raw_cookies)->Cookies {\n  // some implementation\n}"
    )
    entities = []
    get_entities_from_file_cpp(entities, suffix_file)
    assert len(entities) == 1
    assert entities[0].name == "parseCookies"
    assert entities[0].signature == "parseCookies(curl_slist *raw_cookies)->Cookies"
    assert (
        entities[0].stub
        == "parseCookies(curl_slist *raw_cookies)->Cookies {\n\t// TODO: Implement this function\n}"
    )


def test_get_entities_from_file_cpp_overloading(tmp_path):
    overloading_file = tmp_path / "overloading.cpp"
    overloading_file.write_text("""
        void someOverloadedMethod(int) {}
        void someOverloadedMethod(double) {}
    """)
    entities = []
    get_entities_from_file_cpp(entities, overloading_file)
    assert len(entities) == 2
    assert entities[0].name == "someOverloadedMethod"
    assert entities[0].signature == "void someOverloadedMethod(int)"
    assert entities[1].name == "someOverloadedMethod"
    assert entities[1].signature == "void someOverloadedMethod(double)"


def test_get_entities_from_file_cpp_ignore_abstract_methods(tmp_path):
    abstract_method_file = tmp_path / "abstract_method.cpp"
    abstract_method_file.write_text("""
        class SomeAbstractClass {
        public:
          virtual void abstractMethod() = 0;
        };
    """)
    entities = []
    get_entities_from_file_cpp(entities, abstract_method_file)
    assert len(entities) == 0


def test_get_entities_from_file_cpp_multiline_signature(tmp_path):
    multiline_sig_file = tmp_path / "multiline_signature.cpp"
    multiline_sig_file.write_text("""
        void someMethod(
            std::string* arg1,
            std::string* arg2,
            std::string* arg3
            )
        {
        }
    """)
    entities = []
    get_entities_from_file_cpp(entities, multiline_sig_file)
    assert len(entities) == 1
    assert (
        entities[0].signature
        == "void someMethod(std::string* arg1, std::string* arg2, std::string* arg3)"
    )
