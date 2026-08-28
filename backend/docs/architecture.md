# PaceMind - Architecture

## Vision

PaceMind is an AI-powered running coach.

The system does not only analyse workouts.

It understands the athlete.

Its purpose is to combine:

* training history
* physiology
* recovery
* training plan
* subjective feedback
* coaching knowledge

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

---

# Coaching Philosophy

PaceMind is not just a training log or an AI chatbot.

Its purpose is to become an evidence-based running coach that combines sports science, proven coaching methodologies, objective training data, and the athlete's personal experience into clear and actionable recommendations.

The system should:

* Base every recommendation on objective data whenever possible.
* Learn from multiple coaching philosophies rather than following a single methodology.
* Adapt recommendations to the individual athlete instead of applying generic training rules.
* Continuously learn how the athlete responds to different types of training.
* Consider both objective metrics and subjective feedback before making decisions.
* Explain every recommendation with clear reasoning and supporting evidence.
* Prioritize long-term development over short-term performance.
* Reduce injury risk by recognizing fatigue patterns and recurring problems.
* Help the athlete become a smarter and more independent runner over time.

The AI is not responsible for calculating training metrics or making raw performance analyses.

Instead, dedicated analytical modules perform calculations, while the AI acts as an experienced coach that interprets the results, explains them in natural language, answers questions, and supports decision-making.

The ultimate goal of PaceMind is to provide coaching that is personalized, transparent, evidence-based, and continuously improving as it learns more about the athlete.

---

# Coaching Methodology

PaceMind does not follow a single named coaching system.

It may use principles found in established approaches such as Daniels, Lydiard, Pfitzinger, Canova, threshold-oriented models, polarized training, pyramidal training, and other evidence-supported endurance training frameworks.

However, no methodology is treated as universally correct or used as a fixed template.

PaceMind should select training strategies based on:

1. scientific evidence,
2. physiological training principles,
3. the athlete's goal,
4. the athlete's current limiters,
5. historical response to training,
6. current training phase,
7. recovery and recent workload,
8. subjective athlete feedback.

Named coaching methodologies are therefore sources of useful training concepts rather than rigid systems that PaceMind must reproduce.

---

## Training Principles Over Coaching Schools

PaceMind should reason primarily in terms of physiological and performance adaptations rather than named methodologies.

Important training dimensions include:

* aerobic capacity,
* aerobic endurance,
* threshold development,
* VO2max development,
* running economy,
* neuromuscular development,
* speed reserve,
* durability,
* fatigue resistance,
* race-specific endurance,
* recovery capacity,
* musculoskeletal robustness.

A workout should be selected because it addresses a specific training need, not because it belongs to a particular coaching system.

For example:

```text
Athlete limiter
      ↓
Required adaptation
      ↓
Training stimulus
      ↓
Workout structure
```

rather than:

```text
Coaching system
      ↓
Predefined workout
```

---

# Coaching Decision Hierarchy

PaceMind should use the following hierarchy when making coaching decisions:

```text
Scientific evidence
        ↓
Training principles
        ↓
Athlete goal
        ↓
Athlete limiter
        ↓
Historical individual response
        ↓
Current training phase
        ↓
Current recovery and workload
        ↓
Athlete subjective feedback
        ↓
Training recommendation
```

This hierarchy prevents the system from blindly applying generic rules or predefined training tables.

---

# Individual Response

When multiple training approaches are scientifically reasonable, PaceMind should prefer the strategy that appears to work best for the individual athlete.

The system should gradually learn:

* which workouts produce positive adaptation,
* which workloads are well tolerated,
* which workouts repeatedly create excessive fatigue,
* how quickly the athlete recovers from different stimuli,
* which training blocks historically produced performance improvements,
* which patterns preceded stagnation, illness, injury, or excessive fatigue,
* how the athlete responds to changes in volume, intensity, frequency, and workout structure.

Historical individual response should become increasingly important as PaceMind accumulates more athlete-specific data.

General sports-science knowledge provides the prior.

The athlete's own history progressively modifies that prior.

---

# Limiter-Driven Training

Training recommendations should primarily address the athlete's most important current limiter relative to the goal.

Possible limiters include:

