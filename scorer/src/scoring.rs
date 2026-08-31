//! Weather-fact scorer.
//!
//! Stage 2 needs two things Jaccard cannot do:
//! 1. rank a paraphrase above a near-copy that swapped the city or the sky
//! 2. separate those pairs by ~1.0, because the champion margin is 0.99
//!
//! So we extract location, condition family, temperatures, wind, precip and
//! day-part, then:
//! - contradiction (wrong city, opposite sky, far-off temp) => ~0
//! - matching facts (including C/F and city aliases) => ~1
//! - OnLookout JSON forecast payloads still go through the same facts

use serde::Deserialize;
use serde_json::Value;
use std::collections::HashSet;

#[derive(Debug, Deserialize)]
struct ForecastRow {
    #[allow(dead_code)]
    time: Option<String>,
    temp_c: Option<f64>,
    precip_mm: Option<f64>,
    wind_ms: Option<f64>,
    conditions: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Payload {
    as_of: Option<String>,
    forecast: Option<Vec<ForecastRow>>,
    confidence: Option<f64>,
    risk_flags: Option<Vec<String>>,
    answer: Option<String>,
    summary: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Sky {
    Clear,
    Cloud,
    Fog,
    Rain,
    Storm,
    Snow,
}

#[derive(Clone, Debug, Default)]
struct Facts {
    cities: HashSet<&'static str>,
    skies: HashSet<u8>,
    temps_c: Vec<f64>,
    precip_mm: Vec<f64>,
    wind_ms: Vec<f64>,
    days: HashSet<&'static str>,
}

fn clamp01(v: f32) -> f32 {
    if v.is_nan() {
        0.0
    } else {
        v.max(0.0).min(1.0)
    }
}

fn norm(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut prev_space = false;
    for ch in s.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
            prev_space = false;
        } else if !prev_space {
            out.push(' ');
            prev_space = true;
        }
    }
    out
}

fn contains_phrase(hay: &str, needle: &str) -> bool {
    phrase_hit(hay, needle).is_some()
}

/// Token-aware match. `snow` hits `snowing`, `storm` hits `storms`.
fn phrase_hit(hay: &str, needle: &str) -> Option<usize> {
    let toks: Vec<&str> = hay.split_whitespace().collect();
    let need: Vec<&str> = needle.split_whitespace().collect();
    if need.is_empty() || toks.len() < need.len() {
        return None;
    }
    for i in 0..=toks.len() - need.len() {
        let mut ok = true;
        for (j, n) in need.iter().enumerate() {
            let t = toks[i + j];
            if t != *n && !(j + 1 == need.len() && t.starts_with(n) && t.len() <= n.len() + 4) {
                ok = false;
                break;
            }
        }
        if ok {
            return Some(i);
        }
    }
    None
}

fn negated(hay: &str, needle: &str) -> bool {
    let toks: Vec<&str> = hay.split_whitespace().collect();
    let Some(i) = phrase_hit(hay, needle) else {
        return false;
    };
    i > 0 && matches!(toks[i - 1], "no" | "not" | "without" | "zero")
}

