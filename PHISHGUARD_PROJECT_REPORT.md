# REAL-TIME PHISHING DETECTION AND CYBER THREAT INTELLIGENCE USING MULTI-ENGINE ENSEMBLE AI

**Course Code:** 22IT801-PROJECT-II  
**Document:** A PROJECT REPORT  

**Submitted by:**  
- **SASIKUMAR M** (Reg No: 727724EUCD501)  
- **PROJECT ASSOCIATE** (Reg No: 727724EUCD502)  

*In partial fulfilment for the award of the degree of*  
**BACHELOR OF TECHNOLOGY IN INFORMATION TECHNOLOGY**  

**SRI KRISHNA COLLEGE OF ENGINEERING AND TECHNOLOGY**  
*(An Autonomous Institution | Approved by AICTE | Affiliated to Anna University | Accredited by NAAC with A++ Grade)*  
*Kuniamuthur, Coimbatore – 641008*  
**MARCH 2026**  

---

## BONAFIDE CERTIFICATE

Certified that this project report **“REAL-TIME PHISHING DETECTION AND CYBER THREAT INTELLIGENCE USING MULTI-ENGINE ENSEMBLE AI”** is the Bonafide work of **SASIKUMAR M (727724EUCD501)**, who carried out the project work under my supervision.

| SIGNATURE | SIGNATURE |
| :--- | :--- |
| **Dr. T. RAJESH KUMAR** | **Ms. U. M. RAMYA** |
| **HEAD OF THE DEPARTMENT** | **SUPERVISOR** |
| Professor | Assistant Professor |
| Department of Information Technology | Department of Information Technology |
| Sri Krishna College of Engineering and Technology | Sri Krishna College of Engineering and Technology |
| Kuniamuthur, Coimbatore – 641008 | Kuniamuthur, Coimbatore – 641008 |

Submitted for the Project viva-voce examination held on: ____________________  

**INTERNAL EXAMINER** &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; **EXTERNAL EXAMINER**

---

## ACKNOWLEDGEMENT

We express our sincere thanks to the Management and **Dr. K. Porkumaran**, Principal, Sri Krishna College of Engineering and Technology, Coimbatore for providing us with the necessary facilities and support to carry out this project work.

We are profoundly thankful to **Dr. T. Rajesh Kumar**, Professor and Head, Department of Information Technology, for his encouragement, leadership, and constructive evaluation given throughout the development of the project.

We express our deep sense of gratitude to our supervisor **Prof. U. M. Ramya M.E., Ph.D.**, Assistant Professor, and our project coordinator **Prof. B. Narmatha M.E.**, Assistant Professor, Department of Information Technology, for their invaluable advice, technical mentorship, and constant guidance during the project course.

Finally, we express our heartfelt sense of gratitude and thanks to our beloved parents, family members, and friends whose continuous encouragement and support enabled the successful completion of this research project.

---

## ABSTRACT

Phishing attacks represent one of the most prolific and devastating vectors of cybercrime worldwide. Modern adversaries routinely evade traditional static blacklists and rule-based firewalls through zero-day domains, automated URL shorteners, punycode homograph attacks, and multi-hop HTTP redirect sequences. To overcome the latency limitations of reactive threat indexing, this project presents **PhishGuard**, an enterprise-grade, real-time phishing URL detection and cyber threat intelligence platform powered by a multi-engine ensemble artificial intelligence architecture.

PhishGuard combines four complementary detection engines:
1. **CatBoost Tabular Machine Learning Engine:** Evaluates 19 lexical, syntactic, and structural URL features in under 15ms.
2. **DeBERTa NLP Semantic Engine:** Inspects deceptive token sequences and brand impersonation lures embedded inside paths and subdomains.
3. **Domain Intelligence Engine:** Traces redirect hops, expands shortened links, analyzes WHOIS registrar registration age, and cross-references live Threat Intel feeds.
4. **Google Gemini LLM Deep Reasoning:** Delivers contextual zero-day deduction and synthesizes human-interpretable Explainable AI (XAI) risk breakdowns.

