// PhishGuard — JS URL Feature Extractor
// Pure JavaScript port of backend/ml/feature_extractor.py.
//
// ── SCHEMA CONTRACT ──────────────────────────────────────────────────────────
// MODEL_FEATURE_NAMES must be identical — same names, same order — to
// MODEL_FEATURE_NAMES in backend/ml/feature_extractor.py, which is itself
// verified against the trained CatBoost model's feature_names_ by
// ml.validate_model_schema(). backend/ml/export_onnx.py mirrors that schema
// into extension/model/model_meta.json.
//
// background.js builds every inference vector from model_meta.json and
// asserts the vector length against it before the tensor is created, so a
// schema drift can never reach the ONNX session silently.
//
// Only features the trained model actually consumes are computed here. The
// analysis-only features (num_subdomains, has_unicode, is_punycode,
// confusable_chars, mixed_script_changes) are deliberately absent: the model
// never sees them, so producing them locally would only invite presenting
// them as model evidence.

export const MODEL_FEATURE_NAMES = [
  "url_length",
  "hostname_length",
  "path_length",
  "query_length",
  "num_query_params",
  "num_dots",
  "num_hyphens",
  "num_at",
  "num_special_chars",
  "num_digits_in_domain",
  "has_ip_address",
  "entropy",
  "suspicious_keywords",
  "uses_https",
];

export const NUM_MODEL_FEATURES = MODEL_FEATURE_NAMES.length;

// Keywords commonly found in phishing URLs (must match SUSPICIOUS_KEYWORDS
// in backend/ml/feature_extractor.py).
const SUSPICIOUS_KEYWORDS = [
  "login", "verify", "secure", "account", "update", "confirm",
  "bank", "paypal", "signin", "password", "credential", "suspend",
  "alert", "expire", "unlock", "validate", "billing", "invoice",
  "wallet", "recover", "restore", "authenticate", "authorize",
];

const IP_PATTERN = /^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$/;

const SPECIAL_CHARS = new Set(Array.from("?&=%#!~+|"));

// Schemes for which CPython's urllib.parse.urlparse() splits `;params` off
// the end of the path. Must match urllib.parse.uses_params.
const USES_PARAMS = new Set([
  "", "ftp", "hdl", "prospero", "http", "imap", "https", "shttp",
  "rtsp", "rtsps", "rtspu", "sip", "sips", "mms", "sftp", "tel",
]);

// urllib.parse.scheme_chars
const SCHEME_CHARS = new Set(
  Array.from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-.")
);

// urllib.parse._UNSAFE_URL_BYTES_TO_REMOVE
const UNSAFE_URL_BYTES = /[\t\r\n]/g;

const IPV4_PATTERN = /^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/;

function countOccurrences(text, ch) {
  let n = 0;
  for (let i = 0; i < text.length; i++) if (text[i] === ch) n++;
  return n;
}

function shannonEntropy(text) {
  if (!text || text.length === 0) return 0;
  const freq = Object.create(null);
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    freq[ch] = (freq[ch] || 0) + 1;
  }
  const len = text.length;
  let entropy = 0;
  for (const key in freq) {
    const p = freq[key] / len;
    entropy -= p * Math.log2(p);
  }
  return entropy;
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function isValidIpv6(host) {
  // Practical equivalent of Python's ipaddress.IPv6Address() check.
  let h = host;
  const pct = h.indexOf("%");
  if (pct >= 0) h = h.slice(0, pct); // scoped address, e.g. fe80::1%eth0
  if (!h) return false;

  if (h.includes(".")) {
    // Embedded IPv4 tail counts as two hextets.
    const idx = h.lastIndexOf(":");
    if (idx < 0) return false;
    if (!IPV4_PATTERN.test(h.slice(idx + 1))) return false;
    h = h.slice(0, idx + 1) + "0:0";
  }

  const isHextet = (s) => /^[0-9A-Fa-f]{1,4}$/.test(s);
  const compressions = (h.match(/::/g) || []).length;
  if (compressions > 1) return false;

  if (compressions === 1) {
    const [left, right] = h.split("::");
    const lhs = left ? left.split(":") : [];
    const rhs = right ? right.split(":") : [];
    if (!lhs.every(isHextet) || !rhs.every(isHextet)) return false;
    return lhs.length + rhs.length <= 7;
  }

  const groups = h.split(":");
  if (!groups.every(isHextet)) return false;
  return groups.length === 8;
}