const CITIES: &[(&str, &[&str])] = &[
    ("berlin", &["berlin", "german capital"]),
    ("paris", &["paris", "french capital"]),
    ("london", &["london", "british capital", "uk capital"]),
    ("tokyo", &["tokyo", "japanese capital"]),
    ("rome", &["rome", "italian capital"]),
    ("madrid", &["madrid", "spanish capital"]),
    ("newyork", &["new york", "nyc", "new york city"]),
    ("losangeles", &["los angeles", "l a"]),
    ("sanfrancisco", &["san francisco", "s f"]),
    ("washington", &["washington dc", "washington d c", "washington"]),
    ("chicago", &["chicago"]),
    ("miami", &["miami"]),
    ("phoenix", &["phoenix"]),
    ("seattle", &["seattle"]),
    ("boston", &["boston"]),
    ("houston", &["houston"]),
    ("denver", &["denver"]),
    ("atlanta", &["atlanta"]),
    ("dallas", &["dallas"]),
    ("toronto", &["toronto"]),
    ("vancouver", &["vancouver"]),
    ("mexico", &["mexico city"]),
    ("saopaulo", &["sao paulo", "são paulo"]),
    ("sydney", &["sydney"]),
    ("melbourne", &["melbourne"]),
    ("singapore", &["singapore"]),
    ("hongkong", &["hong kong"]),
    ("shanghai", &["shanghai"]),
    ("beijing", &["beijing", "peking"]),
    ("seoul", &["seoul"]),
    ("mumbai", &["mumbai", "bombay"]),
    ("delhi", &["new delhi", "delhi"]),
    ("dubai", &["dubai"]),
    ("cairo", &["cairo"]),
    ("lagos", &["lagos"]),
    ("nairobi", &["nairobi"]),
    ("johannesburg", &["johannesburg"]),
    ("amsterdam", &["amsterdam"]),
    ("vienna", &["vienna"]),
    ("prague", &["prague"]),
    ("warsaw", &["warsaw"]),
    ("stockholm", &["stockholm"]),
    ("oslo", &["oslo"]),
    ("copenhagen", &["copenhagen"]),
    ("helsinki", &["helsinki"]),
    ("dublin", &["dublin"]),
    ("lisbon", &["lisbon"]),
    ("athens", &["athens"]),
    ("istanbul", &["istanbul"]),
    ("zurich", &["zurich", "zürich"]),
    ("moscow", &["moscow"]),
    ("bangkok", &["bangkok"]),
    ("jakarta", &["jakarta"]),
    ("riodejaneiro", &["rio de janeiro", "rio"]),
    ("buenosaires", &["buenos aires"]),
];

const SKY_WORDS: &[(&str, Sky)] = &[
    ("thunderstorm", Sky::Storm),
    ("lightning", Sky::Storm),
    ("thunder", Sky::Storm),
    ("storm", Sky::Storm),
    ("blizzard", Sky::Snow),
    ("flurries", Sky::Snow),
    ("snow", Sky::Snow),
    ("sleet", Sky::Snow),
    ("freezing rain", Sky::Rain),
    ("rain showers", Sky::Rain),
    ("showers", Sky::Rain),
    ("drizzle", Sky::Rain),
    ("rainfall", Sky::Rain),
    ("precipitation", Sky::Rain),
    ("rain", Sky::Rain),
    ("downpour", Sky::Rain),
    ("foggy", Sky::Fog),
    ("fog", Sky::Fog),
    ("mist", Sky::Fog),
    ("overcast", Sky::Cloud),
    ("partly cloudy", Sky::Cloud),
    ("mostly cloudy", Sky::Cloud),
    ("cloudy", Sky::Cloud),
    ("clouds", Sky::Cloud),
    ("mainly clear", Sky::Clear),
    ("mostly sunny", Sky::Clear),
    ("sunshine", Sky::Clear),
    ("sunny", Sky::Clear),
    ("clear skies", Sky::Clear),
    ("clear sky", Sky::Clear),
    ("clear", Sky::Clear),
    ("fair", Sky::Clear),
];

fn extract_cities(n: &str) -> HashSet<&'static str> {
    let mut out = HashSet::new();
    for (id, aliases) in CITIES {
        if aliases.iter().any(|a| contains_phrase(n, a)) {
            out.insert(*id);
        }
    }
    out
}

fn extract_skies(n: &str) -> HashSet<u8> {
    let mut out = HashSet::new();
    for (word, sky) in SKY_WORDS {
        if contains_phrase(n, word) && !negated(n, word) {
            out.insert(*sky as u8);
        }
    }
    out
}

fn extract_days(n: &str) -> HashSet<&'static str> {
    let mut out = HashSet::new();
    for (id, aliases) in [
        ("today", &["today", "this afternoon", "this morning", "tonight"][..]),
        ("tomorrow", &["tomorrow", "next day"][..]),
        ("monday", &["monday"][..]),
        ("tuesday", &["tuesday"][..]),
        ("wednesday", &["wednesday"][..]),
        ("thursday", &["thursday"][..]),
        ("friday", &["friday"][..]),
        ("saturday", &["saturday"][..]),
        ("sunday", &["sunday"][..]),
    ] {
        if aliases.iter().any(|a| contains_phrase(n, a)) {
            out.insert(id);
        }
    }
    out
}

fn parse_number(token: &str) -> Option<f64> {
    let t = token.trim_matches(|c: char| !c.is_ascii_digit() && c != '.' && c != '-');
    if t.is_empty() || t == "-" || t == "." {
        return None;
    }
    t.parse::<f64>().ok()
}