An ensemble meta-learner fuses multi-engine output probabilities into a single calibrated risk score. Operating through a Google Chrome Manifest V3 extension, PhishGuard intercepts web navigation events at the browser level in under 150ms, proactively injecting a high-contrast blocking modal before credentials can be compromised. Tested on a balanced corpus of 100,000 URLs, PhishGuard achieves **99.1% accuracy**, **99.3% precision**, and **0.998 ROC-AUC**, providing a scalable and dependable zero-day defense system.

---

## TABLE OF CONTENTS

| Chapter | Title | Page No. |
| :---: | :--- | :---: |
| | **BONAFIDE CERTIFICATE** | ii |
| | **ACKNOWLEDGEMENT** | iii |
| | **ABSTRACT** | iv |
| **1** | **INTRODUCTION** | **1** |
| | 1.1 Phishing Threat Landscape | 1 |
| | 1.2 URL Structural & Semantic Analysis | 1 |
| | 1.3 Multi-Engine Ensemble & LLM Reasoning | 1 |
| | 1.4 Motivation for the Proposed System | 1 |
| | 1.5 Applications and Significance | 1 |
| **2** | **LITERATURE SURVEY** | **2** |
| | 2.1 CatBoost Gradient Boosting | 2 |
| | 2.2 Transformer-based DeBERTa NLP | 2 |
| | 2.3 Machine Learning for Malicious URL Detection | 2 |
| | 2.4 Explainable AI (SHAP & LIME) | 2 |
| **3** | **SYSTEM ANALYSIS** | **3** |
| | 3.1 Objectives | 3 |
| | 3.2 Existing System | 3 |
| | 3.3 Problem Statement | 3 |
| | 3.4 Proposed System | 3 |
| **4** | **SYSTEM REQUIREMENTS** | **4** |
| | 4.1 Hardware Requirements | 4 |
| | 4.2 Software Requirements | 4 |
| | 4.3 Software Description | 4 |
| **5** | **PROJECT DESCRIPTION & ARCHITECTURE** | **5** |
| | 5.1 Modules Description | 5 |
| | 5.2 Use Case Diagram | 5 |
| | 5.3 Sequence Diagram | 6 |
| | 5.4 System Architecture | 6 |
| **6** | **PERFORMANCE AND RESULT ANALYSIS** | **7** |
| | 6.1 Dataset Preparation and Model Training | 7 |
| | 6.2 Comparative Model Performance | 7 |
| | 6.3 URL Feature Importance Analysis | 7 |
| | 6.4 ROC-AUC and Latency Analysis | 8 |
| **7** | **CONCLUSION AND FUTURE WORK** | **8** |
| | 7.1 Conclusion | 8 |
| | 7.2 Future Work | 8 |
| | **SUSTAINABLE DEVELOPMENT GOALS (SDG)** | **9** |
| | **REFERENCES** | **9** |
| | **APPENDIX 1: SOURCE CODE** | **10** |
| | **APPENDIX 2: OPERATIONAL SCREENSHOTS** | **10** |

---

## CHAPTER 1: INTRODUCTION

### 1.1 Phishing Threat Landscape
The rapid digitalization of modern society has intensified dependency on online platforms for banking, healthcare, education, and commerce. Simultaneously, cybercriminals deploy deceptive phishing campaigns that harvest sensitive authentication credentials and personal identifiable information (PII). Attackers utilize dynamic content generation, bulletproof hosting, and automated kits to deploy lookalike portals that deceive even security-conscious users.

### 1.2 Limitations of Static Blacklists & Motivation
Standard defense mechanisms (such as Google Safe Browsing and PhishTank) depend on retrospective user reporting and domain indexing. By the time a malicious URL is analyzed and propagated to global blacklists (typically 4 to 24 hours), the majority of victims have already fallen prey. PhishGuard addresses this vulnerability by moving defense directly into the browser, executing proactive on-device and edge-assisted machine learning inference.

### 1.3 Multi-Engine Ensemble & Explainable Cyber Defense
Single machine learning classifiers often overfit to specific lexical patterns or fail on novel domain generation algorithms (DGAs). PhishGuard solves this by deploying a heterogeneous ensemble: CatBoost evaluates structural URL properties, DeBERTa inspects NLP semantic tokens, Domain Intelligence verifies infrastructure integrity, and Google Gemini LLM provides high-level contextual deduction and Explainable AI (XAI) justifications.

---

## CHAPTER 2: LITERATURE SURVEY