function checkBracketedHost(hostname) {
  // Mirrors urllib.parse._check_bracketed_host(): rejects IPvFuture syntax
  // errors and refuses to accept an IPv4 literal inside brackets.
  if (hostname.startsWith("v")) {
    if (!/^v[a-fA-F0-9]+\..+$/.test(hostname)) {
      throw new Error("IPvFuture address is invalid");
    }
    return;
  }
  if (IPV4_PATTERN.test(hostname)) {
    throw new Error("An IPv4 address cannot be in brackets");
  }
  if (!isValidIpv6(hostname)) {
    throw new Error("Invalid IPv6 URL");
  }
}

function checkBracketedNetloc(netloc) {
  // Mirrors urllib.parse._check_bracketed_netloc().
  const at = netloc.lastIndexOf("@");
  const hostPort = at >= 0 ? netloc.slice(at + 1) : netloc;
  const open = hostPort.indexOf("[");
  if (open >= 0) {
    // No data is allowed before a bracket.
    if (open > 0) throw new Error("Invalid IPv6 URL");
    const close = hostPort.indexOf("]", 1);
    const hostname = close < 0 ? hostPort.slice(1) : hostPort.slice(1, close);
    const port = close < 0 ? "" : hostPort.slice(close + 1);
    // No data is allowed after the bracket but before the port delimiter.
    if (port && !port.startsWith(":")) throw new Error("Invalid IPv6 URL");
    checkBracketedHost(hostname);
    return;
  }
  const colon = hostPort.indexOf(":");
  checkBracketedHost(colon < 0 ? hostPort : hostPort.slice(0, colon));
}

/**
 * Minimal mirror of CPython's urllib.parse.urlsplit()/urlparse(), so that
 * feature values are computed from exactly the same
 * scheme/netloc/path/params/query/fragment split the backend — and therefore
 * the training data — used. Deliberately does NOT use the WHATWG URL
 * parser: it normalises paths, adds a trailing slash and punycodes hosts,
 * all of which would change the feature values.
 *
 * @throws {Error} on the same malformed input CPython rejects.
 */
function splitUrl(input) {
  let url = String(input).trim().replace(UNSAFE_URL_BYTES, "");
  let scheme = "";

  // CPython urlsplit(): a scheme is recognised only when the first ':' is
  // preceded by a non-empty run of scheme_chars starting with an ASCII letter.
  const colon = url.indexOf(":");
  if (colon > 0 && url.charCodeAt(0) < 128 && /[A-Za-z]/.test(url[0])) {
    let isScheme = true;
    for (let i = 0; i < colon; i++) {
      if (!SCHEME_CHARS.has(url[i])) {
        isScheme = false;
        break;
      }
    }
    if (isScheme) {
      scheme = url.slice(0, colon).toLowerCase();
      url = url.slice(colon + 1);
    }
  }

  let netloc = "";
  let path = url;
  if (path.slice(0, 2) === "//") {
    // _splitnetloc(url, 2): the authority ends at '/', '?' or '#'.
    const body = path.slice(2);
    let end = body.length;
    for (const ch of ["/", "?", "#"]) {
      const i = body.indexOf(ch);
      if (i !== -1 && i < end) end = i;
    }
    netloc = body.slice(0, end);
    path = body.slice(end);

    if (
      (netloc.includes("[") && !netloc.includes("]")) ||
      (netloc.includes("]") && !netloc.includes("["))
    ) {
      throw new Error("Invalid IPv6 URL");
    }
    if (netloc.includes("[") && netloc.includes("]")) checkBracketedNetloc(netloc);
  }

  // CPython splits the fragment before the query.
  let query = "";
  const hash = path.indexOf("#");
  if (hash !== -1) path = path.slice(0, hash);
  const question = path.indexOf("?");
  if (question !== -1) {
    query = path.slice(question + 1);
    path = path.slice(0, question);
  }

  // urlparse() splits `;params` off the last path segment for schemes in
  // uses_params. extract_features() reads .path, so params are discarded.
  if (USES_PARAMS.has(scheme) && path.includes(";")) {
    const lastSlash = path.lastIndexOf("/");
    const semi = lastSlash >= 0 ? path.indexOf(";", lastSlash) : path.indexOf(";");
    if (semi >= 0) path = path.slice(0, semi);
  }

  return { scheme, netloc, path, query };
}

