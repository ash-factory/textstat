//! The command: `textstat --version`, `textstat greet <name>`.
use std::process::ExitCode;

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
        _ => {
            eprintln!("usage: textstat --version | textstat greet <name>");
            ExitCode::from(2)
        }
    }
}
