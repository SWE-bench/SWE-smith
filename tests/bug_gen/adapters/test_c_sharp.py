import pytest
import re
import warnings

from swesmith.bug_gen.adapters.c_sharp import (
    get_entities_from_file_c_sharp,
)


@pytest.fixture
def entities(test_file_c_sharp):
    entities = []
    get_entities_from_file_c_sharp(entities, test_file_c_sharp)
    return entities


def test_get_entities_from_file_c_sharp_max(test_file_c_sharp):
    entities = []
    get_entities_from_file_c_sharp(entities, test_file_c_sharp, 3)
    assert len(entities) == 3


def test_get_entities_from_file_c_sharp_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_c_sharp([], "non-existent-file")


def test_get_entities_from_file_c_sharp_count(entities):
    assert len(entities) == 14


def test_get_entities_from_file_c_sharp_no_methods(tmp_path):
    no_methods_file = tmp_path / "NoMethods.cs"
    no_methods_file.write_text("// there are no methods here")
    entities = []
    get_entities_from_file_c_sharp(entities, no_methods_file)
    assert len(entities) == 0


def test_get_entities_from_file_c_sharp_ignore_abstract_methods(tmp_path):
    abstract_method_file = tmp_path / "HasAbstractMethod.cs"
    abstract_method_file.write_text(
        "abstract class SomeClass { public abstract void SomeMethod(); }"
    )
    entities = []
    get_entities_from_file_c_sharp(entities, abstract_method_file)
    assert len(entities) == 0


def test_get_entities_from_file_c_sharp_ignore_interface_methods(tmp_path):
    interface_file = tmp_path / "HasInterface.cs"
    interface_file.write_text("public interface ISomeInterface { void SomeMethod(); }")
    entities = []
    get_entities_from_file_c_sharp(entities, interface_file)
    assert len(entities) == 0


def test_get_entities_from_file_c_sharp_finalizer(tmp_path):
    finalizer_file = tmp_path / "HasFinalizer.cs"
    finalizer_file.write_text("class SomeClass { ~SomeClass() {} }")
    entities = []
    get_entities_from_file_c_sharp(entities, finalizer_file)
    assert len(entities) == 1
    assert entities[0].name == "SomeClass Finalizer"
    assert entities[0].signature == "~SomeClass()"


def test_get_entities_from_file_c_sharp_malformed(tmp_path):
    malformed_file = tmp_path / "Malformed.cs"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_c_sharp(entities, malformed_file)
        assert any(
            [
                re.search(r"Error encountered parsing .*Malformed.cs", str(w.message))
                for w in ws
            ]
        )


def test_get_entities_from_file_c_sharp_utf_8(tmp_path):
    utf_8_file = tmp_path / "Utf8.cs"
    utf_8_file.write_text(
        "public class Utf8 { public void SomeMethod() { /* ☺︎ */} }", encoding="utf-8"
    )
    entities = []
    get_entities_from_file_c_sharp(entities, utf_8_file)
    assert len(entities) == 1
    assert entities[0].name == "SomeMethod"


def test_get_entities_from_file_c_sharp_utf_8_bom(tmp_path):
    utf_8_file = tmp_path / "Utf8.cs"
    utf_8_file.write_text(
        "public class Utf8 { public void SomeMethod() {} }", encoding="utf-8-sig"
    )
    entities = []
    get_entities_from_file_c_sharp(entities, utf_8_file)
    assert len(entities) == 1
    assert entities[0].name == "SomeMethod"


def test_get_entities_from_file_c_sharp_utf_16_ignored(tmp_path):
    utf_16_file = tmp_path / "Utf16.cs"
    utf_16_file.write_text(
        "public class Utf16 { public void SomeMethod() {} }", encoding="utf-16"
    )
    entities = []

    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_c_sharp(entities, utf_16_file)

    assert len(entities) == 0
    assert any(
        [
            re.search(
                r"Ignoring file .*Utf16.cs as it has an unsupported encoding",
                str(w.message),
            )
            for w in ws
        ]
    )


def test_get_entities_from_file_c_sharp_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "ReadTraceNexusImporter",
        "FindReadTraceExe",
        "ExtractReadTraceReports",
        "LogMessage",
        "GetApproximateTotalRowsInserted",
        "GetLocalServerTimeOffset",
        "SkipFile",
        "FindFirstTraceFile",
        "FileFirstXelFile",
        "Cancel",
        "DoImport",
        "Initialize",
        "OnStatusChanged",
        "OnProgressChanged",
    ]
    assert names == expected_names