/**
 * Extract every model feature as a name -> value map.
 * Mirrors ml.feature_extractor.extract_features() for the model schema.
 *
 * @param {string} url - The URL to analyse
 * @returns {Record<string, number>} - One entry per MODEL_FEATURE_NAMES
 */
export function extractFeatureMap(url) {
  let parts;
  try {
    parts = splitUrl(url);
  } catch (e) {
    // backend/ml/feature_extractor.py falls back to a placeholder URL when
    // parsing fails, so mirror that instead of returning zeros.
    parts = splitUrl("http://invalid.url");
  }

  const raw = String(url).trim();
  const scheme = parts.scheme;
  const hostname = parts.netloc.toLowerCase();
  const path = parts.path;
  const query = parts.query;
  const urlLower = raw.toLowerCase();
  const pathAndHost = scheme + "://" + hostname + path;

  const hostNoPort = hostname.includes(":") ? hostname.split(":")[0] : hostname;

  let specialChars = 0;
  for (let i = 0; i < pathAndHost.length; i++) {
    if (SPECIAL_CHARS.has(pathAndHost[i])) specialChars++;
  }

  let digitsInDomain = 0;
  for (let i = 0; i < hostname.length; i++) {
    if (hostname[i] >= "0" && hostname[i] <= "9") digitsInDomain++;
  }

  let suspiciousKeywords = 0;
  for (const kw of SUSPICIOUS_KEYWORDS) {
    if (urlLower.includes(kw)) suspiciousKeywords++;
  }

  return {
    url_length: raw.length,
    hostname_length: hostname.length,
    path_length: path.length,
    query_length: query.length,
    num_query_params: query ? query.split("&").length : 0,
    num_dots: countOccurrences(hostname, "."),
    num_hyphens: countOccurrences(hostname, "-"),
    num_at: countOccurrences(raw, "@"),
    num_special_chars: specialChars,
    num_digits_in_domain: digitsInDomain,
    has_ip_address: IP_PATTERN.test(hostNoPort) ? 1 : 0,
    entropy: round4(shannonEntropy(pathAndHost)),
    suspicious_keywords: suspiciousKeywords,
    uses_https: scheme === "https" ? 1 : 0,
  };
}

/**
 * Build the ONNX input vector for a URL.
 *
 * @param {string} url - The URL to analyse
 * @param {string[]} [featureNames] - Feature order to emit. Defaults to the
 *   model schema; background.js passes model_meta.json's feature_names so the
 *   vector is always ordered exactly as the shipped model expects.
 * @returns {Float32Array} - Vector of length featureNames.length
 * @throws {Error} if the schema asks for a feature this extractor cannot
 *   compute — never silently pad or truncate.
 */
export function extractFeatures(url, featureNames = MODEL_FEATURE_NAMES) {
  const names = Array.from(featureNames);
  const values = extractFeatureMap(url);
  const vector = new Float32Array(names.length);
  for (let i = 0; i < names.length; i++) {
    const name = names[i];
    if (!Object.prototype.hasOwnProperty.call(values, name)) {
      throw new Error(
        `Feature schema mismatch: model requests "${name}" at index ${i}, ` +
          `but the extractor only computes ${JSON.stringify(MODEL_FEATURE_NAMES)}.`
      );
    }
    vector[i] = values[name];
  }
  return vector;
}
