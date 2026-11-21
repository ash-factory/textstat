//! textstat: textstat: a factory project
//!
//! The library holds the behaviour; `src/main.rs` reads the arguments, calls it and prints.

/// The name and the commit of this build, as `--version` prints them: `<name> <commit>`.
pub fn version() -> String {
    format!("{} {}", env!("CARGO_PKG_NAME"), env!("APP_COMMIT"))
}

/// A greeting for `name`; `None` for a name that is empty or only spaces.
pub fn greet(name: &str) -> Option<String> {
    let name = name.trim();
    (!name.is_empty()).then(|| format!("Hello, {name}!"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_name_is_greeted_and_an_empty_one_is_not() {
        assert_eq!(greet(" Ada ").as_deref(), Some("Hello, Ada!"));
        assert_eq!(greet("  "), None);
    }

    #[test]
    fn the_version_starts_with_the_name() {
        assert!(version().starts_with(concat!(env!("CARGO_PKG_NAME"), " ")));
    }
}
