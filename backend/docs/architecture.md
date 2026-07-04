# PaceMind - Architecture

## Vision

PaceMind is an AI-powered running coach.

The system does not only analyse workouts.

It understands the athlete.

Its purpose is to combine:

- training history
- physiology
- recovery
- training plan
- subjective feedback
- coaching knowledge

into intelligent coaching recommendations.

---

# High Level Architecture

```text
          Garmin Connect
                 │
                 │
            Intervals.icu
                 │
                 │
           Google Sheets
                 │
                 ▼
        ---------------------
        | Import Layer      |
        ---------------------
                 │
                 ▼
        ---------------------
        | Domain Models     |
        ---------------------
                 │
                 ▼
        ---------------------
        | Metrics Engine    |
        ---------------------
                 │
                 ▼
        ---------------------
        | Coach Engine      |
        ---------------------
                 │
                 ▼
        ---------------------
        | AI Assistant      |
        ---------------------
                 │
                 ▼
           User Feedback
```

## Coaching Philosophy

PaceMind is not just a training log or an AI chatbot.

Its purpose is to become an evidence-based running coach that combines sports science, proven coaching methodologies, objective training data, and the athlete's personal experience into clear and actionable recommendations.

The system should:

- Base every recommendation on objective data whenever possible.
- Learn from multiple coaching philosophies rather than following a single methodology.
- Adapt recommendations to the individual athlete instead of applying generic training rules.
- Continuously learn how the athlete responds to different types of training.
- Consider both objective metrics and subjective feedback before making decisions.
- Explain every recommendation with clear reasoning and supporting evidence.
- Prioritize long-term development over short-term performance.
- Reduce injury risk by recognizing fatigue patterns and recurring problems.
- Help the athlete become a smarter and more independent runner over time.

The AI is not responsible for calculating training metrics or making raw performance analyses.

Instead, dedicated analytical modules perform calculations, while the AI acts as an experienced coach that interprets the results, explains them in natural language, answers questions, and supports decision-making.

The ultimate goal of PaceMind is to provide coaching that is personalized, transparent, evidence-based, and continuously improving as it learns more about the athlete.