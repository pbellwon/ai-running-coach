# Domain Model

The entire PaceMind system is built around a small number of core domain objects.

Each object has a single responsibility and represents a real-world concept.

## Core Domain Objects

### Athlete

Represents the runner.

Contains personal information, physiology, goals, preferences, injury history, devices and Athlete DNA.

---

### Workout

Represents a single completed training session.

Contains raw data, calculated metrics and coach observations.

---

### Training Plan

Represents the current training block.

Contains planned workouts, training phases, objectives and progress.

---

### Recovery

Represents the athlete's recovery status.

Combines sleep, HRV, resting heart rate, subjective fatigue and recovery trends.

---

### Goal

Represents both short-term and long-term objectives.

Examples:

- Break 39:00 for 10 km
- Improve 5 km PB
- Stay injury free
- Complete current training block

---

### Athlete DNA

Represents everything the system has learned about the athlete.

Examples:

- responds well to threshold training
- struggles after sudden mileage increases
- recovers slowly after VO₂max sessions
- performs best with two quality workouts per week

This object evolves continuously as the system learns.