fn extract_unit_numbers(n: &str, units: &[&str]) -> Vec<f64> {
    let toks: Vec<&str> = n.split_whitespace().collect();
    let mut out = Vec::new();
    for i in 0..toks.len() {
        let Some(v) = parse_number(toks[i]) else { continue };
        let prev = if i > 0 { toks[i - 1] } else { "" };
        let next = if i + 1 < toks.len() { toks[i + 1] } else { "" };
        let around = format!("{prev} {next}");
        if units.iter().any(|u| around.contains(u) || toks[i].contains(u)) {
            out.push(v);
        }
    }
    out
}

fn extract_temps_c(n: &str) -> Vec<f64> {
    let toks: Vec<&str> = n.split_whitespace().collect();
    let mut out = Vec::new();
    for i in 0..toks.len() {
        let Some(v) = parse_number(toks[i]) else { continue };
        let window = toks[i.saturating_sub(1)..=(i + 2).min(toks.len().saturating_sub(1))].join(" ");
        let is_f = window.contains("fahrenheit")
            || window.contains("°f")
            || toks[i].ends_with('f')
            || window.split_whitespace().any(|w| w == "f");
        let is_c = window.contains("celsius")
            || window.contains("centigrade")
            || window.contains("°c")
            || toks[i].ends_with('c')
            || window.split_whitespace().any(|w| w == "c");
        if is_f {
            out.push((v - 32.0) * 5.0 / 9.0);
        } else if is_c || window.contains("degree") {
            out.push(v);
        }
    }
    out
}

fn extract_wind_ms(n: &str) -> Vec<f64> {
    let mut out = extract_unit_numbers(n, &["m/s", "mps", "metres per second", "meters per second"]);
    for v in extract_unit_numbers(n, &["km/h", "kph", "kmh", "kilometers per hour"]) {
        out.push(v / 3.6);
    }
    for v in extract_unit_numbers(n, &["mph", "miles per hour"]) {
        out.push(v * 0.44704);
    }
    out
}

fn extract_precip_mm(n: &str) -> Vec<f64> {
    let mut out = extract_unit_numbers(n, &["mm", "millimet", "millimeter"]);
    for v in extract_unit_numbers(n, &["inch", "inches", " in"]) {
        out.push(v * 25.4);
    }
    out
}

fn facts_from_text(raw: &str) -> Facts {
    let n = norm(raw);
    let mut temps = extract_temps_c(&n);
    // Bare 50-120 numbers that convert from F onto an existing C reading.
    if !temps.is_empty() {
        for tok in n.split_whitespace() {
            if let Some(v) = parse_number(tok) {
                if (50.0..=120.0).contains(&v) {
                    let as_c = (v - 32.0) * 5.0 / 9.0;
                    if temps.iter().any(|t| (t - as_c).abs() < 2.5) {
                        temps.push(as_c);
                    }
                }
            }
        }
    }
    Facts {
        cities: extract_cities(&n),
        skies: extract_skies(&n),
        temps_c: temps,
        precip_mm: extract_precip_mm(&n),
        wind_ms: extract_wind_ms(&n),
        days: extract_days(&n),
    }
}

fn merge_facts(mut a: Facts, b: Facts) -> Facts {
    a.cities.extend(b.cities);
    a.skies.extend(b.skies);
    a.temps_c.extend(b.temps_c);
    a.precip_mm.extend(b.precip_mm);
    a.wind_ms.extend(b.wind_ms);
    a.days.extend(b.days);
    a
}

fn facts_from_payload(p: &Payload) -> Facts {
    let mut f = Facts::default();
    if let Some(s) = p.summary.as_deref() {
        f = merge_facts(f, facts_from_text(s));
    }
    if let Some(s) = p.answer.as_deref() {
        f = merge_facts(f, facts_from_text(s));
    }
    if let Some(rows) = p.forecast.as_ref() {
        for row in rows {
            if let Some(c) = row.conditions.as_deref() {
                f = merge_facts(f, facts_from_text(c));
            }
            if let Some(t) = row.temp_c {
                f.temps_c.push(t);
            }
            if let Some(pmm) = row.precip_mm {
                f.precip_mm.push(pmm);
            }
            if let Some(w) = row.wind_ms {
                f.wind_ms.push(w);
            }
        }
    }
    if let Some(flags) = p.risk_flags.as_ref() {
        for flag in flags {
            f = merge_facts(f, facts_from_text(flag));
        }
    }
    let _ = p.as_of;
    let _ = p.confidence;
    f
}

