import pytest

from swesmith.bug_gen.adapters.java import (
    get_entities_from_file_java,
)


@pytest.fixture
def entities(test_file_java):
    entities = []
    get_entities_from_file_java(entities, test_file_java)
    return entities


def test_get_entities_from_file_java_count(entities):
    assert len(entities) == 9


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
        "public <T> T verify(T mock)",
        "public <T> T verify(T mock, VerificationMode mode)",
        "public void verify( MockedStatic<?> mockedStatic, MockedStatic.Verification verification, VerificationMode mode)",
        "private boolean objectIsMockToBeVerified(Object mock)",
        "public boolean isVerified(Invocation i)",
        "public void markVerified(Invocation i)",
        "public void verifyNoMoreInteractions()",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_java_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "public List<Object> getMocksToBeVerifiedInOrder() {\n\t// TODO: Implement this function\n}",
        "public InOrderImpl(List<?> mocksToBeVerifiedInOrder) {\n\t// TODO: Implement this function\n}",
        "public <T> T verify(T mock) {\n\t// TODO: Implement this function\n}",
        "public <T> T verify(T mock, VerificationMode mode) {\n\t// TODO: Implement this function\n}",
        "public void verify( MockedStatic<?> mockedStatic, MockedStatic.Verification verification, VerificationMode mode) {\n\t// TODO: Implement this function\n}",
        "private boolean objectIsMockToBeVerified(Object mock) {\n\t// TODO: Implement this function\n}",
        "public boolean isVerified(Invocation i) {\n\t// TODO: Implement this function\n}",
        "public void markVerified(Invocation i) {\n\t// TODO: Implement this function\n}",
        "public void verifyNoMoreInteractions() {\n\t// TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs
