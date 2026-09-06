// PhishGuard — JS URL Feature Extractor
// Pure JavaScript port of backend/ml/feature_extractor.py
// Extracts the same 19 features used to train the CatBoost model.
// Order MUST match FEATURE_NAMES in feature_extractor.py exactly.

const SUSPICIOUS_KEYWORDS = [
  "login", "signin", "verify", "account", "update", "secure",
  "banking", "confirm", "password", "credential", "wallet",
  "payment", "paypal", "amazon", "apple", "microsoft",
];

const CONFUSABLE_MAP = {
  '0': 'o', '1': 'l', '5': 's', '3': 'e', '@': 'a',
};

function shannonEntropy(s) {
  if (!s || s.length === 0) return 0;
  const freq = {};
  for (const ch of s) freq[ch] = (freq[ch] || 0) + 1;
  let entropy = 0;
  const len = s.length;
  for (const count of Object.values(freq)) {
    const p = count / len;
    entropy -= p * Math.log2(p);
  }
  return entropy;
}

function countSpecialChars(s) {
  return (s.match(/[!@#$%^&*()_+\-=\[\]{}|;':",.<>?\/\\]/g) || []).length;
}

function hasIPAddress(hostname) {
  return /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(hostname);
}

function isPunycode(hostname) {
  return hostname.split('.').some(label => label.startsWith('xn--'));
}

function hasUnicode(hostname) {
  return /[^\x00-\x7F]/.test(hostname);
}

function countConfusableChars(hostname) {
  let count = 0;
  for (const ch of hostname.toLowerCase()) {
    if (ch in CONFUSABLE_MAP) count++;
  }
  return count;
}

function countMixedScriptChanges(s) {
  // Count transitions between Latin and non-Latin script
  let changes = 0;
  let prevIsLatin = null;
  for (const ch of s) {
    const isLatin = /[a-zA-Z]/.test(ch);
    if (prevIsLatin !== null && isLatin !== prevIsLatin) changes++;
    prevIsLatin = isLatin;
  }
  return changes;
}

/**
 * Extract 19 URL features matching the Python feature extractor output.
 * @param {string} url - The URL to analyse
 * @returns {Float32Array} - Feature vector of length 19
 */
export function extractFeatures(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch (e) {
    // Return zeros for unparseable URLs
    return new Float32Array(19);
  }

  const hostname = parsed.hostname.toLowerCase();
  const path = parsed.pathname;
  const query = parsed.search;
  const queryParams = query ? query.slice(1).split('&').filter(Boolean).length : 0;

  const urlLower = url.toLowerCase();
  const hasSuspiciousKw = SUSPICIOUS_KEYWORDS.some(kw => urlLower.includes(kw)) ? 1 : 0;
  const numSubdomains = hostname.split('.').length - 2;

  const features = new Float32Array(19);
  features[0]  = url.length;                             // url_length
  features[1]  = hostname.length;                        // hostname_length
  features[2]  = path.length;                            // path_length
  features[3]  = query.length;                           // query_length
  features[4]  = queryParams;                            // num_query_params
  features[5]  = (url.match(/\./g) || []).length;        // num_dots
  features[6]  = (url.match(/-/g) || []).length;         // num_hyphens
  features[7]  = (url.match(/@/g) || []).length;         // num_at
  features[8]  = countSpecialChars(url);                 // num_special_chars
  features[9]  = (hostname.match(/[0-9]/g) || []).length;// num_digits_in_domain
  features[10] = hasIPAddress(hostname) ? 1 : 0;         // has_ip_address
  features[11] = shannonEntropy(hostname);                // entropy
  features[12] = hasSuspiciousKw;                        // suspicious_keywords
  features[13] = parsed.protocol === 'https:' ? 1 : 0;  // uses_https
  features[14] = Math.max(numSubdomains, 0);             // num_subdomains
  features[15] = hasUnicode(hostname) ? 1 : 0;           // has_unicode
  features[16] = isPunycode(hostname) ? 1 : 0;           // is_punycode
  features[17] = countConfusableChars(hostname);         // confusable_chars
  features[18] = countMixedScriptChanges(hostname);      // mixed_script_changes

  return features;
}