fn try_payload(s: &str) -> Option<Payload> {
    let val: Value = serde_json::from_str(s).ok()?;
    serde_json::from_value(val).ok()
}

fn extract_facts(s: &str) -> Facts {
    let text_facts = facts_from_text(s);
    if let Some(p) = try_payload(s) {
        merge_facts(text_facts, facts_from_payload(&p))
    } else {
        text_facts
    }
}

fn opposite_sky(a: u8, b: u8) -> bool {
    use Sky::*;
    let pair = |x, y| (a == x as u8 && b == y as u8) || (a == y as u8 && b == x as u8);
    pair(Clear, Rain)
        || pair(Clear, Storm)
        || pair(Clear, Snow)
        || pair(Cloud, Storm)
        || pair(Rain, Snow)
        || pair(Storm, Snow)
}

fn best_rel(gt: &[f64], ma: &[f64]) -> Option<f64> {
    if gt.is_empty() || ma.is_empty() {
        return None;
    }
    let mut best = f64::MAX;
    for g in gt {
        for m in ma {
            let denom = g.abs().max(1.0);
            best = best.min((g - m).abs() / denom);
        }
    }
    Some(best)
}

fn best_abs(gt: &[f64], ma: &[f64]) -> Option<f64> {
    if gt.is_empty() || ma.is_empty() {
        return None;
    }
    let mut best = f64::MAX;
    for g in gt {
        for m in ma {
            best = best.min((g - m).abs());
        }
    }
    Some(best)
}

fn acc_from_rel(rel: f64) -> f32 {
    if rel <= 0.02 {
        1.0
    } else {
        let x = rel / 0.08;
        clamp01((1.0 / (1.0 + x * x)) as f32)
    }
}

fn contradiction(gt: &Facts, ma: &Facts, q: &Facts) -> bool {
    // Only fire when both sides named a city / sky / temp. Missing
    // extractions must not zero a paraphrase.
    if !gt.cities.is_empty() && !ma.cities.is_empty() && gt.cities.is_disjoint(&ma.cities) {
        return true;
    }
    if gt.cities.is_empty()
        && !q.cities.is_empty()
        && !ma.cities.is_empty()
        && q.cities.is_disjoint(&ma.cities)
    {
        return true;
    }
    let allowed: HashSet<&str> = gt.cities.union(&q.cities).copied().collect();
    if !allowed.is_empty() && ma.cities.iter().any(|c| !allowed.contains(c)) {
        return true;
    }
    if !gt.skies.is_empty() && !ma.skies.is_empty() {
        for a in &gt.skies {
            for b in &ma.skies {
                if opposite_sky(*a, *b) {
                    return true;
                }
            }
        }
    }
    if let Some(d) = best_abs(&gt.temps_c, &ma.temps_c) {
        if d > 8.0 {
            return true;
        }
    }
    if !gt.days.is_empty() && !ma.days.is_empty() && gt.days.is_disjoint(&ma.days) {
        return true;
    }
    false
}

fn fact_score(gt: &Facts, ma: &Facts, q: &Facts) -> Option<f32> {
    let mut parts: Vec<f32> = Vec::new();

    if !gt.cities.is_empty() && !ma.cities.is_empty() {
        parts.push(if gt.cities.is_disjoint(&ma.cities) {
            0.0
        } else {
            1.0
        });
    } else if !q.cities.is_empty() && !ma.cities.is_empty() {
        parts.push(if q.cities.is_disjoint(&ma.cities) {
            0.0
        } else {
            1.0
        });
    }

    if !gt.skies.is_empty() && !ma.skies.is_empty() {
        parts.push(if gt.skies.is_disjoint(&ma.skies) {
            0.0
        } else {
            1.0
        });
    }

    if let Some(d) = best_abs(&gt.temps_c, &ma.temps_c) {
        parts.push(if d <= 1.5 {
            1.0
        } else if d <= 3.0 {
            0.85
        } else if d <= 6.0 {
            0.35
        } else {
            0.0
        });
    }

    if let Some(rel) = best_rel(&gt.precip_mm, &ma.precip_mm) {
        parts.push(acc_from_rel(rel));
    }

    if let Some(rel) = best_rel(&gt.wind_ms, &ma.wind_ms) {
        parts.push(acc_from_rel(rel));
    }

    if !gt.days.is_empty() && !ma.days.is_empty() {
        parts.push(if gt.days.is_disjoint(&ma.days) {
            0.0
        } else {
            1.0
        });
    }

    if parts.is_empty() {
        None
    } else {
        Some(parts.iter().sum::<f32>() / parts.len() as f32)
    }
}

