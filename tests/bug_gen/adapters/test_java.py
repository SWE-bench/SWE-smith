import pytest
import re
import warnings

from swesmith.bug_gen.adapters.java import (
    get_entities_from_file_java,
)


@pytest.fixture
def entities(test_file_java):
    entities = []
    get_entities_from_file_java(entities, test_file_java)
    return entities


def test_get_entities_from_file_java_max(test_file_java):
    entities = []
    get_entities_from_file_java(entities, test_file_java, 3)
    assert len(entities) == 3


def test_get_entities_from_file_java_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_java([], "non-existent-file")


def test_get_entities_from_file_java_count(entities):
    assert len(entities) == 9


def test_get_entities_from_file_java_no_methods(tmp_path):
    no_methods_file = tmp_path / "NoMethods.java"
    no_methods_file.write_text("// there are no methods here")
    entities = []
    get_entities_from_file_java(entities, no_methods_file)
    assert len(entities) == 0


def test_get_entities_from_file_java_ignore_abstract_methods(tmp_path):
    abstract_method_file = tmp_path / "HasAbstractMethod.java"
    abstract_method_file.write_text("protected abstract String getName();")
    entities = []
    get_entities_from_file_java(entities, abstract_method_file)
    assert len(entities) == 0


def test_get_entities_from_file_java_ignore_interface_methods(tmp_path):
    interface_file = tmp_path / "HasInterface.java"
    interface_file.write_text("public interface Nameable { String getName(); }")
    entities = []
    get_entities_from_file_java(entities, interface_file)
    assert len(entities) == 0


def test_get_entities_from_file_java_malformed(tmp_path):
    malformed_file = tmp_path / "Malformed.java"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_java(entities, malformed_file)
        assert any(
            [
                re.search(r"Error encountered parsing .*Malformed.java", str(w.message))
                for w in ws
            ]
        )


def test_get_entities_from_file_java_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "getMocksToBeVerifiedInOrder",
        "InOrderImpl",
        "verify",
        "verify",
        "verify",
        "objectIsMockToBeVerified",
        "isVerified",
        "markVerified",
        "verifyNoMoreInteractions",
    ]
    assert names == expected_names


def test_get_entities_from_file_java_line_ranges(entities):
    actual_ranges = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (38, 40),
        (42, 44),
        (46, 49),
        (51, 72),
        (74, 90),
        (97, 104),
        (106, 109),
        (111, 114),
        (116, 119),
    ]
    assert actual_ranges == expected_ranges


def test_get_entities_from_file_java_extensions(entities):
    assert all([e.ext == "java" for e in entities]), (
        "All entities should have the extension 'java'"
    )


def test_get_entities_from_file_java_file_paths(entities, test_file_java):
    assert all([e.file_path == test_file_java for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_java_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "public List<Object> getMocksToBeVerifiedInOrder()",
        "public InOrderImpl(List<?> mocksToBeVerifiedInOrder)",
        "@Override public <T> T verify(T mock)",
        "@Override public <T> T verify(T mock, VerificationMode mode)",
        "@Override public void verify(MockedStatic<?> mockedStatic, MockedStatic.Verification verification, VerificationMode mode)",
        "private boolean objectIsMockToBeVerified(Object mock)",
        "@Override public boolean isVerified(Invocation i)",
        "@Override public void markVerified(Invocation i)",
        "@Override public void verifyNoMoreInteractions()",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_java_signature_param_annotation(tmp_path):
    annotated_param_file = tmp_path / "AnnotatedParameter.java"
    annotated_param_file.write_text(
        """
@ClassAnnotation
public class SomeClass {
  @MethodAnnotation
  public void someMethod(@ParamAnnotation String param) {
  }
}
    """.strip()
    )
    entities = []
    get_entities_from_file_java(entities, annotated_param_file)
    assert len(entities) == 1
    assert (
        entities[0].signature
        == "@MethodAnnotation public void someMethod(@ParamAnnotation String param)"
    )


def test_get_entities_from_file_java_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "public List<Object> getMocksToBeVerifiedInOrder() {\n\t// TODO: Implement this function\n}",
        "public InOrderImpl(List<?> mocksToBeVerifiedInOrder) {\n\t// TODO: Implement this function\n}",
        "@Override public <T> T verify(T mock) {\n\t// TODO: Implement this function\n}",
        "@Override public <T> T verify(T mock, VerificationMode mode) {\n\t// TODO: Implement this function\n}",
        "@Override public void verify(MockedStatic<?> mockedStatic, MockedStatic.Verification verification, VerificationMode mode) {\n\t// TODO: Implement this function\n}",
        "private boolean objectIsMockToBeVerified(Object mock) {\n\t// TODO: Implement this function\n}",
        "@Override public boolean isVerified(Invocation i) {\n\t// TODO: Implement this function\n}",
        "@Override public void markVerified(Invocation i) {\n\t// TODO: Implement this function\n}",
        "@Override public void verifyNoMoreInteractions() {\n\t// TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs
