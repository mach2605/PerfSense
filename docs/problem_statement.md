# DISSERTATION PROPOSAL

# PerfSense: ML-Based Performance Regression Predictor for React Applications

**MTech in Software Engineering**  
**BITS Pilani - Work Integrated Learning Programme (WILP)**  
**Specialization: Full Stack Engineering**

January 2026

---

## Table of Contents

1. Problem Statement ..................................... 3
2. Research Question ...................................... 5
3. Proposed Solution: PerfSense ........................... 6
4. System Architecture .................................... 11
5. Novelty and Contributions .............................. 13
6. Implementation Timeline (4 Months) ..................... 15
7. Evaluation Methodology ................................. 22
8. Expected Outcomes ...................................... 25
9. Risk Mitigation ........................................ 28
10. Resource Requirements ................................. 30

---

## 1. PROBLEM STATEMENT

Modern web applications, particularly Single Page Applications (SPAs) built with React, face significant performance challenges that directly impact user experience, conversion rates, and business outcomes. Studies show that a 1-second delay in page load time can result in **7% reduction in conversions** and **11% fewer page views**.

### Current State of the Problem

Performance issues in React applications are typically discovered reactively - after deployment to production when users are already affected. Development teams rely on:

- Manual code reviews that may miss performance anti-patterns
- Post-deployment monitoring tools that alert only after problems occur
- Time-consuming manual debugging to identify root causes
- Trial-and-error approaches to optimization

This reactive approach leads to:

- Degraded user experience during the window between deployment and fix
- Increased debugging time (average 4-8 hours per performance incident)
- Wasted CI/CD resources on deployments that should have been caught earlier
- Lost revenue during performance degradation periods
- Developer frustration and reduced productivity

### Existing Limitations

Current performance monitoring tools (Lighthouse, New Relic, Datadog, Sentry) excel at:

✓ Collecting runtime metrics  
✓ Visualizing performance trends  
✓ Setting threshold-based alerts

However, they fail to:

✗ Predict performance regressions before code is deployed  
✗ Automatically correlate specific code changes to performance degradation  
✗ Learn from historical patterns to improve predictions over time  
✗ Provide actionable, code-specific optimization recommendations  
✗ Operate proactively in the development lifecycle

### The Gap

There is no comprehensive system that combines:

1. Predictive analysis of code changes before deployment
2. Machine learning-based pattern recognition from historical data
3. Automated correlation between code commits and performance metrics
4. Intelligent, context-aware optimization recommendations
5. Integration into the CI/CD pipeline for early detection

---

## 2. RESEARCH QUESTION

### Primary Research Question:

**"Can machine learning models accurately predict performance regressions in React applications by analyzing code changes and historical performance metrics before deployment?"**

### Sub-questions:

1. What code-level features are most predictive of performance regressions in React applications?
2. How accurately can ML models predict regressions compared to simple heuristic-based approaches?
3. What is the optimal balance between prediction accuracy and false positive rate for practical deployment?
4. How can such a system be integrated into existing development workflows with minimal friction?

---

## 3. PROPOSED SOLUTION: PerfSense

PerfSense is an intelligent performance management platform that shifts performance monitoring from reactive to proactive by predicting regressions before they reach production.

### Core Innovation

Instead of waiting for performance issues to manifest in production, PerfSense:

1. Analyzes every code commit using ML models trained on historical data
2. Extracts performance-relevant features from code changes
3. Predicts the likelihood of performance regression with confidence scores
4. Provides actionable insights about what might cause the regression
5. Integrates into CI/CD pipelines to alert developers before merge

### Key Components

#### A. Monitoring SDK

- Lightweight JavaScript/TypeScript library (<50KB)
- Collects Core Web Vitals (LCP, FID, CLS)
- Tracks component-level render times
- Monitors bundle sizes and resource loading
- Minimal performance overhead (<1% impact)

#### B. Feature Extraction Pipeline

Automated analysis of code changes to extract:

**Static Code Features:**

- Bundle size delta (percentage change)
- Number of files changed in components directory
- Dependency changes (packages added/removed/updated)
- Code complexity metrics (cyclomatic complexity delta)
- TypeScript/JavaScript syntax patterns

**Performance-Critical Pattern Detection:**

- New useEffect hooks introduced
- New Context providers added
- Large component additions (>200 lines)
- Import statement changes (lazy loading modifications)
- Missing memoization opportunities
- Nested component definitions
- Heavy computations in render methods