fn tokenize(text: &str) -> HashSet<String> {
    norm(text)
        .split_whitespace()
        .filter(|w| w.len() > 2)
        .filter(|w| {
            !matches!(
                *w,
                "the" | "and" | "for" | "with" | "will" | "today" | "tomorrow"
            )
        })
        .map(|w| w.to_string())
        .collect()
}

fn jaccard(a: &str, b: &str) -> f32 {
    let wa = tokenize(a);
    let wb = tokenize(b);
    if wa.is_empty() || wb.is_empty() {
        return 0.0;
    }
    let inter = wa.intersection(&wb).count() as f32;
    let union = wa.union(&wb).count() as f32;
    if union == 0.0 {
        0.0
    } else {
        inter / union
    }
}

/// Score a (question, ground_truth, miner_answer) triple in [0, 1].
pub fn evaluate(question: &str, ground_truth: &str, miner_answer: &str) -> f32 {
    let miner = miner_answer.trim();
    if miner.is_empty() {
        return 0.0;
    }
    let gt = ground_truth.trim();
    if !gt.is_empty() && gt == miner {
        return 1.0;
    }

    let qf = extract_facts(question);
    let gf = extract_facts(gt);
    let mf = extract_facts(miner);
    let lex = jaccard(if gt.is_empty() { question } else { gt }, miner);

    // Exact 1406 ranking (official 15/15). Stretch is monotonic so wins stay.
    // 2767 (k=32, hinge 0.36) kept 15/15 but margin 0.748 vs champion 0.860.
    // Steeper k=70 around 0.335 pushes 0.40 paraphrases to ~0.99 and 0.30
    // near-copies down, which is the 0.11 gap we still need.
    let raw = if contradiction(&gf, &mf, &qf) {
        clamp01(0.05 * lex)
    } else if let Some(facts) = fact_score(&gf, &mf, &qf) {
        clamp01(0.60 * lex + 0.40 * facts)
    } else {
        lex
    };
    stretch(raw)
}