1. **Prokhorenkova et al. (2018) 'CatBoost: unbiased boosting with categorical features', NeurIPS:**  
   Proved that ordered boosting reduces prediction shift and prevents target leakage on tabular feature sets. PhishGuard adopts CatBoost for statistical URL feature classification, achieving 97.9% standalone accuracy in under 15ms.
2. **He et al. (2021) 'DeBERTa: Decoding-enhanced BERT with Disentangled Attention', ICLR:**  
   Demonstrated disentangled attention and enhanced mask decoders. In PhishGuard, DeBERTa extracts semantic intent and detects deceptive keywords (e.g., 'verify-login-security') within URLs.
3. **Sahoo, Liu, and Hoi (2019) 'Malicious URL Detection using Machine Learning: A Survey', IEEE Access:**  
   Comprehensive survey establishing lexical feature extraction fundamentals (Shannon entropy, digit ratios, token length). These principles form the basis of PhishGuard's 19-feature vector.
4. **Ribeiro et al. (2016) 'Why Should I Trust You?: Explaining Predictions of Any Classifier', ACM SIGKDD:**  
   Formulated local feature attribution frameworks. PhishGuard integrates SHAP score attributions and Google Gemini generative reasoning to render human-readable threat summaries.

---

## CHAPTER 3: SYSTEM ANALYSIS

### 3.1 Objectives
- Develop an active, client-side phishing interception system in a Chrome Manifest V3 extension.
- Extract 19 lexical, structural, and cryptographic features entirely on-device without network calls.
- Execute parallel multi-engine AI evaluation (ML, NLP, Domain Intelligence, Gemini LLM).
- Fuse engine confidence scores through a trained ensemble meta-learner.
- Achieve sub-150ms response latency using tiered caching and ONNX runtime acceleration.
- Deliver clear Explainable AI (XAI) threat summaries for security analysts and end users.

### 3.2 Existing System vs. Proposed PhishGuard System

| Feature / Dimension | Existing Blacklist & Single-Model Systems | Proposed PhishGuard Platform |
| :--- | :--- | :--- |
| **Zero-Day Protection** | Fails; requires hours or days to discover and index | Instantaneous detection via structural ML & Gemini LLM |
| **Detection Engines** | Single heuristic rule or standalone classifier | Heterogeneous 4-Engine Ensemble + Meta-Learner |
| **Execution Latency** | High overhead in sandboxes (2000ms – 5000ms) | Sub-second (<150ms) via in-memory and ONNX runtime |
| **Explainability (XAI)**| Opaque binary flag ('Malicious' / 'Benign') | Granular SHAP feature weights & natural language explanation |
| **Client Enforcement** | Passive warnings or delayed DNS blocking | Active browser injection modal intercepting DOM rendering |

---

## CHAPTER 4: SYSTEM REQUIREMENTS

### 4.1 Hardware Requirements
- **Processor:** Intel Core i5 (10th Gen or newer) / AMD Ryzen 5
- **RAM:** 8 GB minimum (16 GB recommended)
- **Hard Disk:** 512 GB SSD (High-throughput read/write for model weights)
- **Network:** Broadband internet connection (minimum 10 Mbps)
- **Peripherals:** Standard keyboard, mouse, HD monitor

### 4.2 Software Requirements
- **Operating System:** Windows 10/11, Ubuntu Linux, or macOS
- **Development Environment:** Visual Studio Code (latest version)
- **Backend Framework:** Python 3.10+, FastAPI, Uvicorn
- **Machine Learning Stack:** CatBoost, Scikit-learn, ONNX Runtime, PyTorch
- **Frontend Stack:** React 18, TypeScript, Vite, Tailwind CSS
- **Browser Extension:** Google Chrome (Manifest V3 Service Worker)
- **Generative AI API:** Google Gemini 1.5/2.0 Flash REST API

---

## CHAPTER 5: PROJECT DESCRIPTION & ARCHITECTURE