def test_get_entities_from_file_c_sharp_line_ranges(entities):
    actual_ranges = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (73, 93),
        (99, 149),
        (154, 266),
        (269, 275),
        (282, 302),
        (304, 328),
        (333, 341),
        (346, 379),
        (380, 401),
        (408, 425),
        (437, 540),
        (562, 583),
        (639, 643),
        (680, 684),
    ]
    assert actual_ranges == expected_ranges


def test_get_entities_from_file_c_sharp_extensions(entities):
    assert all([e.ext == "cs" for e in entities]), (
        "All entities should have the extension 'cs'"
    )


def test_get_entities_from_file_c_sharp_file_paths(entities, test_file_c_sharp):
    assert all([e.file_path == test_file_c_sharp for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_c_sharp_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "public ReadTraceNexusImporter()",
        "private bool FindReadTraceExe()",
        "public bool ExtractReadTraceReports()",
        "void LogMessage(string msg)",
        "private long GetApproximateTotalRowsInserted()",
        "private decimal GetLocalServerTimeOffset()",
        "private bool SkipFile(string FullFileName)",
        "private string FindFirstTraceFile(string[] files)",
        "private string FileFirstXelFile(string[] files)",
        "public void Cancel()",
        "public bool DoImport()",
        "public void Initialize(string Filemask, string connString, string Server, bool UseWindowsAuth, string SQLLogin, string SQLPassword, string DatabaseName, ILogger Logger)",
        "public void OnStatusChanged(EventArgs e)",
        "public void OnProgressChanged(EventArgs e)",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_c_sharp_multiline_signature(tmp_path):
    multiline_sig_file = tmp_path / "MultilineSignature.cs"
    multiline_sig_file.write_text(
        """
        public class MultilineSignature
        {
            void SomeMethod(
                            string arg1,
                            string arg2,
                            string arg3
                           )
            { }
        }
        """
    )
    entities = []
    get_entities_from_file_c_sharp(entities, multiline_sig_file)
    assert len(entities) == 1
    assert (
        entities[0].signature
        == "void SomeMethod(string arg1, string arg2, string arg3)"
    )


def test_get_entities_from_file_c_sharp_signature_attributes(tmp_path):
    attribute_file = tmp_path / "Attributes.cs"
    attribute_file.write_text(
        """
        public class WithAttributes
        {
            [Conditional("CONDITION1"), Conditional("CONDITION2")]
            void MethodWithAttributes([Some][Attribute] string a) {}
        }
        """
    )
    entities = []
    get_entities_from_file_c_sharp(entities, attribute_file)
    assert len(entities) == 1
    assert (
        entities[0].signature
        == '[Conditional("CONDITION1"), Conditional("CONDITION2")] void MethodWithAttributes([Some][Attribute] string a)'
    )


def test_get_entities_from_file_c_sharp_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "public ReadTraceNexusImporter()\n{\n\t// TODO: Implement this function\n}",
        "private bool FindReadTraceExe()\n{\n\t// TODO: Implement this function\n}",
        "public bool ExtractReadTraceReports()\n{\n\t// TODO: Implement this function\n}",
        "void LogMessage(string msg)\n{\n\t// TODO: Implement this function\n}",
        "private long GetApproximateTotalRowsInserted()\n{\n\t// TODO: Implement this function\n}",
        "private decimal GetLocalServerTimeOffset()\n{\n\t// TODO: Implement this function\n}",
        "private bool SkipFile(string FullFileName)\n{\n\t// TODO: Implement this function\n}",
        "private string FindFirstTraceFile(string[] files)\n{\n\t// TODO: Implement this function\n}",
        "private string FileFirstXelFile(string[] files)\n{\n\t// TODO: Implement this function\n}",
        "public void Cancel()\n{\n\t// TODO: Implement this function\n}",
        "public bool DoImport()\n{\n\t// TODO: Implement this function\n}",
        "public void Initialize(string Filemask, string connString, string Server, bool UseWindowsAuth, string SQLLogin, string SQLPassword, string DatabaseName, ILogger Logger)\n{\n\t// TODO: Implement this function\n}",
        "public void OnStatusChanged(EventArgs e)\n{\n\t// TODO: Implement this function\n}",
        "public void OnProgressChanged(EventArgs e)\n{\n\t// TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs
