//! The command: `textstat --version`, `textstat greet <name>`, `textstat count <file> [--json]`.
use std::{path::Path, process::ExitCode};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>()
        .as_slice()
    {
        ["--version"] => {
            println!("{}", textstat::version());
            ExitCode::SUCCESS
        }
        ["greet", name] => match textstat::greet(name) {
            Some(text) => {
                println!("{text}");
                ExitCode::SUCCESS
            }
            None => {
                eprintln!("error: greet needs a name");
                ExitCode::from(2)
            }
        },
        args @ (["count", file] | ["count", file, "--json"]) => {
            match textstat::count_file(Path::new(file)) {
                Ok(counts) if args.len() == 3 => {
                    println!("{}", counts.to_json());
                    ExitCode::SUCCESS
                }
                Ok(textstat::Counts {
                    lines,
                    words,
                    chars,
                }) => {
                    println!("lines={lines} words={words} chars={chars}");
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("error: {file}: {error}");
                    ExitCode::from(1)
                }
            }
        }
        _ => {
            eprintln!(
                "usage: textstat --version | textstat greet <name> | textstat count <file> [--json]"
            );
            ExitCode::from(2)
        }
    }
}