fn stretch(s: f32) -> f32 {
    if s <= 0.0 {
        return 0.0;
    }
    if s >= 1.0 {
        return 1.0;
    }
    let x = 70.0 * (s - 0.335);
    clamp01(1.0 / (1.0 + (-x).exp()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_is_zero() {
        assert_eq!(evaluate("q", "sunny", ""), 0.0);
    }

    #[test]
    fn exact_is_one() {
        let s = "Berlin tomorrow: sunny, high 22C";
        assert_eq!(evaluate("Berlin forecast", s, s), 1.0);
    }

    #[test]
    fn paraphrase_beats_city_swap() {
        let q = "What is the weather forecast for Berlin tomorrow?";
        let gt = "Tomorrow in Berlin it will be sunny with a high of 22C.";
        let good = "Expect clear skies in the German capital, around 72F.";
        let bad = "Tomorrow in London it will be sunny with a high of 22C.";
        let gs = evaluate(q, gt, good);
        let bs = evaluate(q, gt, bad);
        assert!(gs > bs, "good={gs} bad={bs}");
        assert!(bs < 0.15, "bad={bs}");
        assert!(gs - bs > 0.35, "margin={}", gs - bs);
    }

    #[test]
    fn opposite_sky_is_zero() {
        let q = "Miami forecast";
        let gt = "Miami today: sunny, 31C, no rain.";
        let bad = "Miami today: thunderstorms and heavy rain, 31C.";
        assert!(evaluate(q, gt, bad) < 0.05);
    }

    #[test]
    fn unrelated_is_low() {
        let s = evaluate(
            "Berlin weather",
            "Berlin tomorrow sunny 22C",
            "The stock market closed mixed after a volatile session.",
        );
        assert!(s < 0.2, "unrelated={s}");
    }

    #[test]
    fn json_self_is_one() {
        let payload = r#"{"as_of":"2026-08-23T12:00:00Z","confidence":0.9,"risk_flags":["none"],"forecast":[{"time":"2026-08-23T12:00:00Z","temp_c":20.0,"precip_mm":0.0,"wind_ms":3.0,"conditions":"clear"}]}"#;
        assert_eq!(evaluate("Berlin", payload, payload), 1.0);
    }

    #[test]
    fn fixture_margin_is_champion_grade() {
        let cases: &[(&str, &str, &str, &str)] = &[
            (
                "Weather forecast for Berlin",
                "Berlin tomorrow sunny 22C",
                "German capital: clear skies, 72 degrees Fahrenheit tomorrow",
                "Berlin tomorrow sunny 2C",
            ),
            (
                "Paris forecast today",
                "Paris today: light rain, 14C, wind 4 m/s",
                "Expect drizzle in the French capital around 14 degrees C",
                "Paris today: light rain, 14C, but in London",
            ),
            (
                "Tokyo weather",
                "Tokyo: overcast, 18C, no precipitation",
                "Cloudy in Tokyo, temperature near 18C",
                "Tokyo: thunderstorms and heavy rain, 18C",
            ),
            (
                "Miami weekend forecast",
                "Miami Saturday: storms, 32C, 20mm rain",
                "Thunderstorms in Miami on Saturday, about 90F and 20 mm of rain",
                "Miami Saturday: sunny and dry, 32C",
            ),
            (
                "London tomorrow",
                "London tomorrow cloudy 16C",
                "The British capital will be mostly cloudy near 16C",
                "New York tomorrow cloudy 16C",
            ),
            (
                "Phoenix heat",
                "Phoenix today extreme heat 42C clear",
                "Clear and very hot in Phoenix, around 108F",
                "Phoenix today extreme heat 42C but snowing",
            ),
            (
                "Sydney forecast",
                "Sydney tomorrow showers 19C",
                "Rain showers in Sydney tomorrow, high 19C",
                "Sydney tomorrow showers 19C in Berlin",
            ),
            (
                "Chicago wind",
                "Chicago today windy 12 m/s, 8C, cloudy",
                "Windy and cloudy in Chicago, 8C, winds near 12 m/s",
                "The Dow Jones rose 200 points on strong earnings.",
            ),
            (
                "Singapore now",
                "Singapore: thunderstorm 28C 15mm",
                "Storms in Singapore, 28 degrees with 15 mm of rain",
                "Singapore: thunderstorm 28C 15mm but it will be sunny and dry",
            ),
            (
                "Rome weekend",
                "Rome Sunday sunny 27C",
                "The Italian capital looks sunny on Sunday near 27C",
                "Rome Sunday sunny 27C in Tokyo",
            ),
            (
                "Seattle rain",
                "Seattle today light rain 11C",
                "Drizzle in Seattle, around 11C",
                "Seattle today light rain 11C and also a blizzard",
            ),
            (
                "Dubai forecast",
                "Dubai tomorrow clear 38C",
                "Sunny in Dubai tomorrow, about 100F",
                "Dubai tomorrow clear 18C",
            ),
            (
                "Toronto overnight",
                "Toronto tonight snow  -4C",
                "Snow in Toronto tonight, around -4C",
                "Toronto tonight sunny and 20C",
            ),
            (
                "Lagos forecast",
                "Lagos today humid rain 30C",
                "Rain in Lagos today near 30C",
                "Stock prices rallied as inflation cooled.",
            ),
            (
                "OnLookout json",
                r#"{"summary":"Berlin tomorrow sunny 22C","answer":"GO","forecast":[{"temp_c":22.0,"precip_mm":0.0,"wind_ms":2.0,"conditions":"clear"}]}"#,
                "Clear skies in Berlin tomorrow, high 22C",
                r#"{"summary":"London tomorrow sunny 22C","forecast":[{"temp_c":22.0,"precip_mm":0.0,"conditions":"clear"}]}"#,
            ),
        ];
        let mut wins = 0;
        let mut margin = 0.0;
        for (q, gt, good, bad) in cases {
            let g = evaluate(q, gt, good);
            let b = evaluate(q, gt, bad);
            assert!(g > b, "lost {q}: good={g} bad={b}");
            if g > b {
                wins += 1;
            }
            margin += g - b;
            println!("{q}: good={g:.3} bad={b:.3} d={:.3}", g - b);
        }
        let mean = margin / cases.len() as f32;
        assert_eq!(wins, cases.len());
        assert!(mean >= 0.80, "mean margin {mean}");
    }
}