**Historical Context Features:**

- Previous commit performance metrics
- 7-day performance trend
- Time since last regression
- Deployment frequency
- Project-specific patterns

#### C. Machine Learning Model

**Primary Model: Gradient Boosting (XGBoost/LightGBM)**

- Input: 20-30 extracted features per commit
- Output: Binary classification (regression: yes/no) + confidence score
- Training data: 500-1000 labeled commits from open-source React projects
- Target accuracy: >75%
- Target precision: >70% (minimize false positives)

**Model Training Strategy:**

- Feature engineering from code diffs and historical metrics
- Handle class imbalance (regressions are rare events)
- Cross-validation across different repositories
- Chronological train-test split to prevent data leakage

**Baseline Comparison:**

- Simple heuristic rules (e.g., "flag if bundle size increases >10%")
- Logistic regression with basic features
- Random forest for feature importance analysis

#### D. Backend API Service

RESTful API (Node.js/Express or Python/FastAPI):

- POST /api/metrics - Receive real-time performance data
- POST /api/analyze - Trigger analysis on new commit
- GET /api/predictions/:commitId - Retrieve regression prediction
- GET /api/history/:projectId - Access historical metrics

**Database (PostgreSQL):**

- Projects, commits, performance metrics (time-series)
- Labeled regressions for continuous learning
- Feature vectors for each analyzed commit

**GitHub Integration:**

- Webhook listener for new commits/pull requests
- Automatic feature extraction on push
- Status check API for PR integration

#### E. ML Inference Service

Python-based microservice that:

- Loads trained model for real-time predictions
- Accepts commit features from backend
- Returns structured prediction response:

```json
{
  "regression_probability": 0.78,
  "risk_level": "high",
  "contributing_factors": [
    "Bundle size increased by 23%",
    "3 new useEffect hooks without dependencies",
    "Large component added: UserDashboard.tsx (450 lines)"
  ],
  "recommendation": "Review performance impact before merging"
}
```

#### F. Dashboard (React + TypeScript)

Web-based interface providing:

**Commit Analysis View:**

- Prediction results for specific commits
- Visualized extracted features
- Historical performance comparison charts
- Risk indicators and confidence scores

**Project Overview:**

- Recent commits with prediction status
- Performance trend graphs
- Regression history timeline

**Real-time Monitoring:**

- Live performance metrics from deployed applications
- Core Web Vitals tracking
- Alert notifications

**Integration View:**

- GitHub PR status checks
- CI/CD pipeline integration status
- Webhook configuration

---

## 4. SYSTEM ARCHITECTURE

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 React Applications                       │
│               (with PerfSense SDK)                       │
└───────────────────┬─────────────────────────────────────┘
                    │ Performance Metrics
                    ▼
┌─────────────────────────────────────────────────────────┐
│           Backend API Service (Node.js)                  │
│  - Metrics Ingestion  - User Mgmt  - Analytics          │
└──────┬─────────────────────────┬────────────────────────┘
       │                         │
       │ Store           ┌───────┴──────┐ New Commits
       ▼                 │   GitHub     │
┌──────────────┐        │   Webhook    │
│  PostgreSQL  │        └───────┬──────┘
│  - Commits   │                │
│  - Metrics   │                │ Trigger Analysis
│  - Features  │                ▼
└──────────────┘      ┌──────────────────────┐
                      │  Feature Extraction  │
                      │      Pipeline        │
                      └──────────┬───────────┘
                                 │ Features
                                 ▼
                      ┌──────────────────────┐
                      │   ML Inference       │
                      │     Service          │
                      │   (Python/FastAPI)   │
                      └──────────┬───────────┘
                                 │ Predictions
                                 ▼
                      ┌──────────────────────┐
                      │   Web Dashboard      │
                      │  (React + TypeScript)│
                      └──────────────────────┘
