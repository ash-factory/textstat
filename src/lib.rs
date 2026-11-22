//! textstat: textstat: a factory project
//!
//! The library holds the behaviour; `src/main.rs` reads the arguments, calls it and prints.

use std::{fs, io, path::Path};

/// The name and the commit of this build, as `--version` prints them: `<name> <commit>`.
pub fn version() -> String {
    format!("{} {}", env!("CARGO_PKG_NAME"), env!("APP_COMMIT"))
}

/// A greeting for `name`; `None` for a name that is empty or only spaces.
pub fn greet(name: &str) -> Option<String> {
    let name = name.trim();
    (!name.is_empty()).then(|| format!("Hello, {name}!"))
}

#[derive(Debug, PartialEq, Eq)]
pub struct Counts {
    pub lines: usize,
    pub words: usize,
    pub chars: usize,
}

impl Counts {
    /// Format the counts as a JSON object with integer values.
    pub fn to_json(&self) -> String {
        let Self {
            lines,
            words,
            chars,
        } = self;
        format!(r#"{{"lines":{lines},"words":{words},"chars":{chars}}}"#)
    }
}

/// Count lines, whitespace-separated words, and Unicode scalar values in a UTF-8 file.
pub fn count_file(path: &Path) -> io::Result<Counts> {
    fs::read_to_string(path).map(|text| count(&text))
}

fn count(text: &str) -> Counts {
    Counts {
        lines: text.lines().count(),
        words: text.split_whitespace().count(),
        chars: text.chars().count(),
    }
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

    #[test]
    fn counts_text_with_unicode_and_whitespace() {
        for (text, lines, words, chars) in [
            ("héllo wörld\n", 1, 2, 12),
            ("a\t b\n\nc\n", 3, 3, 8),
            ("", 0, 0, 0),
            ("a\r\nb\u{2003}c", 2, 3, 6),
        ] {
            assert_eq!(
                count(text),
                Counts {
                    lines,
                    words,
                    chars,
                },
                "input: {text:?}"
            );
        }
    }
}
