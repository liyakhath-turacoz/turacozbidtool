use std::io::{self, Read};
use strsim::normalized_damerau_levenshtein;

const STOP_WORDS: &[&str] = &[
    "a", "an", "and", "any", "best", "buy", "find", "for", "from", "in", "latest",
    "me", "of", "or", "please", "product", "products", "the", "to", "with",
];

fn words(value: &str) -> Vec<String> {
    let mut result = Vec::new();
    let mut current = String::new();
    for character in value.chars() {
        if character.is_alphanumeric() {
            current.extend(character.to_lowercase());
        } else if !current.is_empty() {
            result.push(std::mem::take(&mut current));
        }
    }
    if !current.is_empty() {
        result.push(current);
    }
    result
}

fn word_score(query: &str, word: &str) -> f32 {
    if query == word {
        return 1.0;
    }
    if query.chars().count() >= 3 && word.starts_with(query) {
        return 0.93;
    }
    if word.chars().count() >= 3 && query.starts_with(word) {
        return 0.86;
    }
    let query_len = query.chars().count();
    let word_len = word.chars().count();
    if query_len.min(word_len) < 4 || query_len.abs_diff(word_len) > 2 {
        return 0.0;
    }
    let similarity = normalized_damerau_levenshtein(query, word) as f32;
    if similarity >= 0.67 { similarity } else { 0.0 }
}

fn field_score(term: &str, field: &str) -> f32 {
    words(field).iter().map(|word| word_score(term, word)).fold(0.0, f32::max)
}

fn score(alias: &str, fields: &[&str]) -> f32 {
    let terms: Vec<String> = words(alias).into_iter().filter(|term| !STOP_WORDS.contains(&term.as_str())).collect();
    if terms.is_empty() { return 0.0; }
    let weights = [1.0, 0.96, 0.94, 1.0, 0.91, 0.91, 0.76];
    let values: Vec<f32> = terms.iter().map(|term| {
        fields.iter().zip(weights.iter()).map(|(field, weight)| field_score(term, field) * weight).fold(0.0, f32::max)
    }).collect();
    let matched = values.iter().filter(|value| **value >= 0.64).count();
    let minimum_matches = (terms.len() * 2 + 2) / 3;
    if matched < minimum_matches { return 0.0; }
    values.iter().sum::<f32>() / values.len() as f32
}

fn main() {
    let mut input = String::new();
    if io::stdin().read_to_string(&mut input).is_err() { return; }
    let mut lines = input.lines();
    let alias_count = lines.next().and_then(|line| line.parse::<usize>().ok()).unwrap_or(0).min(32);
    let aliases: Vec<String> = lines.by_ref().take(alias_count).map(str::to_owned).collect();
    let mut results = Vec::<(String, u32)>::new();
    for line in lines {
        let columns: Vec<&str> = line.splitn(8, '\t').collect();
        if columns.len() < 8 { continue; }
        let best = aliases.iter().map(|alias| score(alias, &columns[1..])).fold(0.0, f32::max);
        if best >= 0.64 {
            results.push((columns[0].to_owned(), (best * 10000.0).round() as u32));
        }
    }
    results.sort_by(|left, right| right.1.cmp(&left.1).then_with(|| left.0.cmp(&right.0)));
    for (record_id, score) in results {
        println!("{}\t{}", record_id, score);
    }
}

#[cfg(test)]
mod tests {
    use super::score;

    #[test]
    fn recovers_transposed_letters_in_a_product_type() {
        let fields = ["ASUS Zenbook 14", "ASUS", "ASUS", "UX3405", "Computers", "Laptops", "16 GB RAM OLED"];
        assert!(score("laptpo", &fields) >= 0.64);
    }

    #[test]
    fn rejects_an_unrelated_product() {
        let fields = ["Front Load Washer", "LG", "LG", "FHM", "Home Appliances", "Washing Machines", "10 kg"];
        assert_eq!(score("laptop", &fields), 0.0);
    }
}