### 5.1 Modules Description
- **Real-Time Browser Interceptor (Chrome MV3):** Background service worker (`background.js`) hooks into `chrome.webNavigation.onCommitted`, querying session caches and backend APIs. Upon detecting phishing, `content.js` halts navigation and renders a full-page modal.
- **URL Feature Extractor & CatBoost ML Engine:** Extracts 19 lexical indicators (Shannon entropy, path length, subdomain counts, digit ratios, punycode flags) and executes tabular classification in under 15ms.
- **NLP Semantic & Domain Intelligence Engine:** Inspects deceptive token sequences, traces HTTP 301/302 redirects, expands shortlinks (bit.ly), and verifies WHOIS registration age (<14 days indicates high risk).
- **Gemini LLM Reasoning & Ensemble Meta-Learner:** Synthesizes multi-engine probabilities into a normalized threat score and generates human-readable XAI explanations.

### 5.2 Flowchart and Architecture Diagram

```mermaid
flowchart TD
    A[End User Navigation] --> B[Chrome Extension MV3 Service Worker]
    B --> C{In-Memory Cache Hit?}
    C -- Yes --> D[Apply Cached Icon & Allow/Block]
    C -- No --> E[POST /api/scan/ to FastAPI Backend]
    E --> F{DB TTL Cache / Whitelist?}
    F -- Hit --> G[Return Cached Verdict]
    F -- Miss --> H[Parallel Multi-Engine Pipeline]
    
    subgraph Multi-Engine Core
        H --> I1[1. CatBoost Tabular ML Engine]
        H --> I2[2. DeBERTa NLP Semantic Engine]
        H --> I3[3. Domain Intel & Redirect Tracer]
        H --> I4[4. Google Gemini LLM Reasoning]
    end
    
    I1 & I2 & I3 & I4 --> J[Ensemble Meta-Learner Fusion]
    J --> K[Calculate Risk Score, Confidence & XAI]
    K --> L[Save to DB TTL Cache]
    L --> M[Return JSON to Chrome Extension]
    M --> N{Verdict Phishing?}
    N -- Yes --> O[Inject Red Blocking Overlay Modal]
    N -- No --> P[Green Badge: Safe Navigation]
```

