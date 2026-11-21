//! The commit this build is of, for `--version` (`<name> <commit>`): APP_COMMIT when set (scripts/verify/start and
//! CI set it), else the clone's HEAD, else "unknown".
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-env-changed=APP_COMMIT");
    println!("cargo:rerun-if-changed=.git/HEAD");
    let commit = std::env::var("APP_COMMIT")
        .ok()
        .filter(|c| !c.is_empty())
        .unwrap_or_else(|| {
            Command::new("git")
                .args(["rev-parse", "HEAD"])
                .output()
                .ok()
                .filter(|out| out.status.success())
                .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_string())
                .filter(|c| !c.is_empty())
                .unwrap_or_else(|| "unknown".to_string())
        });
    println!("cargo:rustc-env=APP_COMMIT={commit}");
}
