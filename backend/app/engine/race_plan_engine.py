"""Deterministic calendar planning; no predicted race times or automatic acceptance."""
from collections import defaultdict
from datetime import date, timedelta
import math

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.engine.planned_workout_engine import PlannedWorkoutEngine
from app.services.coach_chat_service import ChatError

PLAN_COLUMNS = ExistingPlanImporter.REQUIRED_COLUMNS
MARKER = '\n\nObowiązujący trening po korekcie PaceMind:\n'
RACE_COLUMNS = {'date', 'name', 'distance_km', 'priority', 'target_time', 'notes'}


def number(value):
    try:
        result = float(str(value).replace(',', '.'))
        if not math.isfinite(result) or result < 0:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise ChatError(422, 'Dystanse i czasy w arkuszu muszą być nieujemnymi liczbami.')


def parse_calendar(snapshot):
    if not RACE_COLUMNS.issubset(snapshot['headers']):
        raise ChatError(422, 'race_calendar wymaga kolumn: date, name, distance_km, priority, target_time, notes.')
    events, seen = [], set()
    for index, row in enumerate(snapshot['rows'], 2):
        if not any(str(v).strip() for v in row.values()):
            continue
        try:
            day = date.fromisoformat(row.get('date', '').strip())
        except ValueError:
            raise ChatError(422, f'race_calendar, wiersz {index}: data musi mieć format YYYY-MM-DD.')
        priority = row.get('priority', '').strip().upper()
        name = row.get('name', '').strip()
        distance = number(row.get('distance_km', ''))
        if not name or len(name) > 200 or priority not in ('A', 'B', 'C') or not 0 < distance <= 100:
            raise ChatError(422, f'race_calendar, wiersz {index}: podaj nazwę, dystans 0–100 km i priorytet A/B/C.')
        if day in seen:
            raise ChatError(422, f'race_calendar: więcej niż jeden start w dniu {day}. Rozstrzygnij wybór startu.')
        seen.add(day)
        target = row.get('target_time', '').strip()
        if target:
            parts = target.split(':')
            if (len(parts) not in (2, 3) or not all(p.isdigit() for p in parts)
                    or any(int(p) >= 60 for p in parts[1:]) or sum(int(p) for p in parts) == 0):
                raise ChatError(422, f'race_calendar, wiersz {index}: target_time to MM:SS lub HH:MM:SS.')
        events.append({'date': day.isoformat(), 'name': name, 'distance_km': distance,
                       'priority': priority, 'target_time': target, 'notes': row.get('notes', '')})
    return sorted(events, key=lambda e: e['date'])


def recovery_days(event):
    distance = event['distance_km']
    return 10 if distance > 42.2 else 7 if distance > 21.1 else 4 if distance > 10 else 2


class RacePlanEngine:
    def build(self, snapshot, events, preferences, start, end, replace, protected_rows, today):
        if not PLAN_COLUMNS.issubset(snapshot['headers']):
            raise ChatError(422, 'plan_import nie ma wymaganych dotychczasowych kolumn.')
        if start <= today or end < start or (end - start).days > 365 or (start - today).days > 30:
            raise ChatError(422, 'Początek musi przypadać od jutra do 30 dni naprzód; zakres planu to maksymalnie 366 dni.')
        selected = [e for e in events if start.isoformat() <= e['date'] <= end.isoformat()]
        if not any(e['priority'] == 'A' for e in selected):
            raise ChatError(422, 'W wybranym okresie musi być przynajmniej jeden start główny A.')
        rows_by_date = defaultdict(list)
        for index, row in enumerate(snapshot['rows'], 2):
            if not any(str(v).strip() for v in row.values()):
                continue
            try:
                day = date.fromisoformat(row.get('date', ''))
            except ValueError:
                raise ChatError(422, f'plan_import, wiersz {index}: nieprawidłowa data.')
            rows_by_date[day].append((index, row))
        warnings, blockers = [], []
        dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        event_by_date = {date.fromisoformat(e['date']): e for e in events}
        # Every existing row with a correction remains protected, also if its notes were edited later.
        preserved = {}
        for day, entries in rows_by_date.items():
            if day < start or day > end:
                continue
            if (not replace or len(entries) > 1 or any(i in protected_rows or self._protected_description(r['description']) for i, r in entries)):
                preserved[day] = entries
        for day in dates:
            if day in event_by_date and day in preserved:
                event = event_by_date[day]
                total = sum(number(r['planned_distance_km'] or 0) for _, r in preserved[day])
                types = [self._type(r) for _, r in preserved[day]]
                if 'race' not in types or abs(total - event['distance_km']) > 0.2:
                    blockers.append(f'{day}: zachowany trening nie odpowiada startowi {event["name"]}. Skoryguj go osobno lub zezwól na przebudowę, jeżeli nie jest chroniony.')
        for previous, upcoming in zip(events, events[1:]):
            gap = (date.fromisoformat(upcoming['date']) - date.fromisoformat(previous['date'])).days
            if start.isoformat() <= upcoming['date'] <= end.isoformat() and gap <= recovery_days(previous):
                warnings.append(f"{upcoming['date']}: start {upcoming['name']} wypada w okresie regeneracji po {previous['name']}. Rozważ zmianę kalendarza przed akceptacją.")
        entries, weekly, generated_hard = [], [], []
        first_monday = start - timedelta(days=start.weekday())
        monday = first_monday
        while monday <= end:
            week_dates = [monday + timedelta(days=i) for i in range(7)]
            in_range = [d for d in week_dates if start <= d <= end]
            previous_a = [e for e in events if e['priority'] == 'A' and e['date'] < monday.isoformat()]
            cycle_start = max(start, date.fromisoformat(previous_a[-1]['date']) + timedelta(days=recovery_days(previous_a[-1]) + 1)) if previous_a else start
            cycle_monday = cycle_start - timedelta(days=cycle_start.weekday())
            week_number = max(0, (monday - cycle_monday).days // 7)
            main_race = next((e for e in events if e['priority'] == 'A' and e['date'] >= monday.isoformat()), None)
            days_to_main = (date.fromisoformat(main_race['date']) - monday).days if main_race else 999
            factor = min(1.3, 1.05 ** week_number)
            phase = 'Baza' if week_number < 2 else 'Specyfika startowa' if days_to_main <= 42 else 'Budowanie'
            if week_number % 4 == 3:
                factor *= 0.8
                phase = 'Tydzień lżejszy'
            for event in events:
                delta = (date.fromisoformat(event['date']) - monday).days
                if event['priority'] == 'A' and 0 <= delta <= 13:
                    factor = min(factor, 0.5 if delta <= 6 else 0.7)
                    phase = 'Taper przed startem A'
                elif event['priority'] == 'B' and 0 <= delta <= 6:
                    factor = min(factor, 0.8)
                    phase = 'Lżejszy tydzień startu B'
            # Prorate boundary weeks by available training slots, not calendar days.
            scheduled_slots = sum(d.weekday() in preferences['weekdays'] for d in in_range)
            slot_ratio = scheduled_slots / len(preferences['weekdays'])
            full_budget = preferences['weekly_distance_km'] * factor
            budget = full_budget * slot_ratio
            # Existing units outside the requested window also consume this week's budget.
            fixed_km, outside_km = 0, 0
            hard_dates = [d for d in generated_hard if abs((d - monday).days) <= 9]
            for d in week_dates:
                fixed = preserved.get(d, []) if d in in_range else rows_by_date.get(d, [])
                for _, row in fixed:
                    if d in in_range:
                        fixed_km += number(row['planned_distance_km'] or 0)
                    else:
                        outside_km += number(row['planned_distance_km'] or 0)
                    if self._type(row) not in ('easy_run', 'off', 'mobility'):
                        hard_dates.append(d)
            race_km = sum(e['distance_km'] for d, e in event_by_date.items() if d in in_range and d not in preserved)
            remaining = max(0, min(budget - fixed_km - race_km, full_budget - fixed_km - outside_km - race_km))
            candidates = [d for d in in_range if d not in preserved and d not in event_by_date
                          and d.weekday() in preferences['weekdays'] and not self._recovering(d, events)]
            race_dates = list(event_by_date)
            # Race sessions and preserved hard sessions count toward the same spacing rule.
            hard_dates += [d for d in race_dates if monday - timedelta(days=7) <= d <= monday + timedelta(days=13)]
            for d, old in rows_by_date.items():
                if d not in week_dates and monday - timedelta(days=3) <= d <= monday + timedelta(days=9):
                    if any(self._type(r) not in ('easy_run', 'off', 'mobility') for _, r in old):
                        hard_dates.append(d)
            long_day = next((d for d in candidates if d.weekday() == preferences['long_run_day']
                             and all(abs((d - r).days) >= 3 for r in hard_dates)), None)
            long_weight = 1.6 if main_race and main_race['distance_km'] > 10 else 1.4
            weights = {d: (long_weight if d == long_day and len(candidates) >= 3 else 1) for d in candidates}
            weight_total = sum(weights.values()) or 1
            generated_km = 0
            for day in in_range:
                if day in preserved:
                    for row_no, row in preserved[day]:
                        entries.append({'row': row_no, 'action': 'keep', 'before': row, 'after': row, 'phase': 'Zachowany trening'})
                    continue
                reason = phase
                if day in event_by_date:
                    event = event_by_date[day]
                    title, km, duration = f'Zawody: {event["name"]}', event['distance_km'], ''
                    prescription = f'Start {event["priority"]}: {event["name"]}, dystans {km:g} km.'
                    if event['target_time']:
                        prescription += f' Cel zawodnika: {event["target_time"]}; to cel, nie prognoza.'
                    if event['notes']:
                        prescription += f' Uwagi do startu: {event["notes"]}'
                    reason = f'Kalendarz startów, priorytet {event["priority"]}'
                    if day.weekday() not in preferences['weekdays']:
                        warnings.append(f'{day}: start wypada poza wybranymi dniami treningowymi; start jest jawnym wyjątkiem.')
                elif day not in candidates or remaining <= 0:
                    title, km, duration = 'Odpoczynek', 0, 0
                    prescription = 'Odpoczynek. Dzień bez treningu biegowego.'
                    if self._recovering(day, events):
                        reason = 'Regeneracja po starcie'
                else:
                    max_minutes = preferences['max_minutes'][str(day.weekday())]
                    km = math.floor(min(remaining * weights[day] / weight_total,
                                        max_minutes / preferences['easy_pace_min_km']) * 10) / 10
                    duration = round(km * preferences['easy_pace_min_km'])
                    if duration < 15:
                        title, km, duration = 'Odpoczynek', 0, 0
                        prescription = 'Odpoczynek. Budżet tygodnia lub limit czasu nie pozwala na spokojną jednostkę co najmniej 15 min.'
                    else:
                        title = 'Spokojny bieg'
                        prescription = f'Spokojny bieg {km:g} km, około {duration} min, swobodna rozmowa, bez szybkiego finiszu.'
                        # Specificity changes the work duration, never invents a pace from a target time.
                        quality_allowed = (len(preferences['weekdays']) >= 3 and duration >= 35 and week_number >= 2
                                           and 'Taper' not in phase and all(abs((day - h).days) >= 3 for h in hard_dates)
                                           and all(not 0 <= (r - day).days < 7 for r in race_dates)
                                           and len([h for h in hard_dates if h in week_dates]) == 0
                                           and day != long_day
                                           and (long_day is None or abs((day - long_day).days) >= 3))
                        if quality_allowed:
                            title = 'Bieg progowy kontrolowany'
                            repetitions = 2 if main_race and main_race['distance_km'] > 10 else 3
                            rest = 2 * (repetitions - 1)
                            work_min = 3 if phase != 'Specyfika startowa' else min(10 if repetitions == 2 else 6, (duration - 18 - rest) // repetitions)
                            cool = duration - 10 - repetitions * work_min - rest
                            prescription = f'10 min spokojnej rozgrzewki; {repetitions} x {work_min} min threshold / kontrolowany próg, 2 min truchtu między odcinkami; {cool} min spokojnego schłodzenia. Łącznie około {duration} min / {km:g} km. Bez narzuconego tempa startowego.'
                            hard_dates.append(day)
                            generated_hard.append(day)
                        elif day == long_day and len(candidates) >= 3:
                            title = 'Długi spokojny bieg'
                            generated_hard.append(day)
                            prescription = f'Długi spokojny bieg {km:g} km, około {duration} min. Równa, konwersacyjna intensywność.'
                generated_km += km
                old_entries = rows_by_date.get(day, [])
                row_no, before = old_entries[0] if old_entries else (None, None)
                after = dict(before) if before else {h: '' for h in snapshot['headers']}
                note = f'PaceMind {today.isoformat()} | Zmiana: plan pod kalendarz startów, trening {day.isoformat()}. Uzasadnienie: {reason}.'
                description = ((before['description'] + MARKER) if before else '') + prescription + '\n' + note
                if len(description) > 50000:
                    raise ChatError(422, f'{day}: opis wraz z zachowaną historią przekracza limit komórki Google Sheets. Skróć go ręcznie po zabezpieczeniu oryginału.')
                after.update(date=day.isoformat(), title=title, description=description,
                             planned_distance_km=f'{km:g}', planned_duration_min=str(duration),
                             priority=(before['priority'] if before else ('key' if day in event_by_date else 'normal')))
                entries.append({'row': row_no, 'action': 'replace' if before else 'add', 'before': before,
                                'after': after, 'phase': reason})
            total = round(fixed_km + generated_km, 1)
            weekly.append({'week_start': monday.isoformat(), 'phase': phase, 'budget_km': round(budget, 1), 'planned_km': total,
                           'focus': f"{main_race['name']} ({main_race['distance_km']:g} km)" if main_race else 'Regeneracja po ostatnim starcie A'})
            if total < budget * 0.8 and candidates:
                warnings.append(f'Tydzień {monday}: limity dni i czasu ograniczyły objętość do {total:g} km (budżet {budget:.1f} km).')
            if total > budget + 0.5:
                warnings.append(f'Tydzień {monday}: starty lub zachowane jednostki przekraczają budżet ({total:g} / {budget:.1f} km). Nie zwiększono pozostałych treningów.')
            monday += timedelta(days=7)
        for day, old in preserved.items():
            if self._recovering(day, events) and any(number(r['planned_distance_km'] or 0) > 0 for _, r in old):
                warnings.append(f'{day}: zachowany trening wypada w okresie regeneracji po starcie. Oceń go przed akceptacją planu.')
        if preserved:
            warnings.append(f'Zachowano treningi w {len(preserved)} dniach. Ręcznie zachowane jednostki mogą ograniczać taper i regenerację; są widoczne w podglądzie.')
        return {'entries': entries, 'weeks': weekly, 'warnings': warnings, 'blockers': blockers,
                'races': selected, 'can_accept': not blockers}

    @staticmethod
    def _protected_description(description):
        # Rebuilding a generated plan must remain possible; a later single-workout
        # correction has a different final audit note and becomes protected again.
        return MARKER in description and 'Zmiana: plan pod kalendarz startów,' not in description.rsplit('\nPaceMind ', 1)[-1]

    @staticmethod
    def _recovering(day, events):
        return any(0 < (day - date.fromisoformat(e['date'])).days <= recovery_days(e) for e in events)

    @staticmethod
    def _type(row):
        return PlannedWorkoutEngine().build(date.fromisoformat(row['date']), row['title'], row['description']).workout_type