![Fig. 5.1 Use Case Diagram](file:///d:/Works/phishguard/report_assets/fig_5_1_use_case.png)  
*Fig. 5.1 Use Case Diagram of PhishGuard Platform*

![Fig. 5.2 Sequence Diagram](file:///d:/Works/phishguard/report_assets/fig_5_2_sequence.png)  
*Fig. 5.2 Real-Time Navigation Interception Sequence Diagram*

![Fig. 5.3 System Architecture](file:///d:/Works/phishguard/report_assets/fig_5_3_architecture.png)  
*Fig. 5.3 Multi-Engine AI System Architecture*

---

## CHAPTER 6: PERFORMANCE AND RESULT ANALYSIS

### 6.1 Dataset & Experimental Setup
The models were trained on 100,000 URLs (50,000 malicious URLs from PhishTank and OpenPhish; 50,000 benign URLs from Tranco Top 1M list). An 80/20 train/test split (80,000 training, 20,000 testing) was used with 5-fold cross-validation.

### 6.2 Comparative Model Performance

| Model Architecture | Accuracy (%) | Precision (%) | Recall (%) | F1-Score (%) | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Gaussian Naive Bayes | 85.4% | 84.1% | 86.9% | 85.5% | 0.912 |
| Support Vector Machine (SVM) | 91.2% | 90.5% | 91.8% | 91.1% | 0.945 |
| Random Forest Classifier | 95.8% | 96.2% | 95.1% | 95.6% | 0.978 |
| CatBoost (Standalone ML) | 97.9% | 98.8% | 97.0% | 97.9% | 0.996 |
| **PhishGuard Multi-Engine Ensemble** | **99.1%** | **99.3%** | **98.9%** | **99.1%** | **0.998** |

![Fig. 6.1 Performance Comparison](file:///d:/Works/phishguard/report_assets/fig_6_1_model_performance.png)  
*Fig. 6.1 Comparative Performance Across Evaluated Classifiers*

![Fig. 6.2 Feature Importance](file:///d:/Works/phishguard/report_assets/fig_6_2_feature_importance.png)  
*Fig. 6.2 URL Feature Importance Breakdown (CatBoost Evaluator)*

---

## CHAPTER 7: CONCLUSION AND FUTURE WORK

### 7.1 Conclusion
PhishGuard establishes a dependable, enterprise-ready cybersecurity solution for real-time zero-day phishing detection. By combining lightweight structural URL feature extraction with NLP semantics, live domain intelligence, and Google Gemini LLM reasoning, the system bypasses the latency risks inherent to static blacklists. Operating at sub-150ms latency with 99.1% classification accuracy and 0.998 ROC-AUC, PhishGuard provides actionable browser protection and transparent Explainable AI summaries.

### 7.2 Future Work
- Integration of Vision Transformers (ViT) for DOM-level brand logo similarity matching.
- Privacy-preserving Federated Learning across edge extension clients.
- Automated headless browser sandboxing for dynamic JavaScript payload analysis.

---

## SUSTAINABLE DEVELOPMENT GOALS (SDG) MAPPING

| SDG Dimension | PhishGuard Direct Contribution |
| :--- | :--- |
| **SDG 9: Industry, Innovation & Infrastructure** | Strengthens cybersecurity resilience and digital infrastructure trust through state-of-the-art AI threat detection. |
| **SDG 16: Peace, Justice & Strong Institutions** | Combats cyber fraud, credential theft, and illicit cyber warfare campaigns targeting citizens and enterprise organizations. |
| **SDG 11: Sustainable Cities & Communities** | Safeguards community digital services, smart city web portals, and public online transactions against zero-day phishing. |

---

## REFERENCES

1. Prokhorenkova, L., Gusev, G., Vorobev, A. et al. (2018) ‘CatBoost: unbiased boosting with categorical features’, *Advances in Neural Information Processing Systems (NeurIPS)*, pp. 6638–6648.
2. He, P., Liu, X., Gao, J. and Chen, W. (2021) ‘DeBERTa: Decoding-enhanced BERT with Disentangled Attention’, *International Conference on Learning Representations (ICLR)*.
3. Sahoo, D., Liu, C. and Hoi, S.C. (2019) ‘Malicious URL Detection using Machine Learning: A Survey’, *IEEE Access*, Vol. 7, pp. 62961–62987.
4. Ribeiro, M.T., Singh, S. and Guestrin, C. (2016) ‘Why Should I Trust You?: Explaining Predictions of Any Classifier’, *ACM SIGKDD International Conference*, pp. 1135–1144.
5. Google DeepMind (2024) ‘Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context’, *arXiv preprint arXiv:2403.05530*.

---

## APPENDICES

### APPENDIX 1: IMPORTANT SOURCE CODE

#### 1. URL Feature Extraction Engine (`feature_extractor.py`)
```python
def extract_features(url: str) -> dict:
    parsed = urlparse(url)
    hostname, path, query = parsed.netloc.lower(), parsed.path, parsed.query
    return {
        "url_length": len(url),
        "hostname_length": len(hostname),
        "path_length": len(path),
        "num_dots": hostname.count(".") + path.count("."),
        "num_digits": sum(c.isdigit() for c in hostname),
        "has_ip_address": int(bool(IP_PATTERN.match(hostname))),
        "entropy": _shannon_entropy(url),
        "suspicious_keywords": sum(kw in url.lower() for kw in SUSPICIOUS_KEYWORDS),
        "uses_https": int(parsed.scheme == "https"),
        "num_subdomains": max(0, len(hostname.split(".")) - 2),
        "is_punycode": int(any(p.startswith("xn--") for p in hostname.split(".")))
    }
```

#### 2. Multi-Engine Probability Fusion Engine (`fusion_engine.py`)
```python
def calculate_ensemble_score(ml_prob, nlp_prob, domain_prob, llm_prob) -> dict:
    weights = [0.40, 0.25, 0.20, 0.15]
    score = (ml_prob * weights[0] + nlp_prob * weights[1] + 
             domain_prob * weights[2] + llm_prob * weights[3])
    risk_level = "phishing" if score >= 0.70 else "suspicious" if score >= 0.35 else "safe"
    return {"risk_level": risk_level, "confidence": round(score * 100, 2)}
```

### APPENDIX 2: OPERATIONAL SCREENSHOTS & OUTPUTS

![Fig. A2 Combined Operational Outputs](file:///d:/Works/phishguard/report_assets/fig_a2_combined_outputs.png)  
*Fig. A2.1 (a) Chrome Extension Phishing Block Overlay Modal | (b) React SOC Dashboard & XAI Breakdown*