* insufficient aerobic volume,
* poor threshold durability,
* insufficient VO2max stimulus,
* limited running economy,
* insufficient long-run development,
* weak fatigue resistance,
* poor race-specific endurance,
* insufficient speed reserve,
* inadequate recovery,
* excessive training monotony,
* insufficient strength or musculoskeletal robustness.

PaceMind should distinguish between:

```text
What the athlete is currently good at
```

and:

```text
What the athlete needs most in order to reach the goal
```

Training should not simply reinforce the athlete's strongest qualities.

---

# Minimum Effective Stimulus

PaceMind should prefer the minimum effective training stimulus that is likely to produce the required adaptation.

More training is not automatically better.

Additional intensity, volume, or complexity should be introduced only when there is a clear reason to expect additional benefit.

The system should avoid increasing training load simply because the athlete successfully completed the previous workout.

Progression should be justified by adaptation needs and supported by recovery and training history.

---

# Progressive Specificity

Training should become progressively more specific as the athlete approaches the target event.

Earlier phases may prioritize general development such as:

* aerobic volume,
* aerobic durability,
* general threshold capacity,
* strength,
* running economy.

Later phases may increasingly emphasize:

* race-specific pace,
* race-specific duration,
* fatigue resistance at target intensity,
* event-specific workout structures.

Specificity should increase without unnecessarily abandoning previously developed capabilities.

---

# Intensity Distribution

PaceMind should not assume that one fixed intensity distribution is optimal for every athlete or every training phase.

It should not automatically enforce models such as:

* 80/20,
* polarized training,
* pyramidal training,
* threshold-heavy training.

Instead, intensity distribution should emerge from:

* athlete level,
* training history,
* event distance,
* current training phase,
* number of available training days,
* recovery capacity,
* response to previous training.

The system should evaluate intensity distribution as a consequence of the training strategy rather than as an isolated target.

---

# Workout Intent

Every meaningful training session should have an explicit purpose.

Examples include:

* aerobic development,
* recovery,
* threshold development,
* VO2max development,
* running economy,
* neuromuscular stimulus,
* long-run durability,
* race-specific endurance,
* strength development.

PaceMind should evaluate completed training against the intended adaptation rather than judging workouts only by pace, heart rate, or distance.

A workout may have more than one relevant dimension.

For example:

```text
workout_type = tempo_run
session_role = long_run
```

This represents a long run containing a substantial quality component.

Workout intensity and structural role should therefore remain separate concepts throughout the architecture.

---

# Short-Term and Long-Term Reasoning

PaceMind should reason on multiple time scales.

## Short-Term Context

Days to several weeks.

Used to understand:

* recent workload,
* fatigue,
* recovery,
* workout sequencing,
* immediate readiness,
* whether the next planned stimulus is appropriate.

## Medium-Term Context

Several weeks to several months.

Used to understand:

* training block progression,
* volume trends,
* intensity distribution,
* consistency,
* development of key capabilities.

## Long-Term Context

Months to years.

Used to understand:

* recurring performance limiters,
* historical response to different training approaches,
* successful and unsuccessful training blocks,
* durability trends,
* injury or fatigue patterns,
* long-term athlete development.

Short-term information determines what the athlete can reasonably do now.

Long-term information helps determine what the athlete most needs to develop.

---

# Trend Over Single Data Points

PaceMind should avoid changing training strategy because of isolated measurements.

Examples include:

* one poor workout,
* one unusually low HRV reading,
* one night of poor sleep,
* one elevated resting heart rate,
* one unusually strong workout.

Single observations may affect immediate decisions, but meaningful changes to the training plan should normally require a consistent pattern or multiple supporting signals.

The system should distinguish between:

```text
temporary noise
```

and:

```text
meaningful trend
```

---

# Recovery-Aware Coaching

Recovery should influence training decisions but should not mechanically dictate them.

Metrics such as:

* HRV,
* resting heart rate,
* sleep duration,
* sleep quality,
* recent training load,

should be interpreted together with:

* recent workout execution,
* training phase,
* subjective fatigue,
* athlete feedback,
* historical response.

No single recovery metric should automatically cancel or modify a workout unless the signal is exceptionally strong or supported by additional evidence.

---

# Athlete Feedback

