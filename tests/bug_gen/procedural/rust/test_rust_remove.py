import pytest
from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo() -> i32 {
    for i in 0..3 {
        println!("{}", i);
    }
    return 1;
}""",
            """fn foo() -> i32 {
    
    return 1;
}""",
        ),
        (
            """fn bar() -> i32 {
    while true {
        break;
    }
    return 2;
}""",
            """fn bar() -> i32 {
    
    return 2;
}""",
        ),
        (
            """fn baz() -> i32 {
    let mut sum = 0;
    for i in 0..10 {
        sum += i;
    }
    sum
}""",
            """fn baz() -> i32 {
    let mut sum = 0;
    
    sum
}""",
        ),
    ],
)
def test_remove_loop_modifier(tmp_path, src, expected):
    """Test that RemoveLoopModifier removes loop statements."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return x;
    }
    return 0;
}""",
            """fn foo(x: i32) -> i32 {
    
    return 0;
}""",
        ),
        (
            """fn bar(x: i32) -> i32 {
    if x < 0 {
        return -1;
    } else {
        return 1;
    }
}""",
            """fn bar(x: i32) -> i32 {
    
}""",
        ),
        (
            """fn baz(x: i32) -> i32 {
    let mut result = 0;
    if x > 10 {
        result = x * 2;
    }
    result
}""",
            """fn baz(x: i32) -> i32 {
    let mut result = 0;
    
    result
}""",
        ),
    ],
)
def test_remove_conditional_modifier(tmp_path, src, expected):
    """Test that RemoveConditionalModifier removes conditional statements."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo() -> i32 {
    let x = 1;
    return x;
}""",
            """fn foo() -> i32 {
    
    return x;
}""",
        ),
        (
            """fn bar() -> i32 {
    let mut y = 2;
    y += 3;
    return y;
}""",
            """fn bar() -> i32 {
    
    y += 3;
    return y;
}""",
        ),
        (
            """fn baz() -> i32 {
    let z: i32 = 10;
    z * 2
}""",
            """fn baz() -> i32 {
    
    z * 2
}""",
        ),
        (
            """fn qux() -> i32 {
    let mut a = 5;
    a *= 2;
    a
}""",
            """fn qux() -> i32 {
    
    a *= 2;
    a
}""",
        ),
    ],
)
def test_remove_assign_modifier(tmp_path, src, expected):
    """Test that RemoveAssignModifier removes assignment statements."""
    test_file = tmp_path / "test.rs"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_rs(entities, str(test_file))
    assert len(entities) == 1

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite.strip() == expected.strip(), (
        f"Expected {expected}, got {result.rewrite}"
    )
