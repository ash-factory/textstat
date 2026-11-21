//! The transcripts' replay (project kinds design 1.6): CI's `evidence-replay` job copies this file into `tests/` of
//! its own checkout, adds trycmd as a development dependency there, and runs it. It lives under `.github/`, which the
//! guard keeps builders out of, so a builder's change of `tests/` or `Cargo.toml` cannot empty or skip it.
//! EVIDENCE_GLOB names the transcripts of the pull request's own card (the job sets it); each `$ ` line runs the
//! crate's own command (trycmd finds the crate's binaries), and any difference in output or exit code fails.

#[test]
fn the_cards_transcripts_replay() {
    let glob = std::env::var("EVIDENCE_GLOB").expect("EVIDENCE_GLOB names the card's transcripts");
    trycmd::TestCases::new().case(glob);
}