Subjective feedback is a first-class coaching signal.

PaceMind should progressively learn from information such as:

* perceived effort,
* muscle soreness,
* general fatigue,
* motivation,
* sleep quality,
* pain or discomfort,
* whether a workout felt easier or harder than expected,
* perceived ability to continue the workout.

Objective data and subjective feedback should be interpreted together rather than treated as competing sources of truth.

---

# Workout Execution Review

Completed workouts should eventually be evaluated relative to their intended purpose.

A workout may be classified as:

```text
too_easy
on_target
too_hard
```

The assessment should consider, where applicable:

* planned versus completed structure,
* pace,
* heart rate,
* duration,
* distance,
* interval consistency,
* pacing,
* recovery between repetitions,
* overall training load,
* subjective athlete feedback.

The purpose is not merely to score compliance.

The system should determine whether the workout delivered the intended training stimulus.

---

# Adaptive Planning

PaceMind may recommend changes to future training when evidence indicates that the current plan should be adjusted.

Possible adjustments include:

* changing workout intensity,
* changing workout volume,
* modifying interval structure,
* replacing a workout,
* increasing or decreasing easy volume,
* modifying long-run progression,
* changing workout sequencing,
* adding recovery.

However, PaceMind must never autonomously modify the athlete's training plan.

The workflow must always be:

```text
PaceMind identifies a potential adjustment
                ↓
PaceMind proposes the change
                ↓
PaceMind explains the reasoning
                ↓
Athlete accepts / rejects / modifies
                ↓
Accepted change may be written to Google Sheets
```

The athlete always retains final authority over the training plan.

---

# Explainability

Every significant PaceMind recommendation should be explainable.

The explanation should answer:

1. What did PaceMind observe?
2. Why does it matter?
3. Which training principle is relevant?
4. What action is recommended?
5. How confident is the system?
6. What evidence could change the recommendation?

The system should avoid unexplained outputs such as:

```text
Reduce today's workout by 20%.
```

Instead it should produce reasoning conceptually similar to:

```text
Your last seven days contain two quality sessions and a long run,
while recovery indicators have been below baseline for three days.

Today's threshold workout would add another high-load stimulus.

Reducing the threshold volume while preserving some quality work
maintains the intended adaptation with lower recovery cost.
```

---

# Role of Deterministic Engines and AI

PaceMind should separate calculation from interpretation.

Dedicated deterministic modules should calculate and classify:

* workout metrics,
* training load,
* recovery metrics,
* training context,
* workout structure,
* goal progress,
* plan versus execution,
* trends,
* capability estimates.

The AI layer should not invent these calculations.

Instead, the AI should:

* interpret structured outputs,
* combine multiple signals,
* explain conclusions,
* communicate uncertainty,
* answer athlete questions,
* provide coaching context,
* generate understandable recommendations.

Conceptually:

```text
Raw Data
   ↓
Deterministic Analysis
   ↓
Structured Coaching Context
   ↓
AI Interpretation
   ↓
Athlete
```

This separation improves:

* reliability,
* testability,
* explainability,
* reproducibility,
* safety.

---

# Evidence and Uncertainty

PaceMind should distinguish between:

* strong evidence,
* moderate evidence,
* weak evidence,
* insufficient information.

Recommendations should reflect confidence.

The system should not present uncertain conclusions as facts.

When data is insufficient, PaceMind should explicitly acknowledge uncertainty rather than manufacture precision.

Over time, confidence may increase as more athlete-specific evidence becomes available.

---

# Long-Term Objective

The ultimate objective of PaceMind is not simply to generate workouts.

It is to develop an increasingly accurate model of the athlete.

Over time, PaceMind should understand:

```text
What training the athlete needs
             +
What training the athlete tolerates
             +
What training historically works
             +
What the athlete can recover from now
             +
What is required by the target event
```

and convert that understanding into transparent and actionable coaching decisions.

PaceMind should therefore evolve from:

```text
training analysis
```

toward:

```text
individual athlete model
        ↓
coaching reasoning
        ↓
adaptive recommendations
        ↓
feedback
        ↓
better athlete model
```

The system should become more personalized as the athlete uses it, while remaining grounded in sports science and retaining clear human oversight.
