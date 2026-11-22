use std::{path::Path, process::Command};

#[test]
fn count_prints_the_same_unicode_counts_in_json_and_plain_text() {
    let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/sample.txt");
    let mut count = Command::new(env!("CARGO_BIN_EXE_textstat"));
    count.arg("count").arg(fixture);

    let plain = count.output().expect("textstat count runs");
    assert_eq!(plain.status.code(), Some(0));
    assert_eq!(plain.stdout, b"lines=1 words=2 chars=12\n");
    assert!(plain.stderr.is_empty());

    let json = count
        .arg("--json")
        .output()
        .expect("textstat count --json runs");
    assert_eq!(json.status.code(), Some(0));
    assert!(json.stderr.is_empty());
    let counts: serde_json::Value =
        serde_json::from_slice(&json.stdout).expect("stdout contains one JSON value");
    assert_eq!(
        counts,
        serde_json::json!({"lines": 1, "words": 2, "chars": 12})
    );
}
