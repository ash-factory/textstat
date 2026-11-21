//! The planner's acceptance tests (`tests/acceptance/`: Cargo builds `tests/<folder>/main.rs` as one test target).
//! Builders make them pass; they never change, skip or delete them.
use std::process::Command;

fn command() -> Command {
    Command::new(env!("CARGO_BIN_EXE_textstat"))
}

#[test]
fn the_version_names_the_command() {
    let out = command()
        .arg("--version")
        .output()
        .expect("the command runs");
    assert!(out.status.success());
    assert!(String::from_utf8_lossy(&out.stdout).starts_with("textstat "));
}

#[test]
fn greet_without_a_name_is_an_error_on_stderr_with_exit_code_2() {
    let out = command()
        .args(["greet", " "])
        .output()
        .expect("the command runs");
    assert_eq!(out.status.code(), Some(2));
    assert!(out.stdout.is_empty());
    assert!(String::from_utf8_lossy(&out.stderr).contains("greet needs a name"));
}
