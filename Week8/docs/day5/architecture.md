# System architecture

```mermaid
flowchart LR
    Listings[Property listings] --> Clean[Cleaning and feature pipelines]
    CRM[Lead data<br/>synthetic until real outcomes are available] --> LeadPipeline[Lead feature pipeline]
    Clean --> Sale[Sale valuation model]
    Clean --> Rent[Rent valuation model]
    LeadPipeline --> Scorer[Lead scoring model]
    Sale --> API[FastAPI service]
    Rent --> API
    Scorer --> API
    API --> SHAP[TreeSHAP explanations]
    API --> Agent[LangGraph assistant and tools]
    API --> Web[Week 7 web dashboard]
    Voice[Week 7 voice agent] --> API
    API --> Audit[Prediction audit log]
    Train[Training and validation splits] --> Retrain[Candidate retraining]
    Retrain -->|validation improves| Models[Versioned model artifacts]
    Models --> Sale
    Models --> Rent
    Monitor[PSI and labeled MAPE monitoring] --> Retrain
    Clean --> Monitor
    API --> Health[Health and model-info endpoints]
```

The API is the shared serving boundary for the Week 7 web and voice clients, valuation and lead models, explanations, and assistant tools. Model candidates are evaluated on validation data before promotion; the locked test split is reserved for final evaluation. The configured Docker image packages the FastAPI service and model/data artifacts.

The Week 7 dashboard currently displays simulated Week 8 leads with an explicit source label. The lead model must not be treated as production-validated until it has been calibrated against quality-checked CRM outcomes.