```

### Technology Stack

**Frontend:**

- React 18+ with TypeScript
- Recharts for data visualization
- TailwindCSS for styling
- Vite for build tooling

**Backend:**

- Node.js with Express (or Python FastAPI)
- PostgreSQL for structured data
- REST API architecture
- GitHub Webhooks

**ML/AI:**

- Python 3.9+
- scikit-learn for preprocessing
- XGBoost/LightGBM for prediction model
- pandas for data manipulation
- TypeScript Compiler API for AST parsing

**DevOps:**

- Docker for containerization
- GitHub Actions for CI/CD
- Cloud deployment (AWS/Azure/GCP)
- Git version control

---

## 5. NOVELTY AND CONTRIBUTIONS

### Academic Novelty

**1. Predictive Pre-Deployment Analysis**

**Novel aspect:** Predicting performance regressions from code changes before deployment, rather than reactive monitoring post-deployment.

**Contribution:** Demonstrates that static code analysis combined with historical performance data can accurately predict runtime behavior.

**2. Automated Code-to-Runtime Correlation**

**Novel aspect:** Automatically linking specific code changes to performance degradation with high accuracy.

**Contribution:** Graph-based modeling of component dependencies correlated with runtime metrics.

**3. Context-Aware Feature Engineering**

**Novel aspect:** React-specific feature extraction that considers framework semantics (hooks, context, memoization patterns).

**Contribution:** Domain-specific features that outperform generic code metrics.

**4. Integrated Proactive System**

**Novel aspect:** End-to-end platform combining monitoring, prediction, and developer workflow integration.

**Contribution:** Proof that ML-based performance prediction can be practically integrated into real development processes.

### Practical Contributions

**Industry Impact:**

- Reduces time to detect performance issues from days/hours to minutes
- Prevents regression-caused revenue loss
- Improves developer productivity by catching issues early
- Provides data-driven optimization guidance

**Open Source:**

- Reusable SDK for React performance monitoring
- Open dataset of labeled performance regressions
- Feature extraction tools for static code analysis

**Knowledge Base:**

- Empirical evidence of which code patterns predict regressions
- Best practices for performance-aware development
- Benchmark comparisons for ML approaches in this domain

---

## 6. IMPLEMENTATION TIMELINE (4 MONTHS)

### MONTH 1: Foundation & Data Preparation

#### Week 1-2: Literature Review & Problem Formulation

**Tasks:**

- Study existing performance monitoring tools (Lighthouse, New Relic, Datadog)
- Review ML applications in software engineering
- Survey React performance optimization techniques
- Define evaluation metrics and success criteria

**Deliverables:**

- Comprehensive literature review (15-20 pages)
- Refined problem statement
- Evaluation framework

#### Week 3-4: Data Collection & Dataset Construction

**Tasks:**

- Select 8-10 popular open-source React repositories
  - Candidates: React Admin, Ant Design Pro, Grafana UI, Strapi Admin, Metabase frontend, Discourse frontend, Joplin, Sourcegraph web app
- Extract git commit history (last 1-2 years)
- Run Lighthouse CI on historical commits
- Label regression commits (performance degradation >20%)
- Structure dataset with features and labels
- Target: 500-1000 labeled commits

**Deliverables:**

- Curated dataset with labeled regressions
- Data collection scripts and documentation
- Initial exploratory data analysis

---

### MONTH 2: Feature Engineering & Model Development

#### Week 1-2: Feature Extraction Pipeline

**Tasks:**

- Implement TypeScript AST parser for code analysis
- Extract static code features (bundle size, complexity, patterns)
- Detect React-specific patterns (hooks, memoization, lazy loading)
- Build historical context features
- Automate feature extraction for any commit

**Tools:**

- TypeScript Compiler API
- git diff analysis
- Lighthouse CI integration
- Python for data processing

**Deliverables:**

- Automated feature extraction pipeline
- Feature documentation (20-30 features)
- Feature importance preliminary analysis

#### Week 3-4: ML Model Development & Training

**Tasks:**

- Implement baseline model (Logistic Regression)
- Develop primary model (XGBoost/LightGBM)
- Handle class imbalance (SMOTE, class weights)
- Hyperparameter tuning with cross-validation
- Feature selection and engineering iterations
- Model evaluation and comparison

**Evaluation Metrics:**

- Accuracy, Precision, Recall, F1-Score
- ROC-AUC curve
- Confusion matrix analysis
- Cross-repository validation

**Target Performance:**

- Accuracy: >75%
- Precision: >70% (minimize false positives)
- Recall: >60%

**Deliverables:**

- Trained ML models (saved artifacts)
- Model evaluation report
- Feature importance analysis

---

### MONTH 3: System Implementation

#### Week 1: Monitoring SDK Development

**Tasks:**

- Build React/TypeScript SDK for performance tracking
- Implement Web Vitals collection (LCP, FID, CLS)
- Add bundle size tracking
- Create lightweight data transmission layer
- Optimize for minimal overhead (<50KB, <1% performance impact)

**Features:**

- Easy integration (single import)
- Configurable metrics collection
- Automatic batching and transmission
- Error handling and fallbacks

**Deliverables:**

- NPM-ready SDK package
- Integration documentation
- Performance overhead benchmarks

#### Week 2: Backend API Development

**Tasks:**

- Build REST API (Node.js/Express or FastAPI)
- Implement endpoints for metrics, analysis, predictions
- Set up PostgreSQL database schema
- Create GitHub webhook integration
- Implement authentication and project management

**Database Schema:**

- projects (id, name, github_url, config)
- commits (id, hash, project_id, timestamp, features, prediction)
- metrics (id, commit_id, metric_type, value, timestamp)
- regressions (id, commit_id, severity, detected_at)

**Deliverables:**

- Functioning REST API
- Database with migrations
- API documentation

#### Week 3: ML Inference Service

**Tasks:**

- Create Python microservice for model serving
- Load trained model and expose prediction endpoint
- Integrate with feature extraction pipeline
- Implement prediction result formatting
- Add logging and monitoring

**Response Format:**

```json
{
  "commit_id": "abc123",
  "regression_probability": 0.78,
  "risk_level": "high",
  "confidence": 0.85,
  "contributing_factors": [
    "Bundle size increased by 23%",
    "3 new useEffect hooks added"
  ],
  "recommendations": [
    "Review component rendering logic",
    "Consider code splitting"
  ]
}
```

**Deliverables:**

- ML inference service (containerized)
- Integration with backend API
- Prediction latency benchmarks (<2 seconds)

#### Week 4: Dashboard Development

**Tasks:**

- Build React dashboard with TypeScript
- Implement commit analysis view
- Create performance visualization charts
- Add project overview and history views
- Implement real-time metrics display
- Design responsive, intuitive UI

**Key Views:**

1. Project Overview: Recent commits, trends, alerts
2. Commit Analysis: Detailed prediction results, features, charts
3. History: Past predictions vs actual outcomes
4. Metrics: Real-time performance monitoring
5. Settings: Project configuration, integrations

**Technologies:**

- React 18 + TypeScript
- Recharts for charts
- TailwindCSS for styling
- React Query for data fetching

**Deliverables:**

- Fully functional web dashboard
- Responsive design for mobile/desktop
- User documentation

---

### MONTH 4: Evaluation & Documentation

#### Week 1: System Evaluation

**Tasks:**

- Test on held-out commits (20% of dataset)
- Conduct real-world case studies (2-3 demo applications)
- Measure prediction accuracy metrics
- Compare with baseline approaches
- Analyze false positives and negatives
- Benchmark system performance (latency, throughput)
- Conduct feature importance analysis

**Evaluation Components:**

**1. Quantitative Metrics:**

- Prediction accuracy, precision, recall, F1
- ROC-AUC curve
- Confusion matrix
- Comparison with baselines

**2. Case Studies:**

- Deploy SDK to demo applications
- Introduce deliberate performance regressions
- Validate system predictions
- Document successes and failures

**3. System Performance:**

- SDK overhead measurement
- Prediction latency
- API response times
- Database query performance

**Deliverables:**

- Comprehensive evaluation report
- Charts, tables, statistical analysis
- Case study documentation
- Performance benchmarks

#### Week 2: Refinements & Additional Experiments

**Tasks:**

- Fix critical bugs identified during evaluation
- Improve model accuracy if below target
- Enhance dashboard UX based on findings
- Run additional experiments (feature ablation, model variants)
- Implement any missing critical features

**Optional Enhancements:**

- Add basic optimization recommendations
- Improve error handling and logging
- Add export functionality for reports
- Polish documentation

**Deliverables:**

- Refined, production-quality system
- Final model with optimizations
- Updated documentation

#### Week 3-4: Dissertation Writing

**Document Structure (80-100 pages):**

**1. Introduction (8-10 pages)**

- Background and motivation
- Problem statement
- Research questions and objectives
- Contributions
- Dissertation organization

**2. Literature Review (15-20 pages)**

- Web application performance challenges
- React-specific performance issues
- Existing performance monitoring tools
- Machine learning in software engineering
- Performance prediction approaches
- Gap analysis

**3. System Design and Architecture (15-20 pages)**

- Overall architecture
- Component design
- Technology stack justification
- Feature engineering methodology
- ML model selection and design
- Database schema
- Integration strategies

**4. Implementation (12-15 pages)**

- Feature extraction pipeline implementation
- ML model training process
- SDK development
- Backend API implementation
- Dashboard development
- Integration and deployment
- Challenges and solutions

**5. Evaluation and Results (15-20 pages)**

- Experimental setup
- Dataset description
- Evaluation methodology
- Quantitative results
  - Model performance metrics
  - Comparison with baselines
  - Feature importance analysis
- Qualitative results
  - Case studies
  - User feedback (if available)
- System performance benchmarks
- Discussion of findings

**6. Discussion (8-10 pages)**

- Interpretation of results
- Implications for practice
- Comparison with related work
- Limitations and threats to validity
- Lessons learned

**7. Conclusion and Future Work (5-8 pages)**

- Summary of contributions
- Answers to research questions
- Future research directions
- Potential enhancements
- Broader impact

**8. References**

- Comprehensive bibliography (50-70 sources)

**9. Appendices**

- Code samples
- Additional charts and tables
- User study materials (if conducted)
- System screenshots
- API documentation

**Deliverables:**

- Complete dissertation manuscript
- Presentation slides for defense
- Demo video
- GitHub repository with code
- README and documentation

---

### Weekly Time Commitment

**15-20 hours/week (Total: 240-320 hours over 4 months)**

- **Months 1-3:** 70% implementation, 20% research, 10% documentation
- **Month 4:** 30% refinement, 70% writing

---

## 7. EVALUATION METHODOLOGY

### Research Validation Approach

**Primary Evaluation Questions:**

1. How accurately can the system predict performance regressions?
2. How does it compare to baseline heuristic approaches?
3. What features are most predictive of regressions?
4. Is the system practical for real-world development workflows?

### Quantitative Evaluation

#### A. Model Performance Metrics

**Dataset Split:**

- Training: 70% of commits (chronologically earlier)
- Validation: 10% (for hyperparameter tuning)
- Test: 20% (held-out for final evaluation)

**Metrics:**

- Accuracy: Overall correctness
- Precision: Of predicted regressions, how many were actual? Target: >70%
- Recall: Of actual regressions, how many were caught? Target: >60%
- F1-Score: Harmonic mean of precision and recall
- ROC-AUC: Overall discriminative ability
- Confusion Matrix: Detailed breakdown

**Cross-Validation:**

- K-fold cross-validation (k=5)
- Cross-repository validation (train on 7 repos, test on remaining)

#### B. Baseline Comparisons

Compare ML model against:

1. **Simple Heuristics:**
   - "Flag if bundle size increases >10%"
   - "Flag if >5 files changed in /components"
   - Combined heuristic rules

2. **Logistic Regression** with basic features

3. **Random Forest** (for comparison)

#### C. Feature Importance Analysis

- SHAP values for model interpretability
- Permutation importance
- Ablation study: remove feature groups, measure impact

#### D. System Performance Benchmarks

- SDK overhead: Memory usage, execution time, bundle size
- Prediction latency: Time from commit to prediction (<2 seconds target)
- API response times: 95th percentile latency
- Scalability: Commits processed per hour

### Qualitative Evaluation

#### A. Case Studies (2-3 Demo Applications)

**Methodology:**

1. Deploy SDK to real React applications
2. Introduce controlled performance regressions:
   - Add large unoptimized component
   - Remove memoization from expensive computation
   - Add synchronous blocking operation
   - Increase bundle size significantly
3. Measure system predictions vs actual impact
4. Document: True positives, false positives, false negatives

#### B. Error Analysis

- Manually analyze false positives: Why flagged incorrectly?
- Manually analyze false negatives: What regressions were missed?
- Identify patterns in errors
- Suggest improvements

#### C. Developer Feedback (Optional, if time permits)

- Integrate into 1-2 real projects
- Collect feedback on usefulness, accuracy, UX
- Survey: Would they use it? What's missing?

### Success Criteria

**Minimum Viable Success:**
✓ Prediction accuracy >70%
✓ Precision >65% (acceptable false positive rate)
✓ Better than all baseline approaches
✓ System functions end-to-end
✓ At least 1 successful case study

**Stretch Goals:**
✓ Prediction accuracy >80%
✓ Precision >75%
✓ Published open-source with community interest
✓ Accepted to academic workshop/conference

---

## 8. EXPECTED OUTCOMES

### Technical Deliverables

**1. PerfSense Platform**

- Monitoring SDK (npm package)
- Backend API (containerized microservices)
- ML inference service
- Web dashboard (deployed application)
- GitHub integration

**2. Machine Learning Model**

- Trained XGBoost/LightGBM model
- Feature extraction pipeline
- Model evaluation scripts
- Retraining pipeline for continuous learning

**3. Dataset**

- Curated dataset of 500-1000 labeled commits
- Open-source release for research community
- Data collection and labeling scripts

**4. Documentation**

- Complete API documentation
- SDK integration guide
- Developer documentation
- System architecture documentation
- User manual

**5. Source Code**

- Clean, well-documented codebase
- GitHub repository with CI/CD
- Docker compose for easy deployment
- Comprehensive README

### Academic Deliverables

**1. MTech Dissertation**

- 80-100 page comprehensive document
- Novel contributions clearly articulated
- Rigorous evaluation and discussion
- Publication-quality writing

**2. Research Contributions**

- Empirical evidence of ML effectiveness in performance prediction
- Analysis of predictive features for React applications
- Comparison of different modeling approaches
- Best practices for performance-aware development

**3. Potential Publications**

- Workshop paper at ASE, ICSE, or FSE
- Tool demonstration paper
- Dataset paper for MSR (Mining Software Repositories)
- Blog posts and technical articles

### Practical Impact

**For Developers:**

- Catch performance issues before production
- Reduce debugging time
- Learn performance best practices
- Data-driven optimization decisions

**For Organizations:**

- Prevent revenue loss from performance degradation
- Improve user experience metrics
- Reduce operational costs
- Faster time to market with confidence

**For Research Community:**

- Open dataset for future research
- Baseline for comparison
- Reusable tools and methodologies
- Insights into React performance patterns

### Knowledge Contributions

1. Which code patterns most predict regressions?
2. How accurate can pre-deployment prediction be?
3. What is the optimal feature set for this problem?
4. How do different ML approaches compare?
5. What are the practical challenges in deployment?

---

## 9. RISK MITIGATION

### Potential Risks and Mitigation Strategies

| Risk                                                                                       | Mitigation Strategy                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Insufficient Training Data**<br/>Can't find enough labeled performance regressions       | Use synthetic regressions (deliberately introduce performance issues), combine data from multiple repos, use data augmentation techniques, start with smaller dataset for proof of concept                                                  |
| **Low Model Accuracy**<br/>ML model doesn't achieve target accuracy (>70%)                 | Fall back to hybrid approach (rules + ML), increase feature engineering efforts, try ensemble methods, adjust success criteria based on practical usefulness, focus on high-confidence predictions only                                     |
| **Feature Extraction Complexity**<br/>Extracting meaningful features is too time-consuming | Start with simple features (bundle size, file counts), gradually add complex features, use existing tools (ESLint, TypeScript compiler API), precompute features and cache results, prioritize features by expected importance              |
| **GitHub API Rate Limits**<br/>Hitting rate limits while collecting data                   | Use personal access tokens (higher limits), cache all requests, spread data collection over time, use GraphQL API for efficiency, clone repos locally for analysis                                                                          |
| **Time Constraints**<br/>4 months is tight for full implementation                         | HARD DEADLINE: End of Month 3 Week 4 for code freeze, Month 4 is buffer for writing only, use existing libraries and tools (don't reinvent), MVP approach: core features first, parallel work where possible, weekly progress tracking      |
| **Technical Challenges**<br/>Unexpected implementation difficulties                        | Prototype critical components early (Week 1-2), use proven technologies (avoid experimental tools), have fallback approaches for each component, active community support (Stack Overflow, GitHub Discussions), mentor/advisor consultation |
| **Evaluation Challenges**<br/>Difficult to validate results convincingly                   | Multiple evaluation approaches (quantitative + qualitative), compare against established baselines, use standard metrics from literature, conduct ablation studies, document limitations honestly                                           |
| **Scope Creep**<br/>Adding too many features, losing focus                                 | Stick to defined scope religiously, "nice to have" features documented for future work, weekly scope review, focus on research contribution not product perfection                                                                          |

### Contingency Plans

**If Accuracy <70%:**

- Document why (feature quality? data quality? problem difficulty?)
- Still valuable contribution if system works end-to-end
- Focus on insights from failures
- Hybrid approach demonstration

**If Running Out of Time:**

- Prioritize: ML model > Backend > SDK > Dashboard
- Simplify dashboard (basic visualization acceptable)
- Use mock data for demonstration if needed
- Focus on core research contribution

**If Data Collection Fails:**

- Synthetic regression generation
- Single repo deep dive (quality over quantity)
- Use existing benchmark datasets
- Qualitative case studies become primary evaluation

---

## 10. RESOURCE REQUIREMENTS

### Hardware

**Development Machine:**

- Modern laptop/desktop (existing frontend dev machine sufficient)
- Minimum: 16GB RAM, quad-core processor
- Recommended: 32GB RAM for ML training

**Cloud Resources:**

- GitHub account (free tier sufficient)
- Cloud hosting for demo (AWS/Azure/GCP free tier initially)
- Database hosting (PostgreSQL - free tier available)
- CI/CD (GitHub Actions - free for public repos)

**Optional GPU:**

- For ML training: Google Colab (free) or Kaggle kernels
- Not strictly necessary for XGBoost on this scale

### Software (All Free/Open Source)

**Development Tools:**

- VS Code or WebStorm
- Node.js 18+
- Python 3.9+
- PostgreSQL 14+
- Git
- Docker Desktop
- Postman (API testing)

**Libraries & Frameworks:**

- React 18, TypeScript, TailwindCSS
- Express.js or FastAPI
- XGBoost/LightGBM, scikit-learn, pandas
- Recharts (visualization)
- TypeScript Compiler API

**Cloud Services (Free Tiers):**

- GitHub (version control, CI/CD, webhooks)
- AWS/Azure/GCP (hosting, database)
- Vercel/Netlify (dashboard deployment)

### Dataset Sources

**Open Source React Applications for Analysis:**

- React Admin, Ant Design Pro, Grafana UI
- Strapi Admin, Metabase frontend
- Discourse, Joplin, Sourcegraph web app
- All publicly available on GitHub with active development

### Estimated Costs

**Total: $0 - $50**

All development can be done with free tiers.

**Optional:**

- Paid cloud hosting for production deployment: $20-50 for 4 months
- GPU compute if Google Colab insufficient: $20-30

---

## SUMMARY

This dissertation proposes **PerfSense**, an intelligent ML-based platform for predicting performance regressions in React applications before they reach production. By combining static code analysis, historical performance metrics, and machine learning, PerfSense shifts performance management from reactive to proactive.

### Key Highlights:

• **Novel Contribution:** First comprehensive system combining pre-deployment prediction, ML-based analysis, and CI/CD integration for React performance

• **Practical Value:** Reduces debugging time, prevents production issues, improves developer productivity

• **Achievable Scope:** 4-month timeline with clear deliverables and milestones

• **Target Performance:** >75% accuracy, >70% precision in predicting regressions

• **Open Source:** All code, dataset, and tools will be publicly available for research community

The research addresses a critical gap in current performance monitoring tools by enabling predictive, ML-driven analysis integrated directly into the development workflow. With careful scoping and risk mitigation, this dissertation is both academically rigorous and practically achievable within the 4-month timeline.

### Expected Impact:

PerfSense has the potential to significantly improve how development teams manage web application performance, reducing the time and cost associated with performance issues while improving user experience. The research will contribute valuable insights to both academic and industry communities on ML applications in software engineering.

---

**MTech Software Engineering Dissertation Proposal**  
**BITS Pilani - Work Integrated Learning Programme**  
**January 2026**

---

## INSTRUCTIONS FOR MICROSOFT WORD:

1. **Copy all the text above** (Ctrl+A, then Ctrl+C)
2. **Paste into a new Word document** (Ctrl+V)
3. **Apply formatting** (Word will preserve most markdown formatting):
   - Use "Heading 1" style for # headings
   - Use "Heading 2" style for ## headings
   - Use "Heading 3" style for ### headings
   - Tables should format automatically
   - Apply bold to text between \*\* markers
4. **Adjust page layout:**
   - Set margins to 1 inch all around
   - Use 12pt font (Times New Roman or similar)
   - Set line spacing to 1.5 or double
5. **Add page numbers** at the bottom center
6. **Save as .docx**

The document is ready to use as your official dissertation proposal!